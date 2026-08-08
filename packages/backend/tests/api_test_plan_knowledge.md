# Knowledge API — Test Plan & Root Cause Report

**Generated:** 2026-02-21  
**Agent:** api-tester  
**Staging URL:** https://bijou-staging.fly.dev  
**Test Tenant:** `29d48db4-075f-45ee-8c00-a57f8fd3016a`

---

## 1. Root Cause — CONFIRMED ✅

### The Bug

> **All knowledge endpoints use `X-Tenant-ID` as a *mandatory FastAPI header parameter*. The frontend never sends this header — it only sends `Authorization: Bearer <jwt>`. FastAPI rejects every request with `422 Unprocessable Entity` before any business logic runs.**

### Exact FastAPI Declaration (current, broken)

```python
# src/saas/knowledge_api.py  — lines 173–174
@router.get("/list", response_model=DocumentListResponse)
async def list_knowledge_documents(
    tenant_id: str = Header(..., alias="X-Tenant-ID")   # ← MANDATORY header
):
```

When declared with `Header(..., alias="X-Tenant-ID")`:
- `...` means **required / non-optional**
- FastAPI validates headers **before** calling the function
- Missing header → immediate `422` with body:
  ```json
  {"detail":[{"type":"missing","loc":["header","X-Tenant-ID"],"msg":"Field required","input":null}]}
  ```

### All Four Endpoints Affected

| Endpoint | Line | Same pattern? |
|---|---|---|
| `GET  /api/knowledge/list` | 174 | YES |
| `POST /api/knowledge/upload` | 111 | YES (`X-Tenant-ID` + `file`) |
| `DELETE /api/knowledge/{id}` | 236 | YES |
| `GET  /api/knowledge/combined` | 291 | YES |

`GET /api/knowledge/health` is **NOT affected** (no auth required, works fine).

---

## 2. Live HTTP Status Codes (Verified on Staging)

### Test 1 — `GET /api/knowledge/list` without `X-Tenant-ID`
```
curl "https://bijou-staging.fly.dev/api/knowledge/list?tenant_id=29d48db4-..."
```
**HTTP 422 Unprocessable Entity**  
```json
{"detail":[{"type":"missing","loc":["header","X-Tenant-ID"],"msg":"Field required","input":null}]}
```
→ **Confirms root cause. The `?tenant_id=` query param is completely ignored.**

---

### Test 2 — `GET /api/knowledge/list` WITH `X-Tenant-ID` header
```
curl -H "X-Tenant-ID: 29d48db4-..." "https://bijou-staging.fly.dev/api/knowledge/list?tenant_id=29d48db4-..."
```
**HTTP 200 OK**  
```json
{"success":true,"tenant_id":"29d48db4-075f-45ee-8c00-a57f8fd3016a","documents":[],"total_count":0}
```
→ Endpoint works correctly once header is present. DB query is fine. **Zero documents** (no uploads yet).

---

### Test 3 — `POST /api/knowledge/upload` without headers
```
curl -X POST "https://bijou-staging.fly.dev/api/knowledge/upload" \
  -H "Content-Type: application/json" \
  -d '{"title":"test","content":"test content"}'
```
**HTTP 422 Unprocessable Entity**  
```json
{"detail":[
  {"type":"missing","loc":["header","X-Tenant-ID"],"msg":"Field required","input":null},
  {"type":"missing","loc":["body","file"],"msg":"Field required","input":null}
]}
```
→ Two errors: missing `X-Tenant-ID` header AND wrong body format. Upload expects `multipart/form-data` with a `file` field, not raw JSON.

---

### Test 4 — `GET /api/dashboard/health`
```
curl "https://bijou-staging.fly.dev/api/dashboard/health"
```
**HTTP 404 Not Found**  
```json
{"detail":"Not Found"}
```
→ No `/health` route exists on the dashboard router. The knowledge router at `/api/knowledge/health` returns **200**.

---

### Test 5 — `GET /api/dashboard/messages/{chat_jid}` (messages endpoint)
```
curl "https://bijou-staging.fly.dev/api/dashboard/messages/104600321409056@lid?tenant_id=29d48db4-..."
```
**HTTP 200 OK** — Returns full message history (14 messages).  
→ This endpoint is **working correctly** using `verify_session` pattern (accepts `?tenant_id=` query param with no auth token in REQUIRE_DASHBOARD_TOKEN=false mode).

---

### Test 6 — `GET /api/knowledge/health`
```
curl "https://bijou-staging.fly.dev/api/knowledge/health"
```
**HTTP 200 OK**  
```json
{"status":"healthy","service":"knowledge_api","supabase_connected":true}
```
→ Knowledge API is live and Supabase is connected.

---

### Test 7 — `GET /api/knowledge/combined` WITH `X-Tenant-ID`
```
curl -H "X-Tenant-ID: 29d48db4-..." "https://bijou-staging.fly.dev/api/knowledge/combined"
```
**HTTP 200 OK**  
```json
{"success":true,"tenant_id":"29d48db4-075f-45ee-8c00-a57f8fd3016a","combined_text":"","document_count":0,"total_length":0}
```
→ Works once header is provided.

---

## 3. Auth Mechanism Comparison

### `knowledge_api.py` (broken) — Raw header extraction
```python
# No Supabase JWT validation. No session. No `verify_session`.
# Just a FastAPI Header() parameter — mandatory, no fallback.
tenant_id: str = Header(..., alias="X-Tenant-ID")
```
- No `Authorization: Bearer <jwt>` handling
- No `?tenant_id=` query param fallback
- No `verify_session` dependency
- **Frontend sends NONE of what this expects**

### `dashboard_api_simple.py` (working) — `verify_session` dependency
```python
# verify_session (lines 134–206) accepts ALL of:
#   1. X-Tenant-ID header (preferred)
#   2. ?tenant_id= query param
#   3. Authorization: Bearer <jwt> (extracts tenant_id from user.user_metadata)
#   4. ?token= legacy dashboard token

async def verify_session(
    tenant_id: Optional[str] = Query(None),
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),  # Optional!
    token: Optional[str] = Query(None),
    user: Optional[Any] = Depends(get_current_user),
) -> str:
    ...

# Used as:
@router.get("/stats")
async def get_dashboard_stats(tenant_id: str = Depends(verify_session)):
```

**Key difference:** In `verify_session`, `X-Tenant-ID` is `Optional[str] = Header(None, ...)` — it is **never required** on its own. The function accepts any of 4 auth paths and synthesizes `tenant_id` from whichever is present. The knowledge router uses `Header(...)` which makes it **always required**.

---

## 4. Field Name Mapping — Backend vs Frontend

### `GET /api/knowledge/list` response shape

**Backend returns (`DocumentListResponse` model):**
```json
{
  "success": true,
  "tenant_id": "29d48db4-...",
  "documents": [
    {
      "id": "uuid",
      "filename": "my-doc.pdf",
      "file_type": "pdf",
      "content_length": 12345,
      "uploaded_at": "2026-02-07T10:00:00+00:00",
      "metadata": {}
    }
  ],
  "total_count": 0
}
```

**Field name analysis:**

| Backend Field | Type | Frontend Likely Expects | Mismatch? |
|---|---|---|---|
| `success` | `bool` | `success` | ✅ None |
| `tenant_id` | `str` | `tenant_id` | ✅ None |
| `documents` | `array` | `documents` | ✅ None |
| `total_count` | `int` | `total_count` or `totalCount` | ⚠️ Possible camelCase mismatch |
| `documents[].id` | `str` | `id` | ✅ None |
| `documents[].filename` | `str` | `filename` or `name` | ⚠️ Possible — frontend may use `name` |
| `documents[].file_type` | `str` | `file_type` or `fileType` or `type` | ⚠️ Possible |
| `documents[].content_length` | `int` | `content_length` or `size` | ⚠️ Possible — frontend may use `size` |
| `documents[].uploaded_at` | `str` (ISO) | `uploaded_at` or `createdAt` | ⚠️ Possible |
| `documents[].metadata` | `dict` | `metadata` | ✅ None |

**Note:** The DB column is `file_size_kb` but the API model uses `content_length` (converts KB→bytes). There is no `content_length` column in `knowledge_documents` — the value is derived. This is correct behavior.

**Secondary risk:** The DB query selects `content_extracted` for length fallback but the field **is not returned in the API response**. This is intentional — only the computed `content_length` is exposed.

---

## 5. Recommended Fix

### Option A — Minimal Fix: Add `verify_session` to `knowledge_api.py`

This is the **lowest-risk, highest-compatibility** fix. Import and use `verify_session` from `dashboard_api_simple.py` as a dependency, identical to all other dashboard endpoints.

```python
# src/saas/knowledge_api.py — PROPOSED FIX

# Add to imports:
from fastapi import APIRouter, File, Header, HTTPException, Query, Depends
from typing import Optional, Any

# Import verify_session from dashboard_api_simple:
from src.core.dashboard_api_simple import verify_session

# ─── GET /list ───────────────────────────────────────────────
# BEFORE (broken):
@router.get("/list", response_model=DocumentListResponse)
async def list_knowledge_documents(
    tenant_id: str = Header(..., alias="X-Tenant-ID")
):

# AFTER (fixed):
@router.get("/list", response_model=DocumentListResponse)
async def list_knowledge_documents(
    tenant_id: str = Depends(verify_session)
):

# ─── POST /upload ─────────────────────────────────────────────
# BEFORE (broken):
@router.post("/upload", response_model=UploadResponse)
async def upload_knowledge_document(
    file: UploadFile = File(...),
    tenant_id: str = Header(..., alias="X-Tenant-ID")
):

# AFTER (fixed):
@router.post("/upload", response_model=UploadResponse)
async def upload_knowledge_document(
    file: UploadFile = File(...),
    tenant_id: str = Depends(verify_session)
):

# ─── DELETE /{document_id} ───────────────────────────────────
# BEFORE (broken):
@router.delete("/{document_id}", response_model=DeleteResponse)
async def delete_knowledge_document(
    document_id: str,
    tenant_id: str = Header(..., alias="X-Tenant-ID")
):

# AFTER (fixed):
@router.delete("/{document_id}", response_model=DeleteResponse)
async def delete_knowledge_document(
    document_id: str,
    tenant_id: str = Depends(verify_session)
):

# ─── GET /combined ────────────────────────────────────────────
# BEFORE (broken):
@router.get("/combined", response_model=CombinedKnowledgeResponse)
async def get_combined_knowledge(
    tenant_id: str = Header(..., alias="X-Tenant-ID")
):

# AFTER (fixed):
@router.get("/combined", response_model=CombinedKnowledgeResponse)
async def get_combined_knowledge(
    tenant_id: str = Depends(verify_session)
):
```

### Why This Works

After the fix, the frontend can call:

```javascript
// Option 1: JWT only (current frontend pattern)
GET /api/knowledge/list
Authorization: Bearer eyJ...
// verify_session → get_current_user → user.user_metadata.tenant_id ✅

// Option 2: tenant_id query param (used by other dashboard calls)
GET /api/knowledge/list?tenant_id=29d48db4-...
// verify_session → tenant_id from Query ✅

// Option 3: X-Tenant-ID header (original, still works)
GET /api/knowledge/list
X-Tenant-ID: 29d48db4-...
// verify_session → x_tenant_id from Header ✅
```

### Option B — Quick Hack (NOT recommended)

Make the header optional with a query param fallback inside `knowledge_api.py`:
```python
async def list_knowledge_documents(
    tenant_id_header: Optional[str] = Header(None, alias="X-Tenant-ID"),
    tenant_id_query: Optional[str] = Query(None, alias="tenant_id"),
):
    tenant_id = tenant_id_header or tenant_id_query
    if not tenant_id:
        raise HTTPException(status_code=400, detail="X-Tenant-ID header required")
```
This bypasses JWT auth entirely — any caller can access any tenant's documents by guessing the UUID. **Security risk.**

---

## 6. Summary Table

| Test | Endpoint | Status Code | Notes |
|---|---|---|---|
| Without `X-Tenant-ID` | `GET /api/knowledge/list` | **422** | Root cause confirmed |
| With `X-Tenant-ID` | `GET /api/knowledge/list` | **200** | Returns `documents: []` (empty) |
| Without headers | `POST /api/knowledge/upload` | **422** | Two errors: missing header + missing file |
| — | `GET /api/dashboard/health` | **404** | Route doesn't exist on dashboard router |
| `?tenant_id=` only | `GET /api/dashboard/messages/{jid}` | **200** | Messages endpoint works (uses `verify_session`) |
| — | `GET /api/knowledge/health` | **200** | Knowledge API alive, Supabase connected |
| With `X-Tenant-ID` | `GET /api/knowledge/combined` | **200** | Works with header |

---

## 7. Action Items

| Priority | Action | File | Effort |
|---|---|---|---|
| 🔴 P0 | Replace `Header(...)` with `Depends(verify_session)` on all 4 endpoints | `src/saas/knowledge_api.py` | 15 min |
| 🟡 P1 | Verify frontend uses `documents[].filename` (not `name`) | Frontend knowledge component | 5 min |
| 🟡 P1 | Verify frontend uses `total_count` (not `totalCount`) | Frontend knowledge component | 5 min |
| 🟢 P2 | Upload a test document to confirm `POST /upload` works end-to-end | Manual QA | 10 min |
| 🟢 P2 | Add `GET /api/dashboard/health` route if dashboard health probe is needed | `src/core/dashboard_api_simple.py` | 5 min |

---

*Report generated by api-tester agent. All curl probes ran against `bijou-staging.fly.dev` on 2026-02-21.*
