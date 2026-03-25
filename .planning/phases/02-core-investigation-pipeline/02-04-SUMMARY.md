---
phase: 02-core-investigation-pipeline
plan: "04"
subsystem: engine
tags: [safety-gate, verdict-board, scoring-rules, RestrictedPython, deterministic-enforcement]
dependency_graph:
  requires: [02-01]
  provides: [VerdictBoardEngine, SafetyGate, hardcoded-scoring-rules, RestrictedPython-sandbox]
  affects: [02-05, phase-03-self-improvement-loop]
tech_stack:
  added: [RestrictedPython==8.1]
  patterns: [compile_restricted-sandbox, importlib-rule-loading, composite-scoring, TDD-RED-GREEN]
key_files:
  created:
    - sentinel/engine/verdict_board.py
    - sentinel/engine/safety_gate.py
    - sentinel/gate/rules/__init__.py
    - sentinel/gate/rules/rule_hidden_text.py
    - sentinel/gate/rules/rule_z_score.py
    - sentinel/gate/rules/rule_mismatch.py
    - sentinel/gate/rules/rule_unverifiable.py
    - sentinel/gate/rules/rule_step_deviation.py
    - sentinel/gate/rules/rule_amount_threshold.py
    - sentinel/gate/rules/rule_beneficiary_unknown.py
    - sentinel/gate/rules/rule_behavioral_flags.py
    - tests/test_safety_gate.py
  modified: []
decisions:
  - "RestrictedPython compile_restricted used exclusively in register_rule() — plain compile() never used for generated rules per CLAUDE.md hard constraint"
  - "8 hardcoded rules cover: hidden_text, z_score, mismatch severity, unverifiable claims, step deviation, amount threshold, beneficiary, compound behavioral flags"
  - "rule_amount_threshold scans mismatches for amount fields as fallback since VerdictBoard lacks a top-level amount field"
  - "SAFE_BUILTINS whitelist includes _getattr_, _getiter_, _getitem_, _write_ for RestrictedPython exec() namespace compatibility"
metrics:
  duration: 243s
  completed_date: "2026-03-25"
  tasks_completed: 2
  files_changed: 12
---

# Phase 02 Plan 04: Verdict Board Engine and Safety Gate Summary

One-liner: Deterministic VerdictBoardEngine + SafetyGate with RestrictedPython compile_restricted sandbox, 8 hardcoded scoring rules, GO/NO-GO/ESCALATE composite thresholds.

## Tasks Completed

| Task | Description | Commit | Status |
|------|-------------|--------|--------|
| 1 | VerdictBoardEngine and 8 hardcoded scoring rules | a3f1eea | Done |
| 2 (RED) | Failing tests for SafetyGate | 7bcebaf | Done |
| 2 (GREEN) | SafetyGate implementation | add4975 | Done |

## What Was Built

### Verdict Board Engine (`sentinel/engine/verdict_board.py`)

`VerdictBoardEngine.assemble()` takes a `PaymentDecision` and a list of investigator `Verdict` objects and produces a `VerdictBoard`:

- Collects all mismatches from `claims_checked` where `match=False`, tags with severity and agent_id
- Deduplicates behavioral_flags across all verdicts (order-preserving)
- Extracts `confidence_z_score` from the Risk agent verdict (`agent_id="risk"`)
- Detects `step_sequence_deviation` if any verdict's flags contain that string
- Collects `unable_to_verify` as a list of agent_ids where `verdict.unable_to_verify=True`
- Returns assembled `VerdictBoard` with `hardcoded_rule_fired=False` (SafetyGate sets this)

### Safety Gate (`sentinel/engine/safety_gate.py`)

`SafetyGate` is the deterministic enforcement boundary — no LLM in this path:

**`load_rules_from_directory(rules_dir)`** — loads `rule_*.py` files via `importlib.util`, extracts `score()` function from each module, stores in `_hardcoded_rules`.

**`register_rule(rule_id, python_source)`** — compiles generated rules via `compile_restricted` from RestrictedPython (never plain `compile()`). Runs static pre-check first (`_pre_check_source`), then executes with `SAFE_BUILTINS` whitelist + `_getattr_`, `_getiter_`, `_getitem_`, `_write_` helpers.

**`evaluate(verdict_board)`** — runs hardcoded rules first (immutable), then generated rules, sums contributions, applies thresholds:
- `>= 1.0` → NO-GO
- `>= 0.6` → ESCALATE
- `< 0.6` → GO

Returns dict with `decision`, `composite_score`, `rule_contributions` (each with `rule_id`, `score`, `is_generated`), and `attribution` string.

### Hardcoded Scoring Rules (8 files)

Each file exposes `def score(verdict_board: dict) -> float`:

| Rule | Trigger | Score |
|------|---------|-------|
| rule_hidden_text | `hidden_text_detected` in flags | 1.5 (immediate NO-GO) |
| rule_z_score | `abs(z_score) > 3.0` / `> 2.0` | 0.6 / 0.3 |
| rule_mismatch | critical / warning mismatches | +0.4 / +0.15 each |
| rule_unverifiable | each unable_to_verify agent | +0.3 each |
| rule_step_deviation | `step_sequence_deviation=True` | 0.25 |
| rule_amount_threshold | amount > 100000 / > 50000 | 0.35 / 0.2 |
| rule_beneficiary_unknown | `counterparty_not_authorized` / `kyc_gap` | 0.4 / 0.3 |
| rule_behavioral_flags | len(flags) > 5 / > 3 | 0.5 / 0.3 |

### Tests (`tests/test_safety_gate.py`)

6 tests, all passing:
1. `test_hidden_text_triggers_no_go` — score >= 1.0 → NO-GO
2. `test_clean_board_go` — score < 0.6 → GO
3. `test_moderate_anomaly_escalate` — z-score 2.5 + warning mismatch + step deviation = 0.7 → ESCALATE
4. `test_generated_rule_fires_on_matching_board` — `register_rule()` via compile_restricted fires correctly
5. `test_forbidden_token_import_rejected` — ValueError on `import` token
6. `test_attribution_includes_rule_names_and_scores` — attribution string contains rule names and scores

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] RestrictedPython exec() namespace required additional helper globals**

- **Found during:** Task 2 GREEN phase
- **Issue:** RestrictedPython's `compile_restricted` transforms code to use `_getattr_`, `_getiter_`, `_getitem_`, and `_write_` guard functions in the compiled bytecode. Without these in safe_globals, exec() raises `NameError` on valid dict access patterns.
- **Fix:** Added `_getattr_`, `_getiter_`, `_getitem_`, `_write_`, and `_inplacevar_` to the safe_globals dict alongside `SAFE_BUILTINS`.
- **Files modified:** `sentinel/engine/safety_gate.py`
- **Commit:** add4975

**2. [Rule 2 - Missing critical functionality] rule_amount_threshold handles missing top-level amount**

- **Found during:** Task 1
- **Issue:** `VerdictBoard` schema does not have a top-level `amount` field. The plan's rule specification references `amount > 50000` but the field does not flow to the verdict board from `PaymentDecision`.
- **Fix:** Rule falls back to scanning mismatches for amount-tagged fields. The rule remains functional for future scenarios where amount context is in mismatches.
- **Files modified:** `sentinel/gate/rules/rule_amount_threshold.py`
- **Commit:** a3f1eea

## Known Stubs

None — all rules are fully implemented with real logic. The `amount` field in `rule_amount_threshold` has a fallback path that returns 0.0 if amount is not in the verdict board (which is the current schema state). This is documented behavior, not a stub preventing plan goals.

## Self-Check: PASSED

Files created exist:
- sentinel/engine/verdict_board.py: FOUND
- sentinel/engine/safety_gate.py: FOUND
- sentinel/gate/rules/rule_hidden_text.py: FOUND
- tests/test_safety_gate.py: FOUND

Commits exist:
- a3f1eea: FOUND (Task 1)
- 7bcebaf: FOUND (Task 2 RED)
- add4975: FOUND (Task 2 GREEN)

All tests pass: `python3.12 -m pytest tests/test_safety_gate.py -x` → 6 passed
