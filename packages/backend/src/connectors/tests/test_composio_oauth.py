from src.connectors.composio_connector import ComposioConnector


class FakeConnReq:
    def __init__(self, id_="ac_abc123", status="INITIATED", redirect_url="https://accounts.google.com/o/oauth2/x"):
        self.id, self.status, self.redirect_url = id_, status, redirect_url


class FakeConnAccounts:
    def __init__(self, req=None, get_resp=None, exc=None):
        self._req, self._get, self._exc = req, get_resp, exc

    def initiate(self, user_id, auth_config_id, callback_url=None):
        if self._exc:
            raise self._exc
        self.captured = {"user_id": user_id, "auth_config_id": auth_config_id, "callback_url": callback_url}
        return self._req

    def get(self, connection_id):
        self.got = connection_id
        return self._get


class FakeClient:
    def __init__(self, connected_accounts):
        self.connected_accounts = connected_accounts


def test_initiate_connection_returns_redirect_and_id():
    ca = FakeConnAccounts(req=FakeConnReq())
    cc = ComposioConnector(client=FakeClient(ca))
    out = cc.initiate_connection("tenant-9", "ac_sheets", callback_url="https://app/cb")
    assert out == {"connection_id": "ac_abc123", "redirect_url": "https://accounts.google.com/o/oauth2/x", "status": "INITIATED"}
    assert ca.captured == {"user_id": "tenant-9", "auth_config_id": "ac_sheets", "callback_url": "https://app/cb"}


def test_initiate_connection_error_is_captured_not_raised():
    ca = FakeConnAccounts(exc=RuntimeError("composio 500"))
    cc = ComposioConnector(client=FakeClient(ca))
    out = cc.initiate_connection("t", "ac_x")
    assert "error" in out and "composio 500" in out["error"]


def test_connection_status_reads_status_field():
    ca = FakeConnAccounts(get_resp={"status": "ACTIVE"})
    cc = ComposioConnector(client=FakeClient(ca))
    assert cc.connection_status("ac_abc123") == "ACTIVE"
    assert ca.got == "ac_abc123"


def test_connection_status_error_returns_ERROR():
    class Boom:
        def get(self, cid):
            raise RuntimeError("down")
    cc = ComposioConnector(client=FakeClient(Boom()))
    assert cc.connection_status("ac_x") == "ERROR"
