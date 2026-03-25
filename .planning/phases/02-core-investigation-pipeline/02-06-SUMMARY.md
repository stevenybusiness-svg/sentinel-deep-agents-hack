---
phase: 02-core-investigation-pipeline
plan: "06"
subsystem: supervisor-and-api
tags: [supervisor, fastapi, websocket, integration, opus-llm, taskgroup]
dependency_graph:
  requires: ["02-02", "02-03", "02-04", "02-05"]
  provides: ["run_investigation", "FastAPI app", "WebSocket broadcaster", "POST /investigate"]
  affects: ["Phase 3 self-improvement loop", "Frontend dashboard", "Voice interface"]
tech_stack:
  added: [FastAPI lifespan, asyncio.TaskGroup, ConnectionManager, WebSocket]
  patterns: [Opus-drives-Sonnet-turn-by-turn, parallel-investigator-dispatch, graceful-Aerospike-degradation]
key_files:
  created:
    - sentinel/agents/supervisor.py
    - sentinel/api/websocket.py
    - sentinel/api/main.py
    - sentinel/api/routes/__init__.py
    - sentinel/api/routes/investigate.py
    - tests/test_api.py
    - tests/test_supervisor.py
  modified: []
decisions:
  - "Supervisor makes real Opus 4.6 LLM call first, then drives Payment Agent (Sonnet 4.6) turn-by-turn via handle_tool_call/parse_payment_decision (D-03)"
  - "asyncio.TaskGroup used for parallel Risk/Compliance/Forensics dispatch with per-agent exception handling (D-13)"
  - "Aerospike failure gracefully degrades — server continues, episodes not persisted (API-02 non-blocking)"
  - "invoice_path=None when no invoice — Forensics handles None correctly (PIPE-06)"
  - "Active episodes cached in app_state for voice Q&A without additional DB round-trips (API-02)"
metrics:
  duration: "8 minutes"
  completed_date: "2026-03-25"
  tasks: 3
  files: 7
---

# Phase 02 Plan 06: Supervisor and FastAPI Integration Summary

**One-liner:** Opus 4.6 Supervisor drives Sonnet 4.6 Payment Agent turn-by-turn, dispatches 3 parallel investigators via asyncio.TaskGroup, and serves the full investigation pipeline via FastAPI /investigate + WebSocket /ws endpoints.

## What Was Built

### Task 1: Supervisor (Opus 4.6 LLM) + WebSocket ConnectionManager

**`sentinel/agents/supervisor.py`** — `run_investigation()` is the complete pipeline:
1. Broadcasts `investigation_started` over WebSocket
2. Loads recent episodes from Aerospike via `get_recent_episodes()` (MEM-04), injects summaries into the Supervisor's Opus 4.6 LLM system prompt
3. Makes a real Opus 4.6 LLM call to reason about the payment request (D-03)
4. Drives Payment Agent (Sonnet 4.6) multi-turn conversation: `handle_tool_call()` per tool_use block, `parse_payment_decision()` on end_turn
5. Calls `PredictionEngine.predict()` before sub-agent dispatch (D-08)
6. Dispatches Risk, Compliance, Forensics in parallel via `asyncio.TaskGroup` — each wrapped in try/except that produces `unable_to_verify=True` on failure (PIPE-02, D-13)
7. Assembles VerdictBoard, attaches prediction_errors dict (D-12)
8. Calls `PredictionEngine.compare_outcomes()` after investigation (D-09)
9. Runs Safety Gate evaluation (deterministic, no LLM in enforcement path)
10. Builds Episode, writes to Aerospike (graceful degradation), broadcasts remaining events

**`sentinel/api/websocket.py`** — `ConnectionManager` with `broadcast(event, episode_id, data)`, dead connection pruning, and module-level `ws_manager` singleton.

### Task 2: FastAPI App

**`sentinel/api/main.py`** — FastAPI app with lifespan:
- Loads fixtures, LLM client, Safety Gate rules at startup
- Connects to Aerospike and pre-loads behavioral baselines; degrades gracefully if unavailable
- `/ws` WebSocket endpoint using `ws_manager`
- `/health` endpoint with Aerospike status
- Routes from `sentinel/api/routes/investigate.py`

**`sentinel/api/routes/investigate.py`** — `POST /investigate`:
- Accepts `InvestigateRequest` (payment_request, scenario)
- Determines invoice_path based on scenario (`None` for phase2, fixture path for phase1)
- Calls `run_investigation()` with all app_state dependencies
- Caches active episode in `app_state["active_episodes"]` for voice Q&A
- Returns `InvestigateResponse` with decision, composite_score, attribution

### Task 3: Unit Tests

**`tests/test_api.py`** — 6 tests covering: app import, broadcast to connected clients, InvestigateRequest/Response schema validation, disconnect, dead connection pruning.

**`tests/test_supervisor.py`** — 8 tests covering:
- `test_supervisor_uses_opus_model`: verifies first LLM call uses `models["supervisor"]`
- `test_supervisor_drives_payment_agent_turns`: verifies `handle_tool_call` and `parse_payment_decision` called correctly
- `test_parallel_dispatch_taskgroup`: all 3 sub-agents dispatched
- `test_unable_to_verify_fallback`: risk.analyze exception -> verdict.unable_to_verify=True, investigation completes
- `test_event_broadcast_sequence`: events broadcast in correct order
- `test_recent_episodes_injected`: `get_recent_episodes` called and episode summaries in Supervisor prompt
- `test_compare_outcomes_called`: `PredictionEngine.compare_outcomes` called after investigation
- `test_extract_actual_findings_from_verdicts`: helper maps compliance/forensics verdicts to finding keys

## Verification Results

```
14 passed, 11 warnings in 1.56s
```

All acceptance criteria met:
- `python -c "from sentinel.api.main import app"` succeeds
- Routes: `/investigate` (POST), `/ws` (WebSocket), `/health` (GET)
- Supervisor uses `models["supervisor"]` (Opus 4.6) for reasoning call
- Supervisor calls `get_recent_episodes()` and injects into LLM context
- Supervisor calls `compare_outcomes()` after investigation
- No `Path('/dev/null')` in code (only in doc comments)

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all code paths are wired to real dependencies with graceful degradation for Aerospike.

## Self-Check: PASSED

- sentinel/agents/supervisor.py: FOUND
- sentinel/api/websocket.py: FOUND
- sentinel/api/main.py: FOUND
- sentinel/api/routes/__init__.py: FOUND
- sentinel/api/routes/investigate.py: FOUND
- tests/test_api.py: FOUND
- tests/test_supervisor.py: FOUND
- Task 1 commit 72ba9f9: FOUND
- Task 2 commit 3e87bfc: FOUND
- Task 3 commit b7e07a9: FOUND
