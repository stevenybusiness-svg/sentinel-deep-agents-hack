---
phase: 06-demo-preparation-deployment
plan: 01
subsystem: infra
tags: [docker, docker-compose, aerospike, deployment, demo-validation, railway]

# Dependency graph
requires:
  - phase: 01-foundation
    provides: FastAPI app, Aerospike client, config, fixtures
  - phase: 04-dashboard
    provides: React frontend build
provides:
  - Dockerfile for Railway/container deployment
  - docker-compose.yml for full-stack local dev (sentinel + aerospike)
  - demo_check.py pre-flight validation script (7 integration checks)
  - reset_demo.py Aerospike state cleanup between dry runs
affects: [06-02, deployment, demo-dry-runs]

# Tech tracking
tech-stack:
  added: [docker, docker-compose, nodesource-20]
  patterns: [multi-service compose with health-check gating, pre-demo validation script pattern]

key-files:
  created:
    - Dockerfile
    - scripts/demo_check.py
    - scripts/reset_demo.py
  modified:
    - docker-compose.yml

key-decisions:
  - "Adjusted /investigate smoke test to /api/investigate matching actual router prefix"
  - "Fixtures at sentinel/fixtures/ not repo-root fixtures/ -- Dockerfile COPY sentinel/ captures them"

patterns-established:
  - "Pre-demo validation: numbered checks with inline OK/FAIL, exit code summary"
  - "Demo state reset: truncate all Aerospike sets for clean arc replay"

requirements-completed: [INFRA-06, DEMO-01, DEMO-02]

# Metrics
duration: 2min
completed: 2026-03-27
---

# Phase 06 Plan 01: Deployment and Demo Validation Summary

**Dockerfile with aerospike C-extension build, full-stack docker-compose with health-check gating, and demo pre-flight/reset scripts**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-27T03:59:11Z
- **Completed:** 2026-03-27T04:01:22Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Dockerfile builds production container with python:3.12-slim, aerospike C-extension deps, Node.js 20 frontend build, uvicorn entrypoint
- docker-compose.yml extended with sentinel service using build context, env_file, AEROSPIKE_HOST override, and health-check dependency gating
- demo_check.py validates 7 integration points (health, API keys, Bland AI reachability, WebSocket, fixtures, /investigate)
- reset_demo.py truncates episodes/rules/trust Aerospike sets for clean demo arc replay

## Task Commits

Each task was committed atomically:

1. **Task 1: Create Dockerfile and extend docker-compose.yml** - `82c9229` (feat)
2. **Task 2: Create demo_check.py and reset_demo.py scripts** - `6c097cc` (feat)

## Files Created/Modified
- `Dockerfile` - Production container with aerospike C-ext deps, Node.js 20, frontend build, uvicorn CMD
- `docker-compose.yml` - Full-stack local dev: sentinel + aerospike with health-check gating
- `scripts/demo_check.py` - Pre-demo validation (7 checks, --host flag, exit code)
- `scripts/reset_demo.py` - Aerospike set truncation (episodes, rules, trust)

## Decisions Made
- Adjusted /investigate endpoint path to /api/investigate to match actual router mount prefix in main.py (investigate_router mounted with prefix="/api")
- Fixtures live under sentinel/fixtures/ not repo-root fixtures/ -- COPY sentinel/ in Dockerfile captures them automatically; removed separate COPY fixtures/ line

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed /investigate endpoint path**
- **Found during:** Task 2 (demo_check.py)
- **Issue:** Plan specified `/investigate` but router is mounted at `/api` prefix in main.py
- **Fix:** Changed smoke test URL to `/api/investigate`
- **Files modified:** scripts/demo_check.py
- **Verification:** Path matches `app.include_router(investigate_router, prefix="/api")`
- **Committed in:** 6c097cc (Task 2 commit)

**2. [Rule 1 - Bug] Removed COPY fixtures/ from Dockerfile**
- **Found during:** Task 1 (Dockerfile creation)
- **Issue:** Plan specified `COPY fixtures/ ./fixtures/` but no repo-root fixtures/ dir exists; fixtures are at sentinel/fixtures/ already captured by `COPY sentinel/ ./sentinel/`
- **Fix:** Omitted the separate COPY fixtures/ line
- **Files modified:** Dockerfile
- **Verification:** `ls sentinel/fixtures/` confirms location
- **Committed in:** 82c9229 (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (2 bugs)
**Impact on plan:** Both fixes necessary for correctness. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Dockerfile and docker-compose.yml ready for `docker-compose up` local testing
- demo_check.py ready for pre-demo validation against any host
- reset_demo.py ready for state cleanup between dry runs
- Ready for 06-02 (Railway deployment / demo dry run)

## Self-Check: PASSED

All 4 files found. Both commit hashes verified.

---
*Phase: 06-demo-preparation-deployment*
*Completed: 2026-03-27*
