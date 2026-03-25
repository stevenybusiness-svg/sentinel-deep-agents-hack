---
phase: 03-self-improvement-loop
plan: "01"
subsystem: rule-generator
tags: [rule-generator, validation-harness, restrictedpython, opus-4-6, events, self-improvement]

requires:
  - phase: 02
    provides: Safety Gate with RestrictedPython compile_restricted, SAFE_BUILTINS, and _FORBIDDEN_TOKENS patterns

provides:
  - RuleGenerator class with generate() + evolve() + retry + streaming for Opus 4.6 rule generation
  - 4-check validate_rule() harness per D-05 (compile, forbidden tokens, attack fires, clean baseline passes)
  - CLEAN_BASELINE_VERDICT_BOARD constant for false-positive detection in validation check 4
  - RULE_GEN_SYSTEM_PROMPT constraining Opus 4.6 to behavioral VerdictBoard fields only
  - build_rule_gen_prompt() and build_evolution_prompt() for incident and evolution contexts
  - EventType Literal extended with rule_generating and rule_generation_failed (9 total values)
  - 22-test suite covering all validation paths and prompt structure

affects: [03-02-persistence, 03-03-api-wiring, 03-04-evolution]

tech-stack:
  added: []
  patterns:
    - "validate_rule() runs 4 checks in exact D-05 order: compile_restricted → forbidden tokens → attack fires → clean baseline passes"
    - "_exec_rule() duplicates SAFE_BUILTINS from safety_gate.py to avoid circular imports"
    - "Streaming via async with client.messages.stream() — tokens broadcast as rule_generating WebSocket events"
    - "Markdown fence stripping via regex before validation — Opus 4.6 may wrap output in ```python``` blocks"
    - "Retry loop injects previous failure reason into next user prompt for self-correction"

key-files:
  created:
    - sentinel/engine/rule_generator.py
    - tests/test_rule_generator.py
  modified:
    - sentinel/schemas/events.py

key-decisions:
  - "SAFE_BUILTINS duplicated (not imported) from safety_gate.py — avoids circular imports; kept in sync via comment"
  - "Forbidden token check inline in validate_rule() — self-contained harness, no cross-module dependency"
  - "validate_rule() attack score threshold is > 0.6 (exclusive) — matches Safety Gate ESCALATE threshold, not NO-GO"
  - "validate_rule() clean baseline threshold is < 0.2 (exclusive) — strict false-positive guard"
  - "evolve() validates against vb2 (second attack fixture) — the evolved function must demonstrate detection on the newer incident"

duration: 8min
completed: "2026-03-25"
---

# Phase 3 Plan 1: RuleGenerator Core Engine Summary

**Opus 4.6 rule generation engine with 4-check validation harness, behavioral prompt constraints, and RestrictedPython sandbox; EventType extended with 2 new streaming events; 22 tests all passing**

## Performance

- **Duration:** ~8 min
- **Completed:** 2026-03-25
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- `sentinel/engine/rule_generator.py` — complete RuleGenerator engine with:
  - `RULE_GEN_SYSTEM_PROMPT` constraining Opus 4.6 to write only behavioral scoring functions over VerdictBoard fields; includes 2 few-shot examples from existing hardcoded rules
  - `build_rule_gen_prompt()` — injects incident VerdictBoard + prediction errors; instructs behavioral generalization
  - `build_evolution_prompt()` — injects both VerdictBoards + both prediction error sets; instructs DROP/STRENGTHEN evolution per D-09
  - `_exec_rule()` — RestrictedPython compile_restricted + SAFE_BUILTINS execution; returns score callable
  - `validate_rule()` — 4-check harness per D-05: compile, forbidden tokens, attack fires, clean passes
  - `CLEAN_BASELINE_VERDICT_BOARD` — realistic clean transaction (agent_confidence=0.55, z_score=0.8, no anomalies)
  - `RuleGenerator.generate()` — async streaming with up to 3 retries; failure reason injected on retry
  - `RuleGenerator.evolve()` — same retry logic using `build_evolution_prompt()`; validates against vb2
- `sentinel/schemas/events.py` — EventType Literal extended from 7 to 9 values with `rule_generating` and `rule_generation_failed`
- `tests/test_rule_generator.py` — 22 tests covering full validation harness, all rejection paths, prompt content, EventType, and RuleGenerator interface

## Task Commits

1. **Task 1: Extend EventType + build RuleGenerator with validation harness** — `785cc2b` (feat)
2. **Task 2: Test suite for validation harness and rule structure** — `c17a5fd` (test)

## Files Created/Modified

- `sentinel/engine/rule_generator.py` — RuleGenerator class (created, ~320 lines)
- `tests/test_rule_generator.py` — 22 validation harness tests (created, ~300 lines)
- `sentinel/schemas/events.py` — EventType extended with 2 new values

## Decisions Made

- **SAFE_BUILTINS duplicated from safety_gate.py:** Importing from safety_gate would create a circular dependency (safety_gate imports VerdictBoard, rule_generator imports from safety_gate). Duplicated with a comment to keep in sync.
- **Forbidden token check inline:** The validation harness is self-contained — no cross-module call to `_pre_check_source`. This makes the harness independent of Safety Gate internals.
- **Attack score threshold > 0.6:** Uses the Safety Gate's ESCALATE threshold as the minimum signal strength for a generated rule. A rule that can't even trigger ESCALATE on the attack that created it is too weak.
- **evolve() validates against vb2:** The second incident VerdictBoard is the validation fixture for the evolved rule — it must demonstrate detection on the newer incident, not just repeat the first.

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all validation logic is wired. The `generate()` and `evolve()` methods require a real AsyncAnthropic client; Plan 03 will wire the API endpoint with the shared client.

## Self-Check: PASSED

- sentinel/engine/rule_generator.py: FOUND
- tests/test_rule_generator.py: FOUND
- sentinel/schemas/events.py: FOUND (modified)
- Commit 785cc2b: FOUND
- Commit c17a5fd: FOUND
