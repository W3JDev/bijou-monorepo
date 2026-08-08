"""
CRM Tool for Bijou AI
======================

Manages customer relationships, leads, and contact data.
Integrates with the main database (Supabase).
"""

import logging
import os
from typing import Any, Dict, List, Optional
from supabase import create_client, Client

logger = logging.getLogger(__name__)

class CRMTool:
    """
    CRM Tool to manage customers and leads.
    """

    def __init__(self, supabase_client: Optional[Client] = None):
        """
        Initialize CRM tool with Supabase client.
        """
        if supabase_client:
            self.supabase = supabase_client
        else:
            url = os.getenv("SUPABASE_URL")
            key = os.getenv("SUPABASE_SERVICE_KEY")
            if url and key:
                self.supabase = create_client(url, key)
            else:
                self.supabase = None
                logger.warning("⚠️ CRM tool disabled: Supabase not configured")

    def search_customer(self, query: str, tenant_id: str) -> Dict[str, Any]:
        """Search for a customer by name or phone/JID"""
        if not self.supabase:
            return {"success": False, "error": "CRM database not configured"}
            
        try:
            # Search in contacts or leads
            res = self.supabase.table("contacts").select("*").eq("tenant_id", tenant_id).or_(f"name.ilike.%{query}%,phone.ilike.%{query}%").execute()
            return {"success": True, "results": res.data}
        except Exception as e:
            logger.error(f"❌ CRM Search error: {e}")
            return {"success": False, "error": str(e)}

    def add_lead(self, name: str, phone: str, details: Optional[str] = None) -> Dict[str, Any]:
        """Add a new lead to the CRM"""
        if not self.supabase:
            return {"success": False, "error": "CRM database not configured"}
            
        try:
            data = {
                "name": name,
                "phone": phone,
                "details": details,
                "status": "new"
            }
            res = self.supabase.table("leads").insert(data).execute()
            return {"success": True, "lead_id": res.data[0].get("id") if res.data else None}
        except Exception as e:
            logger.error(f"❌ CRM Add Lead error: {e}")
            return {"success": False, "error": str(e)}

    def update_customer_status(self, customer_id: str, status: str, tenant_id: str) -> Dict[str, Any]:
        """Update customer stage/status"""
        if not self.supabase:
            return {"success": False, "error": "CRM database not configured"}
            
        try:
            res = self.supabase.table("contacts").update({"status": status}).eq("tenant_id", tenant_id).eq("id", customer_id).execute()
            return {"success": True, "updated": bool(res.data)}
        except Exception as e:
            logger.error(f"❌ CRM Update error: {e}")
            return {"success": False, "error": str(e)}
