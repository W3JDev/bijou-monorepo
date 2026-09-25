"""Inbound media is only fetched from the bridge.

The media download in BijouAI.process_message sends BRIDGE_USER/BRIDGE_PASSWORD
as Basic Auth to `media_url`, which comes from the webhook payload. The GOWA
parser passes an absolute "http..." media field through verbatim, so a forged
webhook (possible whenever BIJOU_WEBHOOK_SECRET is unset) could make the backend
fetch any URL (SSRF) and leak the bridge credentials to it. The guard rejects
anything that is not same-origin with the configured bridge.
"""

import importlib

import pytest

BRIDGE = "http://bridge:3000"


@pytest.fixture
def guard():
    return importlib.import_module("src.core.bijou")._is_bridge_media_url


@pytest.mark.parametrize("url", [
    "http://bridge:3000/statics/media/abc.ogg",
    "http://BRIDGE:3000/api/media/1?chat_jid=x",
])
def test_bridge_urls_allowed(guard, url):
    assert guard(url, BRIDGE)


@pytest.mark.parametrize("url", [
    "https://evil.example/steal",               # foreign host
    "http://bridge:3001/statics/media/a.ogg",   # other port on same host
    "https://bridge:3000/statics/media/a.ogg",  # scheme change
    "http://bridge:3000@evil.example/a.ogg",    # userinfo trick
    "http://evil.example\\@bridge:3000/a.ogg",  # backslash trick
    "http://169.254.169.254/latest/meta-data/", # cloud metadata
    "tg://file/bot?file_id=1",
    "http://bridge:notaport/a",
    "",
])
def test_non_bridge_urls_rejected(guard, url):
    assert not guard(url, BRIDGE)


def test_unconfigured_bridge_rejects_everything(guard):
    assert not guard("http://bridge:3000/statics/media/a.ogg", "", "")


def test_default_port_equivalence(guard):
    assert guard("https://gowa.example:443/statics/media/a.ogg", "https://gowa.example")
