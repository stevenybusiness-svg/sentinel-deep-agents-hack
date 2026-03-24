# Feature Research

**Domain:** Multi-agent AI supervision system for autonomous financial payments (hackathon demo context)
**Researched:** 2026-03-24
**Confidence:** MEDIUM-HIGH (stack-specific claims HIGH from docs; hackathon strategy claims MEDIUM from community sources; novelty claims MEDIUM from multiple sources cross-checked)

---

## Feature Landscape

### Table Stakes (Judges Expect These — Missing = Demo Fails)

These are non-negotiable. Judges from the payments domain, AWS, and AI safety will penalize hard for missing any of these. They do not award points for having them.

| Feature | Why Expected | Complexity | Demo Risk | Notes |
|---------|--------------|------------|-----------|-------|
| End-to-end working demo | Judges see 3-5 minutes; a broken demo scores near zero regardless of architecture | HIGH | CRITICAL | Must be bulletproof before any polish work; no partial credit for "almost works" |
| Real audit trail / decision log | Financial regulators require full provenance on every autonomous decision; judges from payments domain (Alacriti) will ask for this immediately | MEDIUM | HIGH | Every GO/NO-GO must show what agent said what, when, why |
| Visible attribution chain | "Which agent blocked this and why?" — missing this makes the system look like a black box; judges cannot evaluate what they cannot see | MEDIUM | HIGH | Field-level match/mismatch table is the minimum; must show per-agent contributions |
| Hardcoded safety baseline | Any agentic system in finance with no floor rules is immediately dismissed as unsafe; regulators and enterprise buyers require rules that LLMs cannot override | LOW | MEDIUM | Must exist before generated rules layer on top; "learned rules are additive only" is the correct invariant |
| Multi-agent parallelism | The hackathon theme is "plan, reason, execute across complex multi-step tasks." A single-agent pipeline fails the theme; parallel sub-agents are expected for credibility | HIGH | MEDIUM | Risk + Compliance + Forensics must run simultaneously, not sequentially |
| Persistent storage with visible latency | 3 Aerospike judges. A mock/in-memory store would be noticed instantly and would crater credibility with 3 of the most important judges in the room | MEDIUM | CRITICAL | Latency must be visible on dashboard — e.g., "written to Aerospike in 4ms" |
| LLM separation from enforcement | Deterministic Python enforcement is now an industry expectation for any system claiming auditability. "The LLM generates rules; Python enforces them" is the correct and expected architecture | MEDIUM | MEDIUM | The "no LLM in the enforcement path" invariant is both correct and a judge talking point |
| Real voice integration | 2 Bland AI judges. A simulated voice or text-only fallback destroys credibility with them. Voice must actually work, even if simple | HIGH | CRITICAL | Fallback plan essential; see anti-features section |
| Explainable blocking decision | "Why was this blocked?" must have a human-readable answer within 10 seconds. Financial compliance demands it; judges will ask it | LOW | MEDIUM | Natural language synthesis from verdict board fields; not just a confidence score |

### Differentiators (Competitive Advantage — What Makes Sentinel Stand Out)

These are the features that separate Sentinel from generic "AI safety" hackathon submissions. Each one is genuinely novel or rare in 2025.

| Feature | Value Proposition | Complexity | Demo Risk | Novelty Level | Notes |
|---------|-------------------|------------|-----------|---------------|-------|
| Cross-surface behavioral generalization | A rule learned from a document attack (hidden invoice text) catches an inter-agent trust attack (spoofed KYC). Different mechanism, identical behavioral signature. This is the core "wow" moment | VERY HIGH | HIGH | HIGH — most self-learning systems learn to detect what they already saw | The single most differentiating feature. Must work reliably. "The system didn't learn to detect hidden text. It learned to detect when an agent is lying." |
| Live rule code visibility panel | The generated Python function is readable, attributed to its source episode, and shown on screen in real time. Judges can read the rule the system wrote | MEDIUM | LOW | MEDIUM — "Rule Maker Pattern" is emerging practice in 2025 but rare in hackathon demos | Makes the self-improvement loop auditable rather than magical. Directly addresses "black box" objection |
| Trust score collapse animation | Watching a trust score go from 0.85 to 0.25 in real time during investigation communicates risk quantification viscerally. No explanation needed | MEDIUM | LOW | LOW (visual novelty) — but HIGH execution value in demo | Pure demo theater but strategically placed: it gives judges a shared language for what's happening |
| Voice-interrogable investigation | Operator asks "Why did you block that?" and gets a natural language answer grounded in the actual verdict board fields — not a canned response | HIGH | HIGH | MEDIUM — conversational AI explanation is common; grounding it in live structured data is less common | Bland AI judges will evaluate this directly. Must be genuinely responsive to the actual investigation, not scripted |
| Episodic memory across incidents | The system remembers what it learned from incident 1 when evaluating incident 2, with full provenance. "Blocked by Generated Rule #001 (from invoice attack, deployed 90s ago)" | HIGH | MEDIUM | HIGH — most agent systems have per-session context only; cross-episode persistence is rare in demos | Aerospike integration makes this concrete. The "deployed 90s ago" attribution is the proof-of-memory moment |
| Forensic side-by-side visualization | Clean invoice vs. forensic scan with hidden text highlighted in red — judges can see exactly what the adversary hid and exactly what the vision model found | MEDIUM | LOW | LOW-MEDIUM — document forensics is established; live side-by-side in a demo is rare | Pure visual impact. Requires a real adversarial document fixture, not a synthetic one |
| Override identity verification gate | Operator override requires Okta token introspection before taking effect. Closes the "what stops a bad operator?" objection | LOW-MEDIUM | LOW | MEDIUM — Okta integration exists; pairing it with agent supervision is novel | 30-minute implementation. Strong compliance signal for financial domain judges |
| Additive-only rule architecture | The system cannot learn itself into a weaker state. Generated rules can never modify or delete hardcoded rules. This is a principled safety invariant, not a constraint | LOW | LOW | MEDIUM — few hackathon systems have explicit safety monotonicity | Translates directly into regulatory language: "the system's safety posture can only improve over time" |

### Anti-Features (Deliberately Exclude in 72 Hours)

These look useful but will kill the demo, eat the timeline, or both.

| Anti-Feature | Why Requested | Why Problematic in This Context | Alternative |
|--------------|---------------|--------------------------------|-------------|
| Voice as primary UI path | Impressive in theory; Bland AI judges love it | Barge-in failures add 300-500ms; ambient noise causes false triggers; latency spikes cause "AI keeps talking after being interrupted" failures; demo environment has unknown acoustics | Voice as supplementary Q&A layer only. Dashboard is always the primary visualization. Fallback to dashboard text if voice fails |
| Fine-tuning / weight updates as "learning" | Sounds like a more powerful form of learning | Requires GPU infrastructure, training pipelines, evaluation frameworks, and days not hours. Demo cannot show "learning happened" in 90 seconds | Python rule generation is demonstrably faster, fully readable, and more auditable than weight updates. Frame it correctly: "rules, not weights, because rules are auditable" |
| Multi-tenant / role-based access | Real enterprise systems have it | Adds 6-10 hours of auth scaffolding for zero demo value. No judge will test multi-tenancy in a 3-minute demo | Single operator context. Mention "production would add RBAC" if asked |
| On-chain / stablecoin rails | Crypto judges find it interesting | Fiat wire transfers are universally understood as irreversible. Judges know you cannot undo a wire. Stablecoins require 2 minutes of explanation before the demo starts | Standard fiat wire. Irreversibility is the key intuition — all judges already have it |
| Attack vector expansion beyond 4 specified | More attack types = more comprehensive | Each new attack vector requires a new fixture, a new demo branch, and new failure modes. 4 attack types with 2 demonstrated is the right scope for 72 hours | Hidden text + spoofed KYC covers document forgery AND inter-agent deception — that's two categories with one demo arc |
| Real-time streaming token output | Visible LLM "thinking" looks dynamic | Streaming adds frontend complexity, can cause layout thrash during demo, and focuses attention on LLM verbosity rather than investigation results | Show investigation progress via node activation in the tree (discrete states: pending → active → complete), not token streams |
| Explanations from a separate "explanation agent" | More modular | Adds a 4th LLM call in the critical path; increases latency; can contradict the verdict board if not carefully grounded | Supervisor synthesizes explanation from the verdict board directly. One source of truth. |
| Polling-based dashboard updates | Simpler to implement | Visible refresh lag during live demo destroys immersion. Judges will see the "loading..." state mid-demo | WebSocket or SSE for all live state updates. React state should update sub-second |
| Airbyte sync during demo | Shows a real data pipeline | Airbyte sync requires running infrastructure; if it fails mid-demo, it blocks the investigation. Airbyte is a setup-time tool, not a demo-time tool | Pre-load fixtures. Mention "Airbyte syncs the counterparty DB on schedule; fixtures were loaded before this demo" |

---

## Feature Dependencies

```
[Safety Gate — deterministic Python enforcement]
    └──requires──> [Verdict Board Engine — structured fields to evaluate]
                       └──requires──> [Sub-agent investigations — Risk, Compliance, Forensics]
                                          └──requires──> [Supervisor Agent — dispatches and synthesizes]
                                                             └──requires──> [Payment Agent — produces claims to investigate]

[Self-Improvement Loop]
    └──requires──> [Safety Gate] (generates rules for it)
    └──requires──> [Episode storage — Aerospike] (persists rule source with provenance)
    └──requires──> [Verdict Board Engine] (rules operate only on verdict board fields)

[Episodic Memory]
    └──requires──> [Aerospike] (real persistent storage)
    └──enhances──> [Safety Gate] (loads generated rules at startup)
    └──enhances──> [Trust posture] (loads behavioral baselines)

[Voice Q&A — Bland AI]
    └──requires──> [Supervisor Agent reasoning] (must have something to explain)
    └──enhances──> [Dashboard] (mirrors voice answers as text)
    └──conflicts──> [Demo reliability] (see anti-features — fallback required)

[Forensic side-by-side visualization]
    └──requires──> [Forensics Agent] (must complete scan before display)
    └──requires──> [Adversarial fixture] (real hidden-text document, prepared pre-demo)

[Override identity verification — Okta]
    └──requires──> [Voice interface] (override command comes via voice)
    └──requires──> [Okta token introspection endpoint] (~30 min setup)
```

### Dependency Notes

- **Safety Gate requires Verdict Board Engine:** Rules evaluate structured fields (amount_match, beneficiary_match, etc.), not free text. The field-level comparison must exist before rule generation makes sense.
- **Self-Improvement Loop requires Verdict Board:** Generated rules are behavioral functions over verdict board fields. This is the explicit architectural constraint that makes generalization possible — same behavioral signature, different attack surface.
- **Voice conflicts with Demo Reliability:** Barge-in detection has known failure modes in unfamiliar acoustic environments. The dependency is acceptable only with a dashboard fallback. Never demo with voice as the only path to showing investigation results.
- **Episodic memory enhances Safety Gate:** At investigation start, the gate loads persisted generated rules from Aerospike. This is what makes "Rule #001 blocked this" attribution possible for incident 2.

---

## MVP Definition (72-Hour Solo Build)

### Must Ship (Demo Fails Without These)

- [ ] Payment Agent → Supervisor → [Risk + Compliance + Forensics in parallel] → Verdict Board → Safety Gate pipeline
- [ ] Hidden-text-in-invoice fixture and Forensics detection (Phase 1 demo)
- [ ] Spoofed-KYC-agent fixture and generated rule catch (Phase 2 demo — the generalization proof)
- [ ] Rule generation from confirmed incident: Python function written to Aerospike, loaded back into gate
- [ ] Live investigation tree with node activation (dashboard centerpiece)
- [ ] Verdict board comparison table with match/mismatch/unable-to-verify visualization
- [ ] Generated rule source panel showing readable Python with provenance
- [ ] Trust score collapse animation (0.85 → 0.25) with GO/NO-GO gate decision
- [ ] Aerospike writes visible as latency on dashboard
- [ ] Bland AI voice Q&A answering "Why did you block that?" with grounded natural language

### Add If Time Permits (v1.x — after core loop is bulletproof)

- [ ] Okta override identity verification (30 min; strong compliance demo signal)
- [ ] Forensic side-by-side visualization (adds visual impact for Phase 1)
- [ ] Decision log scrolling panel with full attribution trail
- [ ] Voice barge-in / interruption support (risky — only if Bland AI integration is solid)
- [ ] Airbyte pre-load confirmation message ("KYC data synced via Airbyte at 09:14")

### Defer to Post-Hackathon (v2+)

- [ ] Multi-tenant RBAC
- [ ] Attack vector expansion beyond 4 specified
- [ ] Production-grade Aerospike cluster (single node is fine for demo)
- [ ] Streaming token output / real-time LLM thinking display
- [ ] Fine-tuning or model weight update learning loop

---

## Feature Prioritization Matrix (Demo Impact vs. Implementation Cost)

| Feature | Judge Impact | Build Cost (72h) | Priority | Demo Risk |
|---------|--------------|-----------------|----------|-----------|
| Phase 1 + Phase 2 demo arc (end-to-end) | CRITICAL | HIGH | P0 — build first | CRITICAL |
| Generalization proof (rule #001 catches different attack) | CRITICAL | HIGH | P0 — test rule generation 30+ times before wiring | HIGH |
| Aerospike episode + rule persistence with visible latency | HIGH (3 judges) | MEDIUM | P1 | LOW |
| Bland AI voice Q&A grounded in verdict board | HIGH (2 judges) | MEDIUM-HIGH | P1 — with fallback | HIGH |
| Investigation tree live animation | HIGH (visual demo) | MEDIUM | P1 | LOW |
| Verdict board match/mismatch table | HIGH (compliance signal) | LOW-MEDIUM | P1 | LOW |
| Generated rule source panel | HIGH (auditability) | LOW | P1 | LOW |
| Trust score collapse animation | MEDIUM (theater) | LOW | P2 | LOW |
| Forensic side-by-side visualization | MEDIUM (Phase 1 impact) | MEDIUM | P2 | LOW |
| Okta override verification | MEDIUM (compliance story) | LOW (30 min) | P2 | LOW |
| Decision log panel | LOW-MEDIUM | LOW | P3 | LOW |
| Airbyte mention / fixture confirmation | LOW | VERY LOW | P3 | LOW |

**Priority key:**
- P0: Demo literally fails without this; build first, validate before moving on
- P1: Demo is substantially weaker without this; build after P0 is bulletproof
- P2: Adds meaningful points if time permits; cut if behind schedule
- P3: Polish / nice-to-have; skip unless everything else is done

---

## Competitor Feature Analysis (Hackathon Context)

Most multi-agent hackathon submissions in 2025 fall into predictable patterns. Understanding what others build helps position Sentinel's differentiators.

| Feature | Typical Hackathon Submission | Sentinel's Approach | Why Sentinel Wins |
|---------|------------------------------|---------------------|-------------------|
| Multi-agent coordination | Sequential pipeline: Agent A calls Agent B calls Agent C | Parallel dispatch: Risk + Compliance + Forensics simultaneously | Faster, more independent, can detect cross-agent disagreement |
| "Learning" | RAG over past cases, or none at all | Generates executable Python detection rules from confirmed incidents | Readable, attributed, zero inference latency at evaluation time |
| Auditability | Log output to a database | Verdict board with field-level comparison + rule source code readable on screen | Judges can literally read the rule the system wrote |
| Safety gate | LLM makes final enforcement decision | Deterministic Python `exec()` enforces rules — no LLM in enforcement path | Regulatory-grade; cannot be hallucinated through |
| Demo story | "Here's a feature" → "Here's another feature" | Phase 1 attack → rule generated → Phase 2 different attack → same rule fires | Narrative arc with a payoff moment; judges remember it |
| Voice | Optional chatbot or none | Live bidirectional voice answering grounded Q&A about live investigation | Bland AI judges see genuine integration, not an afterthought |
| Cross-incident memory | Session context only | Aerospike-persisted episodes: "Blocked by Rule #001 deployed 90 seconds ago" | Proof of persistent learning visible in real time |

---

## What Hackathon Judges Actually Care About (Research Finding)

Based on analysis of winning submissions across Microsoft AI Agents Hackathon 2025, Kong Agentic AI Hackathon, and Global Agent Hackathon:

**Top 3 scoring differentiators (in order):**
1. **Working demo with clear reasoning shown** — "Show your reasoning, not just your output." Judges follow the logic from signals to decisions to actions. A demo that shows *why* a decision was made scores higher than one that only shows the decision.
2. **Real-world impact story** — "Technical sophistication without human relevance is just expensive showing off." The irreversible wire transfer framing does this: judges understand stakes immediately.
3. **Effective use of sponsor technologies** — With 8 sponsor judges in the room, every real integration scores directly. Mock integrations (or integrations that fail during demo) hurt more than not having them.

**What loses despite technical quality:**
- Architecture explanation without a demo payoff moment
- Features that work individually but not in sequence
- Demos where voice/audio fails and there is no fallback path

---

## Financial Compliance Features: What to Visually Demonstrate

Based on research into financial AI agent compliance requirements (EU AI Act, FATF, PCI DSS, Gramm-Leach-Bliley):

**Regulatorily expected capabilities to visually prove:**
1. **Full decision provenance** — every blocking decision attributed to specific agent findings, not aggregate confidence
2. **Human override path** — operator can override, but override requires identity verification (Okta gate satisfies this)
3. **Immutable audit log** — decisions written once, not modifiable (Aerospike append pattern)
4. **Independent verification** — Compliance Agent cross-checks claims against KYC ledger independently of Payment Agent (this is the architecture)
5. **Explainable blocking reason** — "Amount mismatch: agent claimed $12,000, document shows $120,000" not just "confidence: 0.25"

The dashboard must make these visible. Judges from the payments domain (Alacriti) will look for exactly these signals as proof the system could pass a regulatory audit.

---

## Self-Learning Novelty Assessment (2025)

| Learning Pattern | Novelty Level | Status in 2025 |
|-----------------|---------------|----------------|
| RAG over past incidents | NONE | Standard practice; table stakes |
| Fine-tuning on observed data | LOW | Common; infrastructure-heavy |
| Prompt evolution (Darwin Gödel Machine) | HIGH | Research-stage; not production |
| Generated executable rules (Rule Maker Pattern) | MEDIUM-HIGH | Emerging practice; rare in demos |
| Cross-surface behavioral generalization | HIGH | Novel claim; must be demonstrated live |
| Additive-only rule architecture (safety monotonicity) | HIGH | No widely-known precedent in production systems |

Sentinel's combination of (1) executable rule generation + (2) cross-surface generalization + (3) additive-only safety invariant is genuinely novel as a packaged claim. The individual components are not new. The combination — and the live demonstration that a rule from attack type A catches attack type B — is what makes the claim defensible and memorable.

**Confidence on novelty claim:** MEDIUM — the generalization demonstration depends on the rule generation prompt being robust enough to produce behavioral rather than mechanistic rules. This is the highest-risk single component. The PROJECT.md note about testing rule generation 30+ times in isolation is correct and critical.

---

## Voice Interface Patterns: What Works vs. What Breaks in Live Demos

### Patterns That Work

| Pattern | Why It Works | Implementation Notes |
|---------|--------------|---------------------|
| Scripted Q&A trigger ("Why did you block that?") | Predictable input → predictable output path; can be tested exhaustively pre-demo | Pre-test 10+ variations of this question in demo acoustic environment |
| Voice as Q&A supplement to dashboard (not replacement) | Dashboard never fails; voice adds richness without being load-bearing | Dashboard shows all answers; voice reads them aloud in natural language |
| Explicit "I'm asking the Supervisor" framing | Sets judge expectations; they know to listen for an answer | Visual indicator that voice session is active |
| Grounded answers from structured data | Supervisor reads from verdict board fields; not free LLM generation | Answers cannot contradict what the dashboard shows |

### Patterns That Break in Live Demos

| Pattern | Failure Mode | Risk Level |
|---------|--------------|------------|
| Barge-in during complex sentence | AI continues speaking 2-3 seconds after interruption; then responds to interruption; feels broken | HIGH in conference room noise |
| Voice as primary path to critical information | If voice fails, judges miss the key moment | CRITICAL — never rely on voice alone |
| Ambient noise triggering false barge-in | System interrupts itself; ASR processes its own TTS output | HIGH in demo environments |
| Long voice responses (>15 seconds) | Judges lose thread; attention drifts back to dashboard | MEDIUM |
| Override command via voice without visual confirmation | If voice mishears "override", could trigger unexpected flow | HIGH — require explicit visual confirmation step |

**Recommended voice strategy for Sentinel:** Use Bland AI for Q&A only. Voice session activates after investigation completes (Phase 3, 2:30–3:00). Keep voice responses under 10 seconds. Show text transcript on dashboard simultaneously. Fallback: "Voice is being demonstrated on request — for reliability during this demo, answers are also visible on the dashboard."

---

## Sources

- [AI Agents Hackathon 2025 — Microsoft Community Hub Winners Showcase](https://techcommunity.microsoft.com/blog/azuredevcommunityblog/ai-agents-hackathon-2025-%E2%80%93-category-winners-showcase/4415088) — winning patterns, MEDIUM confidence
- [Galileo — AI Agent Compliance & Governance in 2025](https://galileo.ai/blog/ai-agent-compliance-governance-audit-trails-risk-management) — compliance features, MEDIUM confidence
- [AI Transaction Monitoring Complete Guide 2025](https://www.ir.com/guides/ai-transaction-monitoring-and-how-it-works-complete-guide-2025) — financial monitoring requirements, MEDIUM confidence
- [The Rule Maker Pattern — tessl.io](https://tessl.io/blog/the-rule-maker-pattern/) — deterministic execution separation, HIGH confidence (verified against multiple sources)
- [Optimizing Voice Agent Barge-In Detection for 2025 — sparkco.ai](https://sparkco.ai/blog/optimizing-voice-agent-barge-in-detection-for-2025) — voice failure modes, HIGH confidence
- [Bland AI Review 2025 — Retell AI](https://www.retellai.com/blog/bland-ai-reviews) — Bland AI reliability issues, MEDIUM confidence
- [AI Agent Observability — IBM Think](https://www.ibm.com/think/insights/ai-agent-observability) — observability features, HIGH confidence
- [Agentic AI Maturity Model 2025 — DextraLabs](https://dextralabs.com/blog/agentic-ai-maturity-model-2025/) — self-learning maturity levels, MEDIUM confidence
- [How to Win an AI Hackathon — Klaviyo Engineering / Medium](https://klaviyo.tech/how-to-win-an-ai-hackathon-build-a-solution-that-actually-matters-aab49307587e) — judging strategy, MEDIUM confidence
- [How to Present a Successful Hackathon Demo — Devpost](https://info.devpost.com/blog/how-to-present-a-successful-hackathon-demo) — demo patterns, MEDIUM confidence
- [AI Agent Technical Architecture in Financial Payment Systems — Intellectyx](https://www.intellectyx.com/ai-agent-technical-architecture-in-financial-payment-systems-for-real-time-fraud-detection/) — payment agent features, MEDIUM confidence
- [Agentic Payments Revolution — Galileo FT](https://www.galileo-ft.com/blog/agentic-payments-secure-ai-banks-fintechs/) — compliance integration patterns, MEDIUM confidence

---

*Feature research for: Sentinel — multi-agent AI supervision system for autonomous financial payments*
*Researched: 2026-03-24*
