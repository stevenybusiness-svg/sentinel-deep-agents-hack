---
phase: 03-self-improvement-loop
plan: "03"
subsystem: api
tags: [confirm-route, rule-generation, rule-evolution, websocket, aerospike]
dependency_graph:
  requires: [03-01, 03-02]
  provides: [POST /confirm endpoint, rule generation pipeline API surface]
  affects: [sentinel/api/main.py, sentinel/gate/rules/, SafetyGate hot-reload]
tech_stack:
  added: []
  patterns:
    - asyncio.create_task for fire-and-forget background pipeline
    - Local import pattern to avoid circular deps (same as investigate.py)
    - ws_broadcast adapter wrapping ws_manager.broadcast() arg order difference
    - Aerospike optional fallback: rule_001 as default when Aerospike unavailable
key_files:
  created:
    - sentinel/api/routes/confirm.py
    - tests/test_confirm_route.py
  modified:
    - sentinel/api/main.py
decisions:
  - Background pipeline wrapped in try/except at top level — uncaught exceptions broadcast rule_generation_failed silently
  - ws_broadcast adapter needed because RuleGenerator.generate() calls ws_broadcast(event, data, episode_id) but ws_manager.broadcast() takes (event, episode_id, data) — adapter bridges the order difference
  - Evolution fallback to new generation when existing rule source not retrievable from Aerospike
  - Pre-existing test_frontend_build failure in test_infra.py (npm packages not installed in worktree) is out of scope — logged to deferred items
metrics:
  duration: "4m 24s"
  completed: "2026-03-25T16:36:43Z"
  tasks_completed: 2
  files_modified: 3
---

# Phase 03 Plan 03: POST /confirm Route with Rule Generation Pipeline Summary

POST /confirm endpoint wiring the complete self-improvement loop: operator confirmation triggers async rule generation/evolution pipeline streaming Opus 4.6 output via WebSocket, writing .py file + Aerospike provenance, and hot-reloading SafetyGate.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | POST /confirm route with background rule generation pipeline | 638d0e1 | sentinel/api/routes/confirm.py, sentinel/api/main.py |
| 2 | Tests for POST /confirm route (TDD) | 995d727 | tests/test_confirm_route.py |

## What Was Built

**sentinel/api/routes/confirm.py** — Full rule generation/evolution pipeline behind a 202 Accepted API:

- `POST /confirm` returns 202 immediately; spawns background `asyncio.create_task` for the pipeline
- Route validates episode exists in `app_state["active_episodes"]` cache (404 if not found)
- Background pipeline (`_run_rule_pipeline`) wrapped in outer try/except to broadcast `rule_generation_failed` on any uncaught error
- **New generation path**: `RuleGenerator.generate()` streams Opus 4.6 tokens as `rule_generating` WebSocket events; on success writes `.py` file to `sentinel/gate/rules/`, calls `gate.load_rules_from_directory()` for hot reload, writes provenance to Aerospike via `write_rule()`, broadcasts `rule_deployed`
- **Evolution path**: detected via non-empty `episode.generated_rules_fired`; loads v1 source + original VerdictBoard from Aerospike/active cache; calls `RuleGenerator.evolve()` with both VBs + prediction errors; overwrites same `.py` file; increments version in Aerospike; broadcasts `rule_deployed` with `version=N`
- ws_broadcast adapter bridges arg order difference between `RuleGenerator` (event, data, episode_id) and `ws_manager.broadcast` (event, episode_id, data)
- Graceful degradation: `rule_id = "rule_001"` fallback when Aerospike unavailable

**sentinel/api/main.py** — confirm_router registered alongside investigate_router.

**tests/test_confirm_route.py** — 7 tests:
1. `test_confirm_returns_202`: valid episode returns 202
2. `test_confirm_returns_404_for_unknown_episode`: nonexistent episode returns 404
3. `test_confirm_request_validation`: missing attack_type returns 422
4. `test_confirm_spawns_background_task`: asyncio.create_task called once
5. `test_confirm_response_schema`: body has episode_id + status="accepted"
6. `test_confirm_request_model`: Pydantic model validates
7. `test_confirm_response_model`: Pydantic model validates

## Verification

All acceptance criteria met:

- `python -c "from sentinel.api.main import app; routes = [r.path for r in app.routes]; assert '/confirm' in routes"` passes
- `python -m pytest tests/test_confirm_route.py -x -q` — 7 tests pass
- `python -m pytest tests/ -x -q --ignore=tests/test_claude_api.py --ignore=tests/test_infra.py` — 163 tests pass (no regressions)

## Deviations from Plan

### Auto-fixed Issues

None — plan executed exactly as specified.

### Observations (not deviations)

**ws_broadcast argument order**: RuleGenerator.generate()/evolve() calls `ws_broadcast(event_str, data_dict, episode_id)` but `ws_manager.broadcast()` signature is `(event, episode_id, data)`. An adapter `_broadcast()` was added to bridge the order difference. This is consistent with the RuleGenerator source code.

## Deferred Items

**test_frontend_build failure (pre-existing)**: `tests/test_infra.py::test_frontend_build` fails because npm packages are not installed in this git worktree. This is a pre-existing infrastructure issue unrelated to this plan's changes. The main repository frontend has its own `node_modules`. Excluded from test runs via `--ignore=tests/test_infra.py`.

## Known Stubs

None — all pipeline paths are wired to real implementations (RuleGenerator, write_rule, SafetyGate.load_rules_from_directory).

## Self-Check: PASSED

- sentinel/api/routes/confirm.py: FOUND
- tests/test_confirm_route.py: FOUND
- Commit 638d0e1: FOUND (feat(03-03): POST /confirm route with background rule generation pipeline)
- Commit 995d727: FOUND (test(03-03): add 7 tests for POST /confirm route)
- `/confirm` route registered in app routes: VERIFIED
- All 7 confirm tests pass: VERIFIED
- No regressions in 163 backend tests: VERIFIED
