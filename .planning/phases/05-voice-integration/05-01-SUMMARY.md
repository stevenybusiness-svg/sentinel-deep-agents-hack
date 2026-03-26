---
phase: 05-voice-integration
plan: 01
subsystem: voice-backend
tags: [bland-ai, voice, webhook, fastapi, tdd]
dependency_graph:
  requires: [sentinel/api/main.py, sentinel/api/routes/investigate.py, sentinel/schemas/episode.py]
  provides: [POST /bland-webhook, POST /bland-call, __latest__ sentinel key in active_episodes]
  affects: [sentinel/api/main.py, sentinel/api/routes/investigate.py]
tech_stack:
  added: []
  patterns: [in-memory voice context cache, __latest__ sentinel key fallback, zero-I/O webhook handler]
key_files:
  created:
    - sentinel/api/routes/bland_webhook.py
    - sentinel/api/routes/bland_call.py
    - tests/test_bland_webhook.py
    - tests/test_bland_call.py
  modified:
    - sentinel/api/main.py
    - sentinel/api/routes/investigate.py
decisions:
  - "Use __latest__ sentinel key as primary fallback strategy (not Bland request_data threading) — simpler and more reliable given underdocumented variable interpolation in dynamic_data body"
  - "Return 503 from /bland-call when BLAND_API_KEY is placeholder — prevents silent auth failure"
  - "first_sentence in call payload allows immediate AI speech without waiting for dynamic_data on first utterance"
metrics:
  duration_seconds: 287
  completed_date: "2026-03-26"
  tasks_completed: 2
  files_created: 4
  files_modified: 2
---

# Phase 05 Plan 01: Bland AI Voice Backend Summary

**One-liner:** Zero-I/O POST /bland-webhook handler with __latest__ fallback + POST /bland-call with model=base, interruption_threshold=150, and dynamic_data injecting 5-field investigation context per utterance.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create POST /bland-webhook handler with tests | a7628e1 | sentinel/api/routes/bland_webhook.py, tests/test_bland_webhook.py, sentinel/api/main.py |
| 2 | Create POST /bland-call route, wire both routes, add __latest__ sentinel key | 24f9224 | sentinel/api/routes/bland_call.py, tests/test_bland_call.py, sentinel/api/main.py, sentinel/api/routes/investigate.py |

## What Was Built

### POST /bland-webhook (sentinel/api/routes/bland_webhook.py)
- Returns 5-field voice context dict from in-memory `active_episodes` cache
- Falls back to `__latest__` sentinel key when `episode_id` is missing or unrecognized
- Returns safe NO-GO fallback dict when cache is empty
- Tolerates malformed/empty request body
- Zero I/O: no Aerospike reads, no LLM calls, no file access — pure dict lookups
- `_summarize_prediction_errors()` extracts z-score, step deviation, outcome mismatches

### POST /bland-call (sentinel/api/routes/bland_call.py)
- Pydantic models: `StartCallRequest(episode_id, phone_number, public_host)`, `StartCallResponse(call_id, status)`
- Returns 404 if episode not in active cache
- Returns 503 if BLAND_API_KEY not configured or is placeholder
- `_build_call_payload(req)`: model="base", interruption_threshold=150, block_interruptions=False
- dynamic_data: single entry with /bland-webhook URL, timeout=3000, cache=False, 5-field response_data mapping
- request_data: episode_id threaded through for dynamic_data body interpolation fallback
- first_sentence: static opening line so AI speaks immediately before dynamic_data load

### main.py wiring
- Registered `bland_call_router` and `bland_webhook_router`
- Added `bland_api_key` and `public_host` to lifespan startup from env vars

### investigate.py
- Added `app_state["active_episodes"]["__latest__"] = result["episode_id"]` after every investigation caches its episode

## Test Results

9 tests, 9 passing:

**test_bland_webhook.py (5):**
- `test_webhook_returns_context` — known episode returns correct 5-field context
- `test_webhook_fallback_latest` — unknown episode_id resolves via `__latest__` key
- `test_webhook_empty_cache` — empty cache returns safe NO-GO fallback
- `test_webhook_no_body` — malformed body falls back to `__latest__`
- `test_context_fields_complete` — response always has exactly 5 keys

**test_bland_call.py (4):**
- `test_call_payload_structure` — phone, task, voice, model=base, /bland-webhook URL, request_data episode_id
- `test_barge_in_params` — interruption_threshold=150, block_interruptions=False
- `test_call_episode_not_found` — unknown episode_id returns 404
- `test_dynamic_data_timeout` — dynamic_data[0]["timeout"] == 3000

## Deviations from Plan

None — plan executed exactly as written.

The `test_confirm_route.py` pre-existing failure (unrelated 405 on `/confirm`) was noted as out-of-scope — not caused by this plan's changes. Confirmed by checking it failed before these changes due to missing aerospike module.

## Known Stubs

None — both routes are fully implemented. The /bland-call route gracefully degrades (503) when BLAND_API_KEY is not configured, which is expected in development without real credentials.

## Self-Check: PASSED

Files created:
- sentinel/api/routes/bland_webhook.py: EXISTS
- sentinel/api/routes/bland_call.py: EXISTS
- tests/test_bland_webhook.py: EXISTS
- tests/test_bland_call.py: EXISTS

Files modified:
- sentinel/api/main.py: bland_call_router, bland_webhook_router, bland_api_key confirmed
- sentinel/api/routes/investigate.py: __latest__ key confirmed

Commits:
- a7628e1: feat(05-01): create POST /bland-webhook handler with tests
- 24f9224: feat(05-01): create POST /bland-call route, wire routes, add __latest__ sentinel key
