# Roadmap: Sentinel

## Overview

Sentinel is built in dependency order: frozen schemas and infrastructure first, then the core investigation pipeline with real LLM payment agent, prediction step, composite anomaly scoring, and Aerospike wired in, then the self-improvement loop with rule evolution (the demo centerpiece, highest failure risk, validated in isolation before anything depends on it), then the React dashboard with anomaly score visualization and forensic attribution, then Bland AI voice integration, and finally explicit demo hardening and deployment. Each phase delivers a complete, independently verifiable capability. The self-improvement loop gets its own phase because it is the entire demo payoff — it cannot share a phase with other work and still receive the isolation testing it requires.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Foundation** - Frozen schemas, infrastructure, Aerospike health check, Claude API tier validation, and demo fixtures (completed 2026-03-24)
- [ ] **Phase 2: Core Investigation Pipeline** - Real LLM Payment Agent, prediction step, parallel sub-agents, Verdict Board Engine, Safety Gate with composite anomaly scoring, Aerospike writes, FastAPI/WebSocket, Phase 1 demo arc end-to-end
- [x] **Phase 3: Self-Improvement Loop** - Rule generation prompt (30+ isolation tests), prediction-error-driven scoring function generation, validation harness, rule evolution across incidents, SafetyGate registry, Phase 2 generalization verified end-to-end (completed 2026-03-25)
- [ ] **Phase 4: Dashboard** - Investigation tree, prediction vs. actual display, verdict board table, anomaly score bar with rule contributions, forensic scan panel, generated rule source panel with evolution history, trust score animation, Zustand state, WebSocket integration
- [ ] **Phase 5: Voice Integration** - Bland AI webhook, barge-in, grounded Q&A with anomaly scores and rule attribution, pre-computed context cache
- [ ] **Phase 6: Demo Preparation + Deployment** - docker-compose, demo_check.py, fixture loading, dry runs, AWS deployment, screen recording fallback

## Phase Details

### Phase 1: Foundation
**Goal**: All inter-component contracts are frozen, infrastructure is validated, and the first demo fixture set is committed — nothing downstream can fail due to missing schemas, wrong Aerospike namespace, or Claude API rate limits
**Depends on**: Nothing (first phase)
**Requirements**: INFRA-01, INFRA-02, INFRA-03, INFRA-04, INFRA-05, SCHEMA-01, SCHEMA-02, SCHEMA-03, SCHEMA-04, DEMO-03
**Success Criteria** (what must be TRUE):
  1. A Python import of all Pydantic schema classes (Verdict, VerdictBoard, Episode, WebSocket event taxonomy) succeeds with no errors and all fields match the frozen spec
  2. Aerospike starts via Docker, the startup health check performs a read-after-write against the configured namespace, and the server logs confirm the namespace is accessible before the application accepts requests
  3. A minimal Claude API call using the configured AsyncAnthropic client returns a response without a 429 error, and prompt caching headers confirm cache_control is active on system prompts
  4. The React frontend boots with @xyflow/react, Zustand, and Tailwind imports resolving without duplicate-context errors
  5. Phase 1 and Phase 2 demo fixture files (invoice image with embedded hidden text, counterparty DB, KYC ledger with Meridian Logistics absent, behavioral baselines) are committed and loadable via a fixture loader
**Plans:** 5/5 plans complete
Plans:
- [x] 01-01-PLAN.md — Python project init, dependency install, package stubs (INFRA-01, INFRA-05)
- [x] 01-02-PLAN.md — Aerospike Docker setup + async client wrapper (INFRA-02)
- [x] 01-03-PLAN.md — React frontend scaffold with @xyflow/react, Zustand, Tailwind + build test (INFRA-04)
- [x] 01-04-PLAN.md — Demo fixtures with forensic invoice PNGs, fixture loader, Claude API validation (DEMO-03, INFRA-03)
- [x] 01-05-PLAN.md — Frozen Pydantic schemas + TDD test suite (SCHEMA-01..04)

### Phase 2: Core Investigation Pipeline
**Goal**: A payment request triggers a complete parallel investigation with a real LLM payment agent, prediction step forms expectations from baselines, three sub-agents adversarially verify claims, the Verdict Board assembles structured comparisons, the Safety Gate computes a composite anomaly score and outputs GO/NO-GO/ESCALATE with attribution, and all results write to Aerospike — the hidden-text-invoice attack scenario runs end-to-end with the payment agent genuinely manipulated
**Depends on**: Phase 1
**Requirements**: PIPE-01, PIPE-02, PIPE-03, PIPE-04, PIPE-05, PIPE-06, PIPE-07, ENGN-01, ENGN-02, ENGN-03, ENGN-04, ENGN-05, ENGN-06, ENGN-07, MEM-01, MEM-03, MEM-04, API-01, API-02
**Success Criteria** (what must be TRUE):
  1. The Payment Agent (real Sonnet 4.6 LLM) receives a payment request with adversarial invoice, makes genuine decisions influenced by the hidden text, and returns a structured verdict with inflated confidence
  2. The prediction step computes expected values from behavioral baselines and stores them for comparison after investigation
  3. The three sub-agents (Risk, Compliance, Forensics) execute in parallel — their completion log timestamps confirm overlapping execution, not sequential
  4. The Verdict Board Engine produces a field-level mismatch list with severity tags, and Forensics correctly identifies the hidden text in the invoice image
  5. The Safety Gate computes a composite anomaly score from hardcoded rules and outputs NO-GO with attribution naming the specific mismatches, rules, and their score contributions
  6. Episode record with prediction errors is written to Aerospike after investigation completes
  7. WebSocket clients connected to /ws receive all named investigation events in sequence
**Plans:** 4/6 plans executed
Plans:
- [x] 02-01-PLAN.md — PaymentDecision schema, VerdictBoard/Episode extensions, PredictionEngine (ENGN-07)
- [x] 02-02-PLAN.md — Payment Agent with tool-use and Claude vision (PIPE-01, PIPE-07)
- [x] 02-03-PLAN.md — Sub-agents: Risk, Compliance, Forensics (PIPE-02..06)
- [x] 02-04-PLAN.md — Verdict Board Engine + Safety Gate with file-based scoring rules (ENGN-01..06)
- [x] 02-05-PLAN.md — Aerospike episode and trust stores with latency tracking (MEM-01, MEM-03, MEM-04)
- [x] 02-06-PLAN.md — Supervisor orchestration, FastAPI server, WebSocket, /investigate endpoint (PIPE-02, API-01, API-02)
**UI hint**: yes

### Phase 3: Self-Improvement Loop
**Goal**: After an operator confirms the Phase 1 attack, the system extracts prediction errors, generates a behavioral scoring function, validates it, deploys it to the Safety Gate registry with Aerospike provenance, and the scoring function fires correctly on the Phase 2 identity-spoofing scenario — then after confirming Attack 2, the scoring function evolves using prediction errors from both incidents
**Depends on**: Phase 2
**Requirements**: LEARN-01, LEARN-02, LEARN-03, LEARN-04, LEARN-05, LEARN-06, MEM-02, MEM-05, API-03
**Success Criteria** (what must be TRUE):
  1. The rule generation prompt, tested 30+ times in isolation, consistently produces a Python scoring function that operates only on behavioral verdict board fields and returns a weighted anomaly score (not binary True/False)
  2. The generated scoring function passes the validation harness: AST parse succeeds, compile() succeeds, returns near-zero score on clean baseline fixtures, returns score > 0.6 on the Phase 1 attack fixture
  3. After /confirm is called, the scoring function appears in the Safety Gate registry with provenance (episode_id, prediction_errors, timestamp) stored in Aerospike
  4. When the Phase 2 identity-spoofing VerdictBoard is evaluated, hardcoded rules alone produce insufficient anomaly score, but the generated scoring function's contribution pushes the composite score above the NO-GO threshold — with attribution "Blocked by Generated Rule #001"
  5. After confirming Attack 2, the system generates a refined scoring function (Rule 001-v2) using prediction errors from both episodes — the refined function is tighter (lower false positive potential) than v1
  6. Aerospike write latency for rule storage is measured and exposed via API
**Plans:** 4/4 plans complete
Plans:
- [x] 03-01-PLAN.md — RuleGenerator core engine with validation harness, Opus 4.6 prompt, EventType extension (LEARN-01, LEARN-02, LEARN-03)
- [x] 03-02-PLAN.md — Aerospike rule store with CRUD, latency tracking, startup loading (MEM-02, MEM-05)
- [x] 03-03-PLAN.md — POST /confirm route with background rule generation pipeline, WebSocket streaming (API-03, LEARN-04)
- [x] 03-04-PLAN.md — Cross-attack generalization proof, rule evolution, end-to-end loop test (LEARN-05, LEARN-06)

### Phase 4: Dashboard
**Goal**: The React dashboard visualizes the complete investigation lifecycle in real time — the investigation tree lights up as sub-agents activate, prediction vs. actual values are displayed, the anomaly score bar fills with color-coded rule contributions, the verdict board shows field-level mismatches, and after rule generation/evolution a new rule node appears with provenance; all information that would be spoken by voice is also visible on screen
**Depends on**: Phase 3
**Requirements**: DASH-01, DASH-02, DASH-03, DASH-04, DASH-05, DASH-06, DASH-07, DASH-08, DASH-09, DASH-10, DASH-11, VOICE-04
**Success Criteria** (what must be TRUE):
  1. The @xyflow/react investigation tree animates sub-agent nodes from pending to active to complete state as WebSocket events arrive, and after rule deployment a new rule node is visible in the tree
  2. The prediction vs. actual panel shows expected values alongside actual findings, with prediction errors highlighted
  3. The composite anomaly score bar displays each rule's weighted contribution with color coding, and the threshold line is visible
  4. The verdict board table displays each claims_checked field with color-coded severity indicators
  5. The forensic scan panel shows clean invoice vs. annotated forensic scan side-by-side
  6. The generated rule source panel shows readable Python with provenance and evolution history (v1 → v2)
  7. The Aerospike write latency metric is displayed live on the dashboard
**Plans:** 2/5 plans executed
Plans:
- [x] 04-01-PLAN.md — Zustand store extensions, WebSocket hook, two-column layout shell with attack buttons (VOICE-04)
- [x] 04-02-PLAN.md — Investigation tree with animated nodes, Gate Decision panel, Anomaly Score Bar (DASH-01, DASH-02, DASH-07, DASH-11)
- [ ] 04-03-PLAN.md — Verdict Board table with prediction sub-rows, Forensic Scan panel (DASH-03, DASH-04, DASH-10)
- [ ] 04-04-PLAN.md — Rule Source panel with streaming/syntax highlighting, Decision Log, Trust Score Bar, Aerospike Latency (DASH-05, DASH-06, DASH-08, DASH-09)
- [ ] 04-05-PLAN.md — Visual verification checkpoint (all DASH requirements)
**UI hint**: yes

### Phase 5: Voice Integration
**Goal**: The Bland AI voice session is live for the demo — the Supervisor answers "Why did you block that?" in plain language using actual anomaly scores, prediction errors, and rule attribution; barge-in works; all voice answers are also visible on the dashboard as text fallback
**Depends on**: Phase 4
**Requirements**: VOICE-01, VOICE-02, VOICE-03, VOICE-04, API-04
**Success Criteria** (what must be TRUE):
  1. A Bland AI voice call is initiated, the Supervisor answers a natural language question about the investigation decision grounded in actual anomaly scores and rule attribution, and the webhook response is delivered within the 8-second budget
  2. Barge-in works during a voice session — interrupting the Supervisor mid-sentence causes it to stop speaking and process the new question
  3. The dashboard displays the same information as voice narration — text fallback is always present if voice fails
**Plans**: TBD
**UI hint**: yes

### Phase 6: Demo Preparation + Deployment
**Goal**: The full Attack 1 → rule generation → Attack 2 → rule fires → rule evolves → voice Q&A arc runs end-to-end without intervention in under 3 minutes, a validation script confirms every integration is live before the demo, the stack starts in one command, and a screen recording fallback exists if anything fails on demo day
**Depends on**: Phase 5
**Requirements**: INFRA-06, DEMO-01, DEMO-02, DEMO-04, DEMO-05
**Success Criteria** (what must be TRUE):
  1. `docker-compose up` starts the full stack (FastAPI, Aerospike, React dev server) with no manual configuration steps required
  2. `demo_check.py` runs without errors, confirming Aerospike namespace accessible, all API keys valid, Bland AI reachable, WebSocket connects, both fixture sets load
  3. Two consecutive full demo arcs run end-to-end in under 3 minutes each without intervention
  4. The application is deployed to EC2/ECS with a public URL that Bland AI webhooks can reach
  5. A screen recording of the complete demo arc exists as a local file before demo day
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 5/5 | Complete   | 2026-03-24 |
| 2. Core Investigation Pipeline | 6/6 | Complete |  |
| 3. Self-Improvement Loop | 4/4 | Complete   | 2026-03-25 |
| 4. Dashboard | 2/5 | In Progress|  |
| 5. Voice Integration | 0/TBD | Not started | - |
| 6. Demo Preparation + Deployment | 0/TBD | Not started | - |
