#!/usr/bin/env python3
"""
WhatsApp Bridge Client - Centralized HTTP client for GOWA bridge
================================================================

Handles Basic Authentication automatically for all bridge requests.
All bridge calls should go through this helper to ensure proper auth.

Usage:
    from src.core.bridge_client import BridgeClient
    
    # Initialize (reads BRIDGE_URL, BRIDGE_USER, BRIDGE_PASSWORD from env)
    client = BridgeClient()
    
    # Make authenticated requests
    response = await client.get("/health")
    response = await client.post("/api/send", json={"recipient": "...", "message": "..."})
"""

import base64
import logging
import os
from typing import Any, Dict, Optional

import aiohttp

logger = logging.getLogger(__name__)


class BridgeClient:
    """
    HTTP client for WhatsApp Bridge with automatic Basic Authentication.
    
    Reads configuration from environment variables:
    - BRIDGE_URL: Base URL of the bridge (required)
    - BRIDGE_USER: Basic auth username (required)
    - BRIDGE_PASSWORD: Basic auth password (required)
    """
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        timeout: int = 30
    ):
        """
        Initialize bridge client with authentication.
        
        Args:
            base_url: Bridge URL (defaults to BRIDGE_URL env var)
            username: Basic auth username (defaults to BRIDGE_USER env var)
            password: Basic auth password (defaults to BRIDGE_PASSWORD env var)
            timeout: Request timeout in seconds (default: 30)
        """
        self.base_url = (base_url or os.getenv("BRIDGE_URL", "")).rstrip("/")
        self.username = username or os.getenv("BRIDGE_USER", "")
        self.password = password or os.getenv("BRIDGE_PASSWORD", "")
        self.timeout = timeout
        
        # Validate configuration
        if not self.base_url:
            raise ValueError(
                "BRIDGE_URL not configured. Set BRIDGE_URL environment variable."
            )
        
        if not self.username or not self.password:
            logger.warning(
                "⚠️ BRIDGE_USER or BRIDGE_PASSWORD not set. "
                "Bridge requests may fail with 401 Unauthorized."
            )
        
        # Generate Basic Auth header
        self._auth_header = self._generate_auth_header()
        
        logger.debug(f"✅ Bridge client initialized: {self.base_url}")
    
    def _generate_auth_header(self) -> str:
        """Generate Basic Authorization header value."""
        if not self.username or not self.password:
            return ""
        
        credentials = f"{self.username}:{self.password}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return f"Basic {encoded}"
    
    def _get_headers(self, additional_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """
        Get headers with Basic Auth included.
        
        Args:
            additional_headers: Extra headers to include
            
        Returns:
            Dict of headers with Authorization header
        """
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        
        if self._auth_header:
            headers["Authorization"] = self._auth_header
        
        if additional_headers:
            headers.update(additional_headers)
        
        return headers
    
    async def get(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> aiohttp.ClientResponse:
        """
        Make authenticated GET request to bridge.
        
        Args:
            path: API path (e.g., "/health", "/api/devices")
            params: Query parameters
            headers: Additional headers
            
        Returns:
            aiohttp.ClientResponse object
            
        Raises:
            aiohttp.ClientError: On request failure
        """
        url = f"{self.base_url}{path}"
        headers = self._get_headers(headers)
        
        logger.debug(f"🔵 GET {url}")
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
            async with session.get(
                url,
                params=params,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as response:
                logger.debug(f"   📥 HTTP {response.status}")
                return response
    
    async def post(
        self,
        path: str,
        json: Optional[Dict[str, Any]] = None,
        data: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> aiohttp.ClientResponse:
        """
        Make authenticated POST request to bridge.
        
        Args:
            path: API path (e.g., "/api/send")
            json: JSON payload
            data: Form data payload
            headers: Additional headers
            
        Returns:
            aiohttp.ClientResponse object
            
        Raises:
            aiohttp.ClientError: On request failure
        """
        url = f"{self.base_url}{path}"
        headers = self._get_headers(headers)
        
        logger.debug(f"🟢 POST {url}")
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
            async with session.post(
                url,
                json=json,
                data=data,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as response:
                logger.debug(f"   📥 HTTP {response.status}")
                return response
    
    async def delete(
        self,
        path: str,
        headers: Optional[Dict[str, str]] = None
    ) -> aiohttp.ClientResponse:
        """
        Make authenticated DELETE request to bridge.
        
        Args:
            path: API path
            headers: Additional headers
            
        Returns:
            aiohttp.ClientResponse object
            
        Raises:
            aiohttp.ClientError: On request failure
        """
        url = f"{self.base_url}{path}"
        headers = self._get_headers(headers)
        
        logger.debug(f"🔴 DELETE {url}")
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
            async with session.delete(
                url,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as response:
                logger.debug(f"   📥 HTTP {response.status}")
                return response
    
    # Synchronous versions for compatibility
    
    def get_sync(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Synchronous GET request (uses requests library).
        
        Args:
            path: API path
            params: Query parameters
            headers: Additional headers
            
        Returns:
            Response JSON as dict
            
        Raises:
            requests.RequestException: On request failure
        """
        import requests
        
        url = f"{self.base_url}{path}"
        headers = self._get_headers(headers)
        
        logger.debug(f"🔵 GET (sync) {url}")
        
        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=self.timeout
        )
        
        logger.debug(f"   📥 HTTP {response.status_code}")
        response.raise_for_status()
        
        return response.json()
    
    def post_sync(
        self,
        path: str,
        json: Optional[Dict[str, Any]] = None,
        data: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Synchronous POST request (uses requests library).
        
        Args:
            path: API path
            json: JSON payload
            data: Form data payload
            headers: Additional headers
            
        Returns:
            Response JSON as dict
            
        Raises:
            requests.RequestException: On request failure
        """
        import requests
        
        url = f"{self.base_url}{path}"
        headers = self._get_headers(headers)
        
        logger.debug(f"🟢 POST (sync) {url}")
        
        response = requests.post(
            url,
            json=json,
            data=data,
            headers=headers,
            timeout=self.timeout
        )
        
        logger.debug(f"   📥 HTTP {response.status_code}")
        response.raise_for_status()
        
        return response.json()


# Singleton instance for shared use
_bridge_client: Optional[BridgeClient] = None


def get_bridge_client() -> BridgeClient:
    """
    Get shared bridge client instance (singleton pattern).
    
    Returns:
        BridgeClient instance with configuration from environment
    """
    global _bridge_client
    
    if _bridge_client is None:
        _bridge_client = BridgeClient()
    
    return _bridge_client
