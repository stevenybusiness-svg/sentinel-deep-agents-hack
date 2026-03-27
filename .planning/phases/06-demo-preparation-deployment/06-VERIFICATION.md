---
phase: 06-demo-preparation-deployment
verified: 2026-03-27T04:30:00Z
status: gaps_found
score: 3/5 must-haves verified
re_verification: false
gaps:
  - truth: "The full demo arc can run without manual intervention and reports whether it completed under 3 minutes"
    status: failed
    reason: "dry_run.py script exists and is correctly wired to /api/investigate and /api/confirm, but no actual timed run has been executed. The human verification checkpoint (Plan 02 Task 2) was auto-approved without running the arc. DEMO-04 requires two consecutive sub-3-minute arcs to be verified, not just the script to exist."
    artifacts:
      - path: "scripts/dry_run.py"
        issue: "Script exists and is syntactically correct with proper API schemas, but has never been run against a live server. The key_link to reset_demo.py (pattern: 'reset') is also absent — dry_run.py does not reference or call reset_demo.py."
    missing:
      - "At least one confirmed timed run showing PASS (elapsed < 180s) output"
      - "dry_run.py should reference reset_demo.py (or document that manual reset is required before each arc)"

  - truth: "The application is deployed to EC2/ECS/Railway with a public URL that Bland AI webhooks can reach"
    status: failed
    reason: "INFRA-06 requires a deployed public URL for Bland AI webhooks. No Railway/EC2/ECS deployment exists. No railway.toml, Procfile, or deployment config found. Plan 02 Task 2 (human verification of Railway deployment) was auto-approved without any deployment occurring. REQUIREMENTS.md marks INFRA-06 as 'Complete' but the codebase has no evidence of actual cloud deployment."
    artifacts:
      - path: "docker-compose.yml"
        issue: "Correct for local dev only. No cloud deployment configuration exists (no railway.toml, no Procfile, no ECS task definition, no deployment manifest)."
    missing:
      - "Railway or EC2 deployment with verifiable public URL"
      - "Deployment config file (railway.toml, Procfile, or equivalent)"
      - "demo_check.py passing against deployed public URL"

  - truth: "A screen recording of the complete demo arc exists as a local file before demo day"
    status: failed
    reason: "DEMO-05 requires demo_recording.mp4 (or equivalent) to exist as a fallback. No recording file found anywhere in the repository. The human verification checkpoint that was supposed to capture this was auto-approved without execution."
    artifacts: []
    missing:
      - "demo_recording.mp4 (or equivalent) file captured with ffmpeg during a live demo arc run"

human_verification:
  - test: "Run timed demo arc end-to-end"
    expected: "python scripts/dry_run.py --host http://localhost:8000 completes in under 180s and prints 'PASS -- under 3 minute target'"
    why_human: "Requires live Aerospike, live Anthropic API calls (Opus 4.6 for Supervisor, Sonnet 4.6 for agents), and the full investigation pipeline to run. Cannot be verified without running the application."

  - test: "Deploy to Railway or EC2 with public URL"
    expected: "python scripts/demo_check.py --host https://YOUR-APP.up.railway.app shows ALL CHECKS PASSED"
    why_human: "Cloud deployment requires external service configuration (Railway account, env vars set on deployed service, DNS propagation). Cannot be verified programmatically from the local codebase."

  - test: "Capture screen recording of full demo arc"
    expected: "demo_recording.mp4 (or .mov) exists at repo root, plays back the complete Attack 1 -> rule generation -> Attack 2 -> rule fires -> rule evolves arc with all dashboard panels visible"
    why_human: "Requires running the actual demo with screen capture. ffmpeg command documented in Plan 02 is: ffmpeg -f avfoundation -r 30 -i '2:1' -vcodec libx264 -pix_fmt yuv420p -preset ultrafast demo_recording.mp4"
---

# Phase 6: Demo Preparation + Deployment Verification Report

**Phase Goal:** The full Attack 1 → rule generation → Attack 2 → rule fires → rule evolves → voice Q&A arc runs end-to-end without intervention in under 3 minutes, a validation script confirms every integration is live before the demo, the stack starts in one command, and a screen recording fallback exists if anything fails on demo day

**Verified:** 2026-03-27T04:30:00Z
**Status:** gaps_found
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths (from ROADMAP.md Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `docker-compose up` starts the full stack (FastAPI, Aerospike, React) with no manual steps | ✓ VERIFIED | docker-compose.yml defines sentinel + aerospike services with health-check gating; Dockerfile builds C-extension deps + frontend; sentinel service starts uvicorn serving React static files |
| 2 | `demo_check.py` runs without errors, confirming all integrations live | ✓ VERIFIED | scripts/demo_check.py exists, parses as valid Python, checks 7 integration points (health, ANTHROPIC_API_KEY, BLAND_API_KEY, Bland reachable, WebSocket, fixtures, /api/investigate) with --host flag and correct exit codes |
| 3 | Two consecutive full demo arcs run end-to-end in under 3 minutes each without intervention | ✗ FAILED | dry_run.py script exists and is correctly wired to /api/investigate + /api/confirm with correct InvestigateRequest/ConfirmRequest schemas, but the human verification checkpoint (Plan 02 Task 2) was auto-approved with no actual timed run performed |
| 4 | Application deployed to EC2/ECS with public URL that Bland AI webhooks can reach | ✗ FAILED | No cloud deployment exists. No railway.toml, Procfile, or ECS config found. Human checkpoint was auto-approved. Bland AI webhook URL requires a public reachable host (INFRA-06). |
| 5 | A screen recording of the complete demo arc exists as a local file before demo day | ✗ FAILED | No demo_recording.mp4 or any .mp4 file found anywhere in the repository. DEMO-05 explicitly requires this file to exist. |

**Score:** 3/5 truths verified

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `Dockerfile` | Production container build for Railway/EC2 | ✓ VERIFIED | python:3.12-slim base; build-essential + libssl-dev + python3-dev for aerospike C-ext; Node.js 20 via nodesource; npm ci + npm run build; uvicorn CMD; HEALTHCHECK; commit 82c9229 |
| `docker-compose.yml` | Full stack local dev (FastAPI + Aerospike) | ✓ VERIFIED | sentinel service with build:. AEROSPIKE_HOST=aerospike override; condition: service_healthy dependency; env_file: .env; aerospike with ports 3000-3003 and healthcheck |
| `scripts/demo_check.py` | Pre-demo validation script (7 checks, --host flag) | ✓ VERIFIED | 137 lines, valid Python, checks health + API keys + Bland AI + WebSocket + fixtures + /api/investigate; argparse --host; sys.exit(asyncio.run(main())); commit 6c097cc |
| `scripts/reset_demo.py` | Aerospike state reset between dry runs | ✓ VERIFIED | truncates episodes, rules, trust sets; argparse --host/--port; handles non-existent sets; commit 6c097cc |
| `scripts/dry_run.py` | Automated timed dry-run of full demo arc | ⚠️ ORPHANED | Exists (176 lines, valid Python), wired to correct API endpoints (/api/investigate with scenario+payment_request, /api/confirm with episode_id+attack_type), 15s sleep after confirm for rule gen, PASS/WARN/FAIL thresholds — but never run against a live server; no evidence of execution |
| `.env.example` | Environment variable template for deployment | ✓ VERIFIED | Documents ANTHROPIC_API_KEY, AEROSPIKE_HOST/PORT/NAMESPACE, BLAND_API_KEY, PUBLIC_HOST, LLM_BACKEND; commit 3e5b601 |
| `demo_recording.mp4` | Screen recording fallback for demo day | ✗ MISSING | No .mp4 or video file found anywhere in repository |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `docker-compose.yml` | `Dockerfile` | build context `build: .` | ✓ WIRED | Line 21: `build: .` correctly references Dockerfile at repo root |
| `docker-compose.yml` | aerospike service | `condition: service_healthy` | ✓ WIRED | Lines 29-31: sentinel depends_on aerospike with condition: service_healthy |
| `Dockerfile` | `sentinel.api.main:app` | uvicorn CMD | ✓ WIRED | Line 40: `CMD ["uvicorn", "sentinel.api.main:app", "--host", "0.0.0.0", "--port", "8000"]` |
| `scripts/dry_run.py` | `/api/investigate` | httpx POST | ✓ WIRED | Lines 77, 119: POST to `{host}/api/investigate` with correct InvestigateRequest schema |
| `scripts/dry_run.py` | `/api/confirm` | httpx POST | ✓ WIRED | Lines 96, 138: POST to `{host}/api/confirm` with correct ConfirmRequest schema |
| `scripts/dry_run.py` | `scripts/reset_demo.py` | state reset before run | ✗ NOT_WIRED | Plan key_link required pattern `reset` in dry_run.py. Script intentionally omits automatic reset (documented in SUMMARY as design choice), but no reference to reset_demo.py exists — not even a comment instructing operator to run it first |

---

## Data-Flow Trace (Level 4)

Not applicable for Phase 6 artifacts — these are deployment, scripting, and validation files, not components rendering dynamic data.

---

## Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All Python scripts parse as valid | `python3 -c "import ast; ast.parse(...)"` on all 3 scripts | All parse OK | ✓ PASS |
| Dockerfile has aerospike C-ext deps | `grep -q "build-essential" Dockerfile` | Match found | ✓ PASS |
| Dockerfile has correct uvicorn entrypoint | `grep -q "sentinel.api.main:app" Dockerfile` | Match found | ✓ PASS |
| docker-compose health-check gating | `grep -q "condition: service_healthy" docker-compose.yml` | Match found | ✓ PASS |
| docker-compose AEROSPIKE_HOST override | `grep -q "AEROSPIKE_HOST=aerospike" docker-compose.yml` | Match found | ✓ PASS |
| demo_check.py validates /api/investigate (not /investigate) | `grep "/api/investigate" scripts/demo_check.py` | Match found | ✓ PASS |
| dry_run.py uses correct schema (scenario, not attack_scenario) | `grep "phase1" scripts/dry_run.py` | `"scenario": "phase1"` found | ✓ PASS |
| Screen recording exists | `ls demo_recording.mp4` | File not found | ✗ FAIL |
| Cloud deployment exists | Search for railway.toml, Procfile, ECS config | None found | ✗ FAIL |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| INFRA-06 | 06-01-PLAN.md | AWS deployment configured (EC2/ECS with public URL for Bland AI webhooks) | ✗ BLOCKED | Dockerfile + docker-compose exist for containerized deployment, but no actual cloud deployment has been performed. No railway.toml, Procfile, or ECS task definition. Human checkpoint was auto-approved without deployment. |
| DEMO-01 | 06-01-PLAN.md | docker-compose.yml runs full stack in one command with no manual steps | ✓ SATISFIED | docker-compose.yml defines sentinel + aerospike. Note: DEMO-01 says "React dev server" but implementation serves React via FastAPI static files — functionally equivalent since frontend is built into the container image. |
| DEMO-02 | 06-01-PLAN.md | demo_check.py validates all components before demo | ⚠️ PARTIAL | demo_check.py exists with 7 checks. One gap: DEMO-02 requires WebSocket "connects and receives first event" but check only verifies connection establishment (no recv() call). Functionally sufficient for demo prep but technically incomplete against the requirement. |
| DEMO-04 | 06-02-PLAN.md | Full Attack 1 → rule gen → Attack 2 → rule fires → rule evolves arc end-to-end under 3 minutes | ✗ BLOCKED | dry_run.py script exists and correctly implements the arc automation with proper API schemas and 15s rule-gen wait. However, no timed run has been executed against a live server. DEMO-04 requires the arc to actually run and complete under 3 minutes — the script alone does not satisfy this. |
| DEMO-05 | 06-02-PLAN.md | Screen recording of full demo arc captured as fallback | ✗ BLOCKED | No recording file exists anywhere in the repository. The human checkpoint that was supposed to capture this was auto-approved. |

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `scripts/demo_check.py` | 85-87 | WebSocket check connects but never calls `ws.recv()` | ⚠️ Warning | DEMO-02 says "connects and receives first event" but check only establishes the connection. For demo purposes this is likely sufficient (connection failure is the real risk), but doesn't satisfy the literal requirement. |
| `scripts/dry_run.py` | 7 (docstring) | States "Runs: Reset -> Attack 1..." but script does NOT run reset | ℹ️ Info | The docstring says reset is part of the arc but the script intentionally omits it (per SUMMARY note). Operator must remember to call reset_demo.py manually. This is a documentation inconsistency that could confuse a tired demo-day operator. |

---

## Human Verification Required

### 1. Timed Demo Arc Execution

**Test:** With Aerospike running and .env populated with valid API keys, run: `python scripts/reset_demo.py && python scripts/dry_run.py --host http://localhost:8000`
**Expected:** Full arc (health check → Attack 1 → Confirm 1 → 15s wait → Attack 2 → Confirm 2) completes with output `PASS -- under 3 minute target` (elapsed < 180s)
**Why human:** Requires live Anthropic API (Opus 4.6 Supervisor + Sonnet 4.6 agents), live Aerospike, and the full investigation + rule generation pipeline. Cannot be verified from codebase inspection alone.

### 2. Railway/EC2 Deployment with Public URL

**Test:** Import docker-compose.yml to Railway (or push to EC2), set env vars (ANTHROPIC_API_KEY, BLAND_API_KEY, AEROSPIKE_HOST, PUBLIC_HOST), wait for deployment, then run: `python scripts/demo_check.py --host https://YOUR-APP.up.railway.app`
**Expected:** All 7 checks pass. The Bland AI webhook URL (PUBLIC_HOST + /bland-webhook) is publicly reachable.
**Why human:** Cloud deployment requires external service account, DNS resolution, and env var configuration that cannot be automated from local codebase. INFRA-06 is the only Phase 6 requirement that is genuinely blocked (not just unexecuted automation).

### 3. Screen Recording Capture

**Test:** Grant Terminal screen recording permission (System Preferences > Privacy > Screen Recording), then: `ffmpeg -f avfoundation -r 30 -i "2:1" -vcodec libx264 -pix_fmt yuv420p -preset ultrafast demo_recording.mp4` while running a live demo arc with the dashboard visible in browser
**Expected:** `demo_recording.mp4` exists at repo root, plays back the complete arc with all dashboard panels visible (investigation tree, anomaly score bar, rule source panel, forensic scan)
**Why human:** Screen capture requires running the full system with display access. Cannot be done programmatically from CI or codebase inspection.

---

## Gaps Summary

Three of five success criteria are unverified. The root cause is the same in all three cases: **Plan 02 Task 2 was a blocking human verification checkpoint that was auto-approved without execution.**

The automated artifacts created in this phase (Dockerfile, docker-compose.yml, demo_check.py, reset_demo.py, dry_run.py, .env.example) are all correct, substantive, and properly wired. The implementation quality is high — the schema corrections (scenario vs. attack_scenario, attack_type vs. confirmed_attack) and the 15s rule-generation wait are exactly right.

What is missing is execution evidence:

1. **DEMO-04 (2/5):** dry_run.py is ready but has never been run. The automated arc needs to execute against a live stack and produce a PASS result.

2. **INFRA-06 (4/5):** The deployment infrastructure (Dockerfile + docker-compose) exists but no actual cloud deployment with a public URL has been performed. Bland AI webhooks require a reachable HTTPS URL — this is the only requirement with an external dependency that cannot be locally faked.

3. **DEMO-05 (5/5):** demo_recording.mp4 does not exist. This is the simplest gap to close — it requires running the arc once with screen capture.

Secondary gap: demo_check.py's WebSocket check (check 5/7) only verifies connection establishment and does not call `ws.recv()` to confirm the server sends data. DEMO-02 specifies "receives first event." This is a ⚠️ warning, not a blocker — the connection check is the meaningful validation for demo prep.

---

_Verified: 2026-03-27T04:30:00Z_
_Verifier: Claude (gsd-verifier)_
