import os
import pytest
from src.connectors.composio_connector import ComposioConnector
from src.connectors.registry import build_registry

_HAVE = all(os.getenv(k) for k in ("COMPOSIO_API_KEY", "COMPOSIO_TEST_TENANT_ID", "COMPOSIO_TEST_SHEET_ID"))


@pytest.mark.skipif(not _HAVE, reason="needs COMPOSIO_API_KEY + a connected test tenant + sheet id")
@pytest.mark.asyncio
async def test_sheets_append_row_live():
    cc = ComposioConnector()  # real client from env
    action = build_registry()["sheets.append_row"]
    r = await cc.execute(
        os.environ["COMPOSIO_TEST_TENANT_ID"], action,
        {"spreadsheet_id": os.environ["COMPOSIO_TEST_SHEET_ID"], "values": ["bijou", "smoke", "test"]},
    )
    assert r.success, r.error
