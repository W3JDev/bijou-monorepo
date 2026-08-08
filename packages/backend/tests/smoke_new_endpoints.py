#!/usr/bin/env python3
"""
Bijou AI - Supplementary Smoke Tests for New Endpoints
=======================================================

Tests the endpoints added in the dashboard polish sprint:
  - GET  /api/dashboard/blacklist
  - POST /api/dashboard/blacklist
  - DELETE /api/dashboard/blacklist/{id}
  - GET  /api/dashboard/messages/{chat_jid}

Auth behaviour on staging: verify_session is lenient — requests without a
valid JWT are NOT always rejected (REQUIRE_DASHBOARD_TOKEN may not enforce
strict mode). So we verify:
  - Routes EXIST (not 404)
  - Routes don't CRASH (not 500)
  - Specific status codes are noted as informational

Usage:
    python tests/smoke_new_endpoints.py --env staging
    python tests/smoke_new_endpoints.py --env local
"""

import argparse
import sys
import json
import requests

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"

TENANT_ID = "29d48db4-075f-45ee-8c00-a57f8fd3016a"


def log(msg: str, color: str = RESET):
    try:
        print(f"{color}{msg}{RESET}")
    except UnicodeEncodeError:
        import re
        print(f"{color}{re.sub(r'[^\x00-\x7F]+', '', msg)}{RESET}")


def check(name: str, passed: bool, detail: str, results: list):
    results.append((name, passed, detail))
    status = f"{GREEN}PASS{RESET}" if passed else f"{RED}FAIL{RESET}"
    log(f"  [{status}]  {name}: {detail}")


def run_smoke(base_url: str) -> bool:
    results = []
    base_url = base_url.rstrip("/")

    log(f"\n{'='*60}")
    log(f"BIJOU AI -- Supplementary Smoke Tests", BLUE)
    log(f"{'='*60}")
    log(f"Target: {base_url}")
    log(f"Note: Auth is lenient on staging (verify_session allows through)")
    log(f"{'='*60}\n")

    # ── 1. GET /api/dashboard/blacklist ────────────────────────────────────
    log(f"{BLUE}[1/5] GET /api/dashboard/blacklist{RESET}")
    try:
        r = requests.get(f"{base_url}/api/dashboard/blacklist", timeout=10)
        # Route must exist (not 404) and not crash (not 500).
        # 200 is expected in lenient-auth staging; 401/403 is fine too.
        ok = r.status_code not in (404, 500)
        detail = f"HTTP {r.status_code}"
        if r.status_code == 200:
            detail += " (route exists, auth lenient)"
        elif r.status_code in (401, 403):
            detail += " (route exists, auth enforced)"
        elif r.status_code == 404:
            detail += " (FAIL: route missing)"
        elif r.status_code == 500:
            detail += " (FAIL: server crash)"
        check("GET /api/dashboard/blacklist", ok, detail, results)
    except Exception as e:
        check("GET /api/dashboard/blacklist", False, f"Request error: {e}", results)

    # ── 2. POST /api/dashboard/blacklist ───────────────────────────────────
    log(f"\n{BLUE}[2/5] POST /api/dashboard/blacklist{RESET}")
    try:
        r = requests.post(
            f"{base_url}/api/dashboard/blacklist",
            json={"phone_number": "60999888777"},
            timeout=10,
        )
        # 200 = success (inserted), 400 = validation error (ok),
        # 401/403 = auth guard (ok). All are acceptable.
        # 500 = crash (FAIL), 404 = route missing (FAIL).
        ok = r.status_code not in (404, 500)
        detail = f"HTTP {r.status_code}"
        if r.status_code == 200:
            detail += " (inserted successfully)"
        elif r.status_code == 400:
            detail += " (validation error — route exists)"
        elif r.status_code in (401, 403):
            detail += " (auth enforced — route exists)"
        elif r.status_code == 500:
            detail += f" (FAIL: server crash — {r.text[:120]})"
        elif r.status_code == 404:
            detail += " (FAIL: route missing)"
        check("POST /api/dashboard/blacklist", ok, detail, results)
    except Exception as e:
        check("POST /api/dashboard/blacklist", False, f"Request error: {e}", results)

    # ── 3. DELETE /api/dashboard/blacklist/{id} ────────────────────────────
    log(f"\n{BLUE}[3/5] DELETE /api/dashboard/blacklist/{{id}}{RESET}")
    fake_id = "00000000-0000-0000-0000-000000000001"
    try:
        r = requests.delete(
            f"{base_url}/api/dashboard/blacklist/{fake_id}", timeout=10
        )
        # 404 "Entry not found" = correct behaviour (fake ID doesn't exist,
        # auth passed through, route reached the DB check).
        # 401/403 = auth enforced (ok). 400 = bad UUID format (ok).
        # 500 = crash (FAIL), and a bare 404 from the *framework* (route missing)
        # is distinguishable only by body — we allow 404 here as it means the
        # route ran and correctly found no matching entry.
        ok = r.status_code not in (500,)
        detail = f"HTTP {r.status_code}"
        if r.status_code == 404:
            body = r.text[:80]
            if "Entry not found" in body or "not found" in body.lower():
                detail += " (correct: route ran, entry not found as expected)"
            else:
                detail += f" (route may be missing — body: {body})"
                ok = False
        elif r.status_code in (401, 403):
            detail += " (auth enforced — route exists)"
        elif r.status_code == 400:
            detail += " (validation error — route exists)"
        elif r.status_code == 200:
            detail += " (unexpected 200 for fake ID — may have matched something)"
        elif r.status_code == 500:
            detail += f" (FAIL: server crash — {r.text[:120]})"
        check("DELETE /api/dashboard/blacklist/{id}", ok, detail, results)
    except Exception as e:
        check("DELETE /api/dashboard/blacklist/{id}", False, f"Request error: {e}", results)

    # ── 4. GET /api/dashboard/messages/{chat_jid} ─────────────────────────
    log(f"\n{BLUE}[4/5] GET /api/dashboard/messages/{{chat_jid}} (route existence){RESET}")
    test_jid = "60123456789%40s.whatsapp.net"
    try:
        r = requests.get(
            f"{base_url}/api/dashboard/messages/{test_jid}", timeout=10
        )
        # Route must exist (not 404) and not crash (not 500).
        ok = r.status_code not in (404, 500)
        detail = f"HTTP {r.status_code}"
        if r.status_code == 200:
            detail += " (route exists, returns data or empty list)"
        elif r.status_code in (401, 403):
            detail += " (route exists, auth enforced)"
        elif r.status_code == 404:
            detail += " (FAIL: route missing)"
        elif r.status_code == 500:
            detail += f" (FAIL: crash — {r.text[:120]})"
        check("GET /api/dashboard/messages/{chat_jid}", ok, detail, results)
    except Exception as e:
        check("GET /api/dashboard/messages/{chat_jid}", False, f"Request error: {e}", results)

    # ── 5. GET /api/dashboard/messages (no path param — old bad path) ──────
    log(f"\n{BLUE}[5/5] Confirm /api/dashboard/messages (no path param) = 404{RESET}")
    try:
        r = requests.get(
            f"{base_url}/api/dashboard/messages?tenant_id={TENANT_ID}",
            timeout=10,
        )
        # This path has no route — must 404.  If auth catches it first (401/403) that's also ok.
        is_404 = r.status_code == 404
        is_auth_gated = r.status_code in (401, 403)
        ok = is_404 or is_auth_gated
        detail = f"HTTP {r.status_code}"
        if is_404:
            detail += " (correct: no such route)"
        elif is_auth_gated:
            detail += " (auth-gated; acceptable)"
        else:
            detail += f" (UNEXPECTED — body: {r.text[:80]})"
        check("GET /api/dashboard/messages (no path param)", ok, detail, results)
    except Exception as e:
        check("GET /api/dashboard/messages (no path param)", False, f"Request error: {e}", results)

    # ── Summary ────────────────────────────────────────────────────────────
    passed = sum(1 for _, p, _ in results if p)
    failed = sum(1 for _, p, _ in results if not p)

    log(f"\n{'='*60}")
    log(f"SUMMARY", BLUE)
    log(f"{'='*60}")
    log(f"Total: {len(results)}  Passed: {passed}  Failed: {failed}")

    if failed:
        log(f"\n{RED}SMOKE TESTS FAILED{RESET}")
        for name, ok, detail in results:
            if not ok:
                log(f"  - {name}: {detail}", RED)
        return False
    else:
        log(f"\n{GREEN}ALL SMOKE TESTS PASSED{RESET}")
        return True


def main():
    parser = argparse.ArgumentParser(description="Smoke test new dashboard endpoints")
    parser.add_argument(
        "--env",
        choices=["staging", "production", "local"],
        default="staging",
    )
    parser.add_argument("--base-url", help="Override base URL")
    args = parser.parse_args()

    urls = {
        "staging": "https://bijou-staging.fly.dev",
        "production": "https://bijou-production.fly.dev",
        "local": "http://localhost:8080",
    }

    base_url = args.base_url or urls[args.env]
    success = run_smoke(base_url)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
