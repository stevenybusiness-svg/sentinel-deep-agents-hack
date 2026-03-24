# Requirements: Sentinel

**Defined:** 2026-03-24
**Core Value:** The self-improvement loop: a rule learned from one attack type must demonstrably catch a completely different attack — live, on stage, in 3 minutes.

## v1 Requirements

### Infrastructure

- [x] **INFRA-01**: Python 3.11+ project initialized with FastAPI, AsyncAnthropic, Aerospike Python client (19.1.0), RestrictedPython (8.2)
- [x] **INFRA-02**: Aerospike running via Docker with startup health check (read-after-write validates namespace exists before accepting traffic)
- [ ] **INFRA-03**: Claude API Tier 2 access confirmed; prompt caching enabled for all agent system prompts to stay within ITPM budget
- [ ] **INFRA-04**: React 18+ frontend initialized with @xyflow/react (12.4.x), Zustand, Tailwind CSS
- [x] **INFRA-05**: Environment configuration via .env (ANTHROPIC_API_KEY, AEROSPIKE_HOST, BLAND_API_KEY, OKTA_DOMAIN, OKTA_CLIENT_ID)
- [ ] **INFRA-06**: TrueFoundry deployment configured for agent fleet (EC2/ECS with AWS infrastructure)

### Schemas

- [ ] **SCHEMA-01**: Verdict schema frozen — agent_id, claims_checked[] (field, agent_claimed, independently_found, match, severity), behavioral_flags[], agent_confidence, confidence_z_score, unable_to_verify
- [ ] **SCHEMA-02**: Verdict Board schema frozen — mismatches[], behavioral_flags[], agent_confidence, confidence_z_score, step_sequence_deviation, hardcoded_rule_fired, unable_to_verify[]
- [ ] **SCHEMA-03**: Episode schema frozen — id, timestamp, action_request, agent_verdicts, verdict_board, gate_decision, gate_rationale, rules_fired, generated_rules_fired, operator_confirmation, attack_type, generated_rule_source, new_rules_deployed
- [ ] **SCHEMA-04**: WebSocket event taxonomy defined — 9 named events: investigation_started, agent_completed (×3), verdict_board_assembled, gate_evaluated, episode_written, rule_generated, rule_deployed

### Investigation Pipeline

- [ ] **PIPE-01**: Payment Agent parses a structured payment request, queries counterparty fixture DB, returns verdict with amount/beneficiary/account/confidence/steps_taken/claims_made
- [ ] **PIPE-02**: Supervisor (Opus 4.6) dispatches Risk, Compliance, Forensics in parallel via asyncio.TaskGroup; collects all verdicts with return_exceptions=True so one failure produces unable_to_verify rather than aborting
- [ ] **PIPE-03**: Risk Agent computes confidence z-score against behavioral baseline (mean 0.52, std 0.11); detects step-sequence deviations; returns structured findings
- [ ] **PIPE-04**: Compliance Agent independently queries KYC ledger and agent activity log; validates agent identity claims against authoritative source; returns structured findings on each claim
- [ ] **PIPE-05**: Forensics Agent independently scans attached document images via vision model; detects adversarial/hidden content regardless of color or contrast; returns actual extracted field values for comparison against agent claims
- [ ] **PIPE-06**: Forensics Agent returns clean result with "no documents available" note when no attachments present (Phase 2 scenario)

### Verdict Board Engine + Safety Gate

- [ ] **ENGN-01**: Verdict Board Engine performs field-level comparison between payment agent claims and each investigator's independently found values; produces mismatch list with severity tags (critical/warning/info)
- [ ] **ENGN-02**: Safety Gate applies hardcoded rules first and immutably (adversarial content in document → NO-GO; agent identity unverifiable in authoritative log → NO-GO)
- [ ] **ENGN-03**: Safety Gate loads all generated Python functions from rule registry and executes each against the verdict board via RestrictedPython sandbox
- [ ] **ENGN-04**: Safety Gate outputs GO / NO-GO / ESCALATE with full attribution — which mismatches, which rules fired, which agents found what
- [ ] **ENGN-05**: exec() sandbox enforces: builtins whitelist (len, any, all, isinstance, etc.), compile() before exec(), explicit namespace extraction (fn = namespace['detect']), 5-second signal.alarm timeout, AST string-level pre-check for import/__

### Self-Improvement Loop

- [ ] **LEARN-01**: On operator-confirmed attack, Supervisor sends full verdict board + critical mismatches + behavioral flags + attack type to Opus 4.6 with rule generation prompt
- [ ] **LEARN-02**: Generated Python function is behavioral — operates only on verdict_board fields; does not reference attack mechanism, document type, or agent names; includes docstring explaining what pattern it detects and why it generalizes
- [ ] **LEARN-03**: Generated function passes validation before deployment: AST parse, compile(), test harness executes function against clean fixture (must return False) and attack fixture (must return True)
- [ ] **LEARN-04**: Validated rule exec()'d into Safety Gate registry with provenance: episode_id, timestamp, attack_type, python_source stored in Aerospike rules set
- [ ] **LEARN-05**: Phase 2 demo end-to-end: generated rule from Phase 1 (invoice attack) fires on Phase 2 verdict board (identity spoofing); gate outputs NO-GO; attribution displays "Blocked by Generated Rule #001 (Confident Agent, Contradicted by Independent Verification) | Rule written after Episode #001 | Deployed [X]s ago"

### Episodic Memory (Aerospike)

- [ ] **MEM-01**: Episode records written to Aerospike `sentinel.episodes` set after each incident resolution; write latency measured per operation
- [ ] **MEM-02**: Generated rule source and provenance written to Aerospike `sentinel.rules` set; fire_count bin updated atomically via increment(); rules loaded into SafetyGate registry at startup via scan()
- [ ] **MEM-03**: Trust postures and behavioral baselines persisted in Aerospike `sentinel.trust` set; updated after each investigation
- [ ] **MEM-04**: Recent episodes queried from Aerospike at investigation start; injected into Supervisor system prompt as context for similarity matching
- [ ] **MEM-05**: Aerospike write latency measured per operation and exposed via API; displayed on dashboard (target: <5ms per write)

### Backend API

- [ ] **API-01**: FastAPI server with WebSocket endpoint (/ws) emitting named investigation events to connected dashboard clients in real time
- [ ] **API-02**: POST /investigate accepts payment request payload; triggers full investigation pipeline; caches active episode state in memory for duration to avoid re-querying Aerospike per WebSocket event
- [ ] **API-03**: POST /confirm accepts operator confirmation (confirmed_attack / false_positive); triggers rule generation pipeline if confirmed_attack; stores result to Aerospike
- [ ] **API-04**: POST /bland-webhook handles Bland AI Q&A turns; responds within 8s; reads pre-computed investigation context from in-memory cache (not Aerospike per-turn)
- [ ] **API-05**: POST /override validates Bearer token via Okta introspect before accepting override command; rejects if override_authority scope absent

### Dashboard

- [ ] **DASH-01**: Investigation tree rendered with @xyflow/react; nodes animate to active state as sub-agents receive their dispatch; edges animate as data flows
- [ ] **DASH-02**: New rule node appears in investigation tree after rule deployment — the tree is visibly larger after learning than before
- [ ] **DASH-03**: Verdict board table shows field-level match/mismatch for all claims_checked with 🔴 MISMATCH / ✅ MATCH / ⚠️ DEVIATION severity indicators
- [ ] **DASH-04**: Forensic scan panel shows clean invoice view (what human sees) vs. forensic scan (hidden text highlighted in red) side-by-side for Phase 1 demo
- [ ] **DASH-05**: Generated rule source panel shows readable Python function the system wrote, with provenance (episode ID, deployed timestamp, attack type that produced it)
- [ ] **DASH-06**: Trust score bar animates from initial value (0.85) to post-investigation value (0.25) as verdict board assembles
- [ ] **DASH-07**: Gate decision (GO / NO-GO / ESCALATE) displayed prominently with full attribution text below it
- [ ] **DASH-08**: Decision log shows timestamped trail of all gate decisions with one-line attribution per entry
- [ ] **DASH-09**: Aerospike latency metric displayed live on dashboard (confirms real integration to Aerospike judges)

### Voice Interface (Bland AI)

- [ ] **VOICE-01**: Bland AI call initiated for demo; Supervisor answers "Why did you block that?" and "What was the confidence score?" in plain language
- [ ] **VOICE-02**: Barge-in configured via interruption_threshold and block_interruptions: false; operator can cut in mid-sentence
- [ ] **VOICE-03**: All investigation context pre-computed and cached before Phase 3 voice demo starts; webhook handler reads from memory cache, not Aerospike, to stay within 8s response window
- [ ] **VOICE-04**: Dashboard always shows the same information as voice narration — text fallback is always present if voice fails
- [ ] **VOICE-05**: Override command received via voice triggers Okta identity verification flow before override is accepted

### Identity Verification (Okta)

- [ ] **AUTH-01**: Okta token introspection: POST /override sends Bearer token to /oauth2/default/v1/introspect via httpx; rejects with 403 if inactive or missing override_authority scope
- [ ] **AUTH-02**: Dashboard shows "Verifying identity... ✓ Confirmed: [name], override_authority granted" during override flow; override proceeds after confirmation

### Demo Preparation

- [ ] **DEMO-01**: docker-compose.yml runs full stack (FastAPI, Aerospike, React dev server) in one command with no manual steps
- [ ] **DEMO-02**: demo_check.py validates all components before demo: Aerospike namespace accessible, API keys valid, Bland AI connectivity, WebSocket connects and receives first event, Phase 1 fixtures load, Phase 2 fixtures load
- [ ] **DEMO-03**: Demo fixtures committed: Phase 1 (invoice image with embedded hidden text, counterparty DB, behavioral baselines), Phase 2 (spoofed KYC pre-clearance payload, empty KYC ledger for Meridian Logistics)
- [ ] **DEMO-04**: Full Phase 1 → rule generation → Phase 2 arc runs end-to-end without intervention in under 3 minutes
- [ ] **DEMO-05**: Screen recording of full demo arc captured as fallback before demo day

---

## v2 Requirements

### Data Pipeline (Airbyte)

- **DATA-01**: Airbyte syncs counterparty authorization records from Google Sheet to counterparty fixture DB
- **DATA-02**: Airbyte syncs KYC/AML verification log from Google Sheet (real KYC agent entries; intentionally empty for Meridian Logistics)

### Additional Attack Vectors

- **ATK-01**: Data poisoning attack scenario — corrupted authorization record in counterparty DB skews agent reasoning
- **ATK-02**: Confidence manipulation as standalone scenario — compromised agent returns anomalously high confidence, triggered by Risk Agent z-score alone

### Extended Observability

- **OBS-01**: TrueFoundry agent fleet observability dashboard showing per-agent latency, token usage, and error rates
- **OBS-02**: Aerospike episode replay — operator can re-run any stored episode through current rule set to see if new rules would have caught it earlier

---

## Out of Scope

| Feature | Reason |
|---------|--------|
| Fine-tuning / model weight updates | Rule generation via executable Python is the learning mechanism; weights not modified |
| Model-level RAG fine-tuning pipeline | Out of 72-hour scope; episodic memory + rule generation is the demo-viable learning path |
| Multi-tenant / SaaS deployment | Single operator context sufficient for hackathon demo |
| Non-payment agent supervision | Architecture is payment-specific for demo clarity; generalization can be pitched without building it |
| Stablecoin / on-chain settlement rails | Fiat wire transfers only — universally understood, no explanation overhead |
| Mobile / native app | Web dashboard only |
| Real-time WebSocket streaming to Bland AI | Not supported in Bland API; webhook is the integration path |
| Attack vectors beyond the 4 in spec | Prompt injection, data poisoning, confidence manipulation, cross-agent deception are demo surface; no expansion during hackathon |
| Generative UI for investigation tree | Static React Flow graph is sufficient; dynamic layout generation adds risk |

---

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| INFRA-01 | Phase 1 | Complete |
| INFRA-02 | Phase 1 | Complete |
| INFRA-03 | Phase 1 | Pending |
| INFRA-04 | Phase 1 | Pending |
| INFRA-05 | Phase 1 | Complete |
| INFRA-06 | Phase 6 | Pending |
| SCHEMA-01 | Phase 1 | Pending |
| SCHEMA-02 | Phase 1 | Pending |
| SCHEMA-03 | Phase 1 | Pending |
| SCHEMA-04 | Phase 1 | Pending |
| PIPE-01 | Phase 2 | Pending |
| PIPE-02 | Phase 2 | Pending |
| PIPE-03 | Phase 2 | Pending |
| PIPE-04 | Phase 2 | Pending |
| PIPE-05 | Phase 2 | Pending |
| PIPE-06 | Phase 2 | Pending |
| ENGN-01 | Phase 2 | Pending |
| ENGN-02 | Phase 2 | Pending |
| ENGN-03 | Phase 2 | Pending |
| ENGN-04 | Phase 2 | Pending |
| ENGN-05 | Phase 2 | Pending |
| LEARN-01 | Phase 3 | Pending |
| LEARN-02 | Phase 3 | Pending |
| LEARN-03 | Phase 3 | Pending |
| LEARN-04 | Phase 3 | Pending |
| LEARN-05 | Phase 3 | Pending |
| MEM-01 | Phase 2 | Pending |
| MEM-02 | Phase 3 | Pending |
| MEM-03 | Phase 2 | Pending |
| MEM-04 | Phase 2 | Pending |
| MEM-05 | Phase 3 | Pending |
| API-01 | Phase 2 | Pending |
| API-02 | Phase 2 | Pending |
| API-03 | Phase 3 | Pending |
| API-04 | Phase 5 | Pending |
| API-05 | Phase 5 | Pending |
| DASH-01 | Phase 4 | Pending |
| DASH-02 | Phase 4 | Pending |
| DASH-03 | Phase 4 | Pending |
| DASH-04 | Phase 4 | Pending |
| DASH-05 | Phase 4 | Pending |
| DASH-06 | Phase 4 | Pending |
| DASH-07 | Phase 4 | Pending |
| DASH-08 | Phase 4 | Pending |
| DASH-09 | Phase 4 | Pending |
| VOICE-01 | Phase 5 | Pending |
| VOICE-02 | Phase 5 | Pending |
| VOICE-03 | Phase 5 | Pending |
| VOICE-04 | Phase 4 | Pending |
| VOICE-05 | Phase 5 | Pending |
| AUTH-01 | Phase 5 | Pending |
| AUTH-02 | Phase 5 | Pending |
| DEMO-01 | Phase 6 | Pending |
| DEMO-02 | Phase 6 | Pending |
| DEMO-03 | Phase 1 | Pending |
| DEMO-04 | Phase 6 | Pending |
| DEMO-05 | Phase 6 | Pending |

**Coverage:**
- v1 requirements: 57 total
- Mapped to phases: 57
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-24*
*Last updated: 2026-03-24 after roadmap creation*
