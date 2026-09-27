"""reset-password.html must send the user to /login after setting a password.

It used to store the recovery token and go to /dashboard. tenant_id was never
stored, and the password change revokes that session anyway, so on production
(2026-09-28) a user who opened the reset email in a fresh browser saw
"Access Denied - please log in" immediately after "Password set!".
"""

from pathlib import Path

PAGE = Path(__file__).resolve().parents[2] / "static" / "reset-password.html"


def test_reset_success_redirects_to_login_not_dashboard():
    js = PAGE.read_text(encoding="utf-8")
    after_change = js.split("/api/auth/change-password", 1)[1]
    assert 'window.location.href = "/login"' in after_change
    assert 'window.location.href = "/dashboard"' not in after_change
    assert 'localStorage.setItem("access_token", RECOVERY_TOKEN)' not in js
