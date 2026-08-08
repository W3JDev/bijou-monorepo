# Repository Cleanup Audit Report
**Date:** 2026-02-21  
**Scope:** Full monorepo — root + `w3j-bijou-enterprise/`  
**Status:** READY TO EXECUTE

---

## Summary

| Category | Delete | Move/Rename | Gitignore (add) | Keep |
|----------|--------|-------------|-----------------|------|
| 1. Repo root junk | 19 files | 4 scripts | 3 patterns | — |
| 2. Root markdown reports | 22 files | — | — | 3 files |
| 3. Enterprise root junk | 13 files | — | 5 patterns | 3 files |
| 4. Enterprise markdown reports | 30 files | — | — | 2 files |
| 5. Security risk JSONs | 4 files | — | already covered | — |
| 6. Tests directory | 10 files | — | 4 patterns | 6 files |
| 7. Postman collections | 4 files | — | 3 patterns | 2 files |
| 8. Archive/dead dirs | 4 dirs | — | — | — |
| 9. `.opencode/` node_modules | 2 dirs | — | 2 patterns | agents/ configs |
| 10. `.gitignore` additions | — | — | see section | — |

---

## Category 1 — Repo Root Junk Files

**Root:** `/mnt/c/.../BijouAi+Clawdbot/Bijou-Ai-With-whatsapp-mcp/`

### DELETE — QR Artifacts
```
nul
qr.png
qr.txt
qr_page.html
qr_test_output.png
qr_cloud_live.png
qr_code_jewel.png
jewel-qr.png
test-agent-2-qr.png
```

### DELETE — Screenshot Artifacts (typos in names = clearly throwaway)
```
"dahsboard -whatsapp-connection-analysiss.png"
"dahsboard -whatsapp-connection-inbox .png"
"dahsboard -whatsapp-connection.png"
dashbaord-issue-14feb.png
qr-scan-not-redirecting-issue.png
```

### DELETE — One-off Outputs
```
audit_results.json
dashboard_verification.json
logs-bijou.txt
logs-gowa-bridge.txt
staging_logs.txt
```

### DELETE — Throwaway HTML Test Pages
```
app_login.html
bridge_homepage.html
swagger.html
swagger_ui_check.html
SCAN_QR_NOW.html
```

### DELETE — Misnamed Handoff Notes (not structured docs)
```
project-document-prompt.md.txt
restarted-resume-work.md.txt
```

### MOVE to `scripts/` directory (or DELETE if one-off)
```
check_tenants.py      → scripts/check_tenants.py  (or delete)
get_qr.py             → scripts/get_qr.py          (or delete)
reset_both_tenants.py → scripts/reset_both_tenants.py
reset_tenant_connection.py → scripts/reset_tenant_connection.py
```
> These are dev utilities that don't belong at repo root. Move to `scripts/` to make them discoverable without cluttering root. If they were one-off, delete.

---

## Category 2 — Root-Level Markdown Reports

Most of these are **session outputs, one-time investigation reports, or superseded deployment notes**. The `.gitignore` already has patterns for some but they were committed before the patterns were added.

### DELETE — One-time Investigation / Session Reports
```
BACKEND_500_FIXES_REPORT.md
COMPREHENSIVE_AUDIT_REPORT.md
CONTINUATION_SUMMARY.md
DASHBOARD_CONFIGURATION_ANSWERS.md
DASHBOARD_FIX_RECOMMENDATIONS.md
DB_FIX_RESULTS.md
DEPLOYMENT_STATUS_v338.md
E2E_TEST_RESULTS.md
EXECUTIVE_SUMMARY.md
FIX_REPORT.md
GOWA_BRIDGE_EXPLORATION_REPORT.md
MULTI_TENANT_DEVICE_IMPLEMENTATION.md
PHASE_1_COMPLETION_REPORT.md
PRODUCTION_READY_v300.md
PROJECT_STATUS.md
TESTING_GUIDE_v294.md
UI_BAKERY_DATASOURCE_CONFIG.md
USER_TESTING_CHECKLIST.md
VERIFICATION_AUDIT_RESULTS.md
WEBHOOK_422_FIX_REPORT.md
"Bijou AI - Codebase Cleanup Session Handoff..."   (the long-named dated file)
```

### KEEP — Reference Documentation
```
GOWA_BRIDGE_EXPERT_GUIDE.md        ← Evergreen ops reference
MULTI_TENANT_WHATSAPP_ARCHITECTURE.md ← Architecture decision doc
README.md                          ← Always keep
```

---

## Category 3 — Enterprise Root Junk Files

**Root:** `w3j-bijou-enterprise/`

### DELETE — Windows Artifacts
```
nul
C:/        ← Entire directory (Windows path leaked into Linux FS)
```

### DELETE — Git Backup
```
.git_backup/    ← Backed-up git internals; unnecessary and large
```

### DELETE — Env Backup
```
.env.backup.20260202_000823   ← Timestamped backup; use git for this
```

### DELETE — One-off Test Outputs
```
deploy.log
security_scan_results.txt
stress_test_bridge.db
```

### DELETE — Stale Test Data JSONs
```
phase1_qr.json
phase1_signup.json
qr_response.json
qr_test.json
real_signup.json
test_download.json
test_final.json
test_message.json
test_phase1.json
test_phase1_v2.json
test_signup.json
test_signup_new.json
```

### DELETE — Duplicate/Superseded Config Files
```
Dockerfile.optimized        ← IDENTICAL to Dockerfile (confirmed by diff)
fly.toml.production         ← DIFFERENT from fly.production.toml (older version v2.2.0 vs current v301); the current canonical is fly.production.toml
requirements.optimized.txt  ← DIFFERENT from requirements.txt (stripped-down version); the current canonical is requirements.txt
```
> `fly.toml.production` appears to be an old v2.2.0 config targeting app `bijou-ai-enterprise-w3j`. The current production app is `bijou-production` using `fly.production.toml`. Safe to delete the old one.

### KEEP
```
Dockerfile              ← Active
fly.production.toml     ← Active production config
fly.staging.toml        ← Active staging config
requirements.txt        ← Active
```

---

## Category 4 — Enterprise Root Markdown Reports

### DELETE — Explicitly Superseded
```
DEPLOYMENT_OLD_v2.2.1.md
```

### DELETE — Session / Phase Reports (one-time outputs)
```
AUDIT_ANALYSIS.md
AUDIT_SUMMARY.md
BACKEND_500_FIXES_STATUS.md
BRIDGE_FIX_SUMMARY.md
DASHBOARD_FIXES_COMPLETE.md
DASHBOARD_LOCATION.md
DATABASE_MIGRATION_PRODUCTION_REPORT.md
DEPLOYMENT_FINAL.md
DEPLOYMENT_REPORT.md
FINAL_DEPLOYMENT_GUIDE.md
FINAL_STATUS_REPORT.md
FIX_REPORT.md
MISSION_CONTROL_REPORT.md
MISSION_CONTROL_STATUS.md
NEXT_STEPS_SUMMARY.md
PHASE_2.5_HOTFIX_SUMMARY.md
PHASE_3.5_COMPLETION.md
PHASE_3_AND_3.5_COMPLETE.md
PHASE_3_E2E_VALIDATION_REPORT.md
PHASE_3_MANUAL_SMOKE_TEST.md
PRODUCTION_LAUNCH_REPORT.md
QR_CODE_BUG_REPORT.md
QR_FIX_DEPLOYMENT.md
QUICK_TEST_COMMANDS.md
SCHEMA_MISMATCH_REPORT.md
SESSION_PROGRESS_v301_CONTINUED.md
SESSION_SUMMARY_v301.md
SHEETS_DASHBOARD_COMPLETE.md
WEBHOOK_IMPLEMENTATION_SUMMARY.md
YESTERDAY_WORK_REPORT_2026-02-10.md
```

### KEEP
```
README.md               ← Always keep
AGENTS.md               ← AI agent context file — actively used
```

---

## Category 5 — Security Risk: Credential JSON Files

> **WARNING:** `project_keys_real_utf8.json` contains a REAL Supabase JWT API key confirmed by inspection. The others failed UTF-8 decoding but likely contain the same.

The root `.gitignore` already includes:
```
project_keys*.json
supabase_keys.json
```
...but these files were committed BEFORE those patterns were added (or were never staged). They need to be:
1. **Deleted from disk immediately**
2. **Removed from git history** if they were ever committed (`git log -- project_keys_real_utf8.json`)
3. **Supabase keys rotated** as a precaution

### DELETE
```
w3j-bijou-enterprise/project_keys.json
w3j-bijou-enterprise/project_keys_real_utf8.json    ← CONFIRMED REAL KEY
w3j-bijou-enterprise/project_keys_utf8.json
w3j-bijou-enterprise/supabase_keys.json
```

---

## Category 6 — Tests Directory

**Root:** `w3j-bijou-enterprise/tests/`

### DELETE — Broken/Empty Filenames
```
tests/api_results/.json    ← File named ".json" — filesystem artifact
```

### DELETE — One-off Test Output JSONs
```
tests/api_results/summary.json
tests/FINAL_REPORT.json
tests/api_report.json
tests/mission_complete.json
tests/postman/enhanced-test-results.json
```

### DELETE — Captured Test Run Outputs
```
tests/postman/newman-output.txt
tests/postman/newman-report.html
tests/postman_run.log
tests/logs/pytest.log
```

### DELETE — Redundant Report MDs in `tests/postman/`
Keep only the most recent/comprehensive; delete the rest:
```
tests/postman/CHANGES.md
tests/postman/FIXES_COMPLETED.md
tests/postman/FIX_REPORT.md
tests/postman/POSTMAN_FIXES_REPORT.md
tests/postman/QUICK_FIX_SUMMARY.md
tests/postman/TESTING_COMPLETED_SUMMARY.md
tests/postman/TEST_RESULTS.md
```
> Keep: `tests/postman/TEST_RESULTS_ANALYSIS.md` only if it contains reusable test strategy. Otherwise delete all 8.

### DELETE — Redundant Report MDs in `tests/e2e/`
```
tests/e2e/E2E_TEST_SUMMARY.md
tests/e2e/IMPLEMENTATION_CHECKLIST.md
tests/e2e/TEST_EXECUTION_SUMMARY.md
```
> Keep: `tests/e2e/TEST_STRATEGY.md` if it documents permanent strategy; delete otherwise.

### KEEP
```
tests/unit/                  ← Actual test code
tests/integration/           ← Actual test code
tests/regression/            ← Actual test code
tests/e2e/                   ← Actual test code (the .py files, not the MDs)
tests/postman/collections/   ← See Category 7
tests/postman/environments/  ← See Category 7
```

---

## Category 7 — Postman Collections (Deduplication)

**Root:** `tests/postman/collections/`

### KEEP — Canonical Collections
```
Bijou AI WhatsApp Enterprise Enhanced.postman_collection.json   ← Current canonical
bijou-api.postman_collection.json                               ← Keep ONLY if it has unique requests not in Enhanced
```

### DELETE — Backups / Duplicates / Scratch
```
"Bijou AI WhatsApp Enterprise Copy.postman_collection.json"              ← "Copy" = manual backup
"Bijou AI WhatsApp Enterprise Copy.postman_collection.json.backup.json"  ← Backup of a copy
"Bijou AI WhatsApp Enterprise Enhanced.postman_collection.json.backup_20260217_030619"  ← Timestamped backup (use git)
"New Collection.postman_collection.json"                                 ← Generic name = scratch
```

### DELETE — Environment Backups
```
tests/postman/environments/bijou-staging.postman_environment.json.backup.json
```

---

## Category 8 — Archive / Dead Directories

### DELETE — Entire Directories
```
w3j-bijou-enterprise/static/_archive_old_html/
    └── dashboard.html    ← Replaced by static/dashboard.html
    └── login.html        ← Replaced by static/onboarding.html / admin.html
    └── onboard.html      ← Replaced

w3j-bijou-enterprise/gemini-dashboard/
    └── "Bijou AI Dashboard (3).html"   ← "(3)" = Gemini draft
    └── gemini-dashboard.jsx            ← Confirmed dead: "Not used (React component without build)"
                                           (per static/PHASE_3_DASHBOARD_SUMMARY.md)

_ARCHIVE_DO_NOT_USE/          ← Root level; already labeled; fully superseded
w3j-bijou-enterprise/_ARCHIVE_DO_NOT_USE/   ← Same
```

### CONSIDER DELETING
```
w3j-bijou-enterprise/_ARCHIVE_2026-02-11/   ← Already archived Feb 11; 2 weeks old.
                                               Safe to delete unless it contains unreplicated docs.
```

---

## Category 9 — `.opencode/` node_modules

Both `.opencode/` directories (root and enterprise) contain large `node_modules/` trees that should never be in git.

### DO NOT DELETE (keep these)
```
.opencode/agents/           ← All agent definition .md files — actively used
.opencode/commands.json
.opencode/opencode.json
.opencode/README.md
w3j-bijou-enterprise/.opencode/agents/
w3j-bijou-enterprise/.opencode/commands.json
w3j-bijou-enterprise/.opencode/opencode.json
w3j-bijou-enterprise/.opencode/test_postman_mcp.py    ← Check if used; possibly delete
w3j-bijou-enterprise/.opencode/test_supabase.py       ← Check if used; possibly delete
```

### GITIGNORE (add to both `.gitignore` files)
```
.opencode/node_modules/
```

---

## Section 10 — `.gitignore` Additions

### Root `.gitignore` — Add These Patterns

The root `.gitignore` is missing coverage for several categories found:

```gitignore
# Screenshots and QR artifacts
*.png
qr.*
qr_*.png
*-qr.png
SCAN_QR_NOW.html

# One-off HTML test pages
app_login.html
bridge_homepage.html
swagger*.html
swagger_ui_check.html

# Captured log files at root
logs-*.txt
staging_logs.txt

# One-off scan outputs
audit_results.json
dashboard_verification.json
*_verification.json
*_results.json

# Windows null device artifacts
nul

# OpenCode tooling (node_modules only — keep agent configs)
.opencode/node_modules/
```

### Enterprise `.gitignore` (`w3j-bijou-enterprise/.gitignore`) — Add These Patterns

```gitignore
# Windows artifacts
nul
C:/

# Git backup
.git_backup/

# Env backups
.env.backup.*

# One-off test data
phase*.json
real_signup.json
test_download.json
test_final.json
test_message.json
test_signup*.json
*_qr.json
qr_response.json
qr_test.json

# One-off test outputs
deploy.log
security_scan_results.txt
stress_test_bridge.db

# Timestamped Postman backups
*.backup_*
*.backup.json

# Newman test output
tests/postman/newman-output.txt
tests/postman/newman-report.html
tests/postman_run.log
tests/logs/pytest.log

# OpenCode tooling
.opencode/node_modules/

# Duplicate/superseded configs
Dockerfile.optimized
fly.toml.production
requirements.optimized.txt

# Archive directories
_ARCHIVE_2026-02-11/
gemini-dashboard/
static/_archive_old_html/
```

---

## Execution Order (Recommended)

Run in this order to minimize risk:

```bash
# 1. Security first — delete credential files immediately
cd w3j-bijou-enterprise
rm project_keys.json project_keys_real_utf8.json project_keys_utf8.json supabase_keys.json
# Then verify they were never committed:
git log --oneline -- project_keys_real_utf8.json

# 2. Windows artifacts
rm nul
rm -rf "C:/"
rm -rf .git_backup/

# 3. Enterprise junk files (safe batch)
rm deploy.log security_scan_results.txt stress_test_bridge.db .env.backup.20260202_000823
rm phase1_qr.json phase1_signup.json qr_response.json qr_test.json real_signup.json
rm test_download.json test_final.json test_message.json test_phase1.json test_phase1_v2.json
rm test_signup.json test_signup_new.json
rm Dockerfile.optimized fly.toml.production requirements.optimized.txt

# 4. Archive directories
rm -rf static/_archive_old_html/
rm -rf gemini-dashboard/
rm -rf _ARCHIVE_DO_NOT_USE/

# 5. Test output junk
rm tests/api_results/summary.json "tests/api_results/.json"
rm tests/FINAL_REPORT.json tests/api_report.json tests/mission_complete.json
rm tests/postman/enhanced-test-results.json tests/postman/newman-output.txt
rm tests/postman/newman-report.html tests/postman_run.log tests/logs/pytest.log

# 6. Postman collection deduplication
cd tests/postman/collections
rm "Bijou AI WhatsApp Enterprise Copy.postman_collection.json"
rm "Bijou AI WhatsApp Enterprise Copy.postman_collection.json.backup.json"
rm "Bijou AI WhatsApp Enterprise Enhanced.postman_collection.json.backup_20260217_030619"
rm "New Collection.postman_collection.json"
rm ../environments/bijou-staging.postman_environment.json.backup.json

# 7. Enterprise markdown session reports (large batch)
cd w3j-bijou-enterprise
rm AUDIT_ANALYSIS.md AUDIT_SUMMARY.md BACKEND_500_FIXES_STATUS.md BRIDGE_FIX_SUMMARY.md
rm DASHBOARD_FIXES_COMPLETE.md DASHBOARD_LOCATION.md DATABASE_MIGRATION_PRODUCTION_REPORT.md
rm DEPLOYMENT_FINAL.md DEPLOYMENT_REPORT.md DEPLOYMENT_OLD_v2.2.1.md FINAL_DEPLOYMENT_GUIDE.md
rm FINAL_STATUS_REPORT.md FIX_REPORT.md MISSION_CONTROL_REPORT.md MISSION_CONTROL_STATUS.md
rm NEXT_STEPS_SUMMARY.md PHASE_2.5_HOTFIX_SUMMARY.md PHASE_3.5_COMPLETION.md
rm PHASE_3_AND_3.5_COMPLETE.md PHASE_3_E2E_VALIDATION_REPORT.md PHASE_3_MANUAL_SMOKE_TEST.md
rm PRODUCTION_LAUNCH_REPORT.md QR_CODE_BUG_REPORT.md QR_FIX_DEPLOYMENT.md
rm QUICK_TEST_COMMANDS.md SCHEMA_MISMATCH_REPORT.md SESSION_PROGRESS_v301_CONTINUED.md
rm SESSION_SUMMARY_v301.md SHEETS_DASHBOARD_COMPLETE.md WEBHOOK_IMPLEMENTATION_SUMMARY.md
rm YESTERDAY_WORK_REPORT_2026-02-10.md

# 8. Root level junk
cd ..
rm nul qr.png qr.txt qr_page.html qr_test_output.png qr_cloud_live.png qr_code_jewel.png
rm jewel-qr.png test-agent-2-qr.png audit_results.json dashboard_verification.json
rm logs-bijou.txt logs-gowa-bridge.txt staging_logs.txt
rm "dahsboard -whatsapp-connection-analysiss.png" "dahsboard -whatsapp-connection-inbox .png"
rm "dahsboard -whatsapp-connection.png" dashbaord-issue-14feb.png qr-scan-not-redirecting-issue.png
rm app_login.html bridge_homepage.html swagger.html swagger_ui_check.html SCAN_QR_NOW.html
rm project-document-prompt.md.txt restarted-resume-work.md.txt
rm _ARCHIVE_DO_NOT_USE/ -rf

# 9. Root markdown reports
rm BACKEND_500_FIXES_REPORT.md COMPREHENSIVE_AUDIT_REPORT.md CONTINUATION_SUMMARY.md
rm DASHBOARD_CONFIGURATION_ANSWERS.md DASHBOARD_FIX_RECOMMENDATIONS.md DB_FIX_RESULTS.md
rm DEPLOYMENT_STATUS_v338.md E2E_TEST_RESULTS.md EXECUTIVE_SUMMARY.md FIX_REPORT.md
rm GOWA_BRIDGE_EXPLORATION_REPORT.md MULTI_TENANT_DEVICE_IMPLEMENTATION.md
rm PHASE_1_COMPLETION_REPORT.md PRODUCTION_READY_v300.md PROJECT_STATUS.md
rm TESTING_GUIDE_v294.md UI_BAKERY_DATASOURCE_CONFIG.md USER_TESTING_CHECKLIST.md
rm VERIFICATION_AUDIT_RESULTS.md WEBHOOK_422_FIX_REPORT.md
rm "Bijou AI - Codebase Cleanup Session Handoff"*

# 10. Update .gitignore files (add patterns from Section 10 above)
# 11. git add -A && git commit -m "chore: repo cleanup — remove temp files, session reports, and security risk credentials"
```

---

## Risk Assessment

| Action | Risk | Mitigation |
|--------|------|------------|
| Delete session report MDs | Low — throwaway outputs | Git history preserves them if ever needed |
| Delete credential JSONs | **Critical urgency** — exposed keys | Rotate Supabase keys after deletion |
| Delete archive directories | Low — already labeled obsolete | Quick `git show HEAD:path` recovers any file |
| Delete Postman backups | Low | Canonical collection is kept |
| Delete `Dockerfile.optimized` | Low — identical to Dockerfile | Confirmed by diff |
| Delete `fly.toml.production` | Medium | `fly.production.toml` is the current canonical; confirm deployment uses correct file |

---

*End of Audit Report — generated 2026-02-21*
