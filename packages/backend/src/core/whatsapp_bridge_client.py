"""
WhatsApp Bridge Client - Unified adapter for GOWA bridge
Supports multi-device architecture with retry logic and error handling
"""

import httpx
import base64
import time
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class WhatsAppBridgeClient:
    """
    Unified client for WhatsApp bridge (GOWA - go-whatsapp-web-multidevice)
    
    Features:
    - Multi-device support
    - Basic authentication
    - Automatic retry with exponential backoff
    - Comprehensive error handling
    - Device management
    """
    
    def __init__(self, base_url: str, api_key: str, device_id: Optional[str] = None):
        """
        Initialize bridge client
        
        Args:
            base_url: Bridge URL (e.g., http://localhost:8081)
            api_key: API key in format "username:password" for Basic Auth
            device_id: Device ID for multi-device support (tenant identifier)
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.device_id = device_id
        self.client = httpx.Client(timeout=30.0)
        
        # Setup Basic Auth headers
        if ':' in api_key:
            auth_str = base64.b64encode(api_key.encode()).decode()
            self.headers = {
                "Authorization": f"Basic {auth_str}",
                "Content-Type": "application/json"
            }
        else:
            self.headers = {
                "X-API-Key": api_key,
                "Content-Type": "application/json"
            }
        
        # Add device ID header if provided
        if device_id:
            self.headers["X-Device-Id"] = device_id
    
    def _get_url(self, endpoint: str) -> str:
        """Build full URL with device_id query param if needed"""
        url = f"{self.base_url}{endpoint}"
        if self.device_id and '?' not in endpoint:
            url += f"?device_id={self.device_id}"
        elif self.device_id:
            url += f"&device_id={self.device_id}"
        return url
    
    def check_connection(self) -> bool:
        """
        Check if bridge is connected to WhatsApp
        
        Returns:
            bool: True if connected, False otherwise
        """
        try:
            url = self._get_url("/app/status")
            response = self.client.get(url, headers=self.headers)
            
            if response.status_code == 200:
                data = response.json()
                return data.get("results", {}).get("is_connected", False)
            return False
        except Exception as e:
            logger.error(f"Failed to check connection: {e}")
            return False
    
    def get_devices(self) -> Dict[str, Any]:
        """
        Get list of all devices registered on the bridge (GOWA v8+)
        
        Note: In GOWA v8+, this endpoint lists all devices without requiring device_id.
        
        Returns:
            dict: Response with device list in 'results' array
        """
        try:
            # Use /devices endpoint which doesn't require device context
            url = f"{self.base_url}/devices"
            response = self.client.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get devices: {e}")
            return {"code": "ERROR", "message": str(e), "results": []}
    
    def create_device(self, device_name: str) -> Dict[str, Any]:
        """
        Create a new device for multi-tenant support (GOWA v8+)
        
        Args:
            device_name: Display name for the device
            
        Returns:
            dict: Response with device_id and metadata
                {
                    "code": "SUCCESS",
                    "message": "Device added",
                    "results": {
                        "id": "device-uuid",
                        "state": "disconnected",
                        "created_at": "2024-01-01T00:00:00Z",
                        ...
                    }
                }
        """
        try:
            url = f"{self.base_url}/devices"
            payload = {"name": device_name}
            
            # Include custom device_id if provided (GOWA v8+ supports this)
            if self.device_id:
                payload["device_id"] = self.device_id
            
            response = self.client.post(
                url,
                headers=self.headers,
                json=payload
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to create device: {e}")
            return {"code": "ERROR", "message": str(e)}
    
    def delete_device(self, device_id: str) -> Dict[str, Any]:
        """
        Delete a device from the bridge (GOWA v8+)
        
        Args:
            device_id: Device ID to delete
            
        Returns:
            dict: Response confirmation
        """
        try:
            url = f"{self.base_url}/devices/{device_id}"
            response = self.client.delete(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to delete device {device_id}: {e}")
            return {"code": "ERROR", "message": str(e)}
    
    def get_device_info(self, device_id: str) -> Dict[str, Any]:
        """
        Get device information (GOWA v8+)
        
        Args:
            device_id: Device ID to query
            
        Returns:
            dict: Device information
        """
        try:
            url = f"{self.base_url}/devices/{device_id}"
            response = self.client.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get device info for {device_id}: {e}")
            return {"code": "ERROR", "message": str(e)}
    
    def get_qr_code(self, device_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get QR code for device onboarding (GOWA v8+)
        
        Note: Device must already exist in bridge before calling this.
        Use create_device() first if device doesn't exist.
        
        Args:
            device_id: Device ID to get QR code for. If not provided, uses self.device_id
        
        Returns:
            dict: Response with QR code data including qr_link and qr_duration
                {
                    "code": "SUCCESS",
                    "message": "Login success",
                    "results": {
                        "device_id": "uuid",
                        "qr_duration": 30,
                        "qr_link": "http://.../scan-qr-xxx.png"
                    }
                }
        """
        try:
            # Use provided device_id or fall back to instance device_id
            target_device_id = device_id or self.device_id
            
            # GOWA v8 still uses /app/login endpoint for QR generation
            # The device_id is passed as query parameter
            url = f"{self.base_url}/app/login"
            if target_device_id:
                url += f"?device_id={target_device_id}"
            
            # Add device_id to headers as well (GOWA v8 supports both)
            headers = self.headers.copy()
            if target_device_id:
                headers["X-Device-Id"] = target_device_id
            
            response = self.client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get QR code for device {device_id}: {e}")
            return {"code": "ERROR", "message": str(e)}
    
    def get_pairing_code(self, phone: str) -> Dict[str, Any]:
        """
        Get pairing code for device onboarding (alternative to QR)
        
        Args:
            phone: Phone number (e.g., "628123456789")
            
        Returns:
            dict: Response with pairing code
        """
        try:
            url = self._get_url(f"/app/login-with-code?phone={phone}")
            response = self.client.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get pairing code: {e}")
            return {"code": "ERROR", "message": str(e)}
    
    def logout(self) -> Dict[str, Any]:
        """
        Logout and remove device data
        
        Returns:
            dict: Response confirmation
        """
        try:
            url = self._get_url("/app/logout")
            response = self.client.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to logout: {e}")
            return {"code": "ERROR", "message": str(e)}
    
    def reconnect(self) -> Dict[str, Any]:
        """
        Reconnect to WhatsApp server
        
        Returns:
            dict: Response confirmation
        """
        try:
            url = self._get_url("/app/reconnect")
            response = self.client.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to reconnect: {e}")
            return {"code": "ERROR", "message": str(e)}
    
    def send_text(self, phone: str, message: str, retry: int = 3) -> Dict[str, Any]:
        """
        Send text message with retry logic
        
        Args:
            phone: Recipient phone number (e.g., "628123456789")
            message: Message text
            retry: Number of retry attempts
            
        Returns:
            dict: Response with message ID
        """
        for attempt in range(retry):
            try:
                url = self._get_url("/send/message")
                response = self.client.post(
                    url,
                    headers=self.headers,
                    json={
                        "phone": phone,
                        "message": message
                    }
                )
                response.raise_for_status()
                return response.json()
            except Exception as e:
                logger.warning(f"Send message attempt {attempt + 1}/{retry} failed: {e}")
                if attempt == retry - 1:
                    raise
                time.sleep(2 ** attempt)  # Exponential backoff: 1s, 2s, 4s
    
    def send_image(self, phone: str, image_url: str, caption: str = "", retry: int = 3) -> Dict[str, Any]:
        """
        Send image message
        
        Args:
            phone: Recipient phone number
            image_url: URL or base64 of image
            caption: Optional image caption
            retry: Number of retry attempts
            
        Returns:
            dict: Response with message ID
        """
        for attempt in range(retry):
            try:
                url = self._get_url("/send/image")
                response = self.client.post(
                    url,
                    headers=self.headers,
                    json={
                        "phone": phone,
                        "image": image_url,
                        "caption": caption
                    }
                )
                response.raise_for_status()
                return response.json()
            except Exception as e:
                logger.warning(f"Send image attempt {attempt + 1}/{retry} failed: {e}")
                if attempt == retry - 1:
                    raise
                time.sleep(2 ** attempt)
    
    def send_video(self, phone: str, video_url: str, caption: str = "", retry: int = 3) -> Dict[str, Any]:
        """
        Send video message
        
        Args:
            phone: Recipient phone number
            video_url: URL or base64 of video
            caption: Optional video caption
            retry: Number of retry attempts
            
        Returns:
            dict: Response with message ID
        """
        for attempt in range(retry):
            try:
                url = self._get_url("/send/video")
                response = self.client.post(
                    url,
                    headers=self.headers,
                    json={
                        "phone": phone,
                        "video": video_url,
                        "caption": caption
                    }
                )
                response.raise_for_status()
                return response.json()
            except Exception as e:
                logger.warning(f"Send video attempt {attempt + 1}/{retry} failed: {e}")
                if attempt == retry - 1:
                    raise
                time.sleep(2 ** attempt)
    
    def send_file(self, phone: str, file_url: str, caption: str = "", retry: int = 3) -> Dict[str, Any]:
        """
        Send file/document message
        
        Args:
            phone: Recipient phone number
            file_url: URL or base64 of file
            caption: Optional file caption
            retry: Number of retry attempts
            
        Returns:
            dict: Response with message ID
        """
        for attempt in range(retry):
            try:
                url = self._get_url("/send/file")
                response = self.client.post(
                    url,
                    headers=self.headers,
                    json={
                        "phone": phone,
                        "file": file_url,
                        "caption": caption
                    }
                )
                response.raise_for_status()
                return response.json()
            except Exception as e:
                logger.warning(f"Send file attempt {attempt + 1}/{retry} failed: {e}")
                if attempt == retry - 1:
                    raise
                time.sleep(2 ** attempt)
    
    def send_audio(self, phone: str, audio_url: str, retry: int = 3) -> Dict[str, Any]:
        """
        Send audio message
        
        Args:
            phone: Recipient phone number
            audio_url: URL or base64 of audio
            retry: Number of retry attempts
            
        Returns:
            dict: Response with message ID
        """
        for attempt in range(retry):
            try:
                url = self._get_url("/send/audio")
                response = self.client.post(
                    url,
                    headers=self.headers,
                    json={
                        "phone": phone,
                        "audio": audio_url
                    }
                )
                response.raise_for_status()
                return response.json()
            except Exception as e:
                logger.warning(f"Send audio attempt {attempt + 1}/{retry} failed: {e}")
                if attempt == retry - 1:
                    raise
                time.sleep(2 ** attempt)
    
    def get_user_info(self, phone: str) -> Dict[str, Any]:
        """
        Get user information
        
        Args:
            phone: Phone number to query
            
        Returns:
            dict: User information
        """
        try:
            url = self._get_url(f"/user/info?phone={phone}")
            response = self.client.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get user info: {e}")
            return {"code": "ERROR", "message": str(e)}
    
    def close(self):
        """Close HTTP client"""
        self.client.close()
