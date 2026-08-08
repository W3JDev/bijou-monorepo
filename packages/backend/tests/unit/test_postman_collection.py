"""
Unit tests for Postman Collection generation and endpoint.

Tests:
- Postman collection file exists
- Collection is valid JSON
- Collection matches Postman v2.1 schema
- /postman-collection endpoint works
- Required environment variables present
- Critical endpoints included
"""

import json
import os
import pytest
from pathlib import Path


class TestPostmanCollectionFile:
    """Test the generated Postman collection file"""
    
    def test_collection_file_exists(self):
        """Test that the collection file exists in docs/"""
        collection_path = Path("docs/bijou-api.postman_collection.json")
        assert collection_path.exists(), f"Postman collection file not found at {collection_path}"
    
    def test_collection_is_valid_json(self):
        """Test that the collection is valid JSON"""
        collection_path = Path("docs/bijou-api.postman_collection.json")
        with open(collection_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            assert isinstance(data, dict), "Collection should be a JSON object"
    
    def test_collection_has_required_fields(self):
        """Test that collection has all required Postman v2.1 fields"""
        collection_path = Path("docs/bijou-api.postman_collection.json")
        with open(collection_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Required root fields
        assert "info" in data, "Collection missing 'info' field"
        assert "item" in data, "Collection missing 'item' field (endpoints)"
        
        # Info fields
        info = data["info"]
        assert "name" in info, "Collection info missing 'name'"
        assert "schema" in info, "Collection info missing 'schema'"
        assert info["schema"] == "https://schema.getpostman.com/json/collection/v2.1.0/collection.json", \
            "Collection schema should be Postman v2.1"
    
    def test_collection_has_environment_variables(self):
        """Test that collection includes required environment variables"""
        collection_path = Path("docs/bijou-api.postman_collection.json")
        with open(collection_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        assert "variable" in data, "Collection missing environment variables"
        
        variables = {var["key"]: var for var in data["variable"]}
        required_vars = ["base_url", "api_key", "dashboard_token", "tenant_id"]
        
        for var_name in required_vars:
            assert var_name in variables, f"Missing required variable: {var_name}"
    
    def test_collection_has_folders(self):
        """Test that collection organizes endpoints into folders"""
        collection_path = Path("docs/bijou-api.postman_collection.json")
        with open(collection_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        folders = data["item"]
        assert len(folders) > 0, "Collection should have at least one folder"
        assert len(folders) >= 5, f"Expected at least 5 folders, got {len(folders)}"
    
    def test_collection_has_critical_endpoints(self):
        """Test that collection includes critical API endpoints"""
        collection_path = Path("docs/bijou-api.postman_collection.json")
        with open(collection_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Extract all request names
        endpoint_names = []
        for folder in data["item"]:
            if "item" in folder:  # It's a folder
                for request in folder["item"]:
                    endpoint_names.append(request["name"].lower())
            else:  # It's a direct request
                endpoint_names.append(folder["name"].lower())
        
        # Check for critical endpoints (case-insensitive)
        critical_keywords = ["health", "dashboard", "conversation", "message"]
        
        for keyword in critical_keywords:
            assert any(keyword in name for name in endpoint_names), \
                f"Collection missing critical endpoint containing '{keyword}'"
    
    def test_collection_size_reasonable(self):
        """Test that collection file size is reasonable (not too large)"""
        collection_path = Path("docs/bijou-api.postman_collection.json")
        file_size = collection_path.stat().st_size
        
        # Collection should be between 10KB and 500KB
        assert 10_000 < file_size < 500_000, \
            f"Collection size ({file_size} bytes) outside expected range (10KB-500KB)"
    
    def test_collection_version_matches_api(self):
        """Test that collection version matches API version"""
        collection_path = Path("docs/bijou-api.postman_collection.json")
        with open(collection_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        version = data["info"].get("version")
        assert version is not None, "Collection missing version"
        assert version == "2.2.0", f"Collection version ({version}) should match API version (2.2.0)"


class TestPostmanCollectionEndpoint:
    """Test the /postman-collection FastAPI endpoint"""
    
    @pytest.fixture
    def client(self):
        """Create FastAPI test client"""
        from fastapi.testclient import TestClient
        from src.core.bijou import app
        return TestClient(app)
    
    def test_endpoint_exists(self, client):
        """Test that /postman-collection endpoint is accessible"""
        response = client.get("/postman-collection")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    
    def test_endpoint_returns_json(self, client):
        """Test that endpoint returns JSON"""
        response = client.get("/postman-collection")
        assert response.headers["content-type"] == "application/json", \
            "Response should be application/json"
    
    def test_endpoint_has_download_header(self, client):
        """Test that response includes Content-Disposition header for download"""
        response = client.get("/postman-collection")
        assert "content-disposition" in response.headers, \
            "Response missing Content-Disposition header"
        
        disposition = response.headers["content-disposition"]
        assert "attachment" in disposition, \
            "Content-Disposition should indicate attachment"
        assert "bijou-api.postman_collection.json" in disposition, \
            "Filename should be bijou-api.postman_collection.json"
    
    def test_endpoint_returns_valid_collection(self, client):
        """Test that endpoint returns a valid Postman collection"""
        response = client.get("/postman-collection")
        data = response.json()
        
        # Validate Postman Collection v2.1 schema
        assert "info" in data, "Response missing 'info' field"
        assert "item" in data, "Response missing 'item' field"
        assert data["info"]["schema"] == "https://schema.getpostman.com/json/collection/v2.1.0/collection.json", \
            "Invalid Postman schema"
    
    def test_endpoint_collection_matches_file(self, client):
        """Test that endpoint returns the same data as the file"""
        response = client.get("/postman-collection")
        endpoint_data = response.json()
        
        # Load file
        collection_path = Path("docs/bijou-api.postman_collection.json")
        with open(collection_path, "r", encoding="utf-8") as f:
            file_data = json.load(f)
        
        # Compare
        assert endpoint_data["info"]["name"] == file_data["info"]["name"], \
            "Endpoint data doesn't match file data"
        assert len(endpoint_data["item"]) == len(file_data["item"]), \
            "Endpoint has different number of folders than file"


class TestPostmanCollectionIntegration:
    """Integration tests for Postman collection workflow"""
    
    def test_collection_can_be_downloaded_and_parsed(self):
        """Test end-to-end: download collection and parse as JSON.

        Requires a live server on localhost:8080; skipped (not failed) when none
        is running so the unit suite stays green without a server.
        """
        import requests

        # Download from endpoint (skip cleanly if no server is up)
        try:
            response = requests.get("http://localhost:8080/postman-collection", timeout=3)
        except requests.exceptions.RequestException:
            pytest.skip("No server running on localhost:8080 (live-server integration test)")
        assert response.status_code == 200, "Failed to download collection"
        
        # Parse as JSON
        data = response.json()
        assert "info" in data, "Downloaded collection is invalid"
        assert len(data["item"]) > 0, "Downloaded collection has no endpoints"
    
    @pytest.mark.skip(reason="Requires Postman CLI installation")
    def test_collection_imports_to_postman_cli(self):
        """Test that collection can be imported via Postman CLI (Newman)"""
        import subprocess
        import tempfile
        
        # Load collection
        collection_path = Path("docs/bijou-api.postman_collection.json")
        with open(collection_path, "r") as f:
            collection_data = f.read()
        
        # Write to temp file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
            tmp.write(collection_data)
            tmp_path = tmp.name
        
        try:
            # Attempt import via Newman (if installed)
            result = subprocess.run(
                ["newman", "run", tmp_path, "--bail"],
                capture_output=True,
                text=True
            )
            # Just check that Newman recognizes it as valid (may fail requests due to auth)
            assert "error" not in result.stderr.lower(), f"Newman import failed: {result.stderr}"
        finally:
            os.unlink(tmp_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
