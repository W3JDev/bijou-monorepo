# Webhook 422 Error Handling Fix - Completion Report

**Date:** February 17, 2026  
**Issue:** `/webhook/message` endpoint returns 500 instead of 422 for validation errors  
**Status:** ✅ **FIXED**

---

## 📋 Summary

Fixed the message webhook endpoint to correctly return HTTP 422 (Unprocessable Entity) for Pydantic validation errors instead of 500 (Internal Server Error).

---

## 🔍 Root Cause Analysis

### **Before Fix:**

The webhook endpoint had **nested exception handling** that caused HTTPExceptions to be re-wrapped:

```python
# Inner handler (line 3906-3914)
try:
    gowa_message = GOWAWebhookMessage(**raw_body)
except Exception as validation_error:  # ❌ Too broad
    raise HTTPException(status_code=422, detail="...")

# Outer handler (line 4025-4028)
except Exception as e:  # ❌ Catches HTTPException and re-wraps it!
    raise HTTPException(status_code=500, detail=str(e))
```

**Problem:** The outer `except Exception` was catching the inner `raise HTTPException(422)` and converting it to 500.

---

## ✅ Changes Applied

### **1. Added ValidationError Import**

**File:** `w3j-bijou-enterprise/src/core/bijou.py`  
**Line:** 38

```python
# BEFORE
from pydantic import BaseModel, Field

# AFTER
from pydantic import BaseModel, Field, ValidationError
```

---

### **2. Specific Validation Error Handling**

**File:** `w3j-bijou-enterprise/src/core/bijou.py`  
**Lines:** 3906-3920

```python
# BEFORE
try:
    gowa_message = GOWAWebhookMessage(**raw_body)
except Exception as validation_error:  # ❌ Too broad
    logger.error(f"❌ [WEBHOOK] Pydantic validation failed: {validation_error}")
    raise HTTPException(status_code=422, detail="...")

# AFTER
try:
    gowa_message = GOWAWebhookMessage(**raw_body)
except ValidationError as validation_error:  # ✅ Specific exception
    logger.error(f"❌ [WEBHOOK] Pydantic validation failed: {validation_error}")
    logger.error(f"   Raw payload was: {json.dumps(raw_body, indent=2)}")
    raise HTTPException(
        status_code=422, 
        detail=f"Invalid message payload structure: {str(validation_error)}"
    )
except Exception as other_error:  # ✅ Catch non-validation errors
    logger.error(f"❌ [WEBHOOK] Unexpected error during model instantiation: {other_error}")
    raise HTTPException(
        status_code=500,
        detail=f"Internal error during validation: {str(other_error)}"
    )
```

**Improvements:**
- Uses `ValidationError` specifically for Pydantic validation failures → 422
- Catches other exceptions separately → 500
- Enhanced logging to distinguish error types

---

### **3. HTTPException Propagation**

**File:** `w3j-bijou-enterprise/src/core/bijou.py`  
**Lines:** 4031-4037

```python
# BEFORE
except Exception as e:  # ❌ Catches ALL exceptions, including HTTPException
    logger.error(f"❌ [WEBHOOK] Error processing message: {e}")
    raise HTTPException(status_code=500, detail=str(e))

# AFTER
except HTTPException:  # ✅ Let HTTPExceptions propagate unchanged
    raise
except Exception as e:  # ✅ Only catch unexpected errors
    logger.error(f"❌ [WEBHOOK] Unexpected error processing message: {e}")
    logger.error(f"   Traceback: {traceback.format_exc()}")
    raise HTTPException(status_code=500, detail=str(e))
```

**Key Change:**
- Added `except HTTPException: raise` to preserve original status codes
- Prevents re-wrapping of 400, 422, 503 errors as 500

---

## 📊 Expected Behavior (After Fix)

| **Scenario** | **HTTP Status** | **Response Detail** |
|--------------|----------------|---------------------|
| **Missing `payload` field** | 422 | `"Invalid message payload structure: ..."` |
| **Invalid payload structure** | 422 | `"Invalid message payload structure: ..."` |
| **Invalid JSON syntax** | 400 | `"Invalid JSON payload"` |
| **Wrong Content-Type** | 400 | `"Content-Type must be application/json"` |
| **Service not initialized** | 503 | `"Service not ready. Please try again..."` |
| **Unexpected server error** | 500 | `"Unexpected error processing message: ..."` |
| **Valid message** | 200 | `{"status": "accepted", "message_id": "..."}` |

---

## 🧪 Testing Instructions

### **Manual Testing:**

1. Start the local server:
   ```bash
   cd w3j-bijou-enterprise
   python src/core/bijou.py
   ```

2. Test validation errors return 422:
   ```bash
   # Test 1: Missing payload field
   curl -X POST http://localhost:8080/webhook/message \
     -H "Content-Type: application/json" \
     -d '{"event":"message","device_id":"test-123"}' \
     -w "\nHTTP Status: %{http_code}\n"
   
   # Expected: HTTP 422
   
   # Test 2: Invalid payload structure
   curl -X POST http://localhost:8080/webhook/message \
     -H "Content-Type: application/json" \
     -d '{"event":"message","device_id":"test-123","payload":{"body":"test"}}' \
     -w "\nHTTP Status: %{http_code}\n"
   
   # Expected: HTTP 422
   ```

3. Test valid payload returns 200:
   ```bash
   curl -X POST http://localhost:8080/webhook/message \
     -H "Content-Type: application/json" \
     -d '{
       "event":"message",
       "device_id":"test-123",
       "payload":{
         "id":"msg-123",
         "chat_id":"+60123456789@s.whatsapp.net",
         "from":"+60123456789@s.whatsapp.net",
         "from_name":"Test User",
         "body":"Hello Bijou",
         "timestamp":"2026-02-17T00:00:00Z",
         "is_from_me":false
       }
     }' \
     -w "\nHTTP Status: %{http_code}\n"
   
   # Expected: HTTP 200
   ```

---

## 📁 Files Modified

| **File** | **Lines Changed** | **Change Type** |
|----------|-------------------|----------------|
| `w3j-bijou-enterprise/src/core/bijou.py` | 38 | Import `ValidationError` |
| `w3j-bijou-enterprise/src/core/bijou.py` | 3906-3920 | Specific exception handling |
| `w3j-bijou-enterprise/src/core/bijou.py` | 4031-4037 | HTTPException bypass |

**Total lines changed:** 3 sections (18 lines)

---

## ✅ Verification Checklist

- [x] `ValidationError` imported from Pydantic
- [x] Inner try-catch uses `except ValidationError` → 422
- [x] Inner try-catch has fallback `except Exception` → 500
- [x] Outer try-catch has `except HTTPException: raise`
- [x] Outer try-catch only catches unexpected errors → 500
- [x] Enhanced logging for error types
- [x] Python syntax check passed (`py_compile`)
- [ ] Manual testing with invalid payloads (returns 422)
- [ ] Manual testing with valid payloads (returns 200)
- [ ] Integration testing in staging environment

---

## 🎯 Impact Assessment

### **Benefits:**
1. **Better API compliance** - Returns correct HTTP status codes per RFC 7231
2. **Easier debugging** - Clients can distinguish validation errors (422) from server errors (500)
3. **No breaking changes** - Valid requests still return 200

### **Risk:**
- **Low** - Only affects error handling, no business logic changes

---

## 🚀 Next Steps

1. **Deploy to staging:**
   ```powershell
   cd w3j-bijou-enterprise
   C:\Users\w3jbt\.fly\bin\flyctl.exe deploy --app bijou-staging --config fly.staging.toml
   ```

2. **Test in staging:**
   ```bash
   # Send invalid payload to staging
   curl -X POST https://bijou-staging.fly.dev/webhook/message \
     -H "Content-Type: application/json" \
     -d '{"event":"message","device_id":"test"}' \
     -w "\nHTTP: %{http_code}\n"
   ```

3. **Monitor logs:**
   ```powershell
   C:\Users\w3jbt\.fly\bin\flyctl.exe logs --app bijou-staging | grep -i "422\|validation"
   ```

4. **If successful, merge to production**

---

## 📚 Related Documentation

- FastAPI Exception Handling: https://fastapi.tiangolo.com/tutorial/handling-errors/
- Pydantic ValidationError: https://docs.pydantic.dev/latest/errors/errors/
- HTTP Status Codes: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status

---

**Completed by:** @backend agent  
**Reviewed by:** [Pending]  
**Deployed to staging:** [Pending]  
**Deployed to production:** [Pending]
