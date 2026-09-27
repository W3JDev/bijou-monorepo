"""POST /api/kb-templates/{vertical}/apply ("Apply to My AI - Go Live").

Every apply returned 500 on production (2026-09-28), for three stacked reasons
this fake enforces the way the real database / supabase-py do:
  - .containedBy() is not a supabase-py method (AttributeError)
  - knowledge_bases.source_type has a CHECK constraint that rejects "template"
  - knowledge_documents.file_size_kb is INTEGER (0.53 is rejected)
  - client_configs.client_type is NOT NULL (Google-signup tenants have no row)
"""

import asyncio
import types

from src.saas.kb_templates_api import ApplyTemplateRequest, apply_template

ALLOWED_SOURCE_TYPES = {"google_sheets", "file_upload", "manual", "web_scrape"}
TEMPLATE = {
    "id": "tmpl-1",
    "variables": [{"key": "BUSINESS_NAME", "required": True}],
    "faq_template": [{"category": "pricing", "question": "Price?", "answer_template": "{{BUSINESS_NAME}} is cheap"}],
    "greeting_template": "Hi from {{BUSINESS_NAME}}",
}


class _Query:
    """Only the builder methods supabase-py really has; anything else raises."""

    def __init__(self, db, table):
        self.db, self.table, self.rows, self.op = db, table, None, "select"

    def select(self, *_a, **_k): return self
    def eq(self, *_a): return self
    def limit(self, *_a): return self
    def contains(self, *_a): return self
    def contained_by(self, *_a): return self
    def delete(self): self.op = "delete"; return self
    def update(self, _row): self.op = "update"; return self

    def insert(self, rows):
        self.op, self.rows = "insert", rows if isinstance(rows, list) else [rows]
        for r in self.rows:
            if self.table == "knowledge_bases":
                assert r["source_type"] in ALLOWED_SOURCE_TYPES, "violates valid_source_type"
            if self.table == "knowledge_documents":
                assert isinstance(r["file_size_kb"], int), "file_size_kb is INTEGER"
            if self.table == "client_configs":
                assert r.get("client_type"), "client_type is NOT NULL"
        return self

    def execute(self):
        if self.op == "insert":
            return types.SimpleNamespace(data=[{"id": f"row-{i}"} for i, _ in enumerate(self.rows)])
        if self.table == "industry_kb_templates":
            return types.SimpleNamespace(data=[TEMPLATE])
        return types.SimpleNamespace(data=[])  # no client_configs row (Google signup)


class _DB:
    def table(self, name): return _Query(self, name)


def test_apply_template_succeeds_against_real_constraints():
    req = types.SimpleNamespace(app=types.SimpleNamespace(state=types.SimpleNamespace(supabase=_DB())))
    body = ApplyTemplateRequest(filled_variables={"BUSINESS_NAME": "E2E Co"})

    result = asyncio.run(apply_template("fnb", body, req, tenant_id="t-1"))

    assert result["success"] is True
    assert result["kb_entries_created"] == 2  # 1 FAQ category + auto-reply
