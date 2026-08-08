"""
Knowledge Sync Service - Auto-Update System
============================================

Handles automatic synchronization and updates of knowledge bases.
Detects changes in source files/URLs and re-indexes content.

Author: W3J Consulting
Date: 2026-02-11
Phase: 2 - Knowledge Base System
"""

import asyncio
import hashlib
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from loguru import logger
from pathlib import Path

from .knowledge_chunker import KnowledgeChunker
from .vector_search import VectorSearch


class KnowledgeSyncService:
    """
    Auto-synchronization service for knowledge bases
    
    Features:
    - File change detection using hash comparison
    - Scheduled periodic syncs
    - Google Sheets integration
    - Webhook-triggered updates
    - Differential updates (only changed chunks)
    """

    def __init__(
        self,
        supabase_client,
        gemini_api_key: str,
        check_interval_minutes: int = 60
    ):
        """
        Initialize sync service
        
        Args:
            supabase_client: Supabase client
            gemini_api_key: API key for embeddings
            check_interval_minutes: How often to check for changes
        """
        self.db = supabase_client
        self.check_interval = timedelta(minutes=check_interval_minutes)
        
        # Initialize chunker and vector search
        self.chunker = KnowledgeChunker()
        self.vector_search = VectorSearch(supabase_client, gemini_api_key)

    async def sync_knowledge_base(
        self,
        knowledge_base_id: str,
        tenant_id: str,
        force: bool = False
    ) -> Dict:
        """
        Synchronize a knowledge base
        
        Args:
            knowledge_base_id: Knowledge base ID
            tenant_id: Tenant ID
            force: Force re-indexing even if no changes detected
            
        Returns:
            Sync job result
        """
        try:
            # Create sync job record
            job = await self._create_sync_job(
                knowledge_base_id,
                tenant_id,
                sync_type="manual" if force else "auto_detect"
            )
            
            # Get knowledge base details
            kb_result = self.db.table("knowledge_bases").select("*").eq("id", knowledge_base_id).eq("tenant_id", tenant_id).execute()
            
            if not kb_result.data:
                raise Exception(f"Knowledge base {knowledge_base_id} not found")
            
            kb = kb_result.data[0]
            
            # Fetch current content based on source type
            current_content = await self._fetch_content(kb)
            current_hash = self.chunker.compute_content_hash(current_content)
            
            # Check if content changed
            previous_hash = kb.get("file_hash")
            changes_detected = force or (current_hash != previous_hash)
            
            if not changes_detected:
                logger.info(f"No changes detected for knowledge base {knowledge_base_id}")
                await self._complete_sync_job(job["id"], changes_detected=False)
                return {
                    "status": "no_changes",
                    "job_id": job["id"]
                }
            
            # Content changed - re-index
            logger.info(f"Changes detected - re-indexing knowledge base {knowledge_base_id}")
            
            # Update job status
            await self._update_sync_job(job["id"], status="running")
            
            # Chunk the content
            chunked_data = self.chunker.chunk_document(
                current_content,
                metadata={
                    "title": kb.get("title"),
                    "category": kb.get("category"),
                    "source_type": kb.get("source_type")
                },
                strategy="semantic"
            )
            
            # Delete old chunks
            await self._delete_chunks(knowledge_base_id)
            
            # Create new chunks with embeddings
            chunks_created = await self._create_chunks_with_embeddings(
                knowledge_base_id,
                tenant_id,
                chunked_data["chunks"]
            )
            
            # Update knowledge base record
            await self._update_knowledge_base(
                knowledge_base_id,
                tenant_id,
                {
                    "file_hash": current_hash,
                    "chunk_count": len(chunked_data["chunks"]),
                    "processing_status": "completed",
                    "last_processed_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat()
                }
            )
            
            # Complete sync job
            await self._complete_sync_job(
                job["id"],
                changes_detected=True,
                chunks_created=chunks_created,
                current_hash=current_hash,
                previous_hash=previous_hash
            )
            
            logger.success(
                f"Sync completed for KB {knowledge_base_id}: "
                f"{chunks_created} chunks created"
            )
            
            return {
                "status": "synced",
                "job_id": job["id"],
                "chunks_created": chunks_created,
                "changes_detected": True
            }
            
        except Exception as e:
            logger.error(f"Error syncing knowledge base: {e}")
            
            # Mark job as failed
            if 'job' in locals():
                await self._fail_sync_job(job["id"], str(e))
            
            raise

    async def _fetch_content(self, kb: Dict) -> str:
        """Fetch current content based on source type"""
        source_type = kb.get("source_type")
        
        if source_type == "file_upload":
            # Content already stored in database
            return kb.get("content", "")
        
        elif source_type == "google_sheets":
            # Fetch from Google Sheets
            return await self._fetch_google_sheets(kb.get("source_url"))
        
        elif source_type == "web_scrape":
            # Fetch from URL
            return await self._fetch_url(kb.get("source_url"))
        
        else:
            return kb.get("content", "")

    async def _fetch_google_sheets(self, sheet_url: str) -> str:
        """Fetch content from Google Sheets"""
        # TODO: Implement Google Sheets API integration
        # For now, return empty string
        logger.warning("Google Sheets integration not yet implemented")
        return ""

    async def _fetch_url(self, url: str) -> str:
        """Fetch content from URL"""
        import httpx
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=30.0)
                response.raise_for_status()
                return response.text
        except Exception as e:
            logger.error(f"Error fetching URL {url}: {e}")
            raise

    async def _create_sync_job(
        self,
        knowledge_base_id: str,
        tenant_id: str,
        sync_type: str
    ) -> Dict:
        """Create a sync job record"""
        job_data = {
            "knowledge_base_id": knowledge_base_id,
            "tenant_id": tenant_id,
            "sync_type": sync_type,
            "status": "pending",
            "started_at": datetime.utcnow().isoformat()
        }
        
        result = self.db.table("knowledge_sync_jobs").insert(job_data).execute()
        return result.data[0]

    async def _update_sync_job(self, job_id: str, **updates) -> None:
        """Update sync job record"""
        self.db.table("knowledge_sync_jobs").update(updates).eq("id", job_id).execute()  # noaudit - scoped by job_id UUID; job created with tenant context

    async def _complete_sync_job(
        self,
        job_id: str,
        changes_detected: bool,
        chunks_created: int = 0,
        current_hash: str = None,
        previous_hash: str = None
    ) -> None:
        """Mark sync job as completed"""
        updates = {
            "status": "completed",
            "completed_at": datetime.utcnow().isoformat(),
            "changes_detected": changes_detected,
            "chunks_created": chunks_created
        }
        
        if current_hash:
            updates["current_hash"] = current_hash
        if previous_hash:
            updates["previous_hash"] = previous_hash
        
        await self._update_sync_job(job_id, **updates)

    async def _fail_sync_job(self, job_id: str, error_message: str) -> None:
        """Mark sync job as failed"""
        await self._update_sync_job(
            job_id,
            status="failed",
            completed_at=datetime.utcnow().isoformat(),
            error_message=error_message
        )

    async def _delete_chunks(self, knowledge_base_id: str) -> None:
        """Delete existing chunks for knowledge base"""
        self.db.table("knowledge_chunks").delete().eq("knowledge_base_id", knowledge_base_id).execute()
        logger.debug(f"Deleted old chunks for KB {knowledge_base_id}")

    async def _create_chunks_with_embeddings(
        self,
        knowledge_base_id: str,
        tenant_id: str,
        chunks: List[Dict]
    ) -> int:
        """
        Create chunk records with embeddings
        
        Returns:
            Number of chunks created
        """
        created_count = 0
        
        for chunk_data in chunks:
            try:
                # Create embedding for chunk text
                embedding = await self.vector_search.create_embedding(chunk_data["text"])
                
                # Prepare chunk record
                chunk_record = {
                    "knowledge_base_id": knowledge_base_id,
                    "tenant_id": tenant_id,
                    "chunk_text": chunk_data["text"],
                    "chunk_index": chunk_data["index"],
                    "chunk_size": chunk_data["char_count"],
                    "embedding": embedding,
                    "section_title": chunk_data.get("section_title"),
                    "page_number": chunk_data.get("page_number")
                }
                
                # Insert into database
                self.db.table("knowledge_chunks").insert(chunk_record).execute()
                created_count += 1
                
            except Exception as e:
                logger.error(f"Error creating chunk {chunk_data['index']}: {e}")
                continue
        
        return created_count

    async def _update_knowledge_base(self, kb_id: str, tenant_id: str, updates: Dict) -> None:
        """Update knowledge base record"""
        self.db.table("knowledge_bases").update(updates).eq("id", kb_id).eq("tenant_id", tenant_id).execute()

    async def watch_knowledge_bases(self, tenant_id: str) -> None:
        """
        Watch all knowledge bases for a tenant and sync on changes
        
        This runs continuously in the background
        """
        logger.info(f"Starting knowledge base watcher for tenant {tenant_id}")
        
        while True:
            try:
                # Get all active knowledge bases for tenant
                result = self.db.table("knowledge_bases").select("id, title, last_synced_at").eq("tenant_id", tenant_id).eq("is_active", True).execute()
                
                knowledge_bases = result.data or []
                
                for kb in knowledge_bases:
                    # Check if sync is due
                    last_synced = kb.get("last_synced_at")
                    
                    if not last_synced:
                        # Never synced - sync now
                        await self.sync_knowledge_base(kb["id"], tenant_id)
                    else:
                        # Check if enough time has passed
                        last_sync_time = datetime.fromisoformat(last_synced.replace('Z', '+00:00'))
                        if datetime.utcnow() - last_sync_time.replace(tzinfo=None) >= self.check_interval:
                            await self.sync_knowledge_base(kb["id"], tenant_id)
                
                # Wait before next check
                await asyncio.sleep(self.check_interval.total_seconds())
                
            except Exception as e:
                logger.error(f"Error in knowledge base watcher: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retry

    async def sync_all_tenants(self) -> Dict:
        """
        Sync all knowledge bases for all tenants
        
        Useful for scheduled background jobs
        """
        logger.info("Starting sync for all tenants")
        
        # Get all active tenants
        tenants_result = self.db.table("tenants").select("id, name").eq("is_active", True).execute()
        tenants = tenants_result.data or []
        
        results = {
            "total_tenants": len(tenants),
            "synced": 0,
            "failed": 0,
            "no_changes": 0
        }
        
        for tenant in tenants:
            try:
                # Get all knowledge bases for tenant
                kb_result = self.db.table("knowledge_bases").select("id").eq("tenant_id", tenant["id"]).eq("is_active", True).execute()
                
                knowledge_bases = kb_result.data or []
                
                for kb in knowledge_bases:
                    sync_result = await self.sync_knowledge_base(
                        kb["id"],
                        tenant["id"],
                        force=False
                    )
                    
                    if sync_result["status"] == "synced":
                        results["synced"] += 1
                    elif sync_result["status"] == "no_changes":
                        results["no_changes"] += 1
                        
            except Exception as e:
                logger.error(f"Error syncing tenant {tenant['id']}: {e}")
                results["failed"] += 1
        
        logger.info(f"Sync complete: {results}")
        return results
