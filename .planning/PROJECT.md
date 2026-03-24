# Sentinel

## What This Is

Sentinel is a runtime multi-agent supervision system for autonomous payment agents. It investigates payment actions in real time using three parallel sub-agents (Risk, Compliance, Forensics), blocks irreversible transfers when agent behavior can't be independently verified, and generates executable Python detection rules from confirmed incidents — so the next attack it catches can be one it has never seen before. Built for the AWS Deep Agents Hackathon (72-hour solo build, deadline ~2026-03-27).

## Core Value

The self-improvement loop: a rule learned from one attack type must demonstrably catch a completely different attack — live, on stage, in 3 minutes.

## Requirements

### Validated

(None yet — ship to validate)

### Active

**Core Investigation Pipeline**
- [ ] Payment Agent processes a payment request and returns a structured verdict (amount, beneficiary, account, confidence, steps taken, claims made)
- [ ] Supervisor Agent (Opus 4.6) builds investigation tree, dispatches Risk/Compliance/Forensics in parallel, synthesizes verdict board
- [ ] Risk Agent computes confidence z-score against behavioral baseline and detects step-sequence deviations
- [ ] Compliance Agent cross-validates claims against independent authoritative sources (KYC ledger, agent activity log)
- [ ] Forensics Agent independently scans document inputs for adversarial content using vision model; extracts actual field values for comparison
- [ ] Verdict Board Engine performs deterministic field-level comparison between payment agent claims and investigator findings (match/mismatch/unable-to-verify — no float math)
- [ ] Safety Gate applies hardcoded rules first, then executes generated Python rules from registry; outputs GO/NO-GO/ESCALATE with full attribution

**Self-Improvement Loop**
- [ ] On operator-confirmed attack, Supervisor sends verdict board + mismatches to Opus 4.6 for Python detection rule generation
- [ ] Generated rule is behavioral (describes pattern, not mechanism) and operates only on verdict board fields
- [ ] Generated rule is exec()'d into Safety Gate rule registry with full provenance (episode ID, timestamp, attack type)
- [ ] Generated rule fires on next incident with matching behavioral pattern, regardless of attack mechanism
- [ ] Rule source code is stored and readable — not a black box

**Episodic Memory (Aerospike)**
- [ ] Episode records written after each incident resolution (verdict board, gate decision, operator confirmation, generated rule source)
- [ ] Context store (trust postures, learned rules, behavioral baselines) queried at investigation start
- [ ] All decisions logged with full provenance and attribution (<5ms write latency)

**Voice Interface (Bland AI)**
- [ ] Supervisor answers operator questions in plain language via real-time bidirectional voice (Bland AI)
- [ ] Barge-in/interruption supported — operator can redirect mid-sentence
- [ ] Override command triggers identity verification flow before accepting
- [ ] Supervisor explains its reasoning in natural language ("Why did you block that?")

**Dashboard**
- [ ] Live investigation tree — nodes light up as sub-agents activate, new rule nodes appear after learning
- [ ] Verdict board comparison table — field-level match/mismatch visualization with severity tags
- [ ] Forensic scan side-by-side — clean invoice view vs. forensic scan with hidden text highlighted in red
- [ ] Generated rule source panel — readable Python that the system wrote, with provenance
- [ ] Trust score collapse animation (0.85 → 0.25) and gate decision displayed prominently
- [ ] Decision log with full attribution trail

**Demo Scenarios (Must Work End-to-End)**
- [ ] Phase 1: Hidden-text-in-invoice attack → Forensics detects → NO-GO → Rule #001 generated and deployed
- [ ] Phase 2: Agent identity spoofing attack → No hardcoded rule fires → Rule #001 catches it → NO-GO with attribution "Blocked by Generated Rule #001 (from invoice attack, deployed 90s ago)"

**Sponsor Integrations (Judges Present)**
- [ ] Aerospike: real persistent storage for episode records, verdict boards, rule source, trust postures, audit trail — latency visible on dashboard
- [ ] Bland AI: live voice session, barge-in, natural language Q&A about investigation decisions
- [ ] AWS: deployed on EC2/ECS, mentioned in architecture narrative
- [ ] Okta: token introspection for override identity verification (option 1 — ~30 min implementation)
- [ ] Airbyte: Google Sheet → counterparty DB + KYC ledger sync (if time permits; otherwise pre-load fixtures)

### Out of Scope

- Fine-tuning / model weight updates — rule generation via Python function is the learning mechanism; model weights are not modified
- Multi-tenant / SaaS deployment — single operator context for hackathon
- Non-payment agent supervision — architecture is payment-specific for demo clarity
- Stablecoin / on-chain rails — standard fiat wire transfers only (universally understood, no explanation needed)
- Mobile / native app — web dashboard only
- Attack vectors beyond the 4 specified — prompt injection, data poisoning, confidence manipulation, cross-agent deception are the demo surface; no expansion during hackathon

## Context

**Hackathon:** AWS Deep Agents Hackathon — theme "Build agents that plan, reason, and execute across complex multi-step tasks autonomously." Judged by representatives from AWS (3), Bland AI (2), Aerospike (3), TrueFoundry (1), plus payments/AI domain experts. Judges from sponsor companies will be evaluating their own integrations. Alacriti judge (payments domain) validates the use case directly.

**Demo arc (3 minutes):** Phase 1 (0:00–1:15) → hidden text attack, Forensics catches it, rule generated. Phase 2 (1:15–2:30) → spoofed KYC agent, no hardcoded rule fires, generated rule catches it, attribution shown. Phase 3 (2:30–3:00) → voice Q&A + override with Okta identity verification. The critical moment: "The system didn't learn to detect hidden text. It learned to detect when an agent is lying."

**The generalization claim:** A rule written from a vision/document attack (invoice hidden text) must catch an inter-agent trust attack (fake KYC pre-clearance). Different attack surface, identical behavioral signature: confident agent whose claims evaporate under independent scrutiny.

**Key architectural invariant:** The Safety Gate is deterministic Python — no LLM in the enforcement path. LLMs investigate and generate rules; pure Python enforces them. Fully auditable for judges/regulators.

**Learned rules are additive only.** Generated rules can never modify or remove hardcoded rules. The system cannot learn itself into a weaker state.

**Rule generation prompt must be tested 30+ times in isolation** before wiring into the loop. The most failure-prone single component — do this before building anything on top of it.

## Constraints

- **Timeline**: 72 hours, solo — build priority order from spec must be followed ruthlessly; voice + Okta + Airbyte are post-core
- **Tech Stack**: Python/FastAPI backend, React frontend, Claude API (Opus 4.6 for Supervisor, Sonnet 4.6 for sub-agents), Aerospike, Bland AI webhooks, HTML5 Canvas animation (per design guide)
- **Safety Gate**: Must use deterministic Python exec() for generated rules — no LLM in the enforcement decision path; this is an explicit architectural invariant and a judge talking point
- **Demo reliability**: The self-improvement loop (incident 1 → rule generation → incident 2 → rule fires) must be bulletproof before any polish work begins; fallback = text narration if voice fails
- **Aerospike**: Real persistent storage required — 3 Aerospike judges; latency must be visible on dashboard
- **Bland AI**: Real voice required — 2 Bland AI judges; fallback to text-on-dashboard only if SDK proves intractable in timeline

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Deterministic Python Safety Gate (no LLM enforcement) | Auditability for judges/regulators; LLMs investigate, Python enforces — clean separation | — Pending |
| Generated rules = executable Python functions | Readable by judges, attributed to source episode, zero inference latency at evaluation time | — Pending |
| Sub-agents run in parallel | Independent investigations, not sequential; supervision must not add more latency than the pipeline itself | — Pending |
| Standard fiat wire transfers (not stablecoin) | Universally understood — judges know you can't undo a wire; no time explaining on-chain finality | — Pending |
| Rule generation prompt tested 30+ times before wiring | Most failure-prone component; demo depends on reliable generalization | — Pending |
| Aerospike for episodic memory (not Postgres) | 3 Aerospike judges; real integration required for credibility | — Pending |
| Okta option 1 (token introspection, not Device Auth flow) | ~30 min implementation, sufficient for demo; visual option 2 if time permits | — Pending |

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
*Last updated: 2026-03-24 after initialization*
