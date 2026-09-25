"""The QR image URL must follow the configured bridge, not a hardcoded scheme.

The bug
-------
src/saas/onboarding_api.py did:

    # Force HTTPS so an http->https redirect can't drop the auth header.
    img_response = await client.get(qr_link.replace("http://", "https://"), ...)

That upgrade is unconditional. It is right when the bridge sits behind a TLS
terminator, and wrong for every plain-HTTP bridge — including an internal
Docker network, which is how an internal-only bridge SHOULD be reached.

Against a real GOWA bridge on a compose network the QR fetch died with:

    500  {"detail":"[SSL: WRONG_VERSION_NUMBER] wrong version number"}

because it spoke TLS to a plaintext port.

There is a second failure mode the same normalisation fixes. GOWA builds
qr_link from the Host header it saw, so the link can point somewhere the
backend cannot reach — `http://localhost:3000/...` means "the backend itself"
when the backend resolves it, not the bridge.

Taking scheme+host from the CONFIGURED bridge URL and keeping only the path
from qr_link handles both: the scheme follows the deployment, and the host is
always one the backend can actually reach.
"""

import pytest

from src.saas.onboarding_api import _normalise_qr_link


class TestSchemeFollowsTheBridge:
    def test_http_bridge_keeps_http(self):
        """The regression: a plain-HTTP bridge must not be upgraded to TLS."""
        assert _normalise_qr_link(
            "http://bridge:3000/statics/qrcode/scan-qr-abc.png",
            "http://bridge:3000",
        ) == "http://bridge:3000/statics/qrcode/scan-qr-abc.png"

    def test_https_bridge_upgrades(self):
        """The original intent still holds when the bridge really is TLS."""
        assert _normalise_qr_link(
            "http://bridge.internal/statics/qrcode/scan-qr-abc.png",
            "https://bridge.mybijou.xyz",
        ) == "https://bridge.mybijou.xyz/statics/qrcode/scan-qr-abc.png"


class TestHostFollowsTheBridge:
    def test_unreachable_localhost_is_rewritten(self):
        """GOWA builds qr_link from the Host header it saw. `localhost` there
        means the BACKEND when the backend resolves it — never the bridge."""
        assert _normalise_qr_link(
            "http://localhost:3000/statics/qrcode/scan-qr-abc.png",
            "http://bridge:3000",
        ) == "http://bridge:3000/statics/qrcode/scan-qr-abc.png"

    def test_port_from_bridge_url_wins(self):
        assert _normalise_qr_link(
            "http://localhost:8080/statics/qrcode/x.png",
            "http://bridge:3000",
        ) == "http://bridge:3000/statics/qrcode/x.png"

    def test_trailing_slash_on_bridge_url_is_tolerated(self):
        assert _normalise_qr_link(
            "http://localhost:3000/statics/qrcode/x.png",
            "http://bridge:3000/",
        ) == "http://bridge:3000/statics/qrcode/x.png"


class TestPathIsPreserved:
    def test_query_string_survives(self):
        assert _normalise_qr_link(
            "http://localhost:3000/statics/qr.png?v=2",
            "http://bridge:3000",
        ) == "http://bridge:3000/statics/qr.png?v=2"

    def test_relative_link_is_resolved_against_the_bridge(self):
        """Some builds return a path rather than an absolute URL."""
        assert _normalise_qr_link(
            "/statics/qrcode/scan-qr-abc.png",
            "http://bridge:3000",
        ) == "http://bridge:3000/statics/qrcode/scan-qr-abc.png"


class TestDegradesSafely:
    @pytest.mark.parametrize("bad", ["", None])
    def test_missing_qr_link_returns_none(self, bad):
        assert _normalise_qr_link(bad, "http://bridge:3000") is None

    def test_missing_bridge_url_returns_link_unchanged(self):
        """Better to try the original than to invent a URL."""
        link = "http://bridge:3000/statics/x.png"
        assert _normalise_qr_link(link, "") == link
