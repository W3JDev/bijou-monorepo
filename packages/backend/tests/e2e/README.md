# Dashboard E2E Tests - Quick Start Guide

## Overview
Comprehensive end-to-end test suite for the Bijou AI dashboard to prevent regressions.

**Test File:** `tests/e2e/test_dashboard_complete.py`  
**Test Count:** 16 tests  
**Pass Rate:** 15/16 (94%)  
**Execution Time:** ~15 seconds  

---

## Quick Start

### Run All Tests
```bash
cd w3j-bijou-enterprise
pytest tests/e2e/test_dashboard_complete.py -v
```

### Run Smoke Tests (Critical Path Only)
```bash
pytest tests/e2e/test_dashboard_complete.py -v -m smoke
```
**Smoke tests (5):**
- Phone numbers display correctly
- Stats endpoint works
- Escalations visible
- WhatsApp QR accessible
- All endpoints responsive

### Run Specific Test Category
```bash
# Phone number tests
pytest tests/e2e/test_dashboard_complete.py -v -k phone_number

# Analytics tests
pytest tests/e2e/test_dashboard_complete.py -v -k stats

# Security tests
pytest tests/e2e/test_dashboard_complete.py -v -k security
```

### Run Single Test
```bash
pytest tests/e2e/test_dashboard_complete.py::test_conversations_show_real_phone_numbers -v
```

---

## Test Categories

### 1️⃣ Phone Number Tests (3 tests)
Prevents regression of @lid device ID bug.
```bash
pytest tests/e2e/test_dashboard_complete.py -v -k "phone"
```

### 2️⃣ Analytics Tests (2 tests)
Validates dashboard metrics accuracy.
```bash
pytest tests/e2e/test_dashboard_complete.py -v -k "stats or analytics"
```

### 3️⃣ Escalations Tests (3 tests)
Ensures all escalation statuses visible.
```bash
pytest tests/e2e/test_dashboard_complete.py -v -k "escalation"
```

### 4️⃣ WhatsApp Tests (2 tests)
Verifies WhatsApp integration endpoints.
```bash
pytest tests/e2e/test_dashboard_complete.py -v -k "whatsapp"
```

### 5️⃣ Integration Tests (1 test)
Full end-to-end data flow validation.
```bash
pytest tests/e2e/test_dashboard_complete.py -v -k "full_flow"
```

### 6️⃣ Security Tests (3 tests, 1 skipped)
Prevents cross-tenant data leakage.
```bash
pytest tests/e2e/test_dashboard_complete.py -v -k "security or tenant or leakage"
```

### 7️⃣ Performance Tests (2 tests)
Ensures acceptable response times.
```bash
pytest tests/e2e/test_dashboard_complete.py -v -k "performance or response_time"
```

---

## Configuration

### Environment Variables
```bash
# Test against staging (default)
export TEST_API_URL=https://bijou-staging.fly.dev
export TEST_TENANT_ID=607690ec-4ff7-4ef4-b98e-bfb00442fe95

# Test against local
export TEST_API_URL=http://localhost:8000
export TEST_TENANT_ID=your-test-tenant-id
```

### Pytest Markers
Tests are tagged with markers for selective execution:
- `@pytest.mark.e2e` - All E2E tests
- `@pytest.mark.smoke` - Critical path tests
- `@pytest.mark.regression` - Regression prevention tests
- `@pytest.mark.slow` - Tests taking >5 seconds

---

## Common Use Cases

### Pre-Deployment Check
```bash
# Run smoke tests before deploying to staging
pytest tests/e2e/test_dashboard_complete.py -v -m smoke
```

### After Bug Fix
```bash
# Verify specific bug is fixed
pytest tests/e2e/test_dashboard_complete.py::test_conversations_show_real_phone_numbers -v
```

### Full Regression Suite
```bash
# Run all tests with detailed output
pytest tests/e2e/test_dashboard_complete.py -v --tb=short
```

### CI/CD Integration
```bash
# Run tests and fail on first error
pytest tests/e2e/test_dashboard_complete.py -v -x --tb=line
```

---

## Test Results Interpretation

### ✅ ALL PASSING
Dashboard is functioning correctly. Safe to deploy.

### ⚠️ 1 SKIPPED
Known issue: Dashboard API has no authentication (security vulnerability).  
**Action:** Do not deploy to production until auth is implemented.

### ❌ FAILURES
Regression detected. Do not deploy. Investigate failed test.

---

## Troubleshooting

### Tests fail with connection errors
**Problem:** Cannot reach staging API  
**Solution:** Check internet connection, verify staging URL

### Tests fail with unexpected response format
**Problem:** API response structure changed  
**Solution:** Update tests to match new API format (see TEST_EXECUTION_SUMMARY.md)

### Tests timeout
**Problem:** Slow network or API performance issues  
**Solution:** Increase timeout in test file (TIMEOUT = 60)

---

## Adding New Tests

### Template for New Test
```python
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_new_feature(
    http_client: AsyncClient,
    auth_headers: Dict[str, str],
):
    """
    Test description: What does this test verify?
    
    Regression: Which bug does this prevent?
    Impact: Why is this important?
    """
    # Arrange
    endpoint = "/api/dashboard/new-feature"
    
    # Act
    response = await http_client.get(endpoint, headers=auth_headers)
    
    # Assert
    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}"
    
    data = response.json()
    assert "expected_field" in data, \
        "❌ Missing expected_field in response"
    
    print(f"✅ New feature test passed")
```

### Add to Smoke Tests
```python
@pytest.mark.smoke  # Add this marker for critical tests
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_critical_feature(...):
    ...
```

---

## Integration with CI/CD

### GitHub Actions (Example)
```yaml
# .github/workflows/dashboard-tests.yml
name: Dashboard E2E Tests

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
          pip install -r requirements.txt
          pip install pytest pytest-asyncio httpx
      
      - name: Run E2E tests
        run: |
          cd w3j-bijou-enterprise
          pytest tests/e2e/test_dashboard_complete.py -v --tb=short
      
      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: test-results
          path: test-results.xml
```

---

## Maintenance

### When to Update Tests
- API response format changes
- New dashboard features added
- Bug fixes that need regression prevention
- Performance requirements change

### Test Review Schedule
- **Daily:** Run smoke tests before any deployment
- **Weekly:** Run full suite and review failures
- **Monthly:** Review test coverage and add missing tests
- **After Bug Fix:** Add regression test immediately

---

## Support

**Issues:** Report test failures in project issue tracker  
**Questions:** Contact QA team  
**Documentation:** See `TEST_EXECUTION_SUMMARY.md` for detailed results  

---

**Last Updated:** 2026-02-14  
**Maintained By:** QA Engineer
