# Bijou AI - Automated Test Suite
**Complete E2E Testing with Mock WhatsApp & Synthetic Tenants**

---

## 🎯 What This Test Suite Does

✅ **No Manual Setup** - Everything is mocked and automated
✅ **4 Business Types** - Property, Gaming, Dental, F&B tenants pre-configured
✅ **WhatsApp Simulator** - Test without real phone numbers
✅ **Complete Coverage** - All features tested in ~2 minutes
✅ **Solo Dev Friendly** - Run one command, get full confidence

---

## 🚀 Quick Start

### Run All Tests (2 minutes)
```bash
cd w3j-bijou-enterprise
pytest tests/ -v
```

### Run Smoke Tests Only (30 seconds)
```bash
pytest tests/ -v -m smoke
```

### Run Specific Test Category
```bash
# Unit tests (fast)
pytest tests/ -v -m unit

# Integration tests
pytest tests/ -v -m integration

# E2E tests
pytest tests/ -v -m e2e
```

---

## 📦 Test Suite Structure

```
tests/
├── README.md                      # This file
├── conftest.py                    # Pytest configuration & fixtures
├── test_e2e_full_suite.py         # Complete E2E test suite (20 tests)
│
├── fixtures/
│   └── test_tenants.py            # 4 synthetic business tenants
│
└── mocks/
    └── whatsapp_mock.py           # WhatsApp bridge simulator
```

---

## 🧪 Test Coverage (20 Tests)

### 1. Self-Service Onboarding API (3 tests)
- ✅ Property agent can sign up via web form
- ✅ Duplicate email signup is rejected
- ✅ QR code is generated for WhatsApp connection

### 2. Message Filter (3 tests)
- ✅ Testing mode only replies to test numbers
- ✅ Ignore list blocks specific numbers
- ✅ Business hours enforcement works

### 3. Knowledge Upload & Retrieval (3 tests)
- ✅ Upload PDF/DOCX knowledge documents
- ✅ Retrieve combined knowledge from all documents
- ✅ Knowledge API /upload endpoint works

### 4. Settings API (3 tests)
- ✅ Toggle testing mode via API
- ✅ Update ignore/private number list
- ✅ Update business hours configuration

### 5. Multi-Tenant Routing (1 test)
- ✅ Messages route to correct tenant based on WhatsApp JID

### 6. Synthetic Tenant Fixtures (3 tests)
- ✅ All tenants have required fields
- ✅ Property tenant has Harmoni Residence data
- ✅ All 4 knowledge bases exist

### 7. Full E2E Flow (2 tests)
- ✅ Complete journey: Signup → Connect → Upload → Message → Reply
- ✅ Ignore list prevents auto-reply

### 8. Smoke Tests (2 tests)
- ✅ API health endpoints respond
- ✅ Tenant fixtures load fast (<1 second)

---

## 🏢 Synthetic Test Tenants

### 1. Harmoni Residence (Property/Real Estate)
- **Business**: Luxury condo sales in KL
- **Features**: Unit pricing, viewing appointments, multi-language
- **Test Numbers**: +60100000001, +60100000002
- **Knowledge**: Property listings, pricing (RM 580k-1.5M), facilities

### 2. GameHub Arena (Gaming/Esports)
- **Business**: Gaming center with high-end PCs, PS5, tournaments
- **Features**: Hourly bookings, memberships, tournament registration
- **Test Numbers**: +60100000003, +60100000004
- **Knowledge**: PC specs (RTX 4090), pricing (RM 8-15/hr), tournaments

### 3. SmileCare Dental (Healthcare)
- **Business**: Family dental clinic
- **Features**: Appointment booking, treatment inquiries, insurance
- **Test Numbers**: +60100000005, +60100000006
- **Knowledge**: Services, pricing (RM 80-8000), dentist profiles

### 4. Bistro Delights (F&B/Restaurant)
- **Business**: Fusion restaurant with artisan coffee
- **Features**: Table reservations, menu inquiries, dietary requests
- **Test Numbers**: +60100000007, +60100000008
- **Knowledge**: Menu items, pricing (RM 10-45), daily specials

---

## 🔧 Using Test Fixtures

### In Your Tests
```python
def test_my_feature(property_tenant, mock_bridge, mock_supabase):
    """Use pre-configured fixtures"""
    # property_tenant = Harmoni Residence data
    # mock_bridge = WhatsApp simulator
    # mock_supabase = Database mock

    tenant_id = property_tenant["id"]
    session_id = "test-session"

    # Create WhatsApp session
    mock_bridge.create_session(session_id, tenant_id)
    mock_bridge.connect_session(session_id, "+60143856929")

    # Simulate customer message
    msg = mock_bridge.simulate_incoming_message(
        session_id,
        "+60100000001",
        "How much is a 2 bedroom?"
    )

    # Assert response (your logic here)
    assert msg.content == "How much is a 2 bedroom?"
```

### Available Fixtures
```python
# Tenants
property_tenant    # Harmoni Residence
gaming_tenant      # GameHub Arena
dental_tenant      # SmileCare Dental
fnb_tenant         # Bistro Delights
test_tenants       # All 4 tenants

# Mocks
mock_bridge        # WhatsApp simulator
mock_supabase      # Database mock
test_client        # FastAPI test client

# Helpers
mock_tenant_id     # UUID for testing
mock_session_id    # WhatsApp session ID
mock_phone_number  # Test phone number
```

---

## 🤖 WhatsApp Mock Simulator

### Simulate User Conversations
```python
from tests.mocks.whatsapp_mock import MockWhatsAppBridge

# Create mock bridge
bridge = MockWhatsAppBridge()

# Create session
bridge.create_session("session-123", "tenant-123")
bridge.connect_session("session-123", "+60143856929")

# Simulate incoming messages
bridge.simulate_incoming_message(
    "session-123",
    "+60100000001",
    "What units are available?"
)

bridge.simulate_incoming_message(
    "session-123",
    "+60100000001",
    "I want a 2 bedroom"
)

# Check AI responses (sent messages)
sent = bridge.get_sent_messages("session-123")
assert len(sent) == 2
```

---

## 📊 Test Reports

### HTML Report (with pytest-html)
```bash
pip install pytest-html
pytest tests/ --html=reports/test_report.html --self-contained-html
```

### Coverage Report (with pytest-cov)
```bash
pip install pytest-cov
pytest tests/ --cov=src --cov-report=html
open htmlcov/index.html
```

### JUnit XML (for CI/CD)
```bash
pytest tests/ --junitxml=reports/junit.xml
```

---

## 🐛 Debugging Tests

### Run Single Test
```bash
pytest tests/test_e2e_full_suite.py::TestOnboardingAPI::test_signup_creates_tenant -v
```

### Show Print Statements
```bash
pytest tests/ -v -s
```

### Stop on First Failure
```bash
pytest tests/ -v -x
```

### Run Last Failed Tests
```bash
pytest tests/ -v --lf
```

### Debug with PDB
```bash
pytest tests/ -v --pdb
```

---

## 🔄 CI/CD Integration

### GitHub Actions Example
```yaml
name: Bijou AI Tests

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
          pip install pytest pytest-asyncio

      - name: Run tests
        run: pytest tests/ -v --junitxml=reports/junit.xml

      - name: Upload test results
        uses: actions/upload-artifact@v3
        with:
          name: test-results
          path: reports/junit.xml
```

---

## 🎓 Writing New Tests

### 1. Unit Test Template
```python
import pytest

@pytest.mark.unit
def test_my_unit():
    """Test: Single function in isolation"""
    from src.my_module import my_function

    result = my_function("input")
    assert result == "expected_output"
```

### 2. Integration Test Template
```python
import pytest

@pytest.mark.integration
def test_my_integration(mock_supabase):
    """Test: Multiple components together"""
    from src.saas.my_feature import MyFeature

    feature = MyFeature(supabase_client=mock_supabase)

    # Mock database response
    mock_supabase.table("tenants").select().execute.return_value.data = [
        {"id": "test-123", "name": "Test Tenant"}
    ]

    result = feature.do_something("test-123")
    assert result["success"] is True
```

### 3. E2E Test Template
```python
import pytest

@pytest.mark.e2e
@pytest.mark.smoke
def test_my_e2e_flow(test_client, mock_bridge, property_tenant):
    """Test: Complete user journey"""
    # Step 1: API call
    response = test_client.post("/api/endpoint", json={"data": "value"})
    assert response.status_code == 200

    # Step 2: WhatsApp interaction
    mock_bridge.simulate_incoming_message(
        "session", "+60100000001", "User message"
    )

    # Step 3: Verify outcome
    sent = mock_bridge.get_sent_messages("session")
    assert len(sent) > 0
```

---

## 📝 Best Practices

### ✅ DO
- Use descriptive test names: `test_ignore_list_blocks_jewel_number`
- Test one thing per test function
- Use fixtures instead of setup/teardown
- Mark tests with appropriate markers (`@pytest.mark.smoke`)
- Write docstrings explaining what you're testing

### ❌ DON'T
- Don't test implementation details
- Don't use sleep() (use mocks instead)
- Don't hardcode values (use fixtures)
- Don't skip cleanup (use `yield` in fixtures)
- Don't test third-party libraries

---

## 🚨 Troubleshooting

### Tests Failing with Import Errors
```bash
# Add project to Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
pytest tests/ -v
```

### Mock Not Working
```python
# Use patch with full module path
with patch("src.saas.onboarding_api.get_supabase", return_value=mock_supabase):
    # Your test code
```

### Async Tests Failing
```python
# Mark test as async
@pytest.mark.asyncio
async def test_async_function():
    result = await my_async_function()
    assert result == "expected"
```

### Fixtures Not Found
```bash
# Make sure conftest.py is in tests/ directory
# Fixtures are auto-discovered by pytest
ls tests/conftest.py  # Should exist
```

---

## 📚 Further Reading

- [Pytest Documentation](https://docs.pytest.org/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [Mock Documentation](https://docs.python.org/3/library/unittest.mock.html)
- [Pytest Fixtures](https://docs.pytest.org/en/stable/fixture.html)

---

## 🎉 Success Metrics

**When tests pass, you have confidence that:**

✅ All 4 business types work correctly
✅ Onboarding flow is functional
✅ Message filtering protects production
✅ Knowledge upload/retrieval works
✅ Settings API is stable
✅ Multi-tenant routing is correct

**Ship with confidence! 🚀**

---

**Author**: W3J Consulting - Muhammad Nurunnabi (Jewel)
**Date**: 2026-02-07
**Version**: 1.0.0
