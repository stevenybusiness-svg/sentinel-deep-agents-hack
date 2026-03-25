---
phase: "02"
plan: "01"
subsystem: schemas-and-prediction-engine
tags: [schemas, pydantic, prediction, tdd, d-05, d-08, d-09, d-10, d-11]
dependency_graph:
  requires: []
  provides: [PaymentDecision-schema, PredictionEngine, PredictionReport]
  affects: [02-02, 02-03, 02-04, 02-05, 02-06, 03-01]
tech_stack:
  added: [sentinel.engine.prediction, sentinel.schemas.payment]
  patterns: [pydantic-v2-models, tdd-red-green, z-score-behavioral-baseline]
key_files:
  created:
    - sentinel/schemas/payment.py
    - sentinel/engine/__init__.py
    - sentinel/engine/prediction.py
    - tests/test_prediction.py
  modified:
    - sentinel/schemas/verdict_board.py
    - sentinel/schemas/episode.py
    - sentinel/schemas/__init__.py
decisions:
  - "PaymentDecision.steps_taken is list[str] (ordered tool calls) — primary signal for step deviation detection"
  - "summary_score formula: abs(z_score) * 0.3 + (0.5 if deviation else 0.0) — deviation weighted higher as stronger signal"
  - "expected_investigation_outcomes derived purely from agent's own claims — no external knowledge required at prediction time"
metrics:
  duration_minutes: 3
  tasks_completed: 2
  files_created: 4
  files_modified: 3
  completed_date: "2026-03-25"
---

# Phase 2 Plan 1: PaymentDecision Schema and PredictionEngine Summary

**One-liner:** PaymentDecision Pydantic schema (D-05), VerdictBoard/Episode extended with prediction fields, and PredictionEngine computing z-score, step deviation, and D-09 expected investigation outcomes before dispatch.

## What Was Built

### Task 1: PaymentDecision Schema + Schema Extensions

Created `sentinel/schemas/payment.py` with the full D-05 `PaymentDecision` model:
- `episode_id`, `decision: Literal["approve", "deny"]`, `amount`, `beneficiary`, `account`
- `rationale` — agent's explanation (may be corrupted by prompt injection)
- `steps_taken: list[str]` — ordered tool calls the agent made
- `confidence: float` (0.0–1.0), `claims: dict[str, str]`, `document_urls: list[str]`

Extended `VerdictBoard` with `prediction_errors: dict | None = None` — populated post-investigation for Phase 3 rule generation.

Extended `Episode` with `prediction_report: dict | None = None` — stores `PredictionReport.model_dump()` for Phase 3 rule generation.

Updated `sentinel/schemas/__init__.py` to re-export `PaymentDecision`.

### Task 2: PredictionEngine (TDD)

Built `sentinel/engine/prediction.py` with:

**`PredictionReport`** — Pydantic model with:
- `predicted_z_score: float` — (confidence - mean) / std
- `step_sequence_deviation: bool` — True if steps differ from expected
- `deviation_details: list[str]` — human-readable deviation descriptions (D-11)
- `summary_score: float` — compact score for dashboard display
- `expected_investigation_outcomes: dict[str, bool]` — D-09 derived expectations

**`PredictionEngine.predict()`** — Forms expectations from behavioral baselines before investigators are dispatched.

**`PredictionEngine.compare_outcomes()`** — Compares expected vs actual investigation findings; returns `outcome_errors`, `error_count`, `total_predictions` for Phase 3 rule generation.

**`PredictionEngine._compute_expected_outcomes()`** — Derives investigation expectations directly from agent's own claims:
- `kyc_verified: true` → `kyc_should_verify: True`
- `counterparty_authorized: true` → `beneficiary_in_counterparty_db: True`
- `read_invoice` in steps → `document_should_be_clean: True`

## TDD Execution

- **RED**: 16 tests written across 6 test classes; committed before implementation; failed with `ModuleNotFoundError`
- **GREEN**: Implementation created; all 16 tests pass; 32 existing schema tests unaffected

## Decisions Made

1. **`steps_taken` is list[str]**: Ordered tool call names (not structured objects) — sufficient for step deviation detection without over-engineering for Phase 2 scope
2. **Summary score formula**: `abs(z_score) * 0.3 + (0.5 if deviation else 0.0)` — deviation adds 0.5 flat contribution because skipping steps is a stronger signal than a high confidence z-score alone
3. **Expected outcomes from claims**: Derived purely from the agent's own claims at prediction time — no external DB lookups. This means if the agent lies about what it checked, the prediction captures those false claims and the error surfaces when investigators find otherwise.

## Deviations from Plan

None — plan executed exactly as written.

## Commits

| Task | Commit | Message |
|------|--------|---------|
| Task 1 | 4b41224 | feat(02-01): create PaymentDecision schema and extend VerdictBoard/Episode |
| Task 2 RED | c25dd14 | test(02-01): add failing tests for PredictionEngine |
| Task 2 GREEN | 94f02a0 | feat(02-01): implement PredictionEngine with z-score, step deviation, D-09 outcomes |

## Self-Check: PASSED

- sentinel/schemas/payment.py: FOUND
- sentinel/engine/__init__.py: FOUND
- sentinel/engine/prediction.py: FOUND
- tests/test_prediction.py: FOUND
- Commit 4b41224: FOUND
- Commit c25dd14: FOUND
- Commit 94f02a0: FOUND
