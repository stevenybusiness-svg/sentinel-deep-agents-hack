---
phase: 01-foundation
plan: "04"
subsystem: fixtures
tags: [fixtures, config, claude-api, pillow, prompt-caching, forensics]

requires:
  - phase: 01-01
    provides: Python project structure, venv, and pyproject.toml already in place

provides:
  - JSON fixture files (kyc_ledger, counterparty_db, behavioral_baselines) loadable by load_fixtures()
  - Forensic invoice PNG pair (invoice_clean.png with white-on-white hidden text, invoice_forensic.png with red highlights)
  - sentinel/fixtures/__init__.py: load_fixtures() + get_invoice_paths() with FixtureData TypedDict
  - sentinel/config.py: centralized Settings + get_settings() loading from .env via python-dotenv
  - tests/test_fixtures.py: 11 passing fixture loader tests
  - tests/test_claude_api.py: Claude API validation with prompt caching and mandatory key check

affects: [02-pipeline, 03-pipeline, 05-agents]

tech-stack:
  added: []
  patterns:
    - "Pillow (PIL) for programmatic invoice PNG generation with white-on-white steganographic text"
    - "FixtureData TypedDict for typed fixture loading contract"
    - "_HAS_REAL_KEY guard in test file to distinguish real API key from conftest placeholder"
    - "conftest.py setdefault pattern: placeholder allows test collection without real keys; skipif guards API calls"

key-files:
  created:
    - sentinel/fixtures/kyc_ledger.json
    - sentinel/fixtures/counterparty_db.json
    - sentinel/fixtures/behavioral_baselines.json
    - sentinel/fixtures/invoice_clean.png
    - sentinel/fixtures/invoice_forensic.png
    - sentinel/fixtures/generate_invoices.py
    - sentinel/config.py
    - tests/test_fixtures.py
    - tests/test_claude_api.py
  modified:
    - sentinel/fixtures/__init__.py

decisions:
  - "Meridian Logistics is intentionally absent from kyc_ledger.json — this is the mechanism that exposes the Phase 2 identity spoofing attack"
  - "Hidden text uses rgb(254,254,254) on white background — 1-step color difference invisible to human eye but detectable by vision model pixel analysis"
  - "invoice_forensic.png renders hidden text in red with red rectangle highlights at exact same positions as clean invoice hidden content"
  - "_HAS_REAL_KEY = key.startswith('sk-ant-') and key != 'sk-ant-test-placeholder' — conftest placeholder passes format check but should not trigger live API calls"

metrics:
  duration_minutes: 4
  completed_date: "2026-03-24"
  tasks_completed: 2
  files_created: 10
---

# Phase 01 Plan 04: Demo Fixtures, Config, and Claude API Validation Summary

**One-liner:** JSON demo fixtures + forensic invoice PNG pair with white-on-white hidden text + fixture loader TypedDict + centralized config + Claude API validation test with prompt caching and mandatory key enforcement.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Demo fixtures, invoice PNGs, fixture loader, config | 517534a | sentinel/fixtures/*.json, invoice_*.png, generate_invoices.py, fixtures/__init__.py, config.py, tests/test_fixtures.py |
| 2 | Claude API connection validation with prompt caching | 53c6cf0 | tests/test_claude_api.py |

## What Was Built

### Fixture Files
- **kyc_ledger.json**: 4 verified companies (Apex Financial, GlobalTrade Corp, Northern Pacific Industries, Silverline Payments). Meridian Logistics is intentionally absent — the Compliance Agent will search for it and find nothing, exposing the spoofed pre-clearance claim.
- **counterparty_db.json**: 4 counterparty records including Meridian Logistics explicitly marked `authorized: false`.
- **behavioral_baselines.json**: `payment_agent.mean=0.52`, `std=0.11` across 847 transactions — the values the Risk Agent uses for z-score computation.

### Invoice PNG Pair
Generated via Pillow script (`generate_invoices.py`):
- **invoice_clean.png** (52,777 bytes): Realistic 800x600 invoice for Meridian Logistics with two hidden text blocks rendered in rgb(254,254,254) on white background — invisible to human eye but detectable by vision model pixel analysis. Hidden content: payment override instruction routing to account 7734-XXXX and a bypass verification directive.
- **invoice_forensic.png** (57,503 bytes): Identical invoice with hidden text areas highlighted by red rectangles and text rendered in red — what the dashboard forensic scan side-by-side panel displays.

### Fixture Loader
`sentinel/fixtures/__init__.py` exports `load_fixtures() -> FixtureData` and `get_invoice_paths() -> dict[str, Path]`. The `FixtureData` TypedDict provides typed access to all three JSON fixtures.

### Config Module
`sentinel/config.py` exports `Settings` class and `get_settings()` singleton. Loads from `.env` at repo root via python-dotenv. Covers ANTHROPIC_API_KEY, AEROSPIKE_*, BLAND_API_KEY, OKTA_*.

### Claude API Test
`tests/test_claude_api.py` implements INFRA-03 validation:
- `test_anthropic_api_key_present`: Always runs; fails hard if key is absent or doesn't start with `sk-ant-`
- `test_claude_api_connection`: Verifies API responds with SENTINEL_OK (skips if no real key)
- `test_claude_prompt_caching`: Verifies cache_creation or cache_read > 0 using 100x repeated system prompt to exceed 1024 token minimum (skips if no real key)
- `test_no_rate_limit`: Passes if SDK doesn't raise RateLimitError (skips if no real key)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] skipif condition did not distinguish real key from conftest placeholder**
- **Found during:** Task 2 execution and test run
- **Issue:** conftest.py sets `ANTHROPIC_API_KEY=sk-ant-test-placeholder` via `os.environ.setdefault`. The plan's skipif condition `not os.getenv("ANTHROPIC_API_KEY")` evaluated to False (key is present), so API call tests ran and failed with 401 AuthenticationError instead of skipping.
- **Fix:** Added `_HAS_REAL_KEY = key.startswith("sk-ant-") and key != "sk-ant-test-placeholder"` constant; all three API call skipif conditions use `not _HAS_REAL_KEY` instead of `not os.getenv("ANTHROPIC_API_KEY")`
- **Files modified:** tests/test_claude_api.py
- **Commit:** 53c6cf0

## Known Stubs

None. All fixture data is fully populated with realistic demo content. Invoice PNGs contain actual white-on-white steganographic content (not placeholder images). The `test_anthropic_api_key_present` test always runs; API call tests skip gracefully when no real key is present — this is intentional design, not a stub.

## Self-Check: PASSED

Files created/verified:
- sentinel/fixtures/kyc_ledger.json: EXISTS
- sentinel/fixtures/counterparty_db.json: EXISTS
- sentinel/fixtures/behavioral_baselines.json: EXISTS
- sentinel/fixtures/invoice_clean.png: EXISTS (52,777 bytes, valid PNG)
- sentinel/fixtures/invoice_forensic.png: EXISTS (57,503 bytes, valid PNG)
- sentinel/fixtures/generate_invoices.py: EXISTS
- sentinel/config.py: EXISTS
- tests/test_fixtures.py: EXISTS (11 tests, all passing)
- tests/test_claude_api.py: EXISTS (1 passing, 3 skipped)

Commits verified:
- 517534a: feat(01-04): demo fixtures, invoice PNGs, fixture loader, and config module
- 53c6cf0: feat(01-04): Claude API connection validation test with prompt caching
