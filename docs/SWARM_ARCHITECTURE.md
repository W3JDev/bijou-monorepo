# Bijou AI Swarm Manager Architecture
**Version:** 1.0.0  
**Created:** 2026-02-15  
**Status:** Production-Ready Blueprint  

---

## 🎯 MISSION

Design a permanent multi-agent orchestration system that enables:
- **Zero manual setup** for complex features
- **Parallel execution** where dependencies allow
- **Enterprise-level quality** with 0% error tolerance
- **Automatic validation** at every phase
- **Intelligent delegation** based on agent expertise

---

## 📐 HIERARCHICAL AGENT STRUCTURE

```
┌─────────────────────────────────────────────────────────────────┐
│                    LEVEL 1: STRATEGIC                           │
│                                                                  │
│                    @architect (Swarm Manager)                    │
│                                                                  │
│  • Project planning & phase management                          │
│  • Agent assignment & task delegation                           │
│  • Quality gates & success criteria                             │
│  • Risk assessment & mitigation                                 │
│  • Cross-cutting concerns (multi-tenancy, security)            │
└────────────┬────────────────────────────────────────────────────┘
             │
             │ DELEGATES TO
             │
┌────────────▼─────────────────────────────────────────────────────┐
│                    LEVEL 2: TACTICAL MANAGERS                     │
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  @db-admin   │  │  @backend    │  │  @devops     │          │
│  │              │  │              │  │              │          │
│  │ • Migrations │  │ • FastAPI    │  │ • Fly.io     │          │
│  │ • Supabase   │  │ • APIs       │  │ • Secrets    │          │
│  │ • RLS        │  │ • Business   │  │ • Deploy     │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ @fullstack   │  │ @google-ws   │  │ @security    │          │
│  │              │  │              │  │              │          │
│  │ • AppScript  │  │ • Sheets API │  │ • Audits     │          │
│  │ • HTML/JS    │  │ • OAuth      │  │ • Credentials│          │
│  │ • UI/UX      │  │ • Drive API  │  │ • Validation │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                   │
│  ┌──────────────┐                                                │
│  │ @qa-engineer │                                                │
│  │              │                                                │
│  │ • Testing    │                                                │
│  │ • Validation │                                                │
│  │ • Quality    │                                                │
│  └──────────────┘                                                │
└───────────┬───────────────────────────────────────────────────────┘
            │
            │ SPAWNS
            │
┌───────────▼──────────────────────────────────────────────────────┐
│                    LEVEL 3: EXECUTION WORKERS                     │
│                                                                   │
│  • Micro-tasks with clear input/output contracts                 │
│  • Parallel execution where possible                             │
│  • Automated verification of each deliverable                    │
│  • Self-documenting progress                                     │
└───────────────────────────────────────────────────────────────────┘
```

---

## 🧬 AGENT RESPONSIBILITY MATRIX (RACI)

### Google Sheets Dashboard Project Example

| Task | @architect | @db-admin | @backend | @fullstack | @google-ws | @security | @qa | @devops |
|------|------------|-----------|----------|------------|------------|-----------|-----|---------|
| **Phase Planning** | A/R | C | C | C | C | C | C | C |
| **Database Schema** | I | A/R | C | I | I | C | I | I |
| **API Endpoints** | I | C | A/R | I | C | C | I | I |
| **AppScript Code** | I | I | C | A/R | C | C | I | I |
| **Sheets Setup** | I | I | I | C | A/R | I | I | I |
| **OAuth Flow** | I | I | I | C | A/R | A | I | I |
| **Webhook Security** | I | I | C | I | C | A/R | I | I |
| **Integration Tests** | I | I | I | I | I | I | A/R | C |
| **Deployment** | I | I | I | I | I | C | C | A/R |

**Legend:**
- **R** = Responsible (does the work)
- **A** = Accountable (final approval)
- **C** = Consulted (provides input)
- **I** = Informed (kept in loop)

---

## 🔄 COMMUNICATION PROTOCOLS

### 1. Task Assignment Protocol

```markdown
**From: @architect**
**To: @backend**
**Task ID:** SHEETS-003
**Phase:** 3 (AppScript Backend)
**Priority:** High
**Blockers:** SHEETS-001, SHEETS-002 (complete)

**Objective:**
Implement webhook receiver endpoint in Bijou backend

**Deliverables:**
1. File: `src/integrations/google_sheets_webhook.py`
2. FastAPI POST endpoint: `/api/v1/webhooks/sheets`
3. Pydantic model: `SheetsWebhookPayload`
4. Unit tests: `tests/unit/test_sheets_webhook.py`

**Input Contract:**
- AppScript will POST JSON with schema:
  {
    "tenant_id": "uuid",
    "action": "update_conversation",
    "data": {...}
  }

**Output Contract:**
- Return 200 OK with {"status": "processed"}
- Update Supabase conversations table
- Log to notification_logs

**Validation Criteria:**
- [ ] Type hints on all functions
- [ ] Async/await for DB calls
- [ ] tenant_id filtering enforced
- [ ] Unit test coverage >80%
- [ ] Integration test with mock AppScript payload

**Estimated Time:** 45 minutes
**Dependencies:** @db-admin must complete migration 010 first
```

### 2. Progress Reporting Protocol

```markdown
**From: @backend**
**To: @architect**
**Task ID:** SHEETS-003
**Status:** ✅ COMPLETE

**Deliverables:**
- [x] File created: `src/integrations/google_sheets_webhook.py` (127 lines)
- [x] Endpoint: POST `/api/v1/webhooks/sheets` (working)
- [x] Tests: `tests/unit/test_sheets_webhook.py` (5 tests, all passing)

**Verification:**
```bash
pytest tests/unit/test_sheets_webhook.py -v
# ✅ test_valid_payload PASSED
# ✅ test_missing_tenant_id PASSED
# ✅ test_invalid_action PASSED
# ✅ test_tenant_isolation PASSED
# ✅ test_database_update PASSED
```

**Code Review Required:**
- Multi-tenancy: Verified with @db-admin (RLS enforced)
- Security: Awaiting @security review for API key validation

**Blockers for Next Task:** None
```

### 3. Quality Gate Protocol

```markdown
**From: @qa-engineer**
**To: @architect**
**Phase:** 5 (Backend Integration)
**Status:** ⚠️ BLOCKED

**Quality Gate: Integration Testing**

**Results:**
- Unit tests: ✅ 47/47 passing
- Integration tests: ⚠️ 3/5 passing
- E2E tests: ❌ Not run (blocked)

**Failures:**
1. `test_sheets_to_backend_flow` - 422 Unprocessable Entity
   - Root cause: Pydantic model expects `conversation_id` (UUID)
   - AppScript sending `conversationId` (camelCase)
   - Owner: @fullstack to fix field naming

2. `test_backend_to_supabase_update` - Connection timeout
   - Root cause: Supabase RLS policy blocking service role
   - Owner: @db-admin to update RLS policy

**Recommendation:**
🛑 **DO NOT PROCEED TO DEPLOYMENT** until both issues resolved

**Next Steps:**
1. @fullstack: Update AppScript to use snake_case
2. @db-admin: Verify RLS policy for google_sheets_webhook_user role
3. @qa-engineer: Re-run integration tests
4. @architect: Gate approval required before Phase 6
```

---

## 🚨 ERROR HANDLING & ESCALATION

### Error Severity Levels

| Level | Response | Example |
|-------|----------|---------|
| **INFO** | Log only | Skipped test marked as `@pytest.mark.skip` |
| **WARNING** | Agent self-corrects | Linting error auto-fixed with Black |
| **ERROR** | Escalate to @architect | Integration test fails |
| **CRITICAL** | STOP ALL WORK | Production deployment health check fails |

### Escalation Flow

```
┌─────────────────┐
│  Worker Agent   │
│  detects error  │
└────────┬────────┘
         │
         ▼
┌─────────────────────────┐
│  Can agent fix in <5min? │
└────┬────────────────┬────┘
     │ YES            │ NO
     ▼                ▼
┌─────────────┐  ┌──────────────┐
│  Fix + Log  │  │ Escalate to  │
│  Continue   │  │ @architect   │
└─────────────┘  └──────┬───────┘
                        │
                        ▼
                 ┌──────────────────┐
                 │ @architect       │
                 │ analyzes impact  │
                 └──────┬───────────┘
                        │
         ┌──────────────┼──────────────┐
         │              │              │
         ▼              ▼              ▼
  ┌──────────┐   ┌──────────┐   ┌──────────┐
  │ Reassign │   │ Rollback │   │ Emergency│
  │ to expert│   │ previous │   │ Hotfix   │
  └──────────┘   └──────────┘   └──────────┘
```

---

## 🎯 PHASE-BASED EXECUTION MODEL

### Phase Structure Template

```yaml
phase:
  id: "SHEETS-003"
  name: "AppScript Backend Development"
  objective: "Implement Google Apps Script functions for Sheets management"
  
  entry_criteria:
    - Database schema deployed (SHEETS-001)
    - API contracts defined (SHEETS-002)
    - OAuth credentials verified
    
  tasks:
    - id: "SHEETS-003-A"
      owner: "@fullstack"
      deliverable: "AppScript functions (create_sheet, update_row, read_data)"
      estimated_time: "60 minutes"
      
    - id: "SHEETS-003-B"
      owner: "@google-ws"
      deliverable: "OAuth 2.0 flow with service account"
      estimated_time: "45 minutes"
      
    - id: "SHEETS-003-C"
      owner: "@security"
      deliverable: "Security audit of credential storage"
      estimated_time: "30 minutes"
      
  parallel_execution:
    - ["SHEETS-003-A", "SHEETS-003-B"]  # Can run simultaneously
    
  sequential_execution:
    - "SHEETS-003-C depends on SHEETS-003-A,B"  # Audit after code
    
  exit_criteria:
    - All unit tests passing
    - Security audit approved
    - Code review by @architect
    - Integration test with staging Sheets
    
  rollback_procedure:
    - Delete test spreadsheet
    - Revoke OAuth credentials
    - Revert AppScript deployment
```

---

## 🔒 QUALITY GATES

### Gate 1: Code Quality (Every Task)

**Automated Checks:**
- ✅ Type hints present (`mypy src/`)
- ✅ Linting passes (`ruff check src/`)
- ✅ Formatting consistent (`black --check src/`)
- ✅ No hardcoded secrets (`git secrets --scan`)

**Manual Review (@architect):**
- ✅ Follows AGENTS.md style guide
- ✅ Multi-tenancy respected
- ✅ Error handling comprehensive
- ✅ Logging at appropriate levels

### Gate 2: Testing (End of Phase)

**Coverage Requirements:**
- Unit tests: >80% line coverage
- Integration tests: All critical paths
- E2E tests: Happy path + 3 error scenarios

**@qa-engineer Sign-off Required:**
```bash
pytest tests/ -v --cov=src --cov-report=term-missing
# Coverage: 87% (✅ PASS - threshold 80%)
```

### Gate 3: Security (Before Deployment)

**@security Checklist:**
- [ ] OAuth credentials stored in Fly.io secrets (NOT .env)
- [ ] API keys rotated if exposed in logs
- [ ] RLS policies prevent cross-tenant access
- [ ] Webhook endpoints validate HMAC signatures
- [ ] No PII logged to stdout

### Gate 4: Deployment (Production Only)

**@devops Pre-flight:**
1. Deploy to staging first
2. Run `tests/e2e_health_check.py --env staging`
3. Monitor logs for 10 minutes
4. Run manual smoke tests
5. Get @architect approval

**Rollback Trigger:**
- Any health check fails
- Error rate >1% in first 10 minutes
- User reports critical bug

---

## 📊 SWARM COORDINATION PATTERNS

### Pattern 1: Sequential Waterfall
**Use Case:** Tasks with strict dependencies

```
@db-admin (Migration) 
    ↓ (blocks)
@backend (API using new schema)
    ↓ (blocks)
@qa-engineer (Integration tests)
    ↓ (blocks)
@devops (Deployment)
```

### Pattern 2: Parallel Fan-Out
**Use Case:** Independent tasks

```
            @architect (Planning)
                    ↓
        ┌───────────┼───────────┐
        ↓           ↓           ↓
   @db-admin   @fullstack   @google-ws
   (Schema)    (UI Code)    (OAuth)
        └───────────┼───────────┘
                    ↓
              @qa-engineer
             (Integration)
```

### Pattern 3: Pipeline
**Use Case:** Continuous delivery

```
@backend ──→ @qa-engineer ──→ @devops (staging) ──→ @qa-engineer ──→ @devops (prod)
(Code)       (Unit Tests)     (Deploy)               (E2E Tests)     (Deploy)
```

### Pattern 4: Review Board
**Use Case:** High-risk changes

```
        @backend (Code)
             ↓
      ┌──────┼──────┐
      ↓      ↓      ↓
  @security @db-admin @architect
  (Audit)   (Schema)  (Architecture)
      └──────┼──────┘
             ↓
        APPROVE/REJECT
```

---

## 🛠️ SWARM MANAGER COMMANDS

### Command 1: `/swarm-init <project_name>`
**Description:** Initialize swarm mode for a new project  
**Example:** `/swarm-init "Google Sheets Dashboard"`

**Actions:**
1. Create `docs/planning/<project_name>/` directory
2. Generate RACI matrix
3. Create phase breakdown document
4. Assign task IDs
5. Set up progress tracking

### Command 2: `/swarm-assign <task_id> <agent>`
**Description:** Manually assign or reassign a task  
**Example:** `/swarm-assign SHEETS-003-A @fullstack`

### Command 3: `/swarm-status`
**Description:** Show current swarm state

**Output:**
```markdown
## Swarm Status: Google Sheets Dashboard

**Phase:** 3/6 (AppScript Backend)
**Progress:** 67% (4/6 tasks complete)
**Health:** 🟢 ON TRACK

**Active Agents:**
- @fullstack: SHEETS-003-A (In Progress - 45 min elapsed)
- @security: SHEETS-003-C (Waiting on SHEETS-003-A)

**Completed:**
- ✅ SHEETS-001: Database schema (@db-admin)
- ✅ SHEETS-002: API contracts (@backend)
- ✅ SHEETS-003-B: OAuth flow (@google-ws)
- ✅ SHEETS-004: Unit tests (@qa-engineer)

**Blockers:** None

**Next Up:**
- SHEETS-005: Integration tests (@qa-engineer)
- SHEETS-006: Deployment (@devops)
```

### Command 4: `/swarm-gate <phase_id>`
**Description:** Run quality gate check  
**Example:** `/swarm-gate SHEETS-PHASE-3`

**Actions:**
1. Run automated tests
2. Check code coverage
3. Verify all deliverables present
4. Request @architect approval
5. Generate gate report

### Command 5: `/swarm-rollback <phase_id>`
**Description:** Emergency rollback  
**Example:** `/swarm-rollback SHEETS-PHASE-5`

**Actions:**
1. Revert code changes
2. Rollback database migrations
3. Delete test data
4. Restore previous deployment
5. Notify all agents

---

## 📁 FILE STRUCTURE

### Global Configuration Location

```
%USERPROFILE%\.opencode\
├── config\
│   ├── swarm_manager.md          # This architecture document
│   ├── agent_registry.json       # List of all available agents
│   └── command_templates.json    # Swarm command definitions
│
└── agents\
    ├── architect.md              # Swarm manager persona
    ├── backend.md
    ├── db-admin.md
    ├── fullstack.md              # NEW: AppScript + HTML/JS specialist
    ├── google-workspace.md       # NEW: Google APIs specialist
    ├── security-auditor.md
    ├── qa-engineer.md
    └── devops.md
```

### Project-Level Tracking

```
<project_root>/.opencode/
├── swarm\
│   ├── active_project.json       # Current swarm project metadata
│   ├── task_registry.json        # All tasks and their status
│   └── progress_log.md           # Human-readable progress report
│
└── tasks\
    ├── SHEETS-001.json           # Individual task metadata
    ├── SHEETS-002.json
    └── ...
```

---

## 🎓 SWARM BEST PRACTICES

### 1. Always Start with @architect
**Reason:** Prevents duplicated work and ensures coherent design

```
❌ BAD:
User → @fullstack "Build Google Sheets integration"
(Agent builds without database schema, security review, or deployment plan)

✅ GOOD:
User → @architect "Design Google Sheets integration"
@architect → Creates 6-phase plan, assigns tasks to 5 agents
```

### 2. Use Parallel Execution Aggressively
**Reason:** Reduces total project time by 50-70%

```
Sequential (Old Way): 4 hours
┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
│Schema  │→│Backend │→│Frontend│→│Deploy  │
│(1h)    │ │(1h)    │ │(1.5h)  │ │(0.5h)  │
└────────┘ └────────┘ └────────┘ └────────┘

Parallel (Swarm): 2.5 hours
┌────────┐
│Schema  │────┐
│(1h)    │    │
└────────┘    ├──→┌────────┐    ┌────────┐
              │   │Tests   │───→│Deploy  │
┌────────┐    │   │(0.5h)  │    │(1h)    │
│Frontend│────┘   └────────┘    └────────┘
│(1.5h)  │
└────────┘
```

### 3. Gate Every Phase
**Reason:** Catch issues early when they're cheap to fix

**Cost of Defects:**
- Caught in unit tests: 1x cost
- Caught in integration tests: 10x cost
- Caught in production: 100x cost

### 4. Document Everything Automatically
**Reason:** Future developers (including AI) need context

**Every task completion should generate:**
- Code changes (obvious)
- Test results (automated)
- Decision log (why this approach?)
- Known limitations (what's not covered?)

---

## 🔮 ADVANCED SWARM FEATURES

### Feature 1: Dynamic Agent Spawning
**Scenario:** Project needs 3 parallel frontend tasks but only 1 @fullstack agent

**Solution:**
```python
# @architect spawns temporary specialized workers
spawn_agent(
    role="sheets-ui-developer",
    parent="@fullstack",
    constraints=[
        "only_work_on: SHEETS-004-A",
        "report_to: @fullstack",
        "lifecycle: task_completion"
    ]
)
```

### Feature 2: Automated Dependency Resolution
**Scenario:** @backend needs @db-admin to finish, but @db-admin blocked

**Detection:**
```json
{
  "task": "SHEETS-003",
  "agent": "@backend",
  "status": "waiting",
  "blocker": "SHEETS-001",
  "blocker_agent": "@db-admin",
  "blocker_status": "error",
  "blocker_error": "Migration syntax error"
}
```

**Auto-Resolution:**
1. @architect detects blocker
2. Reassigns SHEETS-001 to @db-admin (with higher priority)
3. Notifies @backend of delay
4. Suggests @backend work on SHEETS-004 (parallel task) instead

### Feature 3: Quality Prediction
**Use ML to predict task success:**

```python
# Trained on historical project data
task_risk_score = predict_risk(
    agent_experience=0.8,      # @fullstack has done 12 AppScript tasks
    code_complexity=0.6,       # Medium complexity
    test_coverage=0.9,         # 90% coverage
    review_feedback_history=0.7 # Usually needs 1-2 revisions
)

# Output: Risk Score = 0.42 (Medium)
# Recommendation: Add extra QA review before deployment
```

---

## 📈 SUCCESS METRICS

### Project-Level Metrics

| Metric | Target | Current (Baseline) |
|--------|--------|-------------------|
| **Time to Deployment** | <4 hours | ~12 hours (manual) |
| **Code Review Cycles** | ≤2 | ~5 (back-and-forth) |
| **Test Coverage** | >80% | ~60% |
| **Production Bugs** | <1 per release | ~3 per release |
| **Rollback Rate** | <5% | ~15% |
| **Agent Utilization** | >70% | ~30% (sequential) |

### Swarm-Specific Metrics

- **Parallel Execution %:** Tasks running concurrently / Total tasks
- **Gate Pass Rate:** % of phases passing first quality gate
- **Agent Idle Time:** Time agents wait for blockers
- **Handoff Clarity:** % of tasks completed without clarification questions

---

## 🚀 IMPLEMENTATION ROADMAP

### Week 1: Foundation
- [ ] Create global agent configuration files
- [ ] Implement `/swarm-init` command
- [ ] Build task tracking system (JSON-based)
- [ ] Document RACI matrix for common project types

### Week 2: Automation
- [ ] Implement quality gates (automated checks)
- [ ] Build dependency graph visualizer
- [ ] Create progress dashboard
- [ ] Add rollback automation

### Week 3: Intelligence
- [ ] Implement blocker detection
- [ ] Add automatic task reassignment
- [ ] Build risk prediction model
- [ ] Create agent performance analytics

### Week 4: Production
- [ ] Test with Google Sheets project (pilot)
- [ ] Refine based on learnings
- [ ] Document lessons learned
- [ ] Deploy to production projects

---

## 🎯 NEXT STEPS

**Immediate (Next Session):**
1. Review this architecture with user
2. Get approval on RACI matrix
3. Identify any missing agents (e.g., @google-workspace)
4. Prioritize which features to implement first

**Short-Term (Next 3 Sessions):**
1. Implement global configuration files
2. Create task tracking system
3. Build quality gates
4. Test with Google Sheets project

**Long-Term (Next Month):**
1. Refine swarm workflows based on real usage
2. Add ML-based optimizations
3. Create swarm playbooks for common patterns
4. Train new developers on swarm methodology

---

**Document Version:** 1.0.0  
**Last Updated:** 2026-02-15  
**Status:** Ready for Implementation  
**Owner:** @architect  
**Review Cycle:** Every 2 weeks
