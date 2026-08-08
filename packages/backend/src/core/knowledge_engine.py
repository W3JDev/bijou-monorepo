"""
Bijou AI - Knowledge feeding system
====================================

Handles document ingestion and context management for AI training.
"""

import os
import logging
from datetime import datetime
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class KnowledgeEngine:
    def __init__(self, storage_path: str = "/data/knowledge"):
        self.storage_path = storage_path
        os.makedirs(self.storage_path, exist_ok=True)

    def add_context(self, tenant_id: str, content: str, source_name: str = "manual_entry") -> bool:
        """Add raw text context for a tenant"""
        tenant_path = os.path.join(self.storage_path, tenant_id)
        os.makedirs(tenant_path, exist_ok=True)
        
        file_path = os.path.join(tenant_path, f"{source_name}.txt")
        try:
            with open(file_path, "a", encoding="utf-8") as f:
                f.write(f"\n--- Added on {datetime.now().isoformat()} ---\n")
                f.write(content)
                f.write("\n")
            logger.info(f"✅ Context added for {tenant_id} from {source_name}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to add context: {e}")
            return False

    def get_context(self, tenant_id: str) -> str:
        """Retrieve all knowledge context for a tenant"""
        tenant_path = os.path.join(self.storage_path, tenant_id)
        if not os.path.exists(tenant_path):
            return ""
            
        combined_text = []
        for filename in os.listdir(tenant_path):
            if filename.endswith(".txt"):
                try:
                    with open(os.path.join(tenant_path, filename), "r", encoding="utf-8") as f:
                        combined_text.append(f.read())
                except Exception as e:
                    logger.warning(f"⚠️ Could not read {filename}: {e}")
                    
        return "\n\n".join(combined_text)
