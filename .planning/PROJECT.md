# Sentinel

## What This Is

Sentinel is a runtime security system for autonomous AI agents. It intercepts agent actions at the execution boundary, dispatches independent AI investigators to adversarially verify the agent's claims against ground truth, and blocks actions that can't be independently confirmed. When it catches a new attack, it automatically writes a detection rule — inspectable Python, not a black box — that catches the same behavioral pattern in future incidents. The detection capability is monotonically increasing: every confirmed incident makes the system strictly harder to fool.

Built for the AWS Deep Agents Hackathon (72-hour solo build, deadline ~2026-03-27). Payments are the demo scenario; the architecture applies anywhere an autonomous agent touches the real world.

## Core Value

The self-improvement loop: after confirming an attack, the system autonomously generates a composite scoring function from prediction errors, validates it, deploys it, and catches the next attack — even if the attack vector is completely different — because compromised agents exhibit the same behavioral fingerprint regardless of how they were manipulated. Rules evolve across incidents: each confirmed attack refines the system's model of what compromised behavior looks like. Live, on stage, in 3 minutes.

## Threat Model

Most AI security protects LLMs from malicious users (prompt injection, jailbreaks). Sentinel addresses a different threat: **the AI agent itself is the compromised entity.** A payment agent that's been prompt-injected via a document, socially engineered by another agent, or hallucinating with high confidence doesn't crash — it confidently takes the wrong action. Existing guardrails filter inputs and outputs but trust the agent's reasoning. Sentinel doesn't.

## Architecture: Four Layers

**Layer 1 — Autonomous Agent (Real LLM, Not Scripted)**
The payment agent is a Sonnet 4.6 instance that receives a payment request and makes genuine decisions: verifying the counterparty against the KYC ledger, checking authorization, analyzing attached documents, and returning a structured verdict with confidence score and evidence. Attacks work by manipulating its reasoning — prompt injection via documents, identity spoofing via crafted context — so the agent genuinely believes its own incorrect conclusions.

**Layer 2 — Adversarial Verification (AI Investigates)**
Three parallel sub-agents (Risk, Compliance, Forensics) independently investigate the payment agent's claims. They do not ask the agent whether it's telling the truth. Each checks external ground truth directly:
- **Risk Agent** — Computes confidence z-score against behavioral baseline. Detects step-sequence deviations.
- **Compliance Agent** — Checks counterparty identity against KYC ledger. Verifies authorization claims against agent activity log.
- **Forensics Agent** — Analyzes raw document images via vision model. Detects hidden/adversarial content.

Before investigating, the system forms **predictions** based on behavioral baselines: "Given normal agent behavior, here's what we expect to find." The gap between prediction and reality — the prediction error — is the primary learning signal.

**Layer 3 — Verdict Board Assembly (Deterministic)**
Structured comparison: for each claim the payment agent made, did the corresponding investigator independently confirm it? Mechanical field matching, not LLM judgment. Outputs a structured dict with mismatches, unable_to_verify fields, z-scores, and behavioral flags.

**Layer 4 — Safety Gate (The Block Decision Is an If-Statement)**
Two rule tiers execute in order:
- **Tier 1 — Hardcoded rules** (immutable, shipped with system): `adversarial_content_detected → NO-GO`, etc.
- **Tier 2 — Generated scoring functions** (written by LLM once, run deterministically forever): each returns a weighted anomaly score. Individually weak signals compound — total score exceeds threshold → NO-GO.

The gate decision: `total_score >= 1.0 → NO-GO | >= 0.6 → ESCALATE | else → GO`. Pure Python. No inference, no model weights, no probability distribution. You can read every rule, unit test every rule, and you can't prompt-inject an if-statement.

## Self-Improvement Loop

When an operator confirms an attack, the system doesn't learn "what this attack was." It extracts the **behavioral fingerprint** — where its own predictions diverged most from reality:

1. **Extract prediction errors** from the confirmed incident's VerdictBoard — which claims failed verification, how far did confidence deviate from baseline, did the agent skip normal steps?
2. **Generate a scoring function** — the Supervisor (Opus 4.6) writes a Python function that returns a weighted anomaly score over VerdictBoard fields. The prompt constrains: no attack-specific details, no entity names, behavioral signals only.
3. **Validate before deployment** — AST parse, compile, fires on source incident, doesn't fire on clean baselines, contains no prohibited constructs.
4. **Deploy to Safety Gate** — the scoring function runs deterministically on every future transaction.
5. **Rule evolution** — after a second confirmed incident, the system feeds both VerdictBoards and their prediction errors back in and generates a refined scoring function: tighter thresholds, drops conditions that were artifacts of one attack, strengthens conditions that appeared in both.

## Requirements

### Validated

**Core Investigation Pipeline** — Validated in Phase 02: core-investigation-pipeline
- [x] Payment Agent (real Sonnet 4.6 LLM) processes a payment request, queries fixtures, makes genuine decisions, returns structured verdict
- [x] Supervisor Agent (Opus 4.6) forms predictions from behavioral baselines, dispatches Risk/Compliance/Forensics in parallel, computes prediction errors, synthesizes verdict board
- [x] Risk Agent computes confidence z-score against behavioral baseline and detects step-sequence deviations
- [x] Compliance Agent cross-validates claims against independent authoritative sources (KYC ledger, agent activity log)
- [x] Forensics Agent independently scans document inputs for adversarial content using vision model; extracts actual field values for comparison
- [x] Verdict Board Engine performs deterministic field-level comparison between payment agent claims and investigator findings (match/mismatch/unable-to-verify)
- [x] Safety Gate applies hardcoded rules first, then executes generated scoring functions; computes composite anomaly score; outputs GO/NO-GO/ESCALATE with full attribution
- [x] Live end-to-end: hidden-text invoice attack → Payment Agent manipulated → Sentinel returns NO-GO (composite 5.85)

### Active

**Self-Improvement Loop**
- [ ] On operator-confirmed attack, system extracts prediction errors (expected vs actual across all VerdictBoard fields)
- [ ] Generated scoring function is behavioral (operates only on verdict board fields, no attack-specific details) and returns weighted anomaly score (not binary)
- [ ] Generated function passes validation harness before deployment (AST parse, compile, fires on attack fixture, clean on baseline)
- [ ] Generated function deployed to Safety Gate registry with full provenance (episode ID, timestamp, prediction errors that produced it)
- [ ] Rule evolution: after second confirmed incident, system refines scoring function using prediction errors from both episodes
- [ ] Rule source code stored in Aerospike, readable on dashboard — not a black box

**Episodic Memory (Aerospike)**
- [ ] Episode records written after each incident resolution (verdict board, gate decision, prediction errors, operator confirmation, generated rule source)
- [ ] Behavioral baselines and prediction history persisted; queried at investigation start for prediction step
- [ ] All decisions logged with full provenance and attribution (<5ms write latency)

**Voice Interface (Bland AI)**
- [ ] Supervisor answers operator questions in plain language via real-time bidirectional voice (Bland AI)
- [ ] Barge-in/interruption supported — operator can redirect mid-sentence
- [ ] Supervisor explains its reasoning grounded in actual anomaly scores, prediction errors, and rule attribution

**Dashboard**
- [ ] Live investigation tree — nodes light up as sub-agents activate, new rule nodes appear after learning
- [ ] Prediction vs. actual display — shows expected values and where reality diverged
- [ ] Verdict board comparison table — field-level match/mismatch visualization with severity tags
- [ ] Composite anomaly score bar — color-coded contributions from each rule, threshold line visible
- [ ] Forensic scan side-by-side — clean invoice view vs. forensic scan with hidden text highlighted in red
- [ ] Generated rule source panel — readable Python with provenance and evolution history
- [ ] Gate decision displayed prominently with full forensic attribution chain
- [ ] Decision log with attribution trail
- [ ] Aerospike latency metric visible

**Demo Scenarios (Must Work End-to-End)**
- [ ] Attack 1: Hidden-text-in-invoice prompt injection → real LLM payment agent genuinely manipulated → Forensics detects → NO-GO → prediction errors extracted → scoring function generated and deployed
- [ ] Attack 2: Agent identity spoofing → different vector, no adversarial content → hardcoded rules DON'T catch it → generated scoring function catches it via compound behavioral signals → NO-GO with attribution "Blocked by Generated Rule #001 (from invoice attack, deployed Xs ago)"
- [ ] Evolution: Both attacks confirmed → scoring function refines using prediction errors from both → system's detection model gets denser

**Sponsor Integrations (Judges Present)**
- [ ] Aerospike: real persistent storage for episodes, prediction errors, rule registry, baselines, attribution chains — latency visible on dashboard
- [ ] Bland AI: live voice session, barge-in, natural language Q&A grounded in actual anomaly scores and rule attribution
- [ ] AWS: deployed on EC2/ECS, mentioned in architecture narrative

### Out of Scope

- Fine-tuning / model weight updates — rule generation via executable Python is the learning mechanism; model weights are not modified
- Multi-tenant / SaaS deployment — single operator context for hackathon
- Non-payment agent supervision — architecture generalizes but demo uses payments for clarity
- Stablecoin / on-chain rails — standard fiat wire transfers only (universally understood, no explanation needed)
- Mobile / native app — web dashboard only
- Okta identity verification — cut for timeline; mention in Q&A if asked about operator authentication
- Airbyte data sync — pre-load fixtures; mention Airbyte as production integration if asked
- Attack vectors beyond the 4 specified — prompt injection, data poisoning, confidence manipulation, cross-agent deception are the demo surface

## Context

**Hackathon:** AWS Deep Agents Hackathon — theme "Build agents that plan, reason, and execute across complex multi-step tasks autonomously." Judged by representatives from AWS (3), Bland AI (2), Aerospike (3), TrueFoundry (1), plus payments/AI domain experts. Judges from sponsor companies will be evaluating their own integrations. Alacriti judge (payments domain) validates the use case directly.

**Positioning:** Sentinel is positioned as **autonomous agent security** — runtime defense against compromised, manipulated, or malfunctioning AI agents. Payments are the demo scenario, not the product category. The competitive gap: existing AI security products (Straiker, Lakera, NeMo, Zenity) filter inputs/outputs or monitor behavior. None generate inspectable detection rules from incidents that catch novel attacks. None treat the agent itself as the potentially compromised entity.

**Demo arc (3 minutes):** Attack 1 (0:00–1:15) → real LLM agent gets prompt-injected, Sentinel investigates, blocks, shows prediction errors. Rule generation (1:15–1:45) → operator confirms, scoring function generated, readable Python on screen. Attack 2 (1:45–2:30) → different attack, hardcoded rules don't catch it, generated rule fires, attribution chain shown. Evolution (2:30–2:45) → rule refines after second confirmation. Voice Q&A (2:45–3:00) → "Why was this blocked?" with grounded answer.

**The generalization claim:** A scoring function written from a vision/document attack (invoice hidden text) catches an inter-agent trust attack (fake KYC pre-clearance). Different attack surface, identical behavioral fingerprint: overconfident agent whose claims evaporate under independent scrutiny.

**Key architectural invariant:** The block decision is an if-statement. No LLM in the enforcement path. LLMs investigate and generate rules; pure Python enforces them. Fully auditable.

**Learned rules are additive only.** Generated rules can never modify or remove hardcoded rules. The system cannot learn itself into a weaker state.

**Rule generation prompt must be tested 30+ times in isolation** before wiring into the loop.

## Constraints

- **Timeline**: 72 hours, solo — build priority order from spec must be followed ruthlessly; voice is post-core
- **Tech Stack**: Python/FastAPI backend, React frontend, Claude API (Opus 4.6 for Supervisor, Sonnet 4.6 for sub-agents and Payment Agent), Aerospike, Bland AI webhooks
- **Safety Gate**: Must use deterministic Python exec() for generated rules — no LLM in the enforcement decision path; this is an explicit architectural invariant and a judge talking point
- **Demo reliability**: The self-improvement loop (incident 1 → rule generation → incident 2 → rule fires → rule evolves) must be bulletproof before any polish work begins; fallback = text narration if voice fails
- **Aerospike**: Real persistent storage required — 3 Aerospike judges; latency must be visible on dashboard
- **Bland AI**: Real voice required — 2 Bland AI judges; fallback to text-on-dashboard only if SDK proves intractable in timeline

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Deterministic Python Safety Gate (no LLM enforcement) | The block decision is an if-statement; can't be prompt-injected; fully auditable | — Pending |
| Generated rules = composite scoring functions (weighted, not binary) | Individually weak signals compound; more nuanced than pass/fail predicates | — Pending |
| Payment Agent is a real LLM (Sonnet 4.6), not hardcoded | Demo credibility: agent is genuinely manipulated, not scripted | — Pending |
| Prediction step before investigation | System forms expectations from baselines; prediction error is the learning signal for rule generation | — Pending |
| Rule evolution across multiple incidents | Rules refine after second confirmed incident; drops artifacts, strengthens common signals | — Pending |
| Cybersecurity-first framing, payments as use case | Broader competitive positioning; "autonomous agent security" not "payment fraud" | — Pending |
| Sub-agents run in parallel via asyncio.TaskGroup | Independent investigations; structured concurrency with automatic cleanup | — Pending |
| Okta cut from scope | Timeline pressure; not a judge differentiator; mention in Q&A | — Decided |
| Rule generation prompt tested 30+ times before wiring | Most failure-prone component; demo depends on reliable generalization | — Pending |
| Aerospike for episodic memory (not Postgres) | 3 Aerospike judges; real integration required for credibility | — Pending |

## Competitive Position

| What Exists | What Sentinel Does Differently |
|---|---|
| Straiker, Lakera: runtime I/O filtering | Sentinel inspects the full reasoning chain against external ground truth |
| Darktrace: self-learning adaptive models | Sentinel's rules are readable Python with provenance, not opaque model updates |
| SOAR platforms: playbook refinement | Sentinel's loop is autonomous — no human analyst writing detection rules |
| Guardrails AI, NeMo: single-pass filters | Three parallel independent investigators, each checking different dimensions |
| Featurespace, Feedzai: payment fraud ML | Sentinel monitors AI agent decision chains, not human behavior |
| Nobody: auto-generated inspectable detection rules for AI agents | This is unoccupied — the core differentiator |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-03-26 — Phase 02 complete, core investigation pipeline validated live*
