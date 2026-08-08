"""
Bijou AI - Knowledge Management API
====================================

REST API endpoints for tenant knowledge document management.

Endpoints:
- POST /api/knowledge/upload - Upload knowledge document
- GET /api/knowledge/list - List all documents for tenant
- DELETE /api/knowledge/{document_id} - Delete document
- GET /api/knowledge/combined - Get combined knowledge text

Author: W3J Consulting - Muhammad Nurunnabi (Jewel)
Version: 1.1.0  (Security: Added verify_session auth on all endpoints)
Date: 2026-02-21
"""

import logging
import os
import uuid as uuid_lib
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Header, HTTPException, Query, UploadFile
from pydantic import BaseModel
from src.saas.knowledge_upload import KnowledgeUploader
from src.core.dashboard_api_simple import verify_session

from supabase import create_client

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


# ════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ════════════════════════════════════════════════════════════════


def get_supabase():
    """Get Supabase admin client"""
    supabase_url = os.getenv("SUPABASE_URL", "").strip('"')
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY", "").strip('"')

    if not supabase_url or not supabase_key:
        raise RuntimeError("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY")

    return create_client(supabase_url, supabase_key)


async def get_tenant_id(
    tenant_id: Optional[str] = Query(None, description="Tenant UUID"),
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
) -> str:
    """
    Resolve tenant_id from query param OR X-Tenant-ID header.

    The frontend may send either:
    - ``?tenant_id=<uuid>`` query parameter  (preferred)
    - ``X-Tenant-ID: <uuid>`` request header  (legacy / curl)

    Args:
        tenant_id: UUID passed as a URL query parameter.
        x_tenant_id: UUID passed in the X-Tenant-ID HTTP header.

    Returns:
        The resolved tenant UUID string.

    Raises:
        HTTPException 422: If neither source provides a value.
    """
    tid = tenant_id or x_tenant_id
    if not tid:
        raise HTTPException(
            status_code=422,
            detail=(
                "tenant_id is required — supply it as a query parameter "
                "(?tenant_id=<uuid>) or as the X-Tenant-ID request header."
            ),
        )
    return tid


# ════════════════════════════════════════════════════════════════
# PYDANTIC MODELS
# ════════════════════════════════════════════════════════════════


class UploadResponse(BaseModel):
    """Response after document upload"""

    success: bool
    document_id: str
    filename: str
    file_type: str
    content_length: int
    message: str


class DocumentInfo(BaseModel):
    """Information about a knowledge document"""

    id: str
    filename: str
    file_type: str
    content_length: int
    uploaded_at: str
    metadata: dict


class DocumentListResponse(BaseModel):
    """List of documents for a tenant"""

    success: bool
    tenant_id: str
    documents: List[DocumentInfo]
    total_count: int


class DeleteResponse(BaseModel):
    """Response after document deletion"""

    success: bool
    document_id: str
    message: str


class CombinedKnowledgeResponse(BaseModel):
    """Combined knowledge text from all documents"""

    success: bool
    tenant_id: str
    combined_text: str
    document_count: int
    total_length: int


# ════════════════════════════════════════════════════════════════
# API ENDPOINTS
# ════════════════════════════════════════════════════════════════


@router.post("/upload", response_model=UploadResponse)
async def upload_knowledge_document(
    file: UploadFile = File(...),
    tenant_id: str = Depends(verify_session),
):
    """
    Upload a knowledge document for a tenant.

    Supported formats: PDF, DOCX, TXT, MD, CSV, JSON

    Authentication:
        Requires a valid Supabase session (Bearer token) or legacy dashboard token.
        The tenant is resolved from the authenticated session — callers cannot
        supply or override the tenant identity.

    Returns:
        UploadResponse with document details
    """
    try:
        # Sanitize filename to prevent path traversal (M-05)
        raw_filename = file.filename or "upload"
        safe_filename = os.path.basename(raw_filename)
        if not safe_filename:
            safe_filename = "upload"

        logger.info(
            f"📤 Uploading knowledge document for tenant {tenant_id}: {safe_filename}"
        )

        supabase = get_supabase()
        knowledge_uploader = KnowledgeUploader(supabase_client=supabase)

        # Validate tenant exists
        tenant_result = (
            supabase.table("tenants").select("id").eq("id", tenant_id).execute()
        )
        if not tenant_result.data:
            raise HTTPException(status_code=404, detail="Tenant not found")

        # Read file content
        file_content = await file.read()

        # Upload using KnowledgeUploader
        result = await knowledge_uploader.upload_document(
            tenant_id=tenant_id, filename=safe_filename, file_content=file_content
        )

        if result["success"]:
            logger.info(f"✅ Document uploaded: {result['document_id']}")
            content_length = result.get("text_length")
            if content_length is None:
                content_length = int(result.get("file_size_kb", 0) * 1024)
            return UploadResponse(
                success=True,
                document_id=result["document_id"],
                filename=result["filename"],
                file_type=result["file_type"],
                content_length=content_length,
                message=f"Document '{safe_filename}' uploaded successfully",
            )
        else:
            logger.error(f"❌ Upload failed: {result.get('error')}")
            raise HTTPException(
                status_code=500, detail=result.get("error", "Upload failed")
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error uploading document for tenant {tenant_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred during upload. Please try again.")


@router.get("/list", response_model=DocumentListResponse)
async def list_knowledge_documents(tenant_id: str = Depends(verify_session)):
    """
    List all knowledge documents for a tenant.

    Authentication:
        Requires a valid Supabase session (Bearer token) or legacy dashboard token.
        The tenant is resolved from the authenticated session.

    Returns:
        DocumentListResponse with list of documents
    """
    try:
        logger.info(f"📋 Listing knowledge documents for tenant {tenant_id}")

        supabase = get_supabase()

        # Query knowledge_documents table
        result = (
            supabase.table("knowledge_documents")
            .select(
                "id, filename, file_type, file_size_kb, uploaded_at, metadata, content_extracted"
            )
            .eq("tenant_id", tenant_id)
            .order("uploaded_at", desc=True)
            .execute()
        )

        documents = []
        for doc in result.data:
            content_length = doc.get("content_length")
            if content_length is None:
                file_size_kb = doc.get("file_size_kb")
                if file_size_kb is not None:
                    content_length = int(file_size_kb * 1024)
            if content_length is None:
                content_length = len(doc.get("content_extracted") or doc.get("content") or "")
            documents.append(
                DocumentInfo(
                    id=doc["id"],
                    filename=doc["filename"],
                    file_type=doc["file_type"],
                    content_length=content_length,
                    uploaded_at=doc["uploaded_at"],
                    metadata=doc.get("metadata", {}),
                )
            )

        logger.info(f"✅ Found {len(documents)} documents for tenant {tenant_id}")

        return DocumentListResponse(
            success=True,
            tenant_id=tenant_id,
            documents=documents,
            total_count=len(documents),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error listing documents for tenant {tenant_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred while listing documents.")


@router.delete("/{document_id}", response_model=DeleteResponse)
async def delete_knowledge_document(
    document_id: str,
    tenant_id: str = Depends(verify_session),
):
    """
    Delete a knowledge document.

    Path Parameters:
        document_id: Document UUID

    Authentication:
        Requires a valid Supabase session (Bearer token) or legacy dashboard token.
        The tenant is resolved from the authenticated session — callers cannot
        supply or override the tenant identity.

    Returns:
        DeleteResponse with success status
    """
    # Validate document_id is a well-formed UUID (M-03)
    try:
        uuid_lib.UUID(document_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid document_id format — must be a UUID")

    try:
        logger.info(f"🗑️ Deleting document {document_id} for tenant {tenant_id}")

        supabase = get_supabase()

        # Verify document belongs to this tenant (ownership check)
        doc_result = (
            supabase.table("knowledge_documents")
            .select("id, filename")
            .eq("id", document_id)
            .eq("tenant_id", tenant_id)
            .execute()
        )

        if not doc_result.data:
            raise HTTPException(
                status_code=404,
                detail="Document not found",
            )

        filename = doc_result.data[0]["filename"]

        # C-03 FIX: Always include tenant_id in the DELETE clause — the delete must
        # be self-defending and cannot rely solely on the prior SELECT ownership check.
        delete_result = (
            supabase.table("knowledge_documents")
            .delete()
            .eq("id", document_id)
            .eq("tenant_id", tenant_id)
            .execute()
        )

        if not delete_result.data:
            logger.error(
                f"❌ Delete may have failed for doc {document_id} tenant {tenant_id}"
            )
            raise HTTPException(status_code=500, detail="Delete operation failed")

        logger.info(f"✅ Deleted document {document_id}: {filename}")

        return DeleteResponse(
            success=True,
            document_id=document_id,
            message=f"Document '{filename}' deleted successfully",
        )


    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error deleting document {document_id} for tenant {tenant_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred during deletion.")


@router.get("/combined", response_model=CombinedKnowledgeResponse)
async def get_combined_knowledge(tenant_id: str = Depends(verify_session)):
    """
    Get combined knowledge text from all documents for a tenant.

    This is used to inject knowledge into the AI's context.

    Authentication:
        Requires a valid Supabase session (Bearer token) or legacy dashboard token.
        The tenant is resolved from the authenticated session.

    Returns:
        CombinedKnowledgeResponse with combined text
    """
    try:
        logger.info(f"📚 Fetching combined knowledge for tenant {tenant_id}")

        supabase = get_supabase()
        knowledge_uploader = KnowledgeUploader(supabase_client=supabase)

        # Get combined knowledge using KnowledgeUploader
        combined_text = await knowledge_uploader.get_combined_knowledge(tenant_id)

        # Count documents
        doc_result = (
            supabase.table("knowledge_documents")
            .select("id", count="exact")
            .eq("tenant_id", tenant_id)
            .execute()
        )

        document_count = doc_result.count if doc_result.count else 0

        logger.info(
            f"✅ Combined knowledge: {len(combined_text)} chars from {document_count} documents"
        )

        return CombinedKnowledgeResponse(
            success=True,
            tenant_id=tenant_id,
            combined_text=combined_text,
            document_count=document_count,
            total_length=len(combined_text),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting combined knowledge for tenant {tenant_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred while fetching knowledge.")


# ════════════════════════════════════════════════════════════════
# HEALTH CHECK
# ════════════════════════════════════════════════════════════════


@router.get("/health")
async def knowledge_api_health():
    """Health check for knowledge API"""
    try:
        supabase = get_supabase()
        return {
            "status": "healthy",
            "service": "knowledge_api",
            "supabase_connected": True,
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "knowledge_api",
            "error": str(e),
        }
