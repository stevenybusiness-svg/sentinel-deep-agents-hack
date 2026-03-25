# Requirements: Sentinel

**Defined:** 2026-03-24
**Core Value:** The self-improvement loop: the system autonomously generates composite scoring functions from prediction errors, evolves them across incidents, and catches novel attacks — inspectable Python, not a black box. Live, on stage, in 3 minutes.

## v1 Requirements

### Infrastructure

- [x] **INFRA-01**: Python 3.11+ project initialized with FastAPI, AsyncAnthropic, Aerospike Python client (19.1.0), RestrictedPython (8.2)
- [x] **INFRA-02**: Aerospike running via Docker with startup health check (read-after-write validates namespace exists before accepting traffic)
- [x] **INFRA-03**: Claude API Tier 2 access confirmed; prompt caching enabled for all agent system prompts to stay within ITPM budget
- [x] **INFRA-04**: React 18+ frontend initialized with @xyflow/react (12.4.x), Zustand, Tailwind CSS
- [x] **INFRA-05**: Environment configuration via .env (ANTHROPIC_API_KEY, AEROSPIKE_HOST, BLAND_API_KEY)
- [ ] **INFRA-06**: AWS deployment configured (EC2/ECS with public URL for Bland AI webhooks)

### Schemas

- [x] **SCHEMA-01**: Verdict schema frozen — agent_id, claims_checked[] (field, agent_claimed, independently_found, match, severity), behavioral_flags[], agent_confidence, confidence_z_score, unable_to_verify
- [x] **SCHEMA-02**: Verdict Board schema frozen — mismatches[], behavioral_flags[], agent_confidence, confidence_z_score, step_sequence_deviation, hardcoded_rule_fired, unable_to_verify[]
- [x] **SCHEMA-03**: Episode schema frozen — id, timestamp, action_request, agent_verdicts, verdict_board, gate_decision, gate_rationale, rules_fired, generated_rules_fired, operator_confirmation, attack_type, generated_rule_source, new_rules_deployed
- [x] **SCHEMA-04**: WebSocket event taxonomy defined — 9 named events: investigation_started, agent_completed (×3), verdict_board_assembled, gate_evaluated, episode_written, rule_generated, rule_deployed

### Investigation Pipeline

- [x] **PIPE-01**: Payment Agent parses a structured payment request, queries counterparty fixture DB, returns verdict with amount/beneficiary/account/confidence/steps_taken/claims_made
- [x] **PIPE-02**: Supervisor (Opus 4.6) dispatches Risk, Compliance, Forensics in parallel via asyncio.TaskGroup; collects all verdicts with return_exceptions=True so one failure produces unable_to_verify rather than aborting
- [x] **PIPE-03**: Risk Agent computes confidence z-score against behavioral baseline (mean 0.52, std 0.11); detects step-sequence deviations; returns structured findings
- [x] **PIPE-04**: Compliance Agent independently queries KYC ledger and agent activity log; validates agent identity claims against authoritative source; returns structured findings on each claim
- [x] **PIPE-05**: Forensics Agent independently scans attached document images via vision model; detects adversarial/hidden content regardless of color or contrast; returns actual extracted field values for comparison against agent claims
- [x] **PIPE-06**: Forensics Agent returns clean result with "no documents available" note when no attachments present (Phase 2 scenario)
- [x] **PIPE-07**: Payment Agent is a real Sonnet 4.6 LLM instance — not hardcoded; receives payment request, makes genuine decisions, can be genuinely manipulated via prompt injection or social engineering

### Verdict Board Engine + Safety Gate

- [x] **ENGN-01**: Verdict Board Engine performs field-level comparison between payment agent claims and each investigator's independently found values; produces mismatch list with severity tags (critical/warning/info)
- [x] **ENGN-02**: Safety Gate applies hardcoded rules first and immutably (adversarial content in document → NO-GO; agent identity unverifiable in authoritative log → NO-GO)
- [x] **ENGN-03**: Safety Gate loads all generated scoring functions from rule registry and executes each against the verdict board via RestrictedPython sandbox
- [x] **ENGN-04**: Safety Gate outputs GO / NO-GO / ESCALATE with full attribution — which mismatches, which rules fired, which agents found what, and each rule's score contribution
- [x] **ENGN-05**: exec() sandbox enforces: builtins whitelist (len, any, all, isinstance, etc.), compile() before exec(), explicit namespace extraction, 5-second timeout, AST string-level pre-check for import/__
- [x] **ENGN-06**: Safety Gate computes composite anomaly score — each scoring function returns a weighted signal, individually weak signals compound, total score evaluated against threshold (>=1.0 → NO-GO, >=0.6 → ESCALATE, else → GO)
- [x] **ENGN-07**: Prediction step computes expected VerdictBoard values from behavioral baselines before investigation; prediction errors (expected vs actual) stored with episode for rule generation input

### Self-Improvement Loop

- [x] **LEARN-01**: On operator-confirmed attack, system extracts prediction errors from the episode — where expected values diverged most from actual findings across all VerdictBoard fields
- [x] **LEARN-02**: Generated Python scoring function is behavioral — operates only on verdict_board fields; does not reference attack mechanism, document type, or agent names; returns weighted anomaly score (float), not binary bool; includes docstring explaining what behavioral pattern it detects
- [x] **LEARN-03**: Generated function passes validation before deployment: AST parse, compile(), test harness executes function against clean baseline (must return score < 0.3) and attack fixture (must return score > 0.6)
- [x] **LEARN-04**: Validated scoring function exec()'d into Safety Gate registry with provenance: episode_id, prediction_errors, timestamp, python_source stored in Aerospike rules set
- [ ] **LEARN-05**: Phase 2 demo end-to-end: generated scoring function from Phase 1 (invoice attack) fires on Phase 2 verdict board (identity spoofing); hardcoded rules alone insufficient; generated function's contribution pushes composite score above threshold; attribution displays "Blocked by Generated Rule #001 (learned from Episode #001) | Deployed [X]s ago"
- [ ] **LEARN-06**: Rule evolution: after second confirmed incident, system feeds both VerdictBoards and their prediction errors to Opus 4.6 and generates refined scoring function (v2) — tighter thresholds, drops conditions that were artifacts of one attack, strengthens conditions present in both; v2 replaces v1 in registry with full version history in Aerospike

### Episodic Memory (Aerospike)

- [x] **MEM-01**: Episode records written to Aerospike `sentinel.episodes` set after each incident resolution; write latency measured per operation
- [x] **MEM-02**: Generated rule source, provenance, and version history written to Aerospike `sentinel.rules` set; fire_count bin updated atomically via increment(); rules loaded into SafetyGate registry at startup via scan()
- [x] **MEM-03**: Behavioral baselines and prediction history persisted in Aerospike `sentinel.trust` set; queried at investigation start for prediction step
- [x] **MEM-04**: Recent episodes and prediction errors queried from Aerospike at investigation start; injected into Supervisor context
- [x] **MEM-05**: Aerospike write latency measured per operation and exposed via API; displayed on dashboard (target: <5ms per write)

### Backend API

- [x] **API-01**: FastAPI server with WebSocket endpoint (/ws) emitting named investigation events to connected dashboard clients in real time
- [x] **API-02**: POST /investigate accepts payment request payload; triggers full investigation pipeline with prediction step; caches active episode state in memory
- [x] **API-03**: POST /confirm accepts operator confirmation (confirmed_attack / false_positive); extracts prediction errors; triggers scoring function generation pipeline if confirmed_attack; stores result to Aerospike
- [ ] **API-04**: POST /bland-webhook handles Bland AI Q&A turns; responds within 8s; reads pre-computed investigation context from in-memory cache (not Aerospike per-turn)

### Dashboard

- [ ] **DASH-01**: Investigation tree rendered with @xyflow/react; nodes animate to active state as sub-agents receive their dispatch; edges animate as data flows
- [ ] **DASH-02**: New rule node appears in investigation tree after rule deployment — the tree is visibly larger after learning than before
- [ ] **DASH-03**: Verdict board table shows field-level match/mismatch for all claims_checked with severity indicators
- [ ] **DASH-04**: Forensic scan panel shows clean invoice view (what human sees) vs. forensic scan (hidden text highlighted in red) side-by-side for Phase 1 demo
- [ ] **DASH-05**: Generated rule source panel shows readable Python function the system wrote, with provenance (episode ID, deployed timestamp, prediction errors that produced it) and evolution history (v1 → v2)
- [ ] **DASH-06**: Trust score bar animates from initial value (0.85) to post-investigation value (0.25) as verdict board assembles
- [ ] **DASH-07**: Gate decision (GO / NO-GO / ESCALATE) displayed prominently with full attribution text below it
- [ ] **DASH-08**: Decision log shows timestamped trail of all gate decisions with one-line attribution per entry
- [ ] **DASH-09**: Aerospike latency metric displayed live on dashboard (confirms real integration to Aerospike judges)
- [ ] **DASH-10**: Prediction vs. actual panel displays expected values from behavioral baselines alongside actual investigation findings, with prediction errors highlighted
- [ ] **DASH-11**: Composite anomaly score bar shows each rule's weighted contribution color-coded, with threshold line visible; judges can see how individually weak signals compound

### Voice Interface (Bland AI)

- [ ] **VOICE-01**: Bland AI call initiated for demo; Supervisor answers "Why did you block that?" and "What was the anomaly score?" in plain language grounded in actual scores and rule attribution
- [ ] **VOICE-02**: Barge-in configured via interruption_threshold and block_interruptions: false; operator can cut in mid-sentence
- [ ] **VOICE-03**: All investigation context pre-computed and cached before voice demo starts; webhook handler reads from memory cache, not Aerospike, to stay within 8s response window
- [ ] **VOICE-04**: Dashboard always shows the same information as voice narration — text fallback is always present if voice fails

### Demo Preparation

- [ ] **DEMO-01**: docker-compose.yml runs full stack (FastAPI, Aerospike, React dev server) in one command with no manual steps
- [ ] **DEMO-02**: demo_check.py validates all components before demo: Aerospike namespace accessible, API keys valid, Bland AI connectivity, WebSocket connects and receives first event, both fixture sets load
- [x] **DEMO-03**: Demo fixtures committed: Phase 1 (invoice image with embedded hidden text, counterparty DB, behavioral baselines), Phase 2 (spoofed KYC pre-clearance payload, empty KYC ledger for Meridian Logistics)
- [ ] **DEMO-04**: Full Attack 1 → rule generation → Attack 2 → rule fires → rule evolves arc runs end-to-end without intervention in under 3 minutes
- [ ] **DEMO-05**: Screen recording of full demo arc captured as fallback before demo day

---

## v2 Requirements

### Data Pipeline (Airbyte)

- **DATA-01**: Airbyte syncs counterparty authorization records from Google Sheet to counterparty fixture DB
- **DATA-02**: Airbyte syncs KYC/AML verification log from Google Sheet

### Additional Attack Vectors

- **ATK-01**: Data poisoning attack scenario — corrupted authorization record in counterparty DB skews agent reasoning
- **ATK-02**: Confidence manipulation as standalone scenario — compromised agent returns anomalously high confidence

### Extended Observability

- **OBS-01**: TrueFoundry agent fleet observability dashboard showing per-agent latency, token usage, and error rates
- **OBS-02**: Aerospike episode replay — operator can re-run any stored episode through current rule set

### Future Enhancements

- **FUT-01**: Near-miss tracking — transactions where rules almost fired; system learns which rule conditions are load-bearing vs. artifacts
- **FUT-02**: Investigator disagreement as detection signal — inter-agent disagreement patterns as a first-class input to scoring functions
- **FUT-03**: Self-healing rules — detect when rules produce false positives (operators confirm flagged transactions as legitimate) and auto-refine

---

## Out of Scope

| Feature | Reason |
|---------|--------|
| Fine-tuning / model weight updates | Rule generation via executable Python is the learning mechanism; weights not modified |
| Model-level RAG fine-tuning pipeline | Out of 72-hour scope; episodic memory + rule generation is the demo-viable learning path |
| Multi-tenant / SaaS deployment | Single operator context sufficient for hackathon demo |
| Non-payment agent supervision | Architecture generalizes but demo uses payments for clarity |
| Stablecoin / on-chain settlement rails | Fiat wire transfers only — universally understood, no explanation overhead |
| Mobile / native app | Web dashboard only |
| Okta identity verification | Cut for timeline; mention in Q&A if asked about operator authentication |
| Real-time WebSocket streaming to Bland AI | Not supported in Bland API; webhook is the integration path |
| Attack vectors beyond the 4 in spec | Prompt injection, data poisoning, confidence manipulation, cross-agent deception are demo surface |
| Generative UI for investigation tree | Static React Flow graph is sufficient |

---

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| INFRA-01 | Phase 1 | Complete |
| INFRA-02 | Phase 1 | Complete |
| INFRA-03 | Phase 1 | Complete |
| INFRA-04 | Phase 1 | Complete |
| INFRA-05 | Phase 1 | Complete |
| INFRA-06 | Phase 6 | Pending |
| SCHEMA-01 | Phase 1 | Complete |
| SCHEMA-02 | Phase 1 | Complete |
| SCHEMA-03 | Phase 1 | Complete |
| SCHEMA-04 | Phase 1 | Complete |
| PIPE-01 | Phase 2 | Complete |
| PIPE-02 | Phase 2 | Complete |
| PIPE-03 | Phase 2 | Complete |
| PIPE-04 | Phase 2 | Complete |
| PIPE-05 | Phase 2 | Complete |
| PIPE-06 | Phase 2 | Complete |
| PIPE-07 | Phase 2 | Complete |
| ENGN-01 | Phase 2 | Complete |
| ENGN-02 | Phase 2 | Complete |
| ENGN-03 | Phase 2 | Complete |
| ENGN-04 | Phase 2 | Complete |
| ENGN-05 | Phase 2 | Complete |
| ENGN-06 | Phase 2 | Complete |
| ENGN-07 | Phase 2 | Complete |
| LEARN-01 | Phase 3 | Complete |
| LEARN-02 | Phase 3 | Complete |
| LEARN-03 | Phase 3 | Complete |
| LEARN-04 | Phase 3 | Complete |
| LEARN-05 | Phase 3 | Pending |
| LEARN-06 | Phase 3 | Pending |
| MEM-01 | Phase 2 | Complete |
| MEM-02 | Phase 3 | Complete |
| MEM-03 | Phase 2 | Complete |
| MEM-04 | Phase 2 | Complete |
| MEM-05 | Phase 3 | Complete |
| API-01 | Phase 2 | Complete |
| API-02 | Phase 2 | Complete |
| API-03 | Phase 3 | Complete |
| API-04 | Phase 5 | Pending |
| DASH-01 | Phase 4 | Pending |
| DASH-02 | Phase 4 | Pending |
| DASH-03 | Phase 4 | Pending |
| DASH-04 | Phase 4 | Pending |
| DASH-05 | Phase 4 | Pending |
| DASH-06 | Phase 4 | Pending |
| DASH-07 | Phase 4 | Pending |
| DASH-08 | Phase 4 | Pending |
| DASH-09 | Phase 4 | Pending |
| DASH-10 | Phase 4 | Pending |
| DASH-11 | Phase 4 | Pending |
| VOICE-01 | Phase 5 | Pending |
| VOICE-02 | Phase 5 | Pending |
| VOICE-03 | Phase 5 | Pending |
| VOICE-04 | Phase 4 | Pending |
| DEMO-01 | Phase 6 | Pending |
| DEMO-02 | Phase 6 | Pending |
| DEMO-03 | Phase 1 | Complete |
| DEMO-04 | Phase 6 | Pending |
| DEMO-05 | Phase 6 | Pending |

**Coverage:**
- v1 requirements: 55 total
- Mapped to phases: 55
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-24*
*Last updated: 2026-03-24 after competitive analysis and architecture revision*
