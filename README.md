# Sentinel

**Runtime security for autonomous AI agents.**

Sentinel intercepts agent actions at the execution boundary, dispatches independent AI investigators to adversarially verify the agent's claims against ground truth, and blocks actions that can't be independently confirmed. When it catches a novel attack, it autonomously generates a composite scoring function -- inspectable Python, not a black box -- that detects the same behavioral pattern in future incidents. The scoring functions evolve across confirmed attacks, getting sharper with each incident the system sees.

The block decision is an if-statement. No LLM in the enforcement path.

---

## The Problem

Autonomous AI agents are being deployed to handle real-world transactions: payments, procurement, customer service, infrastructure management. Existing guardrails filter inputs and outputs but **trust the agent's internal reasoning**. This creates a critical blind spot: if the agent itself is compromised -- through prompt injection, adversarial documents, or social engineering -- input/output filters see nothing wrong because the agent genuinely believes it's acting correctly.

**The agent is the threat model.** Not the user. Not the network. The agent.

Today, a compromised payment agent can read a poisoned invoice containing invisible text that redirects $47,250 to a fraudulent account, report 95% confidence that everything checks out, and no existing guardrail will catch it -- because from the guardrail's perspective, the agent is behaving normally.

## Target User

**Security/SRE operators** overseeing autonomous agent deployments in regulated environments -- financial services, healthcare, government. Teams that need:

- **Auditability**: Every block decision traceable to specific evidence, not an LLM opinion
- **Deterministic enforcement**: Safety-critical decisions that don't depend on model availability or latency
- **Adaptive defense**: Protection that improves autonomously as new attack patterns emerge
- **Transparency**: Scoring functions are readable Python, not opaque embeddings or probability thresholds

## Why This Matters for AI Safety

As AI agents gain autonomy over real-world actions, the security surface inverts. Traditional cybersecurity assumes a trusted internal system defending against external threats. Autonomous agents break this assumption -- **the system itself can be manipulated into becoming the attack vector**.

Sentinel addresses this with a principle borrowed from institutional security: **separation of duties**. The agent that processes a payment is not the agent that verifies it. Independent investigators with access to ground truth (KYC databases, counterparty registries, behavioral baselines) adversarially check every claim the processing agent makes. Disagreements between what the agent claims and what investigators find become quantified anomaly signals fed into deterministic scoring functions.

This architecture means:
- A compromised agent **cannot** suppress investigation findings
- Block decisions execute in **<1ms** with no LLM dependency
- New attack patterns are **automatically** captured as evolving scoring functions
- Every decision is **fully auditable** -- inspectable Python, not a neural network judgment call

---

## Architecture

```
                          Payment Request
                                |
                                v
                    +------------------------+
                    |   Sentinel Supervisor   |  (Claude Opus 4.6)
                    |   - Loads episodic      |
                    |     memory context      |
                    |   - Forms behavioral    |
                    |     predictions         |
                    +------------------------+
                                |
                    Drives Payment Agent (Sonnet 4.6)
                    turn-by-turn via tool calls
                                |
                                v
                    +------------------------+
                    |     Payment Agent       |  (Claude Sonnet 4.6)
                    |   - Reads invoices      |
                    |   - Checks counterparty |
                    |   - Makes decision      |
                    +------------------------+
                                |
            Parallel dispatch via asyncio.TaskGroup
                    /           |           \
                   v            v            v
          +------------+  +------------+  +-------------+
          | Risk Agent |  | Compliance |  |  Forensics  |
          |  (Sonnet)  |  |  (Sonnet)  |  |  (Sonnet)   |
          |            |  |            |  |             |
          | Z-score    |  | KYC ledger |  | Vision API  |
          | computation|  | Counterpty |  | Hidden text |
          | Step-seq   |  | registry   |  | detection   |
          | deviation  |  | check      |  | Invoice     |
          +------------+  +------------+  | comparison  |
                   \           |          +-------------+
                    \          |          /
                     v         v         v
                    +------------------------+
                    |     Verdict Board       |
                    |   Assembles all agent   |
                    |   findings into scored  |
                    |   anomaly signals       |
                    +------------------------+
                                |
                                v
                    +------------------------+
                    |      Safety Gate        |  <-- deterministic, no LLM
                    |                        |
                    |  Tier 1: 8 hardcoded   |
                    |    scoring rules       |
                    |  Tier 2: N generated   |
                    |    scoring rules       |
                    |                        |
                    |  composite >= 1.0: BLOCK|
                    |  composite >= 0.6: HOLD |
                    |  else: PASS            |
                    +------------------------+
                                |
                        NO-GO / ESCALATE?
                                |
                                v
                    +------------------------+
                    |   Self-Improvement      |
                    |   Loop                  |
                    |                        |
                    |  Opus 4.6 generates    |
                    |  Python scoring fn     |
                    |  from prediction errors |
                    |                        |
                    |  4-check validation:   |
                    |  1. AST parse          |
                    |  2. Fires on attack    |
                    |  3. Silent on clean    |
                    |  4. No forbidden tokens|
                    |                        |
                    |  Hot-deployed to Gate  |
                    +------------------------+
                                |
                                v
                    +------------------------+
                    |      Aerospike         |
                    |   Episodes + Rules     |
                    |   Sub-5ms persistence  |
                    +------------------------+
```

### The Self-Improvement Loop

This is the core innovation. When Sentinel blocks a transaction:

1. **Prediction vs. Reality**: Before investigation, the Supervisor forms behavioral predictions from baselines. After investigation, prediction errors are computed -- the gap between what was expected and what was found.

2. **Rule Generation**: Opus 4.6 analyzes the prediction errors and writes a Python scoring function that captures the behavioral pattern (not entity-specific details -- the function generalizes).

3. **Validation Harness**: The generated function must pass 4 checks:
   - Parses as valid Python AST
   - Fires on the source attack (score > 0.6)
   - Does NOT fire on a clean baseline (score < 0.2)
   - Contains no forbidden tokens (`import`, `__`, `open`, `exec`, `eval`)

4. **Evolution**: When a second incident triggers the same behavioral pattern, the rule evolves -- strengthening signals that appear in both incidents, dropping single-incident artifacts, tightening thresholds to reduce false positives.

5. **Hot Deployment**: Validated rules are immediately registered in the Safety Gate and persisted to Aerospike. No restart. No human in the loop.

**Result**: Attack 1 gets caught by hardcoded rules. The system generates a scoring function. Attack 2 (different vector, same behavioral fingerprint) gets caught by the generated function *before* hardcoded rules even fire. The system learns.

---

## Technical Deep Dive

### Deterministic Safety Gate

The Safety Gate is the enforcement boundary. Every transaction passes through it. The decision is pure computation -- no LLM call, no network request, no stochastic behavior.

```python
# The block decision is an if-statement
composite_score = sum(rule.score(verdict_board) for rule in all_rules)
if composite_score >= 1.0:
    decision = "NO-GO"    # Transaction blocked
elif composite_score >= 0.6:
    decision = "ESCALATE"  # Human review required
else:
    decision = "GO"        # Transaction proceeds
```

**Two-tier rule architecture:**
- **Tier 1 -- Hardcoded** (8 rules, immutable): Hidden text detection, z-score anomaly, behavioral flag aggregation, field mismatch scoring, step-sequence deviation, unverifiable claims, amount thresholds, unknown beneficiary
- **Tier 2 -- Generated** (N rules, evolving): LLM-written Python functions compiled via RestrictedPython with sandboxed execution (allowlisted builtins only, 5-second timeout, forbidden token pre-scan)

### Parallel Sub-Agent Dispatch

Python 3.11's `asyncio.TaskGroup` provides structured concurrency -- if any investigator raises an exception, siblings are cancelled automatically. No zombie agent calls blocking the demo.

```python
async with asyncio.TaskGroup() as tg:
    risk_task = tg.create_task(risk.investigate(payment_decision, baselines))
    compliance_task = tg.create_task(compliance.investigate(payment_decision, fixtures))
    forensics_task = tg.create_task(forensics.investigate(payment_decision, invoice_urls))
```

Three independent AI investigators run simultaneously:
- **Risk Agent**: Computes confidence z-scores against behavioral baselines, detects step-sequence deviations from expected tool-call order
- **Compliance Agent**: Cross-references agent claims against KYC ledger and counterparty authorization database
- **Forensics Agent**: Vision-based invoice analysis, hidden text detection, document comparison between clean reference and submitted invoice

### Behavioral Prediction Engine

Before dispatching investigators, the Supervisor forms predictions from behavioral baselines:

```python
z_score = (agent_confidence - baseline_mean) / baseline_std
# Agent claims 0.95 confidence, baseline mean is 0.52, std is 0.11
# z-score = 3.91 -- extreme statistical anomaly
```

The prediction-vs-reality gap is the primary learning signal. Expected investigation outcomes (e.g., "KYC should verify successfully") are compared against actual findings. Deviations feed directly into rule generation.

### Generated Scoring Functions

Generated rules operate on the `VerdictBoard` -- a structured dict of behavioral signals. Here's a real generated rule from the system:

```python
def score(verdict_board: dict) -> float:
    """Scores identity spoofing: extreme confidence + KYC gaps + critical mismatches."""
    total = 0.0

    # Signal 1: Confidence z-score anomaly
    z = verdict_board.get("confidence_z_score")
    if z is not None:
        if abs(z) > 3.5: total += 0.6
        elif abs(z) > 2.5: total += 0.4

    # Signal 2: Critical mismatches with identity-related fields
    for m in verdict_board.get("mismatches", []):
        if m.get("severity") == "critical": total += 0.25

    # Signal 3: Behavioral flags (KYC, identity, confidence anomaly)
    for flag in verdict_board.get("behavioral_flags", []):
        if any(kw in flag.lower() for kw in ["kyc", "identity", "spoof"]):
            total += 0.15

    # Signal 4: Compound -- high confidence + multiple critical mismatches
    if verdict_board.get("agent_confidence", 0) > 0.9:
        if sum(1 for m in verdict_board.get("mismatches", [])
               if m.get("severity") == "critical") >= 2:
            total += 0.2

    return min(total, 2.0)
```

This function was written by Opus 4.6, validated against attack and clean baselines, compiled via RestrictedPython, and hot-deployed into the Safety Gate -- all autonomously.

### RestrictedPython Sandboxing

Generated code executes in a restricted environment:

```python
SAFE_BUILTINS = {
    "len", "any", "all", "min", "max", "abs", "round", "sum",
    "isinstance", "dict", "list", "str", "int", "bool", "float",
    "True", "False", "None"
}
FORBIDDEN_TOKENS = ["import", "__", "open", "exec", "eval"]
```

Source code is statically scanned for forbidden tokens, compiled via `compile_restricted()`, and executed with a 5-second signal-based timeout. Rules can only read `verdict_board` fields -- no system calls, no file access, no network.

### Episodic Memory (Aerospike)

Every investigation is persisted as an Episode in Aerospike with sub-5ms write latency:

- **Episodes set**: Complete investigation records (verdict board, gate decision, agent verdicts, prediction report, rules fired)
- **Rules set**: Generated rule provenance (source code, episode IDs, version history, fire counts)
- **Index pattern**: `__episode_index__` key tracks all episode IDs for efficient retrieval

The Supervisor loads recent episodes at investigation start, providing cross-incident context that informs behavioral predictions and rule evolution decisions.

### Real-Time Dashboard

WebSocket-driven React frontend streams 10+ event types per investigation:

| Event | Payload |
|-------|---------|
| `investigation_started` | Reset state, initialize investigation tree |
| `agent_completed` (x3) | Agent verdict, animated edge in XYFlow graph |
| `verdict_board_assembled` | Mismatch table, narrative generation |
| `gate_evaluated` | GO/NO-GO/ESCALATE decision, composite score |
| `episode_written` | Aerospike write latency (ms) |
| `rule_generating` | Streaming rule source tokens |
| `rule_deployed` | New rule node added to investigation tree |

Built with XYFlow (React Flow) for the investigation pipeline visualization, Zustand for state management, and native browser WebSocket (no Socket.io overhead).

---

## Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| **Supervisor LLM** | Claude Opus 4.6 | Orchestration, prediction, rule generation |
| **Agent LLMs** | Claude Sonnet 4.6 | Payment processing, Risk/Compliance/Forensics investigation |
| **Backend** | Python 3.12 + FastAPI | Native async, WebSocket support, structured concurrency (TaskGroup) |
| **Persistence** | Aerospike | Sub-5ms read/write, episodic memory, rule provenance storage |
| **Rule Sandbox** | RestrictedPython | Compile-time restriction of generated Python functions |
| **Frontend** | React 18 + Vite | Concurrent features, XYFlow pipeline graph, Zustand state |
| **Auth** | Auth0 | SPA authentication for operator dashboard |
| **Deployment** | Docker + EC2 + Caddy + Vercel | Containerized backend, static frontend, automatic HTTPS |

## Attack Scenarios

### Scenario 1: Invoice Hidden Text Injection
A poisoned invoice contains near-white-on-white hidden text that overrides payment details. The Payment Agent reads the invoice, reports 95% confidence, and approves a $47,250 transfer to a fraudulent account. Sentinel's Forensics Agent detects the hidden text via vision analysis. Hardcoded rules fire immediately. The system generates a scoring function capturing the behavioral pattern.

### Scenario 2: Identity Spoofing
A request references a counterparty that doesn't exist in KYC or authorization databases. The Payment Agent claims the counterparty is authorized with 92% confidence. Sentinel's Compliance Agent cross-references ground truth and finds no record. Hardcoded rules alone score below the block threshold -- but the scoring function generated from Scenario 1 recognizes the shared behavioral fingerprint (extreme confidence + verification failures) and pushes the composite score past NO-GO.

**The system learned. Attack 2 was caught by a function that didn't exist before Attack 1.**

---

## Project Structure

```
sentinel/
  agents/
    supervisor.py          # Opus 4.6 orchestration engine
    payment_agent.py       # Sonnet 4.6 payment processing (the "compromised" agent)
    risk.py                # Z-score computation, step-sequence deviation
    compliance.py          # KYC ledger + counterparty verification
    forensics.py           # Vision-based invoice analysis
  engine/
    safety_gate.py         # Deterministic enforcement (no LLM)
    rule_generator.py      # Self-improvement loop core
    prediction.py          # Behavioral baseline predictions
    verdict_board.py       # Signal assembly
  gate/rules/
    rule_*.py              # 8 hardcoded + N generated scoring functions
  memory/
    aerospike_client.py    # Async wrapper (sync C-extension + ThreadPoolExecutor)
    episode_store.py       # Investigation record persistence
    rule_store.py          # Generated rule provenance
  api/
    main.py                # FastAPI app + WebSocket + investigation routes
  schemas/
    verdict.py             # Agent verdict data model
    verdict_board.py       # Composite signal model
    episode.py             # Investigation record model
    payment.py             # Payment decision model
  fixtures/                # KYC ledger, counterparty DB, behavioral baselines
frontend/
  src/
    components/            # 15 React components
    hooks/useWebSocket.js  # Real-time event subscription
    store.js               # Zustand state (50+ slices)
tests/                     # 20+ test files (end-to-end loop, agents, gate, rules)
```

## Quickstart

```bash
# Backend
cp .env.example .env
# Add your ANTHROPIC_API_KEY to .env
pip install -e .
docker compose up -d aerospike
uvicorn sentinel.api.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev
```

Or run everything with Docker:

```bash
docker compose up --build
```

---

**Built solo in 72 hours for the AWS Deep Agents Hackathon.**
