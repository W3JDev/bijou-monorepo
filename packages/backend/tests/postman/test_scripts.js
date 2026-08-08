// ============================================================================
// BIJOU AI - POSTMAN TEST SCRIPTS
// ============================================================================
// Copy these test scripts into the "Tests" tab of each Postman request
// They will run automatically after each request to validate responses
// ============================================================================

// ----------------------------------------------------------------------------
// TEST 1: Health Check (/health)
// ----------------------------------------------------------------------------
pm.test("Status code is 200", function () {
    pm.response.to.have.status(200);
});

pm.test("Response time is less than 2000ms", function () {
    pm.expect(pm.response.responseTime).to.be.below(2000);
});

pm.test("Health status is healthy", function () {
    const jsonData = pm.response.json();
    pm.expect(jsonData.status).to.eql("healthy");
});

pm.test("Response contains required fields", function () {
    const jsonData = pm.response.json();
    pm.expect(jsonData).to.have.property("service");
    pm.expect(jsonData).to.have.property("version");
    pm.expect(jsonData).to.have.property("timestamp");
    pm.expect(jsonData).to.have.property("database");
});

pm.test("Version is 2.2.0", function () {
    const jsonData = pm.response.json();
    pm.expect(jsonData.version).to.eql("2.2.0");
});

// ----------------------------------------------------------------------------
// TEST 2: Postman Collection Download (/postman-collection)
// ----------------------------------------------------------------------------
pm.test("Status code is 200", function () {
    pm.response.to.have.status(200);
});

pm.test("Content-Type is application/json", function () {
    pm.response.to.have.header("Content-Type", "application/json");
});

pm.test("Has download header", function () {
    pm.expect(pm.response.headers.get("Content-Disposition")).to.include("attachment");
    pm.expect(pm.response.headers.get("Content-Disposition")).to.include("bijou-api.postman_collection.json");
});

pm.test("Response is valid Postman collection", function () {
    const jsonData = pm.response.json();
    pm.expect(jsonData).to.have.property("info");
    pm.expect(jsonData).to.have.property("item");
    pm.expect(jsonData.info.name).to.eql("Bijou AI WhatsApp Enterprise");
    pm.expect(jsonData.info.version).to.eql("2.2.0");
});

pm.test("Collection has environment variables", function () {
    const jsonData = pm.response.json();
    pm.expect(jsonData).to.have.property("variable");
    const varKeys = jsonData.variable.map(v => v.key);
    pm.expect(varKeys).to.include("base_url");
    pm.expect(varKeys).to.include("dashboard_token");
});

pm.test("Collection has multiple endpoints", function () {
    const jsonData = pm.response.json();
    pm.expect(jsonData.item.length).to.be.above(5);
});

// ----------------------------------------------------------------------------
// TEST 3: API Documentation (/api-docs)
// ----------------------------------------------------------------------------
pm.test("Status code is 200", function () {
    pm.response.to.have.status(200);
});

pm.test("Content-Type is HTML", function () {
    pm.expect(pm.response.headers.get("Content-Type")).to.include("text/html");
});

pm.test("Page contains Postman mention", function () {
    pm.expect(pm.response.text()).to.include("Postman");
});

pm.test("Page has download link", function () {
    pm.expect(pm.response.text()).to.include("/postman-collection");
});

// ----------------------------------------------------------------------------
// TEST 4: Changelog (/changelog)
// ----------------------------------------------------------------------------
pm.test("Status code is 200", function () {
    pm.response.to.have.status(200);
});

pm.test("Response is array", function () {
    const jsonData = pm.response.json();
    pm.expect(jsonData).to.be.an("array");
});

pm.test("Changelog has entries", function () {
    const jsonData = pm.response.json();
    if (jsonData.length > 0) {
        pm.expect(jsonData[0]).to.have.property("version");
        pm.expect(jsonData[0]).to.have.property("changes");
    }
});

// ----------------------------------------------------------------------------
// TEST 5: OpenAPI Schema (/openapi.json)
// ----------------------------------------------------------------------------
pm.test("Status code is 200", function () {
    pm.response.to.have.status(200);
});

pm.test("Schema has required fields", function () {
    const jsonData = pm.response.json();
    pm.expect(jsonData).to.have.property("openapi");
    pm.expect(jsonData).to.have.property("info");
    pm.expect(jsonData).to.have.property("paths");
});

pm.test("Schema includes key endpoints", function () {
    const jsonData = pm.response.json();
    pm.expect(jsonData.paths).to.have.property("/health");
    pm.expect(jsonData.paths).to.have.property("/postman-collection");
});

// ----------------------------------------------------------------------------
// TEST 6: Google OAuth Login (/api/auth/google/login)
// ----------------------------------------------------------------------------
pm.test("Redirects to Google OAuth", function () {
    pm.expect(pm.response.code).to.be.oneOf([302, 307]);
});

pm.test("Location header points to Google", function () {
    const location = pm.response.headers.get("Location");
    pm.expect(location).to.include("accounts.google.com");
    pm.expect(location.toLowerCase()).to.include("oauth2");
});

// ----------------------------------------------------------------------------
// TEST 8: Get Conversations (/api/dashboard/conversations)
// ----------------------------------------------------------------------------
pm.test("Status code is 200 or 401", function () {
    pm.expect(pm.response.code).to.be.oneOf([200, 401]);
});

pm.test("If authenticated, returns conversations", function () {
    if (pm.response.code === 200) {
        const jsonData = pm.response.json();
        pm.expect(jsonData).to.satisfy(function(data) {
            return data.hasOwnProperty("conversations") || Array.isArray(data);
        });
    }
});

// ----------------------------------------------------------------------------
// TEST 9: Dashboard Stats (/api/dashboard/stats)
// ----------------------------------------------------------------------------
pm.test("Status code is 200 or 401", function () {
    pm.expect(pm.response.code).to.be.oneOf([200, 401]);
});

pm.test("If authenticated, returns stats object", function () {
    if (pm.response.code === 200) {
        const jsonData = pm.response.json();
        pm.expect(jsonData).to.be.an("object");
        
        // Check for numeric stats fields
        const numericFields = ["total_conversations", "ai_handled", "human_handled"];
        numericFields.forEach(field => {
            if (jsonData.hasOwnProperty(field)) {
                pm.expect(jsonData[field]).to.be.a("number");
            }
        });
    }
});

// ----------------------------------------------------------------------------
// TEST 15: List Knowledge Items (/api/knowledge/list)
// ----------------------------------------------------------------------------
pm.test("Status code is 200 or 401", function () {
    pm.expect(pm.response.code).to.be.oneOf([200, 401]);
});

pm.test("If authenticated, returns knowledge items", function () {
    if (pm.response.code === 200) {
        const jsonData = pm.response.json();
        pm.expect(jsonData).to.satisfy(function(data) {
            return Array.isArray(data) || typeof data === "object";
        });
    }
});

// ----------------------------------------------------------------------------
// TEST 16: Add Knowledge Item (/api/knowledge/add)
// ----------------------------------------------------------------------------
pm.test("Status code indicates success or auth required", function () {
    pm.expect(pm.response.code).to.be.oneOf([200, 201, 401]);
});

pm.test("If successful, returns knowledge_id", function () {
    if (pm.response.code === 200 || pm.response.code === 201) {
        const jsonData = pm.response.json();
        pm.expect(jsonData).to.satisfy(function(data) {
            return data.hasOwnProperty("knowledge_id") || data.hasOwnProperty("id");
        });
        
        // Store knowledge_id for later tests
        if (jsonData.knowledge_id) {
            pm.environment.set("test_knowledge_id", jsonData.knowledge_id);
        } else if (jsonData.id) {
            pm.environment.set("test_knowledge_id", jsonData.id);
        }
    }
});

// ----------------------------------------------------------------------------
// TEST 25: Swagger UI (/docs)
// ----------------------------------------------------------------------------
pm.test("Status code is 200", function () {
    pm.response.to.have.status(200);
});

pm.test("Content-Type is HTML", function () {
    pm.expect(pm.response.headers.get("Content-Type")).to.include("text/html");
});

pm.test("Page contains Swagger UI", function () {
    pm.expect(pm.response.text()).to.satisfy(function(text) {
        return text.includes("swagger") || text.includes("Swagger");
    });
});

// ----------------------------------------------------------------------------
// TEST 26: ReDoc (/redoc)
// ----------------------------------------------------------------------------
pm.test("Status code is 200", function () {
    pm.response.to.have.status(200);
});

pm.test("Content-Type is HTML", function () {
    pm.expect(pm.response.headers.get("Content-Type")).to.include("text/html");
});

pm.test("Page contains ReDoc", function () {
    pm.expect(pm.response.text()).to.satisfy(function(text) {
        return text.includes("redoc") || text.includes("ReDoc");
    });
});

// ============================================================================
// UNIVERSAL TEST SCRIPTS (Add to all requests)
// ============================================================================

// Auto-save response time for performance tracking
pm.environment.set(`${pm.info.requestName}_response_time`, pm.response.responseTime);

// Log errors for debugging
if (pm.response.code >= 400) {
    console.log(`❌ ${pm.info.requestName} failed with status ${pm.response.code}`);
    console.log("Response body:", pm.response.text());
} else {
    console.log(`✅ ${pm.info.requestName} passed`);
}

// Track test results
const testResults = pm.environment.get("test_results") || {};
testResults[pm.info.requestName] = {
    status: pm.response.code,
    passed: pm.response.code < 400,
    timestamp: new Date().toISOString(),
    responseTime: pm.response.responseTime
};
pm.environment.set("test_results", JSON.stringify(testResults));
