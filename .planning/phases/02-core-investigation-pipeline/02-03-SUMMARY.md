---
phase: 02-core-investigation-pipeline
plan: "03"
subsystem: sub-agents
tags: [risk-agent, compliance-agent, forensics-agent, z-score, vision-api, kyc, unit-tests]
dependency_graph:
  requires: [02-01, sentinel/schemas/verdict.py, sentinel/schemas/payment.py, sentinel/fixtures]
  provides: [sentinel/agents/risk.py, sentinel/agents/compliance.py, sentinel/agents/forensics.py]
  affects: [02-04-supervisor, 02-05-verdict-board]
tech_stack:
  added: []
  patterns:
    - "Async sub-agent functions returning structured Verdict objects"
    - "z-score computation against behavioral baselines for anomaly detection"
    - "Claude vision API with base64-encoded PNG for document forensics"
    - "round() for floating-point boundary stability in threshold comparisons"
key_files:
  created:
    - sentinel/agents/risk.py
    - sentinel/agents/compliance.py
    - sentinel/agents/forensics.py
    - tests/test_sub_agents.py
  modified:
    - sentinel/agents/risk.py  # floating-point boundary fix during Task 2
decisions:
  - "z >= 3.0 with round(z, 10) to avoid float64 boundary artifact: (0.85-0.52)/0.11 = 2.9999999999999996"
  - "counterparty_db is keyed by CP-NNN identifiers; compliance agent searches by name through values"
  - "Forensics agent_confidence=0.95 when suspicious content found, 0.80 for clean scan"
metrics:
  duration_seconds: 330
  completed_date: "2026-03-25"
  tasks_completed: 2
  files_created: 4
---

# Phase 02 Plan 03: Sub-Agent Investigators Summary

**One-liner:** Three parallel sub-agent investigators (Risk z-score, Compliance KYC/counterparty lookup, Forensics Claude vision) returning structured Verdict objects with claim checks and behavioral flags.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Build Risk and Compliance agents | 8f392a2 | sentinel/agents/risk.py, sentinel/agents/compliance.py |
| 2 | Build Forensics agent with vision analysis and unit tests | 479074c | sentinel/agents/forensics.py, tests/test_sub_agents.py (+ risk.py fix) |

## What Was Built

### Risk Agent (`sentinel/agents/risk.py`)
- `async def analyze(payment_decision, baselines, expected_step_sequence)` per PIPE-03, D-14
- Computes confidence z-score: `round((confidence - mean) / std, 10)` against `behavioral_baselines.json` (mean=0.52, std=0.11)
- Detects step-sequence deviations by comparing `steps_taken` list against expected order
- Returns `ClaimCheck` for `agent_confidence` field with z-score as `independently_found`
- Behavioral flags: `confidence_anomaly` (|z| > 2.0), `high_confidence_deviation` (z >= 3.0), `step_sequence_deviation`

### Compliance Agent (`sentinel/agents/compliance.py`)
- `async def validate(payment_decision, fixtures)` per PIPE-04, D-16
- Independent KYC lookup: searches `kyc_ledger` dict keyed by beneficiary name
- Independent counterparty lookup: searches `counterparty_db` dict by name through CP-NNN keyed values
- Returns `ClaimCheck` for `kyc_status` and `counterparty_authorized` fields
- Behavioral flags: `kyc_gap` (beneficiary not in KYC ledger), `counterparty_not_authorized` (absent from counterparty DB), `identity_unverifiable` (missing from both)

### Forensics Agent (`sentinel/agents/forensics.py`)
- `async def scan(payment_decision, invoice_path, client, model)` per PIPE-05, PIPE-06, D-15, D-17
- No-document case (PIPE-06): returns clean Verdict with `independently_found="no documents available"` without making API calls
- Vision scan: base64-encodes invoice PNG via `base64.standard_b64encode`, sends to Claude with system prompt for adversarial content detection
- Parses JSON from Claude response including `fields_found`, `hidden_content`, `anomalies`
- Hidden text detection (D-17): adds `hidden_text_detected` to behavioral_flags and a critical `ClaimCheck` for `hidden_content` field
- Field-level comparison: ClaimCheck for each forensics-found field vs. payment_decision.claims

### Unit Tests (`tests/test_sub_agents.py`)
14 tests covering all three agents:
- Risk: z-score value assertion, `confidence_anomaly` flag, `high_confidence_deviation` flag, step deviation, no deviation when no expected sequence
- Compliance: KYC gap, clean (both fixtures present), counterparty not authorized, identity unverifiable
- Forensics: no-document, nonexistent path, mock hidden text detection with critical ClaimCheck, mock clean scan
- Cross-agent: all three return properly structured Verdict objects

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Floating-point boundary artifact in z-score comparison**
- **Found during:** Task 2 (test run)
- **Issue:** `(0.85 - 0.52) / 0.11 = 2.9999999999999996` in float64, causing `z >= 3.0` to return False and `high_confidence_deviation` flag to not fire
- **Fix:** Wrapped z-score computation with `round(z, 10)` before threshold comparisons; also changed `> 3.0` to `>= 3.0` for boundary semantics
- **Files modified:** sentinel/agents/risk.py
- **Commit:** 479074c

## Known Stubs

None — all three agents are fully wired to their data sources (fixtures, Claude vision API). The no-document case in Forensics intentionally returns a partial result (agent_confidence=0.5) which is correct behavior per PIPE-06.

## Self-Check: PASSED

- FOUND: sentinel/agents/risk.py
- FOUND: sentinel/agents/compliance.py
- FOUND: sentinel/agents/forensics.py
- FOUND: tests/test_sub_agents.py
- FOUND: commit 8f392a2 (Task 1)
- FOUND: commit 479074c (Task 2)
- All 14 tests pass: `python -m pytest tests/test_sub_agents.py -x -v`
