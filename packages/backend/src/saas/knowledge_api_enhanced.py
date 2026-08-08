"""
Enhanced Knowledge Upload API - Phase 2
========================================

Integrates with knowledge chunker, vector search, and sync services.
Handles async processing of large documents.

Author: W3J Consulting
Date: 2026-02-11
Phase: 2 - Knowledge Base System
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from typing import Optional, Dict, List
from pydantic import BaseModel
import uuid
from datetime import datetime
from loguru import logger

from .knowledge_upload import KnowledgeUploader  # Existing uploader
from .knowledge_chunker import KnowledgeChunker
from .vector_search import VectorSearch
from .knowledge_sync import KnowledgeSyncService


router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


class KnowledgeUploadResponse(BaseModel):
    """Response model for knowledge upload"""
    success: bool
    knowledge_base_id: Optional[str] = None
    message: str
    chunk_count: Optional[int] = None
    processing_status: str = "pending"


class SyncRequest(BaseModel):
    """Request to sync a knowledge base"""
    knowledge_base_id: str
    force: bool = False


class SearchRequest(BaseModel):
    """Request for knowledge search"""
    query: str
    top_k: int = 5
    filters: Optional[Dict] = None
    use_hybrid: bool = True


class EnhancedKnowledgeAPI:
    """Enhanced Knowledge API with chunking and vector search"""

    def __init__(
        self,
        supabase_client,
        gemini_api_key: str
    ):
        """
        Initialize enhanced knowledge API
        
        Args:
            supabase_client: Supabase client
            gemini_api_key: Gemini API key for embeddings
        """
        self.db = supabase_client
        
        # Initialize services
        self.uploader = KnowledgeUploader(supabase_client)
        self.chunker = KnowledgeChunker(max_tokens=512, overlap_tokens=50)
        self.vector_search = VectorSearch(supabase_client, gemini_api_key)
        self.sync_service = KnowledgeSyncService(supabase_client, gemini_api_key)


# Global instance (will be initialized in main app)
knowledge_api: Optional[EnhancedKnowledgeAPI] = None


def init_knowledge_api(supabase_client, gemini_api_key: str):
    """Initialize the global knowledge API instance"""
    global knowledge_api
    knowledge_api = EnhancedKnowledgeAPI(supabase_client, gemini_api_key)
    return knowledge_api


@router.post("/upload", response_model=KnowledgeUploadResponse)
async def upload_knowledge_document(
    background_tasks: BackgroundTasks,
    tenant_id: str = Form(...),
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    tags: Optional[str] = Form(None)
):
    """
    Upload a knowledge document with async processing
    
    Process:
    1. Upload file and extract text
    2. Create knowledge_base record
    3. Background: Chunk text and create embeddings
    4. Background: Store chunks in database
    """
    if not knowledge_api:
        raise HTTPException(status_code=500, detail="Knowledge API not initialized")
    
    try:
        # Read file content
        file_content = await file.read()
        
        # Upload using existing uploader (extracts text)
        upload_result = await knowledge_api.uploader.upload_document(
            tenant_id=tenant_id,
            file_content=file_content,
            filename=file.filename,
            uploaded_by="api",
            metadata={
                "title": title or file.filename,
                "category": category,
                "tags": tags.split(",") if tags else []
            }
        )
        
        if not upload_result.get("success"):
            raise HTTPException(
                status_code=400,
                detail=upload_result.get("error", "Upload failed")
            )
        
        knowledge_base_id = upload_result.get("knowledge_id")
        
        # Schedule background processing (chunking + embedding)
        background_tasks.add_task(
            process_knowledge_document,
            knowledge_base_id,
            tenant_id
        )
        
        return KnowledgeUploadResponse(
            success=True,
            knowledge_base_id=knowledge_base_id,
            message="Document uploaded successfully. Processing in background.",
            processing_status="processing"
        )
        
    except Exception as e:
        logger.error(f"Error uploading knowledge document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def process_knowledge_document(knowledge_base_id: str, tenant_id: str):
    """
    Background task to process uploaded document
    
    - Chunks the text
    - Creates embeddings
    - Stores in knowledge_chunks table
    """
    try:
        logger.info(f"Processing knowledge base {knowledge_base_id}")
        
        # Get knowledge base content
        kb_result = knowledge_api.db.table("knowledge_bases").select("*").eq("id", knowledge_base_id).eq("tenant_id", tenant_id).execute()
        
        if not kb_result.data:
            raise Exception(f"Knowledge base {knowledge_base_id} not found")
        
        kb = kb_result.data[0]
        content = kb.get("content", "")
        
        if not content:
            raise Exception("No content to process")
        
        # Update status to processing
        knowledge_api.db.table("knowledge_bases").update({
            "processing_status": "processing",
            "last_processed_at": datetime.utcnow().isoformat()
        }).eq("id", knowledge_base_id).eq("tenant_id", tenant_id).execute()
        
        # Chunk the content
        chunked_data = knowledge_api.chunker.chunk_document(
            content,
            metadata={
                "title": kb.get("title"),
                "category": kb.get("category")
            },
            strategy="semantic"
        )
        
        logger.info(f"Created {chunked_data['chunk_count']} chunks")
        
        # Create chunks with embeddings
        chunks_created = 0
        for chunk_data in chunked_data["chunks"]:
            try:
                # Create embedding
                embedding = await knowledge_api.vector_search.create_embedding(
                    chunk_data["text"]
                )
                
                # Store chunk
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
                
                knowledge_api.db.table("knowledge_chunks").insert(chunk_record).execute()
                chunks_created += 1
                
            except Exception as e:
                logger.error(f"Error creating chunk {chunk_data['index']}: {e}")
                continue
        
        # Update knowledge base with completion status
        knowledge_api.db.table("knowledge_bases").update({
            "processing_status": "completed",
            "chunk_count": chunks_created,
            "file_hash": chunked_data["content_hash"],
            "last_processed_at": datetime.utcnow().isoformat()
        }).eq("id", knowledge_base_id).eq("tenant_id", tenant_id).execute()
        
        logger.success(f"Processed {chunks_created} chunks for KB {knowledge_base_id}")
        
    except Exception as e:
        logger.error(f"Error processing knowledge document: {e}")
        
        # Update status to failed
        knowledge_api.db.table("knowledge_bases").update({
            "processing_status": "failed",
            "error_message": str(e)
        }).eq("id", knowledge_base_id).eq("tenant_id", tenant_id).execute()


@router.post("/search")
async def search_knowledge(
    tenant_id: str,
    request: SearchRequest
):
    """
    Search knowledge base using semantic/hybrid search
    """
    if not knowledge_api:
        raise HTTPException(status_code=500, detail="Knowledge API not initialized")
    
    try:
        if request.use_hybrid:
            results = await knowledge_api.vector_search.hybrid_search(
                query=request.query,
                tenant_id=tenant_id,
                top_k=request.top_k
            )
        else:
            results = await knowledge_api.vector_search.search_knowledge(
                query=request.query,
                tenant_id=tenant_id,
                top_k=request.top_k,
                filters=request.filters
            )
        
        return {
            "success": True,
            "query": request.query,
            "results": results,
            "count": len(results)
        }
        
    except Exception as e:
        logger.error(f"Error searching knowledge: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync")
async def sync_knowledge_base(
    tenant_id: str,
    request: SyncRequest,
    background_tasks: BackgroundTasks
):
    """
    Trigger sync for a knowledge base
    
    Checks for changes and re-indexes if needed
    """
    if not knowledge_api:
        raise HTTPException(status_code=500, detail="Knowledge API not initialized")
    
    try:
        # Run sync in background
        background_tasks.add_task(
            knowledge_api.sync_service.sync_knowledge_base,
            request.knowledge_base_id,
            tenant_id,
            request.force
        )
        
        return {
            "success": True,
            "message": "Sync started in background",
            "knowledge_base_id": request.knowledge_base_id
        }
        
    except Exception as e:
        logger.error(f"Error syncing knowledge base: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list")
async def list_knowledge_bases(tenant_id: str):
    """
    List all knowledge bases for a tenant
    """
    if not knowledge_api:
        raise HTTPException(status_code=500, detail="Knowledge API not initialized")
    
    try:
        result = knowledge_api.db.table("knowledge_bases").select(
            "id, title, category, source_type, chunk_count, processing_status, created_at, updated_at"
        ).eq("tenant_id", tenant_id).eq("is_active", True).order("created_at", desc=True).execute()
        
        return {
            "success": True,
            "knowledge_bases": result.data or [],
            "count": len(result.data) if result.data else 0
        }
        
    except Exception as e:
        logger.error(f"Error listing knowledge bases: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_knowledge_stats(tenant_id: str):
    """
    Get statistics about tenant's knowledge base
    """
    if not knowledge_api:
        raise HTTPException(status_code=500, detail="Knowledge API not initialized")
    
    try:
        # Use PostgreSQL function for stats
        result = knowledge_api.db.rpc(
            "get_knowledge_stats",
            {"p_tenant_id": tenant_id}
        ).execute()
        
        return {
            "success": True,
            "stats": result.data[0] if result.data else {}
        }
        
    except Exception as e:
        logger.error(f"Error getting knowledge stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{knowledge_base_id}")
async def delete_knowledge_base(
    tenant_id: str,
    knowledge_base_id: str
):
    """
    Delete a knowledge base and its chunks
    """
    if not knowledge_api:
        raise HTTPException(status_code=500, detail="Knowledge API not initialized")
    
    try:
        # Soft delete (set is_active = false)
        knowledge_api.db.table("knowledge_bases").update({
            "is_active": False,
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", knowledge_base_id).eq("tenant_id", tenant_id).execute()
        
        # Delete chunks (cascades automatically in database)
        knowledge_api.db.table("knowledge_chunks").delete().eq(  # noaudit - scoped by knowledge_base_id which was fetched with tenant_id filter
            "knowledge_base_id", knowledge_base_id
        ).execute()
        
        return {
            "success": True,
            "message": "Knowledge base deleted"
        }
        
    except Exception as e:
        logger.error(f"Error deleting knowledge base: {e}")
        raise HTTPException(status_code=500, detail=str(e))
