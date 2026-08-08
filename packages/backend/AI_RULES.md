# 🚨 AI ASSISTANT RULES - READ THIS FIRST

**Version:** 1.1
**Last Updated:** 2026-02-25
**Mandatory for ALL AI assistants working on this project**

---

## 🎯 CORE PRINCIPLE

**CODE FIRST. DOCS NEVER.**

If you find yourself creating a new markdown file, **STOP IMMEDIATELY** and ask yourself:

- Does this file already exist?
- Can I update an existing file instead?
- Is this actually needed or am I avoiding writing code?

---

## ❌ WHAT NOT TO DO

### 1. **NEVER Create New Documentation Files**

- ❌ Don't create `DEPLOYMENT-SUMMARY.md`
- ❌ Don't create `PHASE2-COMPLETE.md`
- ❌ Don't create `STATUS-REPORT.md`
- ❌ Don't create `IMPLEMENTATION-GUIDE.md`

**Why?** We already have **85+ documentation files**. More docs = more confusion.

### 2. **NEVER Ask User to Run Commands**

- ❌ "Please run: `fly deploy --app bijou-staging`"
- ❌ "Execute this SQL in Supabase..."
- ❌ "Copy this file to..."

**Instead:** Run the command yourself using the `terminal` tool.

### 3. **NEVER Claim Success Without Verification**

- ❌ "Deployment complete! ✅"
- ❌ "Migration successful! ✅"
- ❌ "Feature implemented! ✅"

**Instead:** Run verification commands and show actual output.

### 4. **NEVER Create Test Data with Fake Values**

- ❌ Test tenant with phone `+60123456789` (not user's number)
- ❌ Placeholder emails like `test@example.com`
- ❌ Dummy API keys

**Instead:** Use the user's actual data or ask for it.

### 5. **NEVER Add Code to `bijou.py` Directly**

- ❌ Don't write new routes, models, or logic in `src/core/bijou.py`
- ❌ Don't expand any function in `bijou.py` that already exceeds 100 lines
- ❌ Don't create a new class inside `bijou.py`

**Instead:** Find the correct module in the ownership map in `AGENTS.md` and put the code there.

### 6. **NEVER Ignore the 500-Line File Limit**

- ❌ Don't add any code to a file that is already ≥500 lines
- ❌ Don't claim a file is "fine" without checking its line count

**Instead:** Check first: `wc -l <file>`. If ≥500, extract a module, then add.
Enforcement: CI will fail the build via `scripts/check_file_sizes.sh`.

### 7. **NEVER Create Files in the Project Root**

- ❌ `test_*.py` in root → use `tests/`
- ❌ `run_*.py` / `run_*.sh` in root → use `scripts/`
- ❌ `apply_*.py`, `demo_*.py`, `verify_*.py` in root → use `scripts/`
- ❌ `deploy_*.sh`, `check_*.py`, `close_*.py` in root → use `scripts/`
- ❌ `*_SUMMARY.md`, `*_REPORT.md`, `*_STATUS.md` in root → use `docs/` or `_ARCHIVE/`
- ❌ `BUG-*.md`, `TASK_*.md`, `PHASE*.md`, `VOICE_*.md` in root → use `docs/`
- ❌ `QUICK_*.md`, `MANUAL_*.md`, `MAGIC_*.md` in root → use `docs/`

**Root ALLOWED list:** `README.md`, `AGENTS.md`, `AI_RULES.md`, `Dockerfile*`, `fly.*.toml`, `opencode.json`, `openapi.json`, `requirements*.txt`, `pytest.ini`, `package.json`, `playwright.config.ts`, `.env.example`, `.gitignore`, `.dockerignore`, `.pre-commit-config.yaml`

**Enforcement:** `.gitignore` blocks root violations automatically. `scripts/static_audit.py` flags them in CI.

---

## ✅ WHAT TO DO

### 1. **Update Existing Files Only**

**The ONLY files you're allowed to update:**

- `START_HERE.md` - Current project status (1 file, not 50)
- `README.md` - User-facing documentation
- `src/**/*.py` - Actual code files
- `.env.example` - Environment variable template

**That's it.** Everything else is noise.

### 2. **Run Commands Yourself**

```bash
# Good - You execute
terminal(command="fly deploy --app bijou-staging", cd="w3j-bijou-enterprise")

# Bad - Asking user to execute
"Please run: fly deploy --app bijou-staging"
```

### 3. **Verify Before Claiming Success**

```bash
# Deploy
terminal(command="fly deploy --app bijou-staging", cd="...")

# Verify it actually deployed
terminal(command="fly status --app bijou-staging", cd="...")

# Check logs for errors
terminal(command="fly logs --app bijou-staging --limit 50", cd="...")

# Only then say "Deployed ✅"
```

### 4. **Fix Code, Not Docs**

When something breaks:

- ❌ Don't write "TROUBLESHOOTING-GUIDE.md"
- ✅ Fix the actual code
- ✅ Deploy the fix
- ✅ Verify it works

---

## 📂 FILE LOCATIONS (NEVER CREATE NEW ONES)

### **Deployed Code (PRODUCTION)**

```
w3j-bijou-enterprise/
├── src/
│   ├── core/
│   │   └── bijou.py          ← Main application
│   ├── saas/
│   │   ├── persona_manager.py ← Persona system
│   │   ├── command_handler.py ← Command processing
│   │   └── tenant_router.py   ← Multi-tenant routing
│   └── integrations/
├── Dockerfile                 ← Build config
└── fly.staging.toml          ← Fly.io staging config
```

**CRITICAL:** Changes here get deployed. Everywhere else is ignored.

### **Documentation (UPDATE, DON'T CREATE)**

```
w3j-bijou-enterprise/
├── START_HERE.md    ← Single source of truth for status
└── README.md        ← User-facing docs
```

---

## 🔧 DEPLOYMENT WORKFLOW

### **Every time you change code:**

```bash
# 1. Edit the actual deployed code
edit_file(path="w3j-bijou-enterprise/src/core/bijou.py", ...)

# 2. Deploy immediately
terminal(command="fly deploy --app bijou-staging --config fly.staging.toml", cd="w3j-bijou-enterprise")

# 3. Verify deployment
terminal(command="fly status --app bijou-staging", cd="w3j-bijou-enterprise")

# 4. Check logs for errors
terminal(command="fly logs --app bijou-staging --limit 50", cd="w3j-bijou-enterprise")

# 5. Update START_HERE.md with what changed
edit_file(path="w3j-bijou-enterprise/START_HERE.md", mode="edit", ...)
```

**That's it.** No 10-page deployment guides.

---

## 🐛 DEBUGGING WORKFLOW

### **When something breaks:**

```bash
# 1. Check actual logs (not assumptions)
terminal(command="fly logs --app bijou-staging", cd="...")

# 2. Identify the error line
# (Read the actual Python traceback)

# 3. Fix the code
edit_file(path="w3j-bijou-enterprise/src/...", ...)

# 4. Redeploy
terminal(command="fly deploy ...", cd="...")

# 5. Verify fix worked
terminal(command="fly logs ...", cd="...")
```

**NO documentation about the bug.** Just fix it.

---

## 🎯 TESTING WORKFLOW

### **Use REAL data:**

```python
# ❌ Bad - Fake data
tenant = {
    "phone": "+60123456789",  # Not user's number
    "name": "Test Restaurant"
}

# ✅ Good - Ask for real data
"What's your actual WhatsApp number? I'll create a test tenant with it."
```

### **Verify with actual commands:**

```bash
# ✅ Send real test message
curl -X POST https://bijou-staging.fly.dev/webhook/message \
  -d '{"from": "+60REAL_NUMBER@s.whatsapp.net", "body": "/owner help"}'

# ✅ Check it was processed
fly logs --app bijou-staging --limit 20
```

---

## 📊 STATUS REPORTING

### **When user asks "What's the status?"**

**Don't:**

- Create `STATUS-REPORT.md` with 500 lines
- List every file you created
- Claim everything works

**Do:**

```bash
# Show actual system status
terminal(command="fly status --app bijou-staging", cd="...")

# Show recent logs
terminal(command="fly logs --app bijou-staging --limit 30", cd="...")

# Show database state
terminal(command="supabase db tables list", cd="...")

# Summary in 5 lines:
"✅ App deployed and running
✅ Database connected
❌ Owner commands failing (fixing now)
🟡 Multi-tenant code exists but untested
Next: Fix owner commands, then test with your number"
```

---

## 🚀 FEATURE IMPLEMENTATION WORKFLOW

### **Example: Implementing `/owner` commands**

```bash
# 1. Check if method exists
grep(regex="def process_owner_command", include_pattern="**/persona_manager.py")

# 2. If missing, add it (code, not docs)
edit_file(path="w3j-bijou-enterprise/src/saas/persona_manager.py", mode="edit", ...)

# 3. Deploy immediately
terminal(command="fly deploy --app bijou-staging", cd="w3j-bijou-enterprise")

# 4. Test with curl (real endpoint)
terminal(command="curl -X POST https://bijou-staging.fly.dev/test", cd="...")

# 5. Confirm in logs
terminal(command="fly logs --app bijou-staging | grep 'owner'", cd="...")
```

**Total documentation created:** 0 files

---

## 📝 THE ONLY DOCUMENTATION YOU UPDATE

### **START_HERE.md Structure:**

```markdown
# Bijou AI - Current Status

**Last Updated:** 2026-01-30 15:30
**Deployed Version:** 2.2.1

## ✅ Working

- WhatsApp message polling
- Basic AI responses
- Media handling (images, audio)

## ❌ Broken

- `/owner` commands (method missing)
- Multi-tenant routing (untested)

## 🚧 In Progress

- Fixing owner commands (ETA: 15 min)

## 🔧 Next Steps

1. Deploy owner command fix
2. Test with user's WhatsApp number
3. Verify `/owner help` works

## 🚀 Deployment Info

- App: `bijou-staging` (https://bijou-staging.fly.dev)
- Database: Supabase (lrwzlujomukzjykafmic)
- Logs: `fly logs --app bijou-staging`
```

**That's the ONLY status doc. Update it, don't create new ones.**

---

## 🎓 LEARNING FROM PAST MISTAKES

### **What Happened Before:**

1. AI created 85+ documentation files
2. AI edited code in wrong location (packages/ instead of w3j-bijou-enterprise/)
3. AI claimed "deployed ✅" but didn't run deploy command
4. AI created test data with fake phone numbers
5. AI wrote `process_owner_command()` in docs but not in actual code

### **Why It Happened:**

- Easier to write markdown than debug Python
- No verification after claims
- Confusion about which code is actually deployed
- Asking user to run commands instead of running them

### **Prevention:**

- Follow this document religiously
- Code changes = immediate deployment
- Every claim = verified with terminal output
- Test with real data only

---

## 🔒 FINAL RULES (NO EXCEPTIONS)

1. **Code first. Docs never.**
2. **Deploy immediately after code changes.**
3. **Verify with terminal commands, not assumptions.**
4. **Use real data for testing.**
5. **Update START_HERE.md only. No new files.**
6. **Run commands yourself. Never ask user.**
7. **If you create a .md file, you failed.**

---

## ❓ DECISION TREE

```
┌─────────────────────────────┐
│ Need to document something? │
└──────────┬──────────────────┘
           │
           ▼
    Does START_HERE.md
    cover this already?
           │
      ┌────┴────┐
      │         │
     Yes        No
      │         │
      ▼         ▼
   Update    Add to
   it       START_HERE.md
              │
              ▼
         NEVER create
         new .md file
```

```
┌──────────────────────┐
│ Need to fix a bug?   │
└──────┬───────────────┘
       │
       ▼
  Check logs with
  terminal command
       │
       ▼
  Identify error
  in actual code
       │
       ▼
  Edit the file
  in w3j-bijou-enterprise/
       │
       ▼
  Deploy with
  fly deploy
       │
       ▼
  Verify with
  fly logs
       │
       ▼
  Update START_HERE.md
  with 2-line change log
```

---

## 📞 IF YOU'RE CONFUSED

**Ask yourself:**

1. Am I about to create a new markdown file? → **STOP**
2. Am I asking user to run a command? → **RUN IT YOURSELF**
3. Am I claiming success without logs? → **GET PROOF FIRST**
4. Am I using fake test data? → **USE REAL DATA**

**If in doubt:** Fix code. Deploy. Verify. Update START_HERE.md.

---

**Remember:** The user hired you to build features, not write documentation.

**One working feature > 100 documentation files**

**END OF RULES**
