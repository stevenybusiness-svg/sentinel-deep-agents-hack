---
phase: 06-demo-preparation-deployment
plan: 02
subsystem: infra
tags: [demo, dry-run, automation, deployment, env-config]

# Dependency graph
requires:
  - phase: 06-01
    provides: "Dockerfile, docker-compose.yml, demo_check.py, reset_demo.py"
provides:
  - "Timed dry-run script for full demo arc automation"
  - ".env.example with all environment variables documented"
affects: [demo-day]

# Tech tracking
tech-stack:
  added: [httpx]
  patterns: [timed-demo-arc, async-httpx-client]

key-files:
  created:
    - scripts/dry_run.py
  modified:
    - .env.example

key-decisions:
  - "Adapted API payloads to actual schemas: /api/investigate with scenario+payment_request dict, /api/confirm with episode_id+attack_type (plan had wrong field names)"
  - "Added 15s sleep after confirm to allow background rule generation to complete before Attack 2"

patterns-established:
  - "Dry-run timing: PASS < 180s, WARN 180-240s, FAIL > 240s"

requirements-completed: [DEMO-04, DEMO-05]

# Metrics
duration: 3min
completed: 2026-03-27
---

# Phase 06 Plan 02: Dry-Run Automation and Deployment Readiness Summary

**Timed dry-run script automating full Attack 1 -> Confirm -> Attack 2 -> Confirm demo arc with correct API schemas and deployment env template**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-27T04:03:20Z
- **Completed:** 2026-03-27T04:06:03Z
- **Tasks:** 2 (1 auto + 1 checkpoint auto-approved)
- **Files modified:** 2

## Accomplishments
- dry_run.py automates the full demo arc with wall-clock timing and PASS/WARN/FAIL thresholds
- Corrected API payload schemas to match actual InvestigateRequest (scenario + payment_request dict) and ConfirmRequest (episode_id + attack_type) models
- .env.example updated with comprehensive documentation of all env vars grouped by purpose

## Task Commits

Each task was committed atomically:

1. **Task 1: Create dry_run.py and .env.example** - `3e5b601` (feat)
2. **Task 2: Verify deployment readiness** - auto-approved checkpoint (no commit)

## Files Created/Modified
- `scripts/dry_run.py` - Timed dry-run of full demo arc: health check, Attack 1, Confirm 1, wait for rule gen, Attack 2, Confirm 2, elapsed time report
- `.env.example` - Environment variable template with all vars grouped by purpose (core, aerospike, bland, deployment, LLM backend)

## Decisions Made
- Adapted API payloads to actual endpoint schemas instead of plan's incorrect field names (attack_scenario -> scenario+payment_request, confirmed_attack -> attack_type) -- Rule 1 auto-fix
- Added 15s sleep after first confirm to allow background rule generation task to complete before triggering Attack 2

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Corrected API request schemas to match actual endpoints**
- **Found during:** Task 1 (dry_run.py creation)
- **Issue:** Plan specified `attack_scenario: "phase1_hidden_text"` and `confirmed_attack: True` but actual endpoints use `scenario: "phase1"` with `payment_request` dict and `attack_type` string
- **Fix:** Used correct InvestigateRequest (scenario + payment_request) and ConfirmRequest (episode_id + attack_type) schemas with /api/ prefix
- **Files modified:** scripts/dry_run.py
- **Verification:** Python AST parse passes, field names match actual Pydantic models
- **Committed in:** 3e5b601

**2. [Rule 2 - Missing Critical] Added rule generation wait time between Confirm 1 and Attack 2**
- **Found during:** Task 1 (dry_run.py creation)
- **Issue:** /confirm returns 202 immediately and runs rule generation in background -- Attack 2 must wait for the generated rule to be deployed so it can fire
- **Fix:** Added 15s asyncio.sleep after Confirm 1 to allow background rule generation to complete
- **Files modified:** scripts/dry_run.py
- **Committed in:** 3e5b601

---

**Total deviations:** 2 auto-fixed (1 bug, 1 missing critical)
**Impact on plan:** Both fixes essential for correctness. Without schema fix, requests would fail with 422. Without rule gen wait, Attack 2 would run before the generated rule is deployed.

## Issues Encountered
None beyond the schema corrections documented above.

## User Setup Required

**External services require manual configuration for Railway deployment:**
- ANTHROPIC_API_KEY from Anthropic Console
- BLAND_API_KEY from Bland AI Dashboard
- AEROSPIKE_HOST set to Railway internal DNS
- PUBLIC_HOST set to Railway-generated public URL

## Next Phase Readiness
- All demo scripts created: demo_check.py, reset_demo.py, dry_run.py
- .env.example documents full deployment configuration
- Phase 06 complete -- ready for demo day

---
*Phase: 06-demo-preparation-deployment*
*Completed: 2026-03-27*
