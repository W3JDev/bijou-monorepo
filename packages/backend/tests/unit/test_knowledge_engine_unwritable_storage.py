"""KnowledgeEngine must not raise when its storage dir is unwritable.

Production (non-root container, no /data mount) raised
PermissionError: [Errno 13] Permission denied: '/data' from __init__, so every
dashboard knowledge upload / add-text returned 500 (observed on
app.mybijou.xyz 2026-09-28).
"""

import os
import tempfile

from src.core import knowledge_engine as ke


def test_unwritable_storage_falls_back_and_still_stores(monkeypatch, tmp_path):
    real_makedirs = os.makedirs

    def makedirs(path, *a, **kw):
        if str(path).startswith("/data"):
            raise PermissionError(13, "Permission denied", "/data")
        return real_makedirs(path, *a, **kw)

    monkeypatch.setattr(ke.os, "makedirs", makedirs)
    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(tmp_path))
    monkeypatch.delenv("KNOWLEDGE_STORAGE_PATH", raising=False)

    engine = ke.KnowledgeEngine()  # default "/data/knowledge"

    assert engine.storage_path == os.path.join(str(tmp_path), "bijou-knowledge")
    assert engine.add_context("tenant-1", "We open 9-6.", "faq") is True
    assert "We open 9-6." in engine.get_context("tenant-1")
