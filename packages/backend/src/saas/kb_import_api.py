"""
Bijou AI - Knowledge Base: Listing Importer
============================================

Scrapes a property listing URL (PropertyGuru, iProperty, etc.) and converts it
into a formatted KB article using Gemini AI.

Also supports paste-text mode when scraping is blocked.

Routes:
    POST /api/kb/import-listing  - URL scrape mode
    POST /api/kb/import-text     - Paste text mode (fallback)

Author: W3J Consulting
"""

import logging
import os
import re
from datetime import datetime
from html.parser import HTMLParser
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, HttpUrl

from src.core.dashboard_api_simple import get_supabase, verify_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/kb", tags=["kb-import"])


# ---------------------------------------------------------------------------
# Request/Response Models
# ---------------------------------------------------------------------------


class ImportListingRequest(BaseModel):
    url: str  # Property listing URL
    note: Optional[str] = None  # Optional context note for AI ("This is our project")


class ImportTextRequest(BaseModel):
    text: str  # Raw pasted listing text
    title: Optional[str] = None
    note: Optional[str] = None


class ImportResponse(BaseModel):
    success: bool
    document_id: Optional[str] = None
    title: Optional[str] = None
    content_preview: Optional[str] = None
    message: str
    needs_paste: bool = False  # True when scraping blocked, frontend shows paste mode


# ---------------------------------------------------------------------------
# HTML Text Extractor (no external deps — uses stdlib html.parser)
# ---------------------------------------------------------------------------


class _TextExtractor(HTMLParser):
    """Extracts visible text from HTML, skipping script/style blocks."""

    SKIP_TAGS = {"script", "style", "noscript", "head", "meta", "link"}

    def __init__(self):
        super().__init__()
        self.text_parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag.lower() in self.SKIP_TAGS:
            self._skip_depth += 1

    def handle_endtag(self, tag):
        if tag.lower() in self.SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data):
        if self._skip_depth == 0:
            stripped = data.strip()
            if stripped:
                self.text_parts.append(stripped)


def _html_to_text(html: str) -> str:
    parser = _TextExtractor()
    parser.feed(html)
    raw = " ".join(parser.text_parts)
    # Collapse whitespace
    raw = re.sub(r"\s{3,}", "\n", raw)
    return raw[:12000]  # Cap at 12k chars — more than enough for Gemini


# ---------------------------------------------------------------------------
# Gemini Helper
# ---------------------------------------------------------------------------

GEMINI_PROMPT_TEMPLATE = """You are a real estate AI assistant.

Below is raw text scraped from a property listing page.
Convert it into a clean, structured knowledge article a WhatsApp chatbot can use to answer buyer/investor questions.

Use this format:
Property: <name or project>
Type: <Condo / Landed / Commercial / etc.>
Location: <address or area>
Price: <price or price range>
Size: <sqft / sqm range>
Bedrooms/Bathrooms: <if available>
Tenure: <Freehold / Leasehold>
Facilities: <bullet list>
Key Features: <bullet list>
Payment: <booking fee, loan details if any>
Developer/Agent: <name if stated>
Contact: <phone / email if stated>
Summary: <2-3 sentence pitch>

If any field is unavailable, omit it. Do not invent data.

Extra context from agent (if any): {note}

Raw listing text:
---
{raw_text}
---

Output only the formatted article, no preamble."""


async def _call_gemini(raw_text: str, note: str = "") -> str:
    """Call Gemini REST API to format raw listing text into a KB article."""
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not configured")

    prompt = GEMINI_PROMPT_TEMPLATE.format(
        raw_text=raw_text[:10000], note=note or "None provided"
    )

    async with httpx.AsyncClient(timeout=30) as client:
        res = await client.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}",
            json={"contents": [{"parts": [{"text": prompt}]}]},
        )
        res.raise_for_status()
        data = res.json()
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()


# ---------------------------------------------------------------------------
# Supabase Insert
# ---------------------------------------------------------------------------


async def _insert_kb_document(
    supabase,
    tenant_id: str,
    title: str,
    content: str,
    source_url: str = "",
) -> str:
    """Insert formatted KB article into knowledge_documents table. Returns document ID."""
    metadata = {
        "source": "listing_import",
        "source_url": source_url,
        "imported_at": datetime.utcnow().isoformat(),
        "word_count": len(content.split()),
    }
    result = (
        supabase.table("knowledge_documents")
        .insert(
            {
                "tenant_id": tenant_id,
                "filename": title,
                "file_type": "text/plain",
                "file_size_kb": round(len(content.encode()) / 1024, 2),
                "content_extracted": content,
                "uploaded_by": "listing_import",
                "uploaded_at": datetime.utcnow().isoformat(),
                "metadata": metadata,
            }
        )
        .execute()
    )
    if result.data and len(result.data) > 0:
        return result.data[0]["id"]
    raise RuntimeError("Insert returned no data")


# ---------------------------------------------------------------------------
# Route: URL scrape mode
# ---------------------------------------------------------------------------


@router.post("/import-listing", response_model=ImportResponse)
async def import_listing_url(
    req: ImportListingRequest,
    tenant_id: str = Depends(verify_session),
):
    """
    Scrape a property listing URL and add it to the AI knowledge base.

    Supports: PropertyGuru, iProperty, EdgeProp, Mudah, and any property site.
    Falls back to paste-text mode if the page is JS-rendered or blocked.
    """
    url = req.url.strip()
    if not url.startswith("http"):
        raise HTTPException(status_code=400, detail="Please provide a valid http/https URL")

    logger.info(f"[KB Import] tenant={tenant_id} scraping: {url}")

    # --- Step 1: Fetch the page ---
    raw_html = ""
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        }
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code != 200:
                logger.warning(f"[KB Import] HTTP {resp.status_code} for {url}")
                return ImportResponse(
                    success=False,
                    message=f"Could not fetch listing page (HTTP {resp.status_code}). Please paste the listing text instead.",
                    needs_paste=True,
                )
            raw_html = resp.text
    except Exception as e:
        logger.warning(f"[KB Import] Fetch error: {e}")
        return ImportResponse(
            success=False,
            message="Could not reach the listing page. Please paste the listing text instead.",
            needs_paste=True,
        )

    # --- Step 2: Extract visible text ---
    raw_text = _html_to_text(raw_html)
    if len(raw_text) < 200:
        # Likely a JS-only page
        return ImportResponse(
            success=False,
            message="This page requires JavaScript to load. Please paste the listing text directly instead.",
            needs_paste=True,
        )

    # --- Step 3: Gemini formats the text ---
    try:
        formatted = await _call_gemini(raw_text, note=req.note or "")
    except Exception as e:
        logger.error(f"[KB Import] Gemini error: {e}")
        raise HTTPException(status_code=500, detail="AI formatting failed. Please try again.")

    # --- Step 4: Build title ---
    title_match = re.search(r"Property:\s*(.+)", formatted)
    title = (
        title_match.group(1).strip()[:80]
        if title_match
        else f"Listing Import {datetime.utcnow().strftime('%d %b %Y')}"
    )

    # --- Step 5: Store in KB ---
    supabase = get_supabase()
    try:
        doc_id = await _insert_kb_document(supabase, tenant_id, title, formatted, source_url=url)
    except Exception as e:
        logger.error(f"[KB Import] DB insert error: {e}")
        raise HTTPException(status_code=500, detail="Failed to save to knowledge base.")

    logger.info(f"[KB Import] Saved doc_id={doc_id} title='{title}' tenant={tenant_id}")
    return ImportResponse(
        success=True,
        document_id=str(doc_id),
        title=title,
        content_preview=formatted[:300] + "..." if len(formatted) > 300 else formatted,
        message=f"✅ Listing imported and saved as '{title}'",
    )


# ---------------------------------------------------------------------------
# Route: Paste text mode (fallback / manual entry)
# ---------------------------------------------------------------------------


@router.post("/import-text", response_model=ImportResponse)
async def import_listing_text(
    req: ImportTextRequest,
    tenant_id: str = Depends(verify_session),
):
    """
    Parse pasted listing text and add it to the AI knowledge base.

    Use this when the listing URL is blocked or JS-rendered.
    """
    text = req.text.strip()
    if len(text) < 50:
        raise HTTPException(status_code=400, detail="Please paste more listing details (at least 50 characters).")

    logger.info(f"[KB Import Text] tenant={tenant_id} chars={len(text)}")

    # Gemini formats the raw pasted text
    try:
        formatted = await _call_gemini(text[:10000], note=req.note or "")
    except Exception as e:
        logger.error(f"[KB Import Text] Gemini error: {e}")
        raise HTTPException(status_code=500, detail="AI formatting failed. Please try again.")

    # Build title
    if req.title:
        title = req.title[:80]
    else:
        title_match = re.search(r"Property:\s*(.+)", formatted)
        title = (
            title_match.group(1).strip()[:80]
            if title_match
            else f"Listing {datetime.utcnow().strftime('%d %b %Y')}"
        )

    supabase = get_supabase()
    try:
        doc_id = await _insert_kb_document(supabase, tenant_id, title, formatted)
    except Exception as e:
        logger.error(f"[KB Import Text] DB insert error: {e}")
        raise HTTPException(status_code=500, detail="Failed to save to knowledge base.")

    return ImportResponse(
        success=True,
        document_id=str(doc_id),
        title=title,
        content_preview=formatted[:300] + "..." if len(formatted) > 300 else formatted,
        message=f"✅ Listing saved as '{title}'",
    )
