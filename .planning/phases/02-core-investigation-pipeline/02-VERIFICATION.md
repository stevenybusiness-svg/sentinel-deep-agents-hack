---
phase: 02-core-investigation-pipeline
verified: 2026-03-25T04:00:00Z
status: gaps_found
score: 18/20 requirements verified
re_verification: false
gaps:
  - truth: "exec() sandbox enforces 5-second timeout per ENGN-05"
    status: failed
    reason: "Safety Gate register_rule() / evaluate() contains no timeout. The requirement text (ENGN-05) explicitly lists '5-second timeout' but the implementation omits it. The plan truth omits it too, but the requirement text does not."
    artifacts:
      - path: "sentinel/engine/safety_gate.py"
        issue: "No asyncio.timeout(), threading.Timer, or signal-based timeout wrapping exec() in register_rule() or evaluate()"
    missing:
      - "Add a timeout guard around exec() in register_rule() (e.g., asyncio.timeout(5) or concurrent.futures with 5s cancel)"
  - truth: "Supervisor Opus 4.6 reasoning output is used to direct the Payment Agent conversation (D-03)"
    status: partial
    reason: "The Supervisor makes a real Opus 4.6 LLM call, but the response is completely discarded and never fed into the Payment Agent conversation. The plan template also shows this as fire-and-forget, so the implementation matches the plan — but the goal of 'Supervisor drives Payment Agent turn-by-turn' is not fully realized: the Supervisor reasons in isolation and the Payment Agent then runs its own independent conversation. This is a design-level gap against D-03 intent."
    artifacts:
      - path: "sentinel/agents/supervisor.py"
        issue: "Line 117: `await llm_client.messages.create(model=models['supervisor'], ...)` — response is not assigned; the supervisor_response variable from the plan template was never wired to shape agent_messages"
    missing:
      - "Capture supervisor_response and either inject its content into the first Payment Agent user message OR use it to decide which tool calls the Payment Agent should make next"
human_verification:
  - test: "Run POST /investigate with the forensic invoice scenario and confirm the Payment Agent is genuinely manipulated by the hidden-text injection"
    expected: "Forensics agent detects hidden_text_detected flag; Safety Gate returns NO-GO with rule_hidden_text score >= 1.5; gate decision is NO-GO"
    why_human: "Requires a live ANTHROPIC_API_KEY and a running FastAPI server — Claude vision API must be exercised against the actual invoice PNG"
  - test: "Confirm Aerospike write latency is visible and non-zero in the API response and dashboard"
    expected: "write_latency_ms > 0.0 in InvestigateResponse; Aerospike cluster is reachable"
    why_human: "Requires a running Aerospike instance; automated tests use mocks"
---

# Phase 2: Core Investigation Pipeline Verification Report

**Phase Goal:** A payment request triggers a complete parallel investigation with a real LLM payment agent, prediction step forms expectations from baselines, three sub-agents adversarially verify claims, the Verdict Board assembles structured comparisons, the Safety Gate computes a composite anomaly score and outputs GO/NO-GO/ESCALATE with attribution, and all results write to Aerospike — the hidden-text-invoice attack scenario runs end-to-end with the payment agent genuinely manipulated
**Verified:** 2026-03-25T04:00:00Z
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | PaymentDecision schema importable with all D-05 fields | VERIFIED | `sentinel/schemas/payment.py` has all 9 fields; `from sentinel.schemas import PaymentDecision` succeeds |
| 2 | PredictionEngine computes z-score and step deviation before investigation | VERIFIED | `sentinel/engine/prediction.py` 156 lines; predict() correctly computes `(confidence - mean) / std`; 16 tests pass |
| 3 | Three sub-agents (Risk, Compliance, Forensics) return structured Verdict objects | VERIFIED | All three files exist with full implementations; 14 sub-agent tests pass |
| 4 | Risk Agent computes confidence z-score against baseline mean=0.52 std=0.11 | VERIFIED | `sentinel/agents/risk.py` lines 32-38; uses `round((confidence - mean) / std, 10)` for float64 boundary safety |
| 5 | Compliance Agent independently queries KYC ledger and counterparty DB | VERIFIED | `sentinel/agents/compliance.py` fully wired to `fixtures["kyc_ledger"]` and `counterparty_db`; 4 compliance tests pass |
| 6 | Forensics Agent scans invoice PNG via Claude vision API | VERIFIED | `sentinel/agents/forensics.py` uses `client.messages.create` with base64 PNG; handles None path per PIPE-06 |
| 7 | Forensics Agent detects hidden text and sets hidden_text_detected flag | VERIFIED | Lines 161-163 in forensics.py set `"hidden_text_detected"` in behavioral_flags; `hidden_content` ClaimCheck added |
| 8 | Verdict Board Engine produces field-level mismatch list with severity tags | VERIFIED | `sentinel/engine/verdict_board.py` assembles mismatches with severity tags from all agent claims_checked |
| 9 | Safety Gate applies hardcoded rules first and immutably | VERIFIED | `_hardcoded_rules` dict iterated before `_generated_rules`; 8 rule files loaded at startup |
| 10 | Safety Gate loads generated rules via RestrictedPython compile_restricted | VERIFIED | `register_rule()` calls `compile_restricted` explicitly; never uses plain `compile()` |
| 11 | Safety Gate outputs GO/NO-GO/ESCALATE with full attribution | VERIFIED | `evaluate()` returns `{decision, composite_score, rule_contributions, attribution}`; test_attribution passes |
| 12 | exec() sandbox uses compile_restricted, builtins whitelist, AST pre-check | VERIFIED | `SAFE_BUILTINS`, `_FORBIDDEN_TOKENS` pre-check, RestrictedPython guards all present |
| 13 | exec() sandbox enforces 5-second timeout (ENGN-05) | FAILED | No timeout guard in `register_rule()` or `evaluate()`; requirement text mandates it |
| 14 | Composite anomaly score: >=1.0 NO-GO, >=0.6 ESCALATE, else GO | VERIFIED | Lines 210-215 in safety_gate.py; confirmed by 6 Safety Gate tests |
| 15 | Supervisor makes real Opus 4.6 LLM call before investigation | VERIFIED | Line 117 in supervisor.py; first `messages.create` call uses `models["supervisor"]`; test_supervisor_uses_opus_model passes |
| 16 | Supervisor Opus response is used to direct Payment Agent (D-03) | PARTIAL | Opus call is made but response is discarded — Payment Agent conversation runs independently |
| 17 | asyncio.TaskGroup dispatches Risk/Compliance/Forensics in parallel | VERIFIED | Lines 262-265 in supervisor.py; `asyncio.TaskGroup()` with three tasks |
| 18 | Sub-agent failure produces unable_to_verify verdict, not abort | VERIFIED | Each agent wrapped in try/except that sets `unable_to_verify=True` |
| 19 | Episode written to Aerospike with write latency measured | VERIFIED | `sentinel/memory/episode_store.py` uses `time.perf_counter()`; returns latency ms; graceful degradation if Aerospike absent |
| 20 | FastAPI POST /investigate + WebSocket /ws endpoints serve the pipeline | VERIFIED | `sentinel/api/main.py` has both endpoints; `sentinel/api/routes/investigate.py` calls `run_investigation()` |

**Score:** 18/20 truths verified (1 failed, 1 partial)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `sentinel/schemas/payment.py` | PaymentDecision Pydantic model | VERIFIED | 27 lines; all D-05 fields present |
| `sentinel/engine/prediction.py` | PredictionEngine and PredictionReport | VERIFIED | 156 lines; all methods implemented |
| `sentinel/agents/payment_agent.py` | PAYMENT_TOOLS, handle_tool_call, parse_payment_decision | VERIFIED | 236 lines; 3 tools; handles base64 PNG vision |
| `sentinel/agents/risk.py` | Risk Agent analyze function | VERIFIED | 93 lines; z-score + step deviation |
| `sentinel/agents/compliance.py` | Compliance Agent validate function | VERIFIED | 105 lines; KYC + counterparty lookup |
| `sentinel/agents/forensics.py` | Forensics Agent scan function | VERIFIED | 208 lines; vision API + hidden text detection |
| `sentinel/engine/verdict_board.py` | VerdictBoardEngine | VERIFIED | 87 lines; full field-level comparison |
| `sentinel/engine/safety_gate.py` | SafetyGate with rule registry | VERIFIED | 241 lines; RestrictedPython sandbox present; missing timeout |
| `sentinel/gate/rules/rule_hidden_text.py` | Hidden text detection rule | VERIFIED | `def score(verdict_board)` returns 1.5 on hidden_text_detected |
| `sentinel/gate/rules/` (7 other rules) | Additional scoring rules | VERIFIED | rule_z_score, rule_mismatch, rule_unverifiable, rule_step_deviation, rule_amount_threshold, rule_beneficiary_unknown, rule_behavioral_flags all present |
| `sentinel/memory/episode_store.py` | Episode read/write with latency | VERIFIED | write_episode returns float ms; get_recent_episodes for MEM-04 |
| `sentinel/memory/trust_store.py` | Behavioral baseline persistence | VERIFIED | load_baselines with fallback; store_prediction_history for Phase 3 |
| `sentinel/agents/supervisor.py` | Supervisor orchestration | VERIFIED | 376 lines; Opus 4.6 call + TaskGroup dispatch + Safety Gate + Aerospike write |
| `sentinel/api/main.py` | FastAPI app with lifespan | VERIFIED | 135 lines; loads all dependencies at startup |
| `sentinel/api/websocket.py` | ConnectionManager | VERIFIED | 64 lines; broadcasts 7 event types; dead connection pruning |
| `sentinel/api/routes/investigate.py` | POST /investigate | VERIFIED | 80 lines; wired to run_investigation() |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `sentinel/engine/prediction.py` | `sentinel/schemas/payment.py` | `from sentinel.schemas.payment import PaymentDecision` | WIRED | Line 12 of prediction.py |
| `sentinel/engine/prediction.py` | behavioral_baselines | `baselines.get("payment_agent", ...)` | WIRED | Line 46; uses mean/std |
| `sentinel/agents/payment_agent.py` | `sentinel/schemas/payment.py` | returns PaymentDecision | WIRED | `parse_payment_decision` returns PaymentDecision |
| `sentinel/agents/payment_agent.py` | `sentinel/fixtures/__init__.py` | uses kyc_ledger/counterparty_db | WIRED | Lines 130, 145 |
| `sentinel/agents/risk.py` | `sentinel/schemas/verdict.py` | returns Verdict | WIRED | Line 86: `return Verdict(agent_id="risk", ...)` |
| `sentinel/agents/forensics.py` | anthropic SDK | `client.messages.create` | WIRED | Line 102 |
| `sentinel/agents/compliance.py` | `sentinel/fixtures/__init__.py` | kyc_ledger and counterparty_db | WIRED | Lines 39-40 |
| `sentinel/engine/safety_gate.py` | `sentinel/gate/rules/` | `load_rules_from_directory` | WIRED | Lines 93-107; uses `glob("rule_*.py")` |
| `sentinel/engine/safety_gate.py` | `sentinel/schemas/verdict_board.py` | `verdict_board.model_dump()` | WIRED | Line 174 |
| `sentinel/engine/verdict_board.py` | `sentinel/schemas/verdict.py` | compares Verdict claims | WIRED | `from sentinel.schemas.verdict import Verdict` |
| `sentinel/agents/supervisor.py` | `sentinel/agents/payment_agent.py` | PAYMENT_TOOLS, handle_tool_call, parse_payment_decision | WIRED | Lines 27-31 |
| `sentinel/agents/supervisor.py` | anthropic SDK | Opus 4.6 LLM call | WIRED | Line 117 |
| `sentinel/agents/supervisor.py` | `sentinel/agents/risk.py` | `risk.analyze` | WIRED | Line 207 |
| `sentinel/agents/supervisor.py` | `sentinel/engine/safety_gate.py` | `safety_gate.evaluate` | WIRED | Line 292 |
| `sentinel/agents/supervisor.py` | `sentinel/memory/episode_store.py` | `get_recent_episodes` | WIRED | Lines 100 |
| `sentinel/agents/supervisor.py` | `sentinel/engine/prediction.py` | `compare_outcomes` | WIRED | Line 273 |
| `sentinel/api/routes/investigate.py` | `sentinel/agents/supervisor.py` | `run_investigation` | WIRED | Line 59 |
| `sentinel/api/websocket.py` | `sentinel/schemas/events.py` | broadcasts WSEvent | WIRED | Lines 12, 38 |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|-------------------|--------|
| `supervisor.py` | `payment_decision` | Payment Agent LLM response parsed via `parse_payment_decision` | Yes — real Sonnet 4.6 response via tool-use loop | FLOWING |
| `supervisor.py` | `verdicts` | Risk/Compliance/Forensics agents return Verdict objects | Yes — deterministic fixture lookups + vision API | FLOWING |
| `supervisor.py` | `verdict_board` | `VerdictBoardEngine.assemble()` from verdicts | Yes — real field-level comparison | FLOWING |
| `supervisor.py` | `gate_result` | `safety_gate.evaluate(verdict_board)` | Yes — deterministic rule scoring | FLOWING |
| `episode_store.py` | `bins` | `episode.verdict_board.model_dump()` | Yes — serialized from real episode | FLOWING |
| `trust_store.py` | baselines | Aerospike put/get with JSON | Yes — falls back to fixtures on miss | FLOWING |
| `investigate.py` | `InvestigateResponse` | `result` from `run_investigation()` | Yes — all fields populated | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All Phase 2 unit tests pass | `python3.12 -m pytest tests/test_prediction.py tests/test_payment_agent.py tests/test_sub_agents.py tests/test_safety_gate.py tests/test_memory_stores.py tests/test_api.py tests/test_supervisor.py -q` | 74 passed, 16 warnings in 1.87s | PASS |
| Schema imports work | `python3.12 -c "from sentinel.schemas import PaymentDecision, VerdictBoard, Episode"` | OK | PASS |
| FastAPI app imports cleanly | `python3.12 -c "from sentinel.api.main import app"` | OK | PASS |
| rule_hidden_text fires correctly | `score({"behavioral_flags": ["hidden_text_detected"]})` | Returns 1.5 | PASS |
| Composite threshold arithmetic | 1.5 >= 1.0 threshold | NO-GO | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| PIPE-01 | 02-02 | Payment Agent returns structured decision with all fields | SATISFIED | `parse_payment_decision` returns PaymentDecision with all D-05 fields |
| PIPE-02 | 02-06 | Parallel dispatch via TaskGroup; one failure → unable_to_verify | SATISFIED | asyncio.TaskGroup at lines 262-265; try/except per agent |
| PIPE-03 | 02-03 | Risk Agent z-score + step deviation | SATISFIED | risk.py: z-score with boundary fix; step_sequence_deviation flag |
| PIPE-04 | 02-03 | Compliance Agent KYC + counterparty lookup | SATISFIED | compliance.py: independent fixture queries |
| PIPE-05 | 02-03 | Forensics Agent vision scan | SATISFIED | forensics.py: base64 PNG + Claude vision API |
| PIPE-06 | 02-03 | Forensics returns clean result with no documents | SATISFIED | Lines 82-96 in forensics.py: `invoice_path is None` branch |
| PIPE-07 | 02-02 | Payment Agent is real Sonnet 4.6 LLM | SATISFIED | No hardcoded decision logic; full tool-use conversation loop |
| ENGN-01 | 02-04 | Verdict Board Engine field-level comparison with severity tags | SATISFIED | VerdictBoardEngine.assemble() produces mismatch list with severity |
| ENGN-02 | 02-04 | Hardcoded rules applied first and immutably | SATISFIED | `_hardcoded_rules` iterated before `_generated_rules` in evaluate() |
| ENGN-03 | 02-04 | Generated rules via RestrictedPython sandbox | SATISFIED | `compile_restricted` used exclusively; never `compile()` |
| ENGN-04 | 02-04 | GO/NO-GO/ESCALATE with full attribution | SATISFIED | evaluate() returns attribution string with rule names and scores |
| ENGN-05 | 02-04 | exec() sandbox: builtins whitelist, compile_restricted, AST pre-check, 5s timeout | PARTIAL | Builtins whitelist: YES. compile_restricted: YES. AST pre-check: YES (forbidden tokens). 5-second timeout: MISSING |
| ENGN-06 | 02-04 | Composite score thresholds: >=1.0 NO-GO, >=0.6 ESCALATE | SATISFIED | Lines 210-215 in safety_gate.py |
| ENGN-07 | 02-01 | Prediction step from baselines before investigation | SATISFIED | PredictionEngine.predict() called at line 195 of supervisor.py, before TaskGroup dispatch |
| MEM-01 | 02-05 | Episodes written to Aerospike with write latency | SATISFIED | write_episode() returns latency ms; graceful degradation |
| MEM-03 | 02-05 | Behavioral baselines persisted in Aerospike trust set | SATISFIED | store_baselines / load_baselines in trust_store.py |
| MEM-04 | 02-05 | Recent episodes injected into Supervisor context | SATISFIED | get_recent_episodes() called at line 100; injected into SUPERVISOR_SYSTEM_PROMPT |
| API-01 | 02-06 | FastAPI WebSocket /ws emitting named events | SATISFIED | ws_manager.broadcast() called for all 5 event types |
| API-02 | 02-06 | POST /investigate triggers full pipeline; caches active episode | SATISFIED | /investigate route calls run_investigation(); active_episodes dict updated |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `sentinel/agents/supervisor.py` | 117 | `await llm_client.messages.create(...)` result discarded | Warning | Supervisor Opus 4.6 reasoning output never used to steer Payment Agent; D-03 intent partially unmet |
| `sentinel/engine/safety_gate.py` | 146 | `exec(code, safe_globals, namespace)` without timeout | Warning | Malformed generated rule could hang the evaluation loop; ENGN-05 5s timeout requirement not met |

### Human Verification Required

#### 1. Hidden-text invoice attack end-to-end

**Test:** Start the FastAPI server with a valid ANTHROPIC_API_KEY, send `POST /investigate` with `{"scenario": "phase1", "payment_request": {"amount": 75000, "beneficiary": "Meridian Logistics"}}`. Observe the WebSocket event stream.
**Expected:** Forensics Agent calls Claude vision API against `sentinel/fixtures/invoice_forensic.png`; `hidden_text_detected` appears in behavioral_flags; Safety Gate evaluates `rule_hidden_text` scoring 1.5; gate decision is NO-GO with attribution naming `rule_hidden_text`; Payment Agent's final decision is "approve" (it was manipulated) while Sentinel blocks it.
**Why human:** Requires a live ANTHROPIC_API_KEY + running Aerospike instance; the LLM's actual response to prompt injection is non-deterministic and must be observed live.

#### 2. Aerospike write latency visible in response

**Test:** With Aerospike running, send `POST /investigate` and inspect the response body's `write_latency_ms` field.
**Expected:** `write_latency_ms` is a positive float (> 0.0), confirming real Aerospike writes are happening, not silently falling through the degradation path.
**Why human:** Requires a live Aerospike cluster; automated tests mock the Aerospike client.

### Gaps Summary

Two gaps block full requirement satisfaction:

**Gap 1 — ENGN-05 timeout (Warning):** The exec() sandbox in `sentinel/engine/safety_gate.py` has the builtins whitelist, RestrictedPython compile_restricted, and forbidden-token pre-check, but is missing the 5-second timeout that REQUIREMENTS.md ENGN-05 explicitly requires. A slow-looping generated rule would block the evaluation thread indefinitely. Fix: wrap `exec()` in `asyncio.wait_for()` or use `concurrent.futures.ThreadPoolExecutor` with a 5s `timeout=` parameter.

**Gap 2 — Supervisor response discarded (Partial, Warning):** The Supervisor's initial Opus 4.6 LLM call is made (satisfying the "real LLM" requirement) but the response is discarded before the Payment Agent conversation begins. The plan template also shows this pattern, meaning the implementation faithfully follows the plan — but D-03's stated intent ("Supervisor controls the Payment Agent by sending it tool calls one at a time") is not realized: the Payment Agent runs an independent loop not informed by the Supervisor's reasoning. For demo purposes this is acceptable since the Opus call does occur and proves non-hardcoded behavior; for the full architectural claim it is incomplete.

Neither gap prevents the core demo scenario (hidden-text attack detection) from running. The Safety Gate, parallel dispatch, Aerospike persistence, and WebSocket broadcasting are all fully implemented and tested.

---

_Verified: 2026-03-25T04:00:00Z_
_Verifier: Claude (gsd-verifier)_
