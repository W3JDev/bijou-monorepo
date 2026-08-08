"""
Session Manager - Handle WhatsApp device session lifecycle
Manages device sessions for multi-tenant WhatsApp connectivity via GOWA bridge
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from uuid import UUID
from supabase import Client

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Manages WhatsApp device sessions for multi-tenant architecture
    
    Responsibilities:
    - Create and delete device sessions
    - Track session status (pending, active, disconnected, expired)
    - Map device_id to tenant_id for webhook routing
    - Monitor session health and expiration
    """
    
    def __init__(self, supabase_client: Client):
        """
        Initialize SessionManager
        
        Args:
            supabase_client: Authenticated Supabase client
        """
        self.supabase = supabase_client
    
    async def create_session(
        self,
        tenant_id: UUID,
        device_id: str,
        bridge_url: str,
        status: str = "pending",
        qr_code_url: Optional[str] = None,
        qr_duration: int = 30
    ) -> Dict[str, Any]:
        """
        Create a new device session for onboarding
        
        Args:
            tenant_id: UUID of the tenant
            device_id: Device ID from GOWA bridge
            qr_code_url: URL to QR code image (optional)
            qr_duration: QR code validity in seconds
            
        Returns:
            dict: Created session data
        """
        try:
            qr_expires_at = datetime.utcnow() + timedelta(seconds=qr_duration)
            
            session_data = {
                "tenant_id": str(tenant_id),
                "device_id": device_id,
                "bridge_url": bridge_url, # Storing the bridge URL
                "status": status,
                "qr_code_url": qr_code_url,
                "qr_expires_at": qr_expires_at.isoformat(),
                "created_at": datetime.utcnow().isoformat()
            }
            
            result = self.supabase.table("device_sessions").insert(session_data).execute()
            
            logger.info(f"Created session for tenant {tenant_id}, device {device_id}")
            return result.data[0] if result.data else {}
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            raise
    
    async def get_session_by_device_id(self, device_id: str, tenant_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get session by device ID
        
        Args:
            device_id: Device ID from GOWA
            tenant_id: Optional tenant ID for additional security
            
        Returns:
            dict: Session data or None
        """
        try:
            query = self.supabase.table("device_sessions").select("*").eq("device_id", device_id)
            if tenant_id:
                query = query.eq("tenant_id", tenant_id)
            result = query.execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Failed to get session by device_id {device_id}: {e}")
            return None
    
    async def get_session_by_tenant_id(self, tenant_id: UUID) -> Optional[Dict[str, Any]]:
        """
        Get active session for a tenant
        
        Args:
            tenant_id: UUID of the tenant
            
        Returns:
            dict: Session data or None
        """
        try:
            result = (
                self.supabase.table("device_sessions")
                .select("*")
                .eq("tenant_id", str(tenant_id))
                .eq("status", "active")
                .execute()
            )
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Failed to get session for tenant {tenant_id}: {e}")
            return None
    
    async def update_session_status(
        self,
        device_id: str,
        status: str,
        whatsapp_jid: Optional[str] = None,
        tenant_id: Optional[str] = None
    ) -> bool:
        """
        Update session status (e.g., pending -> active after QR scan)
        
        Args:
            device_id: Device ID from GOWA
            status: New status ('pending', 'active', 'disconnected', 'expired')
            whatsapp_jid: WhatsApp JID (e.g., "628123456789@s.whatsapp.net")
            tenant_id: Optional tenant ID for additional security
            
        Returns:
            bool: Success status
        """
        try:
            update_data = {
                "status": status,
                "last_seen": datetime.utcnow().isoformat()
            }
            
            if whatsapp_jid:
                update_data["whatsapp_jid"] = whatsapp_jid
            
            if status == "active":
                update_data["connected_at"] = datetime.utcnow().isoformat()
            
            query = self.supabase.table("device_sessions").update(update_data).eq("device_id", device_id)
            
            if tenant_id:
                query = query.eq("tenant_id", tenant_id)
            
            result = query.execute()
            
            # Also update tenants table for quick access
            if status == "active" and whatsapp_jid:
                session = await self.get_session_by_device_id(device_id)
                if session:
                    self.supabase.table("tenants").update({
                        "device_id": device_id,
                        "whatsapp_jid": whatsapp_jid,
                        "session_active": True,
                        "session_connected_at": datetime.utcnow().isoformat()
                    }).eq("id", session["tenant_id"]).execute()
            
            logger.info(f"Updated session {device_id} to status: {status}")
            return True
        except Exception as e:
            logger.error(f"Failed to update session status: {e}")
            return False
    
    async def delete_session(self, device_id: str, tenant_id: Optional[str] = None) -> bool:
        """
        Delete a device session (e.g., during logout)
        
        Args:
            device_id: Device ID from GOWA
            tenant_id: Optional tenant ID for additional security
            
        Returns:
            bool: Success status
        """
        try:
            # Get session to find tenant_id
            session = await self.get_session_by_device_id(device_id, tenant_id)
            if not session:
                logger.warning(f"Session {device_id} not found for deletion")
                return False
            
            # Delete from device_sessions with tenant_id filter
            query = self.supabase.table("device_sessions").delete().eq("device_id", device_id)
            if tenant_id:
                query = query.eq("tenant_id", tenant_id)
            query.execute()
            
            # Clear tenant device mapping
            self.supabase.table("tenants").update({
                "device_id": None,
                "whatsapp_jid": None,
                "session_active": False
            }).eq("id", session["tenant_id"]).execute()
            
            logger.info(f"Deleted session {device_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete session: {e}")
            return False
    
    async def get_tenant_id_by_device_id(self, device_id: str) -> Optional[UUID]:
        """
        Map device_id to tenant_id for webhook routing
        
        Args:
            device_id: Device ID from GOWA webhook
            
        Returns:
            UUID: Tenant ID or None
        """
        session = await self.get_session_by_device_id(device_id)
        if session:
            return UUID(session["tenant_id"])
        return None
    
    async def list_active_sessions(self, tenant_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all active device sessions
        
        Args:
            tenant_id: Optional tenant ID to filter sessions (None = all tenants, admin only)
        
        Returns:
            list: Active session data
        """
        try:
            query = (
                self.supabase.table("device_sessions")
                .select("*, tenants(*)")
                .eq("status", "active")
            )
            
            if tenant_id:
                query = query.eq("tenant_id", tenant_id)
            
            result = query.execute()
            return result.data
        except Exception as e:
            logger.error(f"Failed to list active sessions: {e}")
            return []
    
    async def expire_old_qr_codes(self, tenant_id: Optional[str] = None) -> int:
        """
        Mark sessions with expired QR codes as 'expired'
        
        Args:
            tenant_id: Optional tenant ID to filter sessions (None = all tenants, system maintenance)
        
        Returns:
            int: Number of sessions marked as expired
        """
        try:
            now = datetime.utcnow().isoformat()
            query = (
                self.supabase.table("device_sessions")
                .update({"status": "expired"})
                .eq("status", "pending")
                .lt("qr_expires_at", now)
            )
            
            if tenant_id:
                query = query.eq("tenant_id", tenant_id)
            
            result = query.execute()
            count = len(result.data) if result.data else 0
            if count > 0:
                logger.info(f"Expired {count} old QR codes")
            return count
        except Exception as e:
            logger.error(f"Failed to expire old QR codes: {e}")
            return 0
    
    async def mark_inactive_sessions(self, threshold_hours: int = 24, tenant_id: Optional[str] = None) -> int:
        """
        Mark sessions as 'disconnected' if no activity for threshold_hours
        
        Args:
            threshold_hours: Hours of inactivity before marking disconnected
            tenant_id: Optional tenant ID to filter sessions (None = all tenants, system maintenance)
            
        Returns:
            int: Number of sessions marked as disconnected
        """
        try:
            threshold = datetime.utcnow() - timedelta(hours=threshold_hours)
            threshold_iso = threshold.isoformat()
            
            query = (
                self.supabase.table("device_sessions")
                .update({"status": "disconnected"})
                .eq("status", "active")
                .lt("last_seen", threshold_iso)
            )
            
            if tenant_id:
                query = query.eq("tenant_id", tenant_id)
            
            result = query.execute()
            count = len(result.data) if result.data else 0
            if count > 0:
                logger.warning(f"Marked {count} sessions as disconnected (inactive > {threshold_hours}h)")
            return count
        except Exception as e:
            logger.error(f"Failed to mark inactive sessions: {e}")
            return 0
