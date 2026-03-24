# Roadmap: Sentinel

## Overview

Sentinel is built in dependency order: frozen schemas and infrastructure first, then the deterministic engines and core investigation pipeline with Aerospike wired in, then the self-improvement loop (the demo centerpiece, highest failure risk, validated in isolation before anything depends on it), then the React dashboard, then sponsor voice and auth integrations, and finally explicit demo hardening and deployment. Each phase delivers a complete, independently verifiable capability. The self-improvement loop gets its own phase because it is the entire demo payoff — it cannot share a phase with other work and still receive the isolation testing it requires.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Foundation** - Frozen schemas, infrastructure, Aerospike health check, Claude API tier validation, and demo fixtures
- [ ] **Phase 2: Core Investigation Pipeline** - Payment Agent, parallel sub-agents, Verdict Board Engine, Safety Gate, Aerospike writes, FastAPI/WebSocket, Phase 1 demo arc end-to-end
- [ ] **Phase 3: Self-Improvement Loop** - Rule generation prompt (30+ isolation tests), validation harness, SafetyGate registry, Phase 2 generalization verified end-to-end
- [ ] **Phase 4: Dashboard** - Investigation tree, verdict board table, forensic scan panel, generated rule source panel, trust score animation, Zustand state, WebSocket integration
- [ ] **Phase 5: Voice + Auth** - Bland AI webhook, barge-in, Okta token introspection, override flow, pre-computed context cache
- [ ] **Phase 6: Demo Preparation + Deployment** - docker-compose, demo_check.py, fixture loading, dry runs, TrueFoundry/AWS deployment, screen recording fallback

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
**Plans:** 2/5 plans executed
Plans:
- [x] 01-01-PLAN.md — Python project init, dependency install, package stubs (INFRA-01, INFRA-05)
- [x] 01-02-PLAN.md — Aerospike Docker setup + async client wrapper (INFRA-02)
- [ ] 01-03-PLAN.md — React frontend scaffold with @xyflow/react, Zustand, Tailwind + build test (INFRA-04)
- [ ] 01-04-PLAN.md — Demo fixtures with forensic invoice PNGs, fixture loader, Claude API validation (DEMO-03, INFRA-03)
- [ ] 01-05-PLAN.md — Frozen Pydantic schemas + TDD test suite (SCHEMA-01..04)

### Phase 2: Core Investigation Pipeline
**Goal**: A payment request submitted to the API triggers a complete parallel investigation, produces a verdict board, passes through the Safety Gate, and writes all results to Aerospike — the hidden-text-invoice attack scenario runs end-to-end and produces NO-GO with correct attribution
**Depends on**: Phase 1
**Requirements**: PIPE-01, PIPE-02, PIPE-03, PIPE-04, PIPE-05, PIPE-06, ENGN-01, ENGN-02, ENGN-03, ENGN-04, ENGN-05, MEM-01, MEM-03, MEM-04, API-01, API-02
**Success Criteria** (what must be TRUE):
  1. The three sub-agents (Risk, Compliance, Forensics) execute in parallel — their completion log timestamps confirm overlapping execution, not sequential
  2. The Verdict Board Engine produces a field-level mismatch list with severity tags for the Phase 1 fixture, and Forensics correctly identifies the hidden text in the invoice image
  3. The Safety Gate fires the hardcoded adversarial-content rule, outputs NO-GO, and the attribution string names the specific mismatch and rule that fired
  4. Episode record is written to Aerospike `sentinel.episodes` after investigation completes, and a subsequent read returns the full verdict board and gate decision
  5. WebSocket clients connected to /ws receive all 9 named investigation events (investigation_started through episode_written) in sequence for a single investigation run
**Plans**: TBD
**UI hint**: yes

### Phase 3: Self-Improvement Loop
**Goal**: After an operator confirms the Phase 1 attack, the system generates a behavioral Python detection rule, validates it against both fixtures, deploys it to the Safety Gate registry with Aerospike provenance, and the rule fires correctly on the Phase 2 identity-spoofing fixture — the full generalization demo arc works end-to-end
**Depends on**: Phase 2
**Requirements**: LEARN-01, LEARN-02, LEARN-03, LEARN-04, LEARN-05, MEM-02, MEM-05, API-03
**Success Criteria** (what must be TRUE):
  1. The rule generation prompt, tested 30+ times in isolation against the Phase 1 verdict board, consistently produces a Python function that operates only on behavioral verdict board fields (agent_confidence, field_mismatches, claims_verified_count) and contains no references to document type, forensics fields, or agent names
  2. The generated rule passes the validation harness: AST parse succeeds, compile() succeeds, function returns False on the clean fixture, and function returns True on the Phase 1 attack fixture
  3. After /confirm is called with confirmed_attack, the generated rule appears in the Safety Gate registry and its source is readable in Aerospike `sentinel.rules` with full provenance (episode_id, timestamp, attack_type)
  4. When the Phase 2 identity-spoofing verdict board is evaluated by the Safety Gate, the generated rule (not a hardcoded rule) fires and the gate outputs NO-GO with attribution "Blocked by Generated Rule #001 (Confident Agent, Contradicted by Independent Verification)"
  5. Aerospike write latency for rule storage is measured per operation and the value is exposed via the API endpoint
**Plans**: TBD

### Phase 4: Dashboard
**Goal**: The React dashboard visualizes the complete investigation lifecycle in real time — the investigation tree lights up as sub-agents activate, the verdict board shows field-level mismatches, the trust score collapses, and after rule generation a new rule node appears in the tree; all information that would be spoken by voice is also visible on screen
**Depends on**: Phase 3
**Requirements**: DASH-01, DASH-02, DASH-03, DASH-04, DASH-05, DASH-06, DASH-07, DASH-08, DASH-09, VOICE-04
**Success Criteria** (what must be TRUE):
  1. The @xyflow/react investigation tree animates sub-agent nodes from pending to active to complete state as WebSocket events arrive, and after rule deployment a new rule node is visible in the tree
  2. The verdict board table displays each claims_checked field with a color-coded indicator (red MISMATCH, green MATCH, yellow DEVIATION) matching the severity tags from the backend
  3. The forensic scan panel shows the clean invoice and the annotated forensic scan side-by-side, with hidden text areas highlighted in red
  4. The trust score bar animates from 0.85 to 0.25 as the verdict board assembles, and the gate decision (GO / NO-GO / ESCALATE) is displayed prominently with the full attribution text
  5. The Aerospike write latency metric is displayed live on the dashboard and updates with each investigation cycle
**Plans**: TBD
**UI hint**: yes

### Phase 5: Voice + Auth
**Goal**: The Bland AI voice session is live for the demo — the Supervisor answers "Why did you block that?" and "What was the confidence score?" in plain language using pre-computed context, barge-in works, the override command triggers Okta identity verification, and all voice answers are also visible on the dashboard as text fallback
**Depends on**: Phase 4
**Requirements**: VOICE-01, VOICE-02, VOICE-03, VOICE-05, AUTH-01, AUTH-02, API-04, API-05
**Success Criteria** (what must be TRUE):
  1. A Bland AI voice call is initiated, the Supervisor answers a natural language question about the investigation decision, and the webhook response is delivered within the 8-second budget (measured in test)
  2. Barge-in works during a voice session — interrupting the Supervisor mid-sentence causes it to stop speaking and process the new question
  3. POST /override with a valid Bearer token containing override_authority scope is accepted; a request without the scope is rejected with 403
  4. The dashboard displays "Verifying identity... Confirmed: [name], override_authority granted" during the override flow before the override is accepted
**Plans**: TBD
**UI hint**: yes

### Phase 6: Demo Preparation + Deployment
**Goal**: The full Phase 1 → rule generation → Phase 2 → voice Q&A arc runs end-to-end without intervention in under 3 minutes, a validation script confirms every integration is live before the demo, the stack starts in one command, and a screen recording fallback exists if anything fails on demo day
**Depends on**: Phase 5
**Requirements**: INFRA-06, DEMO-01, DEMO-02, DEMO-04, DEMO-05
**Success Criteria** (what must be TRUE):
  1. `docker-compose up` starts the full stack (FastAPI, Aerospike, React dev server) with no manual configuration steps required
  2. `demo_check.py` runs without errors, confirming Aerospike namespace accessible, all API keys valid, Bland AI reachable, WebSocket connects and receives first event, and both fixture sets load
  3. Two consecutive full Phase 1 → Phase 2 demo arcs run end-to-end in under 3 minutes each without intervention
  4. The application is deployed to EC2/ECS with a public URL that Bland AI webhooks can reach, and the deployment URL is tested with a live webhook roundtrip
  5. A screen recording of the complete demo arc (including voice Q&A and Okta override) exists as a local file before demo day
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 2/5 | In Progress|  |
| 2. Core Investigation Pipeline | 0/TBD | Not started | - |
| 3. Self-Improvement Loop | 0/TBD | Not started | - |
| 4. Dashboard | 0/TBD | Not started | - |
| 5. Voice + Auth | 0/TBD | Not started | - |
| 6. Demo Preparation + Deployment | 0/TBD | Not started | - |
