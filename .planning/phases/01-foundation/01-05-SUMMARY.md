---
phase: 01-foundation
plan: 05
subsystem: schemas
tags: [pydantic, schemas, tdd, type-safety]
dependency_graph:
  requires: ["01-01"]
  provides: ["sentinel.schemas.*", "tests/test_schemas.py"]
  affects: ["all downstream phases — schemas are the inter-component contract"]
tech_stack:
  added: []
  patterns: ["Pydantic v2 BaseModel", "Literal type validators for Safety Gate fields", "loose str/list/dict for agent reasoning fields"]
key_files:
  created:
    - sentinel/schemas/verdict.py
    - sentinel/schemas/verdict_board.py
    - sentinel/schemas/episode.py
    - sentinel/schemas/events.py
    - tests/test_schemas.py
  modified:
    - sentinel/schemas/__init__.py
decisions:
  - "D-06 enforced: strict Literal/Field validators on severity, confidence, match, gate_decision — these are deterministic enforcement paths"
  - "D-07 enforced: behavioral_flags, mismatches, gate_rationale use loose str/list/dict — tighten in Phase 2 if agent returns bad data"
  - "EventType defined as 7-value Literal covering 9 named events (agent_completed sent 3x, one per sub-agent)"
  - "datetime.utcnow() used in schemas per plan spec — deprecation warning is cosmetic, not behavioral"
metrics:
  duration_seconds: 131
  completed_date: "2026-03-24"
  tasks_completed: 2
  files_changed: 6
---

# Phase 1 Plan 5: Frozen Pydantic Schemas Summary

**One-liner:** All 4 Pydantic schema modules frozen with strict Safety Gate validators (Literal severity, float 0-1 confidence, Literal gate_decision) and 32 passing tests via TDD.

## What Was Built

Four Pydantic schema files establishing the inter-component contract for all downstream phases:

- **sentinel/schemas/verdict.py** — `ClaimCheck` + `Verdict`: individual sub-agent output with strict `severity: Literal["critical","warning","info"]` and `agent_confidence: float = Field(ge=0.0, le=1.0)`
- **sentinel/schemas/verdict_board.py** — `VerdictBoard`: synthesized comparison board with strict confidence bounds and loose mismatch/flag lists
- **sentinel/schemas/episode.py** — `Episode`: complete incident record with `gate_decision: Literal["GO","NO-GO","ESCALATE"]`, auto-UUID id, auto-timestamp, and nested `Verdict`/`VerdictBoard`
- **sentinel/schemas/events.py** — `WSEvent` + `EventType`: 7-value Literal type covering 9 named WebSocket events, including `agent_completed` sent 3x per investigation
- **sentinel/schemas/__init__.py** — re-exports all 6 public names for clean `from sentinel.schemas import ...` usage

## Test Results

All 32 tests pass across 5 test classes:

| Class | Tests | Coverage |
|-------|-------|----------|
| `TestClaimCheck` | 5 | valid construction, all severities, invalid severity rejected, match bool, critical mismatch |
| `TestVerdict` | 8 | confidence boundaries (0.0/1.0/1.01/-0.01), defaults, nested claims |
| `TestVerdictBoard` | 4 | valid construction, confidence bounds, unable_to_verify default, dict mismatches |
| `TestEpisode` | 9 | all gate decisions, invalid rejected, auto-id/timestamp, nested verdicts, serialization round-trip, optional defaults |
| `TestWSEvent` | 6 | all 7 event types, invalid rejected, data default/payload |

## TDD Order Respected

1. Task 1 committed `tests/test_schemas.py` (32 tests, all failing — RED)
2. Task 2 implemented all 4 schema modules + `__init__.py` (32 tests, all passing — GREEN)

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all schema fields are implemented with their intended types and validators. No placeholder values or empty return stubs.

## Self-Check: PASSED

Files created:
- sentinel/schemas/verdict.py: FOUND
- sentinel/schemas/verdict_board.py: FOUND
- sentinel/schemas/episode.py: FOUND
- sentinel/schemas/events.py: FOUND
- sentinel/schemas/__init__.py: FOUND (modified)
- tests/test_schemas.py: FOUND

Commits:
- 8f9b525: test(01-05): add failing schema test suite (TDD RED) — FOUND
- 70f6fe6: feat(01-05): implement frozen Pydantic schemas SCHEMA-01 through SCHEMA-04 — FOUND
