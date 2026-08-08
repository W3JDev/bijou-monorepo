from src.connectors.auth_configs import auth_config_id, supported_toolkits


def test_auth_config_id_reads_env(monkeypatch):
    monkeypatch.setenv("COMPOSIO_AUTH_ID_GOOGLE_SHEETS", "ac_sheets_1")
    assert auth_config_id("googlesheets") == "ac_sheets_1"
    assert auth_config_id("GoogleSheets") == "ac_sheets_1"  # case-insensitive


def test_auth_config_id_unknown_or_unset_is_none(monkeypatch):
    monkeypatch.delenv("COMPOSIO_AUTH_ID_LINKEDIN", raising=False)
    assert auth_config_id("linkedin") is None
    assert auth_config_id("nonexistent_toolkit") is None


def test_supported_toolkits_lists_only_configured(monkeypatch):
    for k in ("COMPOSIO_AUTH_ID_GOOGLE_SHEETS", "COMPOSIO_AUTH_ID_GOOGLE_CALENDAR",
              "COMPOSIO_AUTH_ID_GOOGLE_DRIVE", "COMPOSIO_AUTH_ID_GOOGLE_DOCS",
              "COMPOSIO_AUTH_ID_GOOGLE_TASKS", "COMPOSIO_AUTH_ID_LINKEDIN",
              "COMPOSIO_AUTH_ID_INSTAGRAM"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("COMPOSIO_AUTH_ID_GOOGLE_SHEETS", "ac_1")
    monkeypatch.setenv("COMPOSIO_AUTH_ID_INSTAGRAM", "ac_2")
    assert set(supported_toolkits()) == {"googlesheets", "instagram"}
