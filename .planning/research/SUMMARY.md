# Project Research Summary

**Project:** Sentinel — Runtime Security for Autonomous AI Agents
**Domain:** Autonomous agent security / runtime defense / AI threat detection (payments as demo scenario)
**Researched:** 2026-03-24, updated after competitive analysis (20+ products evaluated)
**Confidence:** MEDIUM-HIGH

## Executive Summary

Sentinel is a runtime security system for autonomous AI agents. It intercepts agent actions at the execution boundary, dispatches three independent AI investigators to adversarially verify the agent's claims against ground truth, and blocks actions that can't be confirmed. The core threat model: the AI agent itself is the compromised entity — prompt-injected via documents, socially engineered by other agents, or hallucinating with high confidence. Existing guardrails (Lakera, Straiker, NeMo, Guardrails AI) filter inputs and outputs but trust the agent's reasoning. Sentinel doesn't.

The central demo payoff is the self-improvement loop: after confirming an attack, the system extracts prediction errors (where its expectations diverged from reality), generates a composite scoring function (inspectable Python, not a black box), validates it, deploys it, and catches the next attack — even with a completely different attack vector — because compromised agents exhibit the same behavioral fingerprint. After a second confirmed incident, the scoring function evolves: drops conditions that were artifacts of one attack, strengthens signals present in both. No existing product does this: Darktrace updates opaque models; SOAR platforms require human analysts; Sentinel autonomously writes readable, testable, attributable detection rules.

**Competitive position (validated March 2026):** The AI agent security market is exploding (Straiker, Lakera→Check Point, Zenity, HiddenLayer, Cisco AI Defense, NVIDIA NeMo). But no product generates inspectable detection rules from incidents that catch novel attacks. No product treats the agent as the potentially compromised entity with adversarial verification. No product provides composite anomaly scoring where individually weak signals compound. This is the unoccupied niche.

The recommended approach is a Python/FastAPI backend with AsyncAnthropic SDK, Aerospike for persistent storage, @xyflow/react for the dashboard, and Bland AI for voice Q&A. The payment agent is a real Sonnet 4.6 LLM (not hardcoded) that gets genuinely manipulated. The block decision is an if-statement — no LLM in the enforcement path.

The most significant risks remain: (1) Claude API rate limits at Tier 1; (2) the scoring function generation prompt (30+ isolation tests required); (3) Bland AI webhook latency. Okta has been cut from scope for timeline reasons.

## Key Findings

### Recommended Stack

The backend is Python 3.11+ with FastAPI 0.115.x and `AsyncAnthropic` 0.86.0 as the core runtime. Python 3.11 is required (not merely recommended) because `asyncio.TaskGroup` provides structured concurrency semantics needed for parallel sub-agent dispatch — older `asyncio.gather()` is acceptable but TaskGroup is cleaner for exception handling. The Aerospike Python client (19.1.0) is synchronous-only (C-extension); all Aerospike calls must be wrapped in `loop.run_in_executor()` to avoid blocking FastAPI's async event loop. The frontend uses React 18 (not 19, which introduces breaking changes not worth debugging in 72 hours) with `@xyflow/react` 12.4.4 for the investigation tree node graph. Note the package was renamed from `reactflow` — mixing old and new package names causes duplicate React context errors.

**Core technologies:**
- Python 3.11 + FastAPI 0.115.x: Async HTTP and WebSocket server; asyncio.TaskGroup for parallel agent dispatch
- `anthropic` 0.86.0 (`[aiohttp]` extra): Official SDK; AsyncAnthropic shared client instance (never per-request); Opus 4.6 for Supervisor + RuleGenerator, Sonnet 4.6 for sub-agents
- `aerospike` 19.1.0: Persistent episode/rule/trust storage; synchronous C-extension requires `run_in_executor` wrapper in async context
- React 18 + `@xyflow/react` 12.4.4: Real-time investigation tree with animated edges; CSS transitions for node state changes
- `RestrictedPython` 8.2: Compile-time restriction for generated rule Python; always set explicit `__builtins__` allowlist in exec namespace
- `okta-jwt-verifier` 0.4.0 (or direct httpx introspection): Identity verification for operator override gate; ~30-minute integration
- Bland AI (REST + webhook): Outbound voice call initiation; synchronous webhook response within 8-second timeout budget

**What to avoid:** `asyncio.gather()` over TaskGroup for new code; `reactflow` (old package name); `aioaerospike` (archived Aug 2025); Socket.io; LangChain/LlamaIndex (obscures agent calls judges need to see); `eval()` for rule execution; `BaseJWTVerifier` (deprecated).

### Expected Features

Research identified a clear three-tier feature structure for a 72-hour hackathon build, driven by which sponsor judges are in the room (3 Aerospike, 2 Bland AI, 1 Alacriti payments) and what financial compliance requires.

**Must have (table stakes — demo fails without these):**
- End-to-end Phase 1 + Phase 2 demo arc (the generalization proof is the entire demo narrative)
- Live investigation tree with per-node activation states (pending/active/complete/flagged)
- Verdict board with field-level match/mismatch/unable-to-verify per agent
- Generated rule source panel showing readable Python with episode provenance
- Aerospike episode + rule writes with visible latency on dashboard (required for 3 Aerospike judges)
- Bland AI voice Q&A grounded in actual verdict board fields (required for 2 Bland AI judges)
- Hardcoded safety baseline (LLM-generated rules are additive only — this is the regulatory invariant)
- Multi-agent parallelism (sequential pipeline fails the hackathon theme)

**Should have (competitive differentiators):**
- Trust score collapse animation (0.85 → 0.25) — visceral risk communication, no explanation needed
- Forensic side-by-side visualization (clean invoice vs. annotated forensic scan)
- Okta override identity verification gate — closes "what stops a bad operator?" objection in ~30 minutes
- Decision log with full attribution trail — satisfies financial compliance provenance requirement
- Cross-surface behavioral generalization proof — the core novel claim; must be live, not described

**Defer to v2+:**
- Multi-tenant RBAC (zero demo value in 3-minute presentation)
- Attack vector expansion beyond the 4 specified
- Fine-tuning / weight-based learning (days not hours; also less auditable than rule generation)
- Streaming token output per sub-agent (adds frontend complexity; node activation states are sufficient)
- Airbyte live sync during demo (use pre-loaded fixtures; mention Airbyte sync is pre-configured)

### Architecture Approach

Four-layer architecture:

1. **Autonomous Agent (Real LLM)** — Payment Agent is Sonnet 4.6 making genuine decisions. Attacks manipulate its reasoning via prompt injection or social engineering. Not hardcoded.

2. **Adversarial Verification (AI Investigates)** — Supervisor (Opus 4.6) forms predictions from behavioral baselines, dispatches Risk + Compliance + Forensics in parallel via asyncio.TaskGroup. Each investigator checks external ground truth directly — they don't ask the agent if it's telling the truth. Prediction errors (expected vs actual) are computed and stored.

3. **Verdict Board Assembly (Deterministic)** — Structured field-level comparison: agent claimed X, investigator found Y, match/mismatch/unable_to_verify. No LLM judgment.

4. **Safety Gate (If-Statement)** — Hardcoded rules first (immutable), then generated composite scoring functions. Each function returns a weighted anomaly score; individually weak signals compound. Total score exceeds threshold → NO-GO. No LLM in the enforcement path.

**Self-Improvement Loop:** Operator confirms attack → system extracts prediction errors → Opus generates composite scoring function over VerdictBoard fields → validation harness → deploy to registry → catches next attack. After second confirmation → scoring function evolves using prediction errors from both episodes.

This design cleanly separates LLM reasoning from deterministic enforcement across well-defined Pydantic schema boundaries.

**Major components:**
1. **SupervisorAgent** — Orchestrates investigation, assembles VerdictBoard from sub-agent returns, handles voice Q&A; does NOT apply rules or write decisions
2. **VerdictBoardEngine** — Deterministic field comparison; enum (match/mismatch/unable_to_verify) only; no float math; no LLM calls
3. **SafetyGate** — Runs hardcoded rules first (cannot be removed), then generated rule registry; outputs GO/NO_GO/ESCALATE with full attribution; no LLM calls
4. **RuleRegistry** — In-memory + Aerospike-backed; generated rules exec()'d at registration time; rules loaded from Aerospike at startup
5. **AerospikeStore** — Three sets: `episodes`, `rules`, `trust`; all writes via `run_in_executor`; startup read-after-write health check required
6. **ConnectionManager (WebSocket)** — Server-to-client only for pipeline events; named typed events with sequence numbers; individual try/except per send
7. **RuleGenerator** — Opus 4.6 prompt → Python source → compile check → exec validation → registration; most failure-prone component; isolated in `improvement/` module

### Critical Pitfalls

1. **Claude API Tier 1 ITPM wall** — A single Sentinel investigation (Supervisor + 3 sub-agents + rule gen) can consume 15,000–35,000 input tokens in under 10 seconds. At Tier 1 (30,000 ITPM), the second demo cycle hits a 429 with a 30–60 second retry-after. Prevention: advance to Tier 2 before building anything; enable prompt caching on all system prompts (`cache_control: ephemeral`); run two consecutive full demo cycles in staging and check `anthropic-ratelimit-input-tokens-remaining` headers.

2. **exec() rule silent failure** — Generated rules exec()'d into a registry namespace that is never extracted correctly cause the gate to return GO silently. The `except: pass` anti-pattern swallows the NameError. Prevention: always explicitly extract `fn = namespace['detect']`; wrap each rule evaluation individually with logging; never swallow rule exceptions as silent pass.

3. **Rule generalization failure** — Opus defaults to mechanistic rules (checking forensics fields) rather than behavioral rules (checking confidence/mismatch pattern). Phase 2 uses a different attack surface; the mechanistic rule never fires. Prevention: the rule generation prompt must explicitly ban attack-specific field names (`forensics_findings`, `document_scan`) and constrain the field vocabulary to behavioral fields (`agent_confidence`, `field_mismatches`, `claims_verified_count`). Test the generated rule against a Phase 2 fixture before wiring into the loop.

4. **Bland AI webhook timeout** — If the webhook handler calls a live Claude endpoint for voice context, Bland AI's ~8-second timeout is easily exceeded under load. Prevention: pre-compute all voice context (write `voice_context` record to Aerospike when gate fires); webhook handler reads from Aerospike (<5ms) only; measure webhook response time in testing.

5. **Aerospike namespace mismatch** — Writing to a namespace not configured in `aerospike.conf` succeeds at the API level but data is dropped. The default Docker image only has the `test` namespace. Prevention: run a startup read-after-write health check; crash loudly on failure; use the `test` namespace or mount a custom `aerospike.conf` that declares `sentinel`.

6. **Demo environment divergence** — Environment variables missing, localhost webhook URL not reachable from Bland AI's servers, wrong Aerospike host. Prevention: write a `demo_check.py` script that validates all integrations; run at T-1 hour and T-15 minutes; use docker-compose for single-command stack startup.

## Implications for Roadmap

Based on build-order dependencies identified in ARCHITECTURE.md, combined with pitfall prevention phases from PITFALLS.md and MVP definition from FEATURES.md, the following phase structure is recommended:

### Phase 1: Foundation Infrastructure + Core Pipeline
**Rationale:** All other phases depend on schema contracts, the deterministic engine, and Aerospike connectivity. The most dangerous pitfalls (API tier, Aerospike namespace, latency budget) must be caught here before any downstream work is built on broken foundations.
**Delivers:** Pydantic schemas for all boundary types; VerdictBoardEngine; SafetyGate with hardcoded rules; AerospikeStore with startup health check; AsyncAnthropic client configured; end-to-end latency budget established (Phase 1 arc must complete in under 60 seconds)
**Addresses:** Table stakes — audit trail, hardcoded safety baseline, persistent storage
**Avoids:** Aerospike namespace mismatch (Pitfall 5); API Tier 1 ITPM wall (Pitfall 1 — upgrade and configure prompt caching before first integration test); Opus latency (Pitfall 7 — set max_tokens and measure during first pipeline test)

### Phase 2: Sub-Agent Layer + Parallel Investigation
**Rationale:** Sub-agents are independently testable; they must exist before the Supervisor can be wired. Parallel dispatch is a core demo claim and must be proven to work within the latency budget before UI is built on top.
**Delivers:** RiskAgent, ComplianceAgent, ForensicsAgent each independently tested against fixture PaymentVerdict inputs; SupervisorAgent with asyncio.gather() dispatch; complete Phase 1 demo scenario (hidden text invoice) running end-to-end; fixture adversarial documents prepared
**Uses:** AsyncAnthropic parallel dispatch pattern; asyncio.gather(return_exceptions=True)
**Implements:** Sub-agent layer + SupervisorAgent from architecture diagram
**Avoids:** Sequential sub-agent execution (Anti-Pattern 3); passing raw dicts across boundaries (Anti-Pattern 2)

### Phase 3: Self-Improvement Loop + Rule Generation
**Rationale:** Rule generation is the highest-risk component and must be isolated and tested exhaustively before being wired into the pipeline. Phase 2 of the demo depends entirely on this working correctly.
**Delivers:** RuleGenerator with Opus prompt that produces behavioral (not mechanistic) rules; RuleRegistry with exec()/compile validation harness; self-improvement loop triggered from /confirm-incident endpoint; Phase 2 demo scenario (identity spoofing caught by generated rule) verified end-to-end
**Uses:** RestrictedPython 8.2; Aerospike rule_store set; RuleRegistry in-memory + persistent
**Implements:** Self-Improvement Loop from architecture
**Avoids:** exec() silent failure (Pitfall 2 — explicit namespace extraction + per-rule logging); rule generalization failure (Pitfall 3 — constrained prompt vocabulary; test against Phase 2 fixture before wiring)
**Research flag:** Rule generation prompt is the single most failure-prone component. Requires 30+ isolation tests. This phase should not be considered complete until the generated rule passes both Phase 1 and Phase 2 fixture verdict boards.

### Phase 4: Real-Time Dashboard
**Rationale:** Frontend can be developed in parallel with Phases 2-3 using a fixture event broadcaster, but should be integrated only after the backend pipeline is stable. WebSocket event schema is the contract.
**Delivers:** React dashboard with investigation tree (@xyflow/react), verdict board table, trust score animation, generated rule source panel, Aerospike write latency badge, WebSocket reconnection handling, event sequence numbers
**Uses:** @xyflow/react 12.4.4; native browser WebSocket; Zustand or useReducer for single state object; Prism.js for rule source syntax highlighting
**Implements:** WebSocket Event Bus + ConnectionManager; all 9 named events from event taxonomy
**Avoids:** WebSocket race conditions (Pitfall 6 — event sequence numbers; single state store); canvas main thread blocking (Pitfall 11 — pre-compute node positions; CSS transitions for state changes); React full-state broadcasts (Anti-Pattern 4)

### Phase 5: Voice Interface + Auth Gate
**Rationale:** Voice is sponsor-critical for Bland AI judges but depends on having a stable pipeline and pre-computed voice context. Okta override is low-complexity but requires a working voice path. Both are added after core demo loop is bulletproof.
**Delivers:** Bland AI call initiation + webhook endpoint; pre-computed voice context written to Aerospike at gate evaluation; operator Q&A flow grounded in verdict board; Okta token introspection for override command; text fallback on dashboard for all voice answers
**Uses:** Bland AI REST API; httpx for Okta introspection; okta-jwt-verifier 0.4.0
**Implements:** Entry Layer (Bland AI webhook); Okta integration
**Avoids:** Bland AI webhook timeout (Pitfall 4 — pre-compute context; measure webhook response time); voice as primary UI path (Anti-Feature — dashboard is always authoritative)

### Phase 6: Demo Preparation + Deployment
**Rationale:** Demo environment divergence is a consistent hackathon killer that requires an explicit phase, not "handled at the end." This phase must happen with enough time remaining to fix any issues found.
**Delivers:** `demo_check.py` validation script; docker-compose single-command stack; demo script with scripted click/voice sequence; two consecutive full Phase 1 → Phase 2 → Phase 3 cycles verified; screen recording fallback prepared; EC2 deployment with public URL for Bland AI webhook
**Avoids:** Demo environment divergence (Pitfall 8 — explicit validation; public URL; run T-1 hour before demo)

### Phase Ordering Rationale

- Schemas first: all inter-component contracts are defined in Phase 1 before any component is built, preventing interface drift that causes late-stage failures
- Deterministic engine before LLM calls: VerdictBoardEngine and SafetyGate are testable without any API calls, making them the safest foundation
- Aerospike health check before first pipeline integration: catches the namespace mismatch pitfall before hours of downstream code are built on it
- Rule generation isolated before wiring: the highest-failure-risk component gets its own phase with a clear go/no-go gate (30+ tests pass; Phase 2 fixture returns True)
- Dashboard built against a stable event schema: the frontend can use a fixture broadcaster while the backend is being built, enabling parallel work
- Voice added last, after core is bulletproof: voice failure is recoverable with narration; pipeline failure is not
- Demo prep as an explicit phase: not an afterthought; must complete with time to fix issues

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 3 (Rule Generation):** The rule generation prompt is the highest-risk single artifact. The exact prompt structure, field vocabulary constraints, and test harness design may need iterative refinement. Recommend 30+ test runs in complete isolation before considering this phase complete.
- **Phase 5 (Bland AI):** Bland AI's real-time webhook behavior and exact pathway configuration for dynamic variable injection (passing `episode_id` and `operator_question`) are not fully documented publicly. Integration should be prototyped end-to-end (including webhook roundtrip) before any dependent features are built.

Phases with standard, well-documented patterns (skip additional research):
- **Phase 1 (Foundation):** FastAPI + Pydantic + AsyncAnthropic patterns are all well-documented. Aerospike Docker setup with namespace configuration is straightforward once the `test` vs custom namespace gotcha is understood.
- **Phase 4 (Dashboard):** @xyflow/react, native WebSocket, and React state management patterns are all mature. No additional research needed.
- **Phase 6 (Demo Prep):** Standard deployment patterns. docker-compose + EC2 + ngrok for webhook is a solved problem.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Core SDK and async patterns verified against official docs. Aerospike client version 19.1.0 confirmed. Only gap is Bland AI real-time WebSocket specifics (LOW) — confirmed that REST + webhook is the correct integration model for hackathon scope. |
| Features | MEDIUM-HIGH | Table stakes and MVP definition are well-grounded in both judge composition and financial compliance requirements. Novelty claims (cross-surface generalization, additive-only rules) are defensible but depend on rule generation prompt producing behavioral rules — this is implementation-dependent, not just architectural. |
| Architecture | HIGH | Core patterns (asyncio.gather, typed WebSocket events, exec() safety gate, Aerospike schema) are well-documented and the research provides complete working code patterns for each. Bland AI webhook integration model is MEDIUM — synchronous call-and-response pattern is confirmed but exact pathway variable structure requires testing. |
| Pitfalls | HIGH | Eight demo-critical pitfalls are identified with specific prevention strategies. Rate limits, exec() scoping rules, Aerospike namespace behavior, and WebSocket state management are all well-documented failure modes. Pitfall severity ratings are calibrated to hackathon context specifically. |

**Overall confidence:** MEDIUM-HIGH

### Gaps to Address

- **Bland AI pathway variable injection:** The exact structure for passing `episode_id` and `operator_question` as custom variables through a Bland AI pathway to the webhook has sparse public documentation. Build a minimal end-to-end webhook prototype on Day 1 before committing to the full voice integration design.
- **Rule generation prompt:** This is the most important and most uncertain artifact. The research confirms the pattern exists (Rule Maker Pattern) and what behavioral constraints the prompt must include, but the exact prompt wording must be developed and validated empirically. Budget 2-3 hours on Day 2 for prompt iteration in isolation.
- **Aerospike on demo hardware:** If the demo machine is Apple Silicon (M-series Mac), the `aerospike` Python package C-extension requires additional flags to compile (`ARCHFLAGS="-arch arm64"`). Validate the install immediately on Day 1 before building any application code on top of it.
- **Generalization proof scope:** The cross-surface behavioral generalization claim depends on the verdict board for the identity spoofing attack having sufficient structural similarity to the invoice attack verdict board (both showing high agent confidence + investigator field mismatches). The fixture for Phase 2 must be designed to expose this similarity, not just demonstrate the attack.

## Sources

### Primary (HIGH confidence)
- [anthropic-sdk-python GitHub + official docs](https://platform.claude.com/docs/en/api/sdks/python) — AsyncAnthropic, TaskGroup, prompt caching, rate limits, structured output
- [Python asyncio official docs](https://docs.python.org/3/library/asyncio-task.html) — TaskGroup structured concurrency
- [RestrictedPython docs](https://restrictedpython.readthedocs.io/en/latest/) — v8.2 compile_restricted, exec namespace patterns
- [okta-jwt-verifier GitHub](https://github.com/okta/okta-jwt-verifier-python) — v0.4.0, AccessTokenVerifier
- [xyflow/xyflow GitHub + reactflow.dev](https://reactflow.dev) — @xyflow/react v12.4.4, animated edges
- [FastAPI WebSocket docs](https://fastapi.tiangolo.com/advanced/websockets/) — ConnectionManager, WebSocket broadcast patterns
- [Aerospike Python Client docs](https://aerospike-python-client.readthedocs.io/en/latest/) — version 19.1.0, write policies, run_in_executor pattern
- [Claude API Rate Limits — Official](https://platform.claude.com/docs/en/api/rate-limits) — Tier 1/2 ITPM limits

### Secondary (MEDIUM confidence)
- [Bland AI docs](https://docs.bland.ai/) — webhook patterns, call initiation, barge-in configuration; real-time WebSocket specifics LOW
- [The Rule Maker Pattern — tessl.io](https://tessl.io/blog/the-rule-maker-pattern/) — deterministic execution separation
- [Aerospike Python Client PyPI / community forum](https://discuss.aerospike.com/) — version confirmation, write policy patterns
- [AI Agents Hackathon 2025 — Microsoft Community Hub](https://techcommunity.microsoft.com/blog/azuredevcommunityblog/) — winning patterns analysis
- [Galileo — AI Agent Compliance & Governance 2025](https://galileo.ai/blog/ai-agent-compliance-governance-audit-trails-risk-management) — compliance feature requirements

### Tertiary (LOW confidence)
- [Agentic AI Maturity Model 2025 — DextraLabs](https://dextralabs.com/blog/agentic-ai-maturity-model-2025/) — self-learning novelty assessment
- [Bland AI Review 2025 — Retell AI](https://www.retellai.com/blog/bland-ai-reviews) — Bland AI reliability issues in demo environments

---
*Research completed: 2026-03-24*
*Ready for roadmap: yes*
