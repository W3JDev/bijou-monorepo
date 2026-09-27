"""
Bijou AI - Knowledge feeding system
====================================

Handles document ingestion and context management for AI training.
"""

import os
import logging
import tempfile
from datetime import datetime
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class KnowledgeEngine:
    def __init__(self, storage_path: str = "/data/knowledge"):
        # The production image runs as non-root `bijou` with no /data mount
        # (ops/dokploy/Dockerfile.backend.dokploy), so makedirs raised
        # PermissionError and every dashboard knowledge upload / add-text
        # 500'd with "[Errno 13] Permission denied: '/data'" (measured on
        # app.mybijou.xyz 2026-09-28) — and BijouAI's startup init, which
        # constructs this inside one big try, aborted everything after it.
        # Nothing reads these files back (replies use knowledge_documents),
        # so a temp-dir fallback is safe.
        # ponytail: files are ephemeral in the fallback; mount a volume at
        # KNOWLEDGE_STORAGE_PATH if anything ever starts reading them.
        self.storage_path = os.getenv("KNOWLEDGE_STORAGE_PATH", storage_path)
        try:
            os.makedirs(self.storage_path, exist_ok=True)
        except OSError as e:
            fallback = os.path.join(tempfile.gettempdir(), "bijou-knowledge")
            logger.warning(f"⚠️ {self.storage_path} not writable ({e}); using {fallback}")
            self.storage_path = fallback
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
