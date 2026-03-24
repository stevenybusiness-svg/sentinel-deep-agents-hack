---
phase: quick
plan: 260324-j7c
subsystem: llm-client
tags: [bedrock, anthropic-sdk, config, factory]
dependency_graph:
  requires: []
  provides: [sentinel/llm_client.py]
  affects: [sentinel/config.py]
tech_stack:
  added: [anthropic[bedrock] extra, AsyncAnthropicBedrock]
  patterns: [factory function, singleton reset for tests, instance-level env reads]
key_files:
  created:
    - sentinel/llm_client.py
    - tests/test_llm_client.py
  modified:
    - sentinel/config.py
    - pyproject.toml
    - .env.example
decisions:
  - "Settings reads env vars in __init__ (instance-level) not at class body (class-level) — required for singleton reset pattern to work in tests and for env-var-based config to be runtime-switchable"
  - "get_model_ids() reads from _settings singleton per call — no caching of model IDs separately from settings"
metrics:
  duration: "~12 minutes"
  completed: "2026-03-24"
  tasks: 2
  files: 5
---

# Quick Task 260324-j7c: Add Bedrock Backend Support Summary

**One-liner:** LLM client factory with `LLM_BACKEND` env switch — returns `AsyncAnthropic` by default, `AsyncAnthropicBedrock` when set to `bedrock`, with per-backend model ID defaults and env overrides.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | Failing tests for LLM client factory | 40e818e | tests/test_llm_client.py |
| 1+2 (GREEN) | Bedrock backend + LLM client factory | f8000cd | sentinel/llm_client.py, sentinel/config.py, pyproject.toml, .env.example |

## What Was Built

### `sentinel/llm_client.py`
New factory module with two exported functions:

- `get_async_client()` — Returns `AsyncAnthropic` (default) or `AsyncAnthropicBedrock` based on `LLM_BACKEND`. Raises `ValueError` for unknown backends.
- `get_model_ids()` — Returns `{"supervisor": ..., "agent": ...}` with per-backend defaults, overridable via `SUPERVISOR_MODEL` / `AGENT_MODEL` env vars.

Model ID defaults:
| Backend | Supervisor | Agent |
|---------|-----------|-------|
| anthropic | claude-opus-4-6 | claude-sonnet-4-6 |
| bedrock | us.anthropic.claude-opus-4-5-20251101-v1:0 | us.anthropic.claude-sonnet-4-5-20251001-v1:0 |

### Config Changes
- `sentinel/config.py`: Moved all `os.getenv()` calls from class body to `__init__` so env vars are read at instantiation, enabling the singleton-reset pattern in tests
- Added: `LLM_BACKEND`, `AWS_REGION`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `SUPERVISOR_MODEL`, `AGENT_MODEL`
- `pyproject.toml`: `anthropic[aiohttp,bedrock]==0.86.0` (added `bedrock` extra)
- `.env.example`: Documents new LLM backend vars with comments

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed Settings class body vs instance env var reading**
- **Found during:** Task 1/2 GREEN — tests failed because `patch.dict(os.environ, ...)` had no effect on Settings
- **Issue:** `Settings` class attributes were evaluated once at class definition time (`class Settings: FIELD = os.getenv(...)`), not at `Settings()` instantiation. Resetting `_settings = None` created a new `Settings()` but the class body was already evaluated, so all fields still held the original import-time values.
- **Fix:** Moved all `os.getenv()` calls to `Settings.__init__()` so each instantiation re-reads the environment. This is the correct pattern for a singleton that needs to be reset between tests.
- **Files modified:** sentinel/config.py
- **Commit:** f8000cd
- **Backward compatibility:** Zero breakage — attribute access (`settings.FIELD`) is identical; only evaluation timing changed.

## Test Results

```
56 passed, 5 skipped (live services) in 3.25s
```

All 8 new LLM client tests pass. No regressions in existing test suite.

## Verification

- `python -c "from sentinel.llm_client import get_async_client, get_model_ids; print('imports ok')"` — PASSED
- `python -c "from sentinel.config import get_settings; s = get_settings(); print(s.LLM_BACKEND)"` — prints `anthropic`
- `python -m pytest tests/test_llm_client.py -v` — 8/8 passed
- `python -m pytest tests/ -v` — 56 passed, 5 skipped

## Known Stubs

None — factory is fully wired. Bedrock client construction is validated by test with mock AWS credentials.

## Self-Check: PASSED

- sentinel/llm_client.py: FOUND
- tests/test_llm_client.py: FOUND
- Commit 40e818e: FOUND
- Commit f8000cd: FOUND
