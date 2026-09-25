"""Whether the agent may answer in a WhatsApp GROUP chat.

Why this file exists
--------------------
The decision — "group chat support on or off for this message" — had no test
coverage at all. tests/unit/test_group_chat_detection.py covers `is_group_chat`,
which only parses a JID and says whether it looks like a group. That is the
easy half. The half that decides whether the bot SPEAKS was untested.

tests/integration/test_group_chat_webhook.py looked like it covered this and
did not: it replaced `bijou_instance` with a MagicMock, so
`BijouAI.process_message` — which is where the skip actually happens — never
ran. Two of its assertions therefore failed against an empty mock set rather
than against any real behaviour. Those tests now assert the webhook's real
contract (accept and queue), and the decision is asserted here.

To make that possible the branch was lifted out of `process_message` into
`_group_chat_support_enabled`. It sat roughly 500 lines into a method that
needs a database, a tenant router and a live message before it is reachable,
which is why nobody had tested it.

Failing closed is the point
---------------------------
A bot replying in a customer's group chat is embarrassing in a way a missed
reply is not, so absence of configuration must mean OFF.
"""

import pytest

from src.core.bijou import _group_chat_support_enabled


@pytest.fixture(autouse=True)
def clear_env(monkeypatch):
    monkeypatch.delenv("ENABLE_GROUP_CHAT_SUPPORT", raising=False)


class TestGlobalDefault:
    def test_unset_means_disabled(self):
        """Fail closed. This is the case that matters most."""
        assert _group_chat_support_enabled() is False

    def test_enabled_by_env(self, monkeypatch):
        monkeypatch.setenv("ENABLE_GROUP_CHAT_SUPPORT", "true")
        assert _group_chat_support_enabled() is True

    def test_env_is_case_insensitive_and_trimmed(self, monkeypatch):
        monkeypatch.setenv("ENABLE_GROUP_CHAT_SUPPORT", "  TRUE  ")
        assert _group_chat_support_enabled() is True

    @pytest.mark.parametrize("value", ["false", "False", "0", "no", "", "yes", "1", "on"])
    def test_only_true_enables_it(self, monkeypatch, value):
        """The env var is a strict "true"/not-true switch. Anything else — a
        typo, an empty value, a well-meant "yes" — leaves it off rather than
        guessing that the operator meant to enable it."""
        monkeypatch.setenv("ENABLE_GROUP_CHAT_SUPPORT", value)
        assert _group_chat_support_enabled() is False


class TestTenantOverride:
    """Currently INERT in production: client_config is `SELECT *` from
    `client_configs` and that table has no `enable_group_chat` column
    (verified against the live database, 2026-09-06). These tests pin the
    intended semantics so the column can be added without re-deriving them."""

    def test_absent_key_falls_back_to_the_global(self, monkeypatch):
        monkeypatch.setenv("ENABLE_GROUP_CHAT_SUPPORT", "true")
        assert _group_chat_support_enabled({"some_other_setting": 1}) is True

    def test_empty_config_falls_back_to_the_global(self, monkeypatch):
        monkeypatch.setenv("ENABLE_GROUP_CHAT_SUPPORT", "true")
        assert _group_chat_support_enabled({}) is True

    def test_none_config_falls_back_to_the_global(self, monkeypatch):
        monkeypatch.setenv("ENABLE_GROUP_CHAT_SUPPORT", "true")
        assert _group_chat_support_enabled(None) is True

    def test_tenant_can_opt_out_of_a_global_yes(self, monkeypatch):
        monkeypatch.setenv("ENABLE_GROUP_CHAT_SUPPORT", "true")
        assert _group_chat_support_enabled({"enable_group_chat": False}) is False

    def test_tenant_can_opt_in_to_a_global_no(self):
        assert _group_chat_support_enabled({"enable_group_chat": True}) is True

    def test_explicit_null_means_not_configured(self, monkeypatch):
        """A nullable column with no value set is 'unconfigured', not 'off'.
        Reading it as off would silently override a global yes for every tenant
        that had never touched the setting."""
        monkeypatch.setenv("ENABLE_GROUP_CHAT_SUPPORT", "true")
        assert _group_chat_support_enabled({"enable_group_chat": None}) is True


class TestStringValuesAreCoercedNotTrusted:
    """The regression this repo has already shipped once.

    `tenants.onboarding_completed` was scaffolded as `text` holding the string
    "false", which is TRUE in Python, and login skipped onboarding for every
    new user. If `enable_group_chat` is later added as `text` by the same
    scaffold, the identical bug would switch group replies ON for every tenant
    that had turned them off.
    """

    @pytest.mark.parametrize("value", ["false", "False", "FALSE", "0", "no", "off", ""])
    def test_falsey_strings_disable(self, monkeypatch, value):
        monkeypatch.setenv("ENABLE_GROUP_CHAT_SUPPORT", "true")
        assert _group_chat_support_enabled({"enable_group_chat": value}) is False

    @pytest.mark.parametrize("value", ["true", "True", "TRUE", "1", "yes", "on", " true "])
    def test_truthy_strings_enable(self, value):
        assert _group_chat_support_enabled({"enable_group_chat": value}) is True

    def test_return_is_always_a_bool(self):
        """Callers branch on this. Returning the raw column value would leak a
        string or an int into `if not enable_groups`."""
        for cfg in ({"enable_group_chat": 1}, {"enable_group_chat": "true"}, {}):
            assert isinstance(_group_chat_support_enabled(cfg), bool)
