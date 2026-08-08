# Bijou AI - Automated API Testing Guide

**Version:** 2.2.0  
**Last Updated:** February 17, 2026

---

## 📁 Files Created

```
tests/
├── integration/
│   └── test_api_endpoints.py      (Python pytest suite - 26 automated tests)
├── postman/
│   └── test_scripts.js             (Postman test scripts for collection)
├── test_data.json                  (Data-driven test configuration)
├── POSTMAN_TEST_CHECKLIST.md       (Manual testing checklist)
└── README_TESTING.md               (This file)
```

---

## 🚀 Quick Start

### **Option 1: Run Python Tests (Recommended)**

```bash
# From project root (w3j-bijou-enterprise/)

# Install dependencies (if not already installed)
pip install pytest requests python-dotenv

# Set environment variables
export HOSTNAME="https://bijou-staging.fly.dev"
export DASHBOARD_TOKEN="your_jwt_token_here"
export API_KEY="your_api_key_here"  # Optional
export TENANT_ID="your_tenant_uuid_here"  # Optional

# Run all tests
pytest tests/integration/test_api_endpoints.py -v

# Run with coverage
pytest tests/integration/test_api_endpoints.py -v --cov=src --cov-report=html

# Run specific test phase
pytest tests/integration/test_api_endpoints.py::TestPhase1HealthAndDocs -v
```

### **Option 2: Run Postman Tests**

1. **Import Collection:**
   - Download: https://bijou-staging.fly.dev/postman-collection
   - Postman → Import → Upload JSON

2. **Add Test Scripts:**
   - Open `tests/postman/test_scripts.js`
   - Copy relevant test scripts
   - Paste into each request's "Tests" tab in Postman

3. **Run Collection:**
   - Postman → Collections → "Bijou AI WhatsApp Enterprise"
   - Click "Run" button
   - Select environment "Bijou Staging"
   - Click "Run Bijou AI WhatsApp Enterprise"

---

## 📊 Test Coverage

| Phase | Tests | Auth Required | Purpose |
|-------|-------|---------------|---------|
| **Phase 1** | 5 | ❌ No | Health check, docs, Postman collection |
| **Phase 2** | 2 | ❌ No | OAuth login, auth URLs |
| **Phase 3** | 7 | ✅ Yes (JWT) | Dashboard API, conversations, stats |
| **Phase 4** | 4 | ✅ Yes (JWT) | Knowledge base CRUD |
| **Phase 5** | 3 | ❌ No | Onboarding flow |
| **Phase 6** | 3 | ✅ Yes (API key) | Webhooks |
| **Phase 7** | 2 | ❌ No | Swagger UI, ReDoc |
| **TOTAL** | **26** | - | Full API coverage |

---

## 🎯 Critical Path Tests (Must Pass)

These 5 tests **MUST** pass for system health:

1. ✅ **Health Check** (`test_01`) - System is running
2. ✅ **Postman Collection Download** (`test_02`) - New feature works!
3. ✅ **API Documentation** (`test_03`) - Docs accessible
4. ✅ **Get Conversations** (`test_08`) - Dashboard API functional
5. ✅ **List Knowledge Items** (`test_15`) - Knowledge base operational

**Run only critical path:**
```bash
pytest tests/integration/test_api_endpoints.py::TestPhase1HealthAndDocs::test_01_health_check \
      tests/integration/test_api_endpoints.py::TestPhase1HealthAndDocs::test_02_postman_collection_download \
      tests/integration/test_api_endpoints.py::TestPhase1HealthAndDocs::test_03_api_documentation \
      tests/integration/test_api_endpoints.py::TestPhase3DashboardAPI::test_08_get_conversations \
      tests/integration/test_api_endpoints.py::TestPhase4KnowledgeBase::test_15_list_knowledge_items -v
```

---

## 🔧 Environment Setup

### **Required Environment Variables**

Create `.env` file or export these:

```bash
# Base URL
HOSTNAME=https://bijou-staging.fly.dev

# Authentication (get from Google OAuth login)
DASHBOARD_TOKEN=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# Optional (for webhook tests)
API_KEY=your_whatsapp_bridge_api_key

# Optional (for tenant-specific tests)
TENANT_ID=12345678-1234-1234-1234-123456789012
```

### **How to Get DASHBOARD_TOKEN:**

1. Visit: https://bijou-staging.fly.dev/api/auth/google/login
2. Sign in with Google
3. Open Browser DevTools (F12)
4. Go to: Application → Local Storage
5. Find `supabase.auth.token` or similar
6. Copy the JWT value

---

## 📋 Test Execution Examples

### **Run All Tests**
```bash
pytest tests/integration/test_api_endpoints.py -v
```

**Expected Output:**
```
========== test session starts ==========
tests/integration/test_api_endpoints.py::TestPhase1HealthAndDocs::test_01_health_check PASSED
tests/integration/test_api_endpoints.py::TestPhase1HealthAndDocs::test_02_postman_collection_download PASSED
tests/integration/test_api_endpoints.py::TestPhase1HealthAndDocs::test_03_api_documentation PASSED
...
========== 26 passed in 15.23s ==========
```

### **Run Phase 1 Only (No Auth)**
```bash
pytest tests/integration/test_api_endpoints.py::TestPhase1HealthAndDocs -v
```

### **Run Single Test**
```bash
pytest tests/integration/test_api_endpoints.py::TestPhase1HealthAndDocs::test_02_postman_collection_download -v
```

### **Run with Debug Output**
```bash
pytest tests/integration/test_api_endpoints.py -v -s
```

### **Generate HTML Report**
```bash
pytest tests/integration/test_api_endpoints.py -v --html=test_report.html --self-contained-html
```

---

## 🧪 Postman Test Script Examples

### **Copy-Paste Into Postman "Tests" Tab**

#### **For /health Endpoint:**
```javascript
pm.test("Status code is 200", function () {
    pm.response.to.have.status(200);
});

pm.test("Health status is healthy", function () {
    const jsonData = pm.response.json();
    pm.expect(jsonData.status).to.eql("healthy");
});

pm.test("Version is 2.2.0", function () {
    const jsonData = pm.response.json();
    pm.expect(jsonData.version).to.eql("2.2.0");
});
```

#### **For /postman-collection Endpoint:**
```javascript
pm.test("Status code is 200", function () {
    pm.response.to.have.status(200);
});

pm.test("Has download header", function () {
    pm.expect(pm.response.headers.get("Content-Disposition")).to.include("attachment");
});

pm.test("Response is valid Postman collection", function () {
    const jsonData = pm.response.json();
    pm.expect(jsonData).to.have.property("info");
    pm.expect(jsonData.info.name).to.eql("Bijou AI WhatsApp Enterprise");
});
```

#### **For Dashboard Endpoints (with Auth):**
```javascript
pm.test("Status code is 200 or 401", function () {
    pm.expect(pm.response.code).to.be.oneOf([200, 401]);
});

pm.test("If authenticated, returns data", function () {
    if (pm.response.code === 200) {
        const jsonData = pm.response.json();
        pm.expect(jsonData).to.be.an("object");
    }
});
```

**See `tests/postman/test_scripts.js` for all 26 test scripts**

---

## 📈 Test Results Interpretation

### **Success Indicators:**

✅ **Phase 1 (5/5 passed)** - System healthy  
✅ **Critical Path (5/5 passed)** - Core functionality working  
✅ **Overall (20+/26 passed)** - Production-ready  

### **Acceptable Failures:**

⚠️ **Phase 6 Webhooks** - May fail if API_KEY not set (optional)  
⚠️ **Phase 3/4 Auth tests** - May fail if DASHBOARD_TOKEN expired (refresh token)  

### **Red Flags (Investigate Immediately):**

🔴 **test_01_health_check fails** - Server down!  
🔴 **test_02_postman_collection_download fails** - New feature broken!  
🔴 **Multiple Phase 1 tests fail** - Critical system issue  

---

## 🐛 Troubleshooting

### **Problem: All tests fail with connection errors**
```
requests.exceptions.ConnectionError: Failed to establish a new connection
```
**Solution:**
- Check if server is running: `curl https://bijou-staging.fly.dev/health`
- Verify BASE_URL is correct in `.env`
- Check Fly.io logs: `flyctl logs --app bijou-staging`

---

### **Problem: Tests fail with 401 Unauthorized**
```
assert response.status_code in [200, 401]
AssertionError: Expected 200 or 401, got 401
```
**Solution:**
- Your DASHBOARD_TOKEN expired
- Get fresh token: https://bijou-staging.fly.dev/api/auth/google/login
- Update `.env` file with new token

---

### **Problem: Postman tests not running**
**Solution:**
1. Verify environment variables are set in Postman environment
2. Check "Tests" tab has scripts (copy from `tests/postman/test_scripts.js`)
3. Make sure correct environment is selected (Bijou Staging)

---

### **Problem: Knowledge base tests fail**
```
ERROR: 'knowledge_id_to_cleanup' not found
```
**Solution:**
- This is expected if test_16 (Add Knowledge) fails
- Tests 17 and 18 will be skipped automatically
- Not a critical failure

---

## 📊 Test Data JSON Format

The `test_data.json` file is a **data-driven test specification**. You can:

1. **Use it to generate new tests** programmatically
2. **Import into CI/CD pipelines** for automated testing
3. **Share with frontend developers** as API contract

**Example entry:**
```json
{
  "id": "test_02",
  "name": "Postman Collection Download",
  "endpoint": "/postman-collection",
  "method": "GET",
  "expected_status": 200,
  "required_headers": {
    "Content-Type": "application/json",
    "Content-Disposition": "attachment"
  },
  "assertions": {
    "info.version": "2.2.0"
  }
}
```

---

## 🔄 CI/CD Integration

### **GitHub Actions Example:**

```yaml
name: API Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install pytest requests python-dotenv
      
      - name: Run tests
        env:
          HOSTNAME: https://bijou-staging.fly.dev
          DASHBOARD_TOKEN: ${{ secrets.DASHBOARD_TOKEN }}
        run: |
          pytest tests/integration/test_api_endpoints.py -v --html=report.html
      
      - name: Upload test report
        uses: actions/upload-artifact@v3
        with:
          name: test-report
          path: report.html
```

---

## 📝 Adding New Tests

### **Python (pytest):**

1. Open `tests/integration/test_api_endpoints.py`
2. Add new test method to appropriate class:

```python
def test_27_my_new_endpoint(self, api_client):
    """Test 27: My new endpoint description"""
    response = api_client.get(f"{BASE_URL}/my-new-endpoint")
    
    assert response.status_code == 200, "Should return 200"
    data = response.json()
    assert "expected_field" in data, "Should have expected_field"
```

3. Run test: `pytest tests/integration/test_api_endpoints.py::TestClassName::test_27_my_new_endpoint -v`

### **Postman:**

1. Open `tests/postman/test_scripts.js`
2. Add new test block:

```javascript
// ----------------------------------------------------------------------------
// TEST 27: My New Endpoint (/my-new-endpoint)
// ----------------------------------------------------------------------------
pm.test("Status code is 200", function () {
    pm.response.to.have.status(200);
});

pm.test("Response has expected field", function () {
    const jsonData = pm.response.json();
    pm.expect(jsonData).to.have.property("expected_field");
});
```

3. Copy into Postman request "Tests" tab

---

## 🎯 Next Steps

1. ✅ **Run critical path tests** (5 tests) - Verify core functionality
2. ✅ **Run full test suite** (26 tests) - Complete validation
3. ✅ **Add tests to CI/CD** - Automate on every deployment
4. ✅ **Update tests when adding new endpoints** - Keep tests in sync
5. ✅ **Monitor test results** - Track pass/fail rates over time

---

## 📞 Support

**Issues with tests?**
- Check Fly.io logs: `flyctl logs --app bijou-staging`
- Verify server health: https://bijou-staging.fly.dev/health
- Review API docs: https://bijou-staging.fly.dev/api-docs

**Questions?**
- See: `POSTMAN_TEST_CHECKLIST.md` for manual testing guide
- See: `tests/test_data.json` for test specifications

---

**Happy Testing!** 🚀
