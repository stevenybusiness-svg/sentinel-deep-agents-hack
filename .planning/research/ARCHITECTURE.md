# Architecture Research

**Domain:** Real-time multi-agent supervision system (payment agent oversight)
**Researched:** 2026-03-24
**Confidence:** HIGH (core patterns), MEDIUM (Bland AI integration details)

## Standard Architecture

### System Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│                        ENTRY LAYER                                   │
│  ┌──────────────────┐           ┌────────────────────────────────┐   │
│  │  Bland AI Voice  │           │  FastAPI HTTP /investigate     │   │
│  │  Webhook POST    │           │  (payment agent verdict input) │   │
│  └────────┬─────────┘           └────────────┬───────────────────┘   │
│           │ call_id + transcript              │ PaymentVerdict        │
└───────────┼──────────────────────────────────┼───────────────────────┘
            │                                  │
            ▼                                  ▼
┌──────────────────────────────────────────────────────────────────────┐
│                     SUPERVISOR LAYER (Opus 4.6)                      │
│  ┌───────────────────────────────────────────────────────────────┐   │
│  │  SupervisorAgent                                               │   │
│  │  - Receives PaymentVerdict                                     │   │
│  │  - Builds investigation context from Aerospike (trust, rules)  │   │
│  │  - Emits WS: investigation_started                             │   │
│  │  - asyncio.gather() → 3 sub-agents                             │   │
│  │  - Assembles VerdictBoard from sub-agent returns               │   │
│  │  - Emits WS: verdict_board_assembled                           │   │
│  └───────────────────────────────────────────────────────────────┘   │
└──────────────────────────┬────────────────────────────────────────────┘
                           │ asyncio.gather()
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
┌─────────────────┐ ┌─────────────┐ ┌──────────────────┐
│  Risk Agent     │ │  Compliance │ │  Forensics Agent │
│  (Sonnet 4.6)   │ │  Agent      │ │  (Sonnet 4.6 +   │
│                 │ │  (Sonnet    │ │   vision)         │
│  z-score vs     │ │  4.6)       │ │                  │
│  baseline,      │ │             │ │  doc scan,        │
│  step-sequence  │ │  KYC cross- │ │  hidden text,     │
│  deviation      │ │  validation │ │  field extract    │
│                 │ │             │ │                  │
│  → AgentVerdict │ │ → AgentVerdict│ → AgentVerdict   │
└─────────────────┘ └─────────────┘ └──────────────────┘
          │                │                │
          └────────────────┼────────────────┘
                           │ List[AgentVerdict]
                           ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    VERDICT BOARD ENGINE (deterministic)              │
│  ┌───────────────────────────────────────────────────────────────┐   │
│  │  field-level comparison: payment claims vs investigator finds  │   │
│  │  outputs: match | mismatch | unable_to_verify per field        │   │
│  │  NO float math — enum comparison only                          │   │
│  │  → VerdictBoard dict                                           │   │
│  └───────────────────────────────────────────────────────────────┘   │
└──────────────────────────┬───────────────────────────────────────────┘
                           │ VerdictBoard
                           ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    SAFETY GATE (deterministic Python)                │
│  ┌───────────────────────────────────────────────────────────────┐   │
│  │  1. Hardcoded rules (always run first, cannot be removed)      │   │
│  │  2. Generated rule registry (exec()'d Python functions)        │   │
│  │  → GateDecision: GO | NO_GO | ESCALATE + attribution list      │   │
│  └───────────────────────────────────────────────────────────────┘   │
└──────────────────────────┬───────────────────────────────────────────┘
                           │ GateDecision
          ┌────────────────┴────────────────────────┐
          ▼                                         ▼
┌──────────────────────┐              ┌──────────────────────────────┐
│  Aerospike           │              │  Self-Improvement Loop       │
│  Episode Write       │              │  (operator confirms attack)  │
│  (<5ms target)       │              │                              │
│                      │              │  Opus 4.6 generates Python   │
│  namespace: sentinel │              │  rule → exec() → registry   │
│  set: episodes       │              │  → Aerospike rule_store      │
│  set: rules          │              └──────────────────────────────┘
│  set: trust          │
└──────────────────────┘
                           │ (all events throughout)
                           ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    WEBSOCKET EVENT BUS                               │
│  ConnectionManager broadcasts typed events → React dashboard        │
└──────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Boundary — What It Does NOT Do |
|-----------|----------------|-------------------------------|
| SupervisorAgent | Orchestrates investigation, synthesizes verdict board, handles voice Q&A | Does not apply rules, does not write decisions to Aerospike |
| RiskAgent | z-score confidence analysis, step-sequence deviation detection | Does not cross-validate documents |
| ComplianceAgent | KYC ledger cross-validation, agent activity log cross-check | Does not scan documents visually |
| ForensicsAgent | Vision-based document scan, hidden text extraction, field value extraction | Does not apply behavioral pattern analysis |
| VerdictBoardEngine | Deterministic field comparison, enum match/mismatch/unable_to_verify | No LLM calls, no float math |
| SafetyGate | Applies hardcoded then generated rules, outputs GO/NO_GO/ESCALATE with full attribution | No LLM calls — pure Python only |
| SelfImprovementLoop | Sends confirmed incident → Opus for rule generation, exec()'s result into registry | Cannot modify or delete existing rules |
| AerospikeStore | Persistent episode records, rule registry, trust postures, baselines | Not used for transient in-flight state |
| WebSocketBus | Broadcasts typed events to dashboard clients | Not used for request/response; one-way push |
| FastAPI | HTTP routes for payment input, webhook receiver, WebSocket endpoint | Not a business logic layer |
| BlandAI | Voice interface for operator Q&A; triggers FastAPI webhook on call events | Does not have access to verdict data except via Supervisor response |

## Recommended Project Structure

```
sentinel/
├── agents/
│   ├── supervisor.py        # SupervisorAgent — Opus 4.6, orchestrates gather()
│   ├── risk.py              # RiskAgent — Sonnet 4.6, z-score + step-sequence
│   ├── compliance.py        # ComplianceAgent — Sonnet 4.6, KYC cross-validate
│   └── forensics.py         # ForensicsAgent — Sonnet 4.6 + vision, doc scan
├── engine/
│   ├── verdict_board.py     # VerdictBoardEngine — deterministic comparisons
│   ├── safety_gate.py       # SafetyGate — hardcoded + exec() rule runner
│   └── rule_registry.py     # RuleRegistry — in-memory + Aerospike-backed store
├── memory/
│   ├── aerospike_client.py  # Connection pool, namespace/set constants
│   ├── episode_store.py     # Write/read episode records
│   ├── rule_store.py        # Persist/load generated rules
│   └── trust_store.py       # Trust posture + behavioral baselines
├── api/
│   ├── main.py              # FastAPI app init, lifespan
│   ├── routes/
│   │   ├── investigate.py   # POST /investigate — payment verdict input
│   │   ├── operator.py      # POST /confirm-incident, GET /episode/{id}
│   │   └── bland.py         # POST /webhook/bland — voice event receiver
│   └── websocket.py         # WS /ws — ConnectionManager + event bus
├── schemas/
│   ├── payment.py           # PaymentVerdict (input from payment agent)
│   ├── agent.py             # AgentVerdict (output from each sub-agent)
│   ├── verdict_board.py     # VerdictBoard, FieldVerdict
│   ├── gate.py              # GateDecision, RuleFire
│   └── events.py            # All WebSocket event types (typed dicts)
├── improvement/
│   └── rule_generator.py    # Opus prompt + rule generation + validation
├── integrations/
│   └── okta.py              # Token introspection for override verification
└── frontend/                # React app (separate build)
    ├── src/
    │   ├── components/
    │   │   ├── InvestigationTree.tsx   # Canvas-based animated tree
    │   │   ├── VerdictBoard.tsx        # Field-level comparison table
    │   │   ├── ForensicsPanel.tsx      # Invoice side-by-side view
    │   │   ├── RulePanel.tsx           # Generated rule source + provenance
    │   │   └── DecisionLog.tsx         # Attribution trail
    │   └── hooks/
    │       └── useWebSocket.ts         # WS connection + event dispatch
    └── public/
```

### Structure Rationale

- **agents/**: Isolated by concern — each agent can be tested independently against fixture inputs before wiring into gather()
- **engine/**: Deterministic code lives here, zero LLM calls; this is the auditable enforcement path judges inspect
- **memory/**: Aerospike access fully encapsulated — schema constants, serialization, and write/read patterns in one place
- **schemas/**: Typed Pydantic models serve as interface contracts across component boundaries; no dict-passing between layers
- **improvement/**: Rule generation isolated because it is the most failure-prone component (per PROJECT.md — test 30+ times before wiring)

## Architectural Patterns

### Pattern 1: asyncio.gather() for 3 Fixed Parallel Sub-Agents

**What:** Supervisor dispatches all three agents simultaneously using `asyncio.gather()` and waits for all to return before assembling the verdict board.

**When to use:** Task count is known and fixed (exactly 3 agents), all must complete before synthesis, no backpressure needed. `asyncio.gather()` is correct here — queues add unnecessary overhead when you have 3 known coroutines, not a dynamic stream of work.

**Trade-offs:**
- `gather()` with `return_exceptions=True` lets one slow or failed agent not block the others; exceptions are caught in the result list
- If an agent times out, the supervisor can substitute `unable_to_verify` for its fields rather than hanging
- Task queues would add indirection with no benefit for a fixed 3-way fan-out

**Pattern:**
```python
async def investigate(verdict: PaymentVerdict) -> VerdictBoard:
    await ws_bus.emit("agent_dispatched", {"agents": ["risk", "compliance", "forensics"]})

    results = await asyncio.gather(
        risk_agent.analyze(verdict),
        compliance_agent.validate(verdict),
        forensics_agent.scan(verdict),
        return_exceptions=True
    )

    agent_verdicts = []
    for i, r in enumerate(results):
        if isinstance(r, Exception):
            agent_verdicts.append(AgentVerdict.unable_to_verify(AGENT_NAMES[i], str(r)))
        else:
            agent_verdicts.append(r)
            await ws_bus.emit("agent_completed", {"agent": AGENT_NAMES[i], "verdict": r.summary})

    return verdict_board_engine.assemble(verdict, agent_verdicts)
```

### Pattern 2: Typed WebSocket Event Stream

**What:** A `ConnectionManager` holds all active WebSocket connections. All internal pipeline components emit named events through it. The frontend dispatches on event type to update specific UI panels.

**When to use:** Real-time dashboard where multiple panels need to update independently as pipeline stages complete. Named typed events (not raw state) let the frontend partially update without knowing full pipeline state.

**Event Taxonomy (complete list, in emission order):**

| Event Name | Emitted By | Payload Fields | UI Effect |
|---|---|---|---|
| `investigation_started` | SupervisorAgent | `episode_id`, `payment_summary`, `timestamp` | Tree root node lights up |
| `agent_dispatched` | SupervisorAgent | `agents: list[str]` | 3 child nodes appear, pulsing |
| `agent_completed` | SupervisorAgent (per agent) | `agent`, `verdict_summary`, `confidence`, `findings: list` | Node turns green/red, findings populate |
| `verdict_board_assembled` | VerdictBoardEngine | `board: VerdictBoard`, `mismatch_count`, `severity` | Verdict table populates |
| `gate_evaluated` | SafetyGate | `decision: GO|NO_GO|ESCALATE`, `rules_fired: list`, `attribution: list` | Gate decision banner + trust score animation |
| `rule_fired` | SafetyGate | `rule_id`, `rule_type: hardcoded|generated`, `episode_source` | Rule highlight in gate panel |
| `episode_written` | EpisodeStore | `episode_id`, `aerospike_write_latency_ms` | Latency badge (visible to Aerospike judges) |
| `rule_generated` | RuleGenerator | `rule_id`, `source_episode`, `python_source`, `attack_type` | Rule source panel populates, new rule node appears |
| `rule_deployed` | RuleRegistry | `rule_id`, `registry_size` | Tree gains new rule leaf node |

**Trade-offs:**
- Granular per-event (not full-state diff) keeps payloads small and lets frontend animate incrementally
- Single WebSocket endpoint (not per-panel) reduces connection overhead
- JSON-only — no binary framing needed at this scale

**Implementation:**
```python
class ConnectionManager:
    def __init__(self):
        self.connections: list[WebSocket] = []

    async def broadcast(self, event: str, payload: dict):
        msg = json.dumps({"event": event, "payload": payload, "ts": time.time()})
        dead = []
        for ws in self.connections:
            try:
                await ws.send_text(msg)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.connections.remove(ws)
```

### Pattern 3: exec() Safety Gate with Restricted Globals

**What:** Generated Python rule functions are exec()'d into a restricted namespace at registration time, then called at evaluation time with the `VerdictBoard` as the only input.

**Critical constraint:** This is architecturally NOT a security sandbox against adversarial input — it is a controlled execution surface for rules that Opus generates from a tightly-constrained prompt. The restriction is about preventing accidental scope pollution, not defeating a determined attacker.

**Restriction approach:**
```python
SAFE_BUILTINS = {
    "len": len, "any": any, "all": all,
    "isinstance": isinstance, "dict": dict, "list": list,
    "str": str, "int": int, "bool": bool, "float": float,
    "True": True, "False": False, "None": None,
}

GATE_GLOBALS = {
    "__builtins__": SAFE_BUILTINS,
}

def register_rule(rule_id: str, python_source: str) -> None:
    """Compile and register a generated rule function."""
    namespace = dict(GATE_GLOBALS)
    try:
        compiled = compile(python_source, f"<rule_{rule_id}>", "exec")
        exec(compiled, namespace)
    except SyntaxError as e:
        raise RuleRegistrationError(f"Rule {rule_id} syntax error: {e}")

    fn_name = _extract_function_name(python_source)  # parse AST to get def name
    if fn_name not in namespace:
        raise RuleRegistrationError(f"Rule {rule_id}: no function found after exec")

    _registry[rule_id] = namespace[fn_name]

def evaluate_rule(rule_id: str, verdict_board: VerdictBoard) -> bool:
    """Call a registered rule with a 5-second timeout."""
    fn = _registry[rule_id]
    with _timeout(seconds=5):
        return fn(verdict_board.model_dump())
```

**Timeout via `signal.alarm`** (Unix only — acceptable for Linux deploy on EC2):
```python
import signal
from contextlib import contextmanager

@contextmanager
def _timeout(seconds: int):
    def handler(signum, frame):
        raise RuleTimeoutError("Rule execution exceeded time limit")
    signal.signal(signal.SIGALRM, handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)
```

**Rule function contract (enforced by prompt and AST check):**
- Single argument: `verdict_board: dict`
- Returns: `bool` (True = this rule fires / block)
- No side effects permitted in the restricted namespace
- Rule source is stored verbatim in Aerospike and readable on dashboard

### Pattern 4: Aerospike Episode Storage Schema

**What:** Records organized across 3 sets in one namespace, using bins for structured fields and map bins for nested data (VerdictBoard, rule source).

**Schema design:**

```
Namespace: "sentinel"

Set: "episodes"
  Key: episode_id (UUID string)
  Bins:
    - episode_id: str
    - timestamp: int (unix ms)
    - payment_summary: map  { amount, beneficiary, account, confidence }
    - verdict_board: map    { fields: [{field, payment_claim, investigator_finding, status}] }
    - gate_decision: str    GO | NO_GO | ESCALATE
    - rules_fired: list     [{ rule_id, rule_type, attribution }]
    - operator_confirmed: bool
    - attack_type: str | None
    - rule_generated: str | None  (rule_id if rule was generated)

Set: "rules"
  Key: rule_id (str, e.g., "rule_001")
  Bins:
    - rule_id: str
    - python_source: str
    - attack_type: str
    - source_episode_id: str
    - deployed_at: int (unix ms)
    - fire_count: int  (increment on each fire — use add() operation)

Set: "trust"
  Key: agent_id (str, payment agent identifier)
  Bins:
    - agent_id: str
    - trust_score: float
    - behavioral_baseline: map  { step_sequences: list, confidence_distribution: map }
    - incident_count: int
    - last_updated: int
```

**Write pattern:** Use `put()` for full episode writes (< 5ms on local Aerospike). Use `increment()` on `fire_count` bin — single-bin atomic increment, no full record rewrite needed.

**Read pattern:** At investigation start, supervisor calls:
1. `get(("sentinel", "trust", agent_id))` — load trust posture and baseline
2. `scan("sentinel", "rules")` with `select(["rule_id", "python_source", "deployed_at"])` — load all generated rules into SafetyGate registry on startup

### Pattern 5: Bland AI Webhook → Agent Pipeline Handoff

**What:** Bland AI calls a FastAPI webhook URL during or after a call. FastAPI receives the event, extracts operator intent from the transcript, and routes to the Supervisor for a response that Bland AI can speak.

**Bland AI integration model:** Bland AI's webhook is primarily a **synchronous** call-and-response during a call pathway — it sends a POST with call context, expects a JSON response with values to inject back into the conversation. This is not a fire-and-forget event stream.

**Pattern:**
```
Operator voice call
    → Bland AI pathway node
        → POST /webhook/bland { call_id, transcript_excerpt, custom_vars }
            → FastAPI extracts operator question
            → SupervisorAgent.answer_operator_question(question, episode_id)
            → Returns { response_text: "I blocked the transfer because..." }
        → Bland AI reads response_text aloud
```

**FastAPI route:**
```python
@router.post("/webhook/bland")
async def bland_webhook(payload: BlandWebhookPayload) -> BlandWebhookResponse:
    question = payload.variables.get("operator_question", "")
    episode_id = payload.variables.get("episode_id", "")

    answer = await supervisor.answer_operator_question(
        question=question,
        episode_id=episode_id,
        timeout_seconds=8  # Bland AI has a response timeout
    )

    return BlandWebhookResponse(response=answer)
```

**Override flow:** Operator says "override" → Bland AI sends `override_requested: true` variable → FastAPI routes to Okta token introspection → returns `verified: true/false` → Bland AI speaks result.

**Timeout critical:** Bland AI will time out if the webhook doesn't respond quickly enough. The Supervisor answer_operator_question call must complete within ~8 seconds. Keep a cache of the most recent episode state in memory to avoid Aerospike lookup on every Q&A turn.

## Data Flow

### Primary Investigation Flow

```
POST /investigate { PaymentVerdict }
    │
    ▼
SupervisorAgent.run(verdict)
    │ asyncio.gather()
    ├──→ RiskAgent.analyze(verdict) ─────────────────→ AgentVerdict{risk}
    ├──→ ComplianceAgent.validate(verdict) ──────────→ AgentVerdict{compliance}
    └──→ ForensicsAgent.scan(verdict) ───────────────→ AgentVerdict{forensics}
                                                              │
                                                              ▼
                                              VerdictBoardEngine.assemble(
                                                  payment_verdict,
                                                  [risk, compliance, forensics]
                                              ) → VerdictBoard
                                                              │
                                                              ▼
                                              SafetyGate.evaluate(VerdictBoard)
                                                  → hardcoded rules
                                                  → generated rules (registry)
                                                  → GateDecision
                                                              │
                                              ┌───────────────┘
                                              │
                                              ▼
                                  Aerospike.put(episode)
                                  WS broadcast: gate_evaluated
                                              │
                                  HTTP response: { episode_id, decision }
```

### Self-Improvement Flow

```
POST /confirm-incident { episode_id, attack_type }
    │
    ▼
RuleGenerator.generate(verdict_board, mismatches, attack_type)
    │ Opus 4.6 API call
    │ Returns python_source (function string)
    ▼
RuleRegistry.register(rule_id, python_source)
    │ exec() into restricted namespace
    │ validates function found and callable
    ▼
Aerospike.put(("sentinel", "rules", rule_id), bins)
    │
    ▼
WS broadcast: rule_generated + rule_deployed
```

### WebSocket Event Stream Direction

```
All pipeline components → ConnectionManager → WS clients (React dashboard)

Direction is ALWAYS server → client for pipeline events.
Client → server only for: operator actions (confirm-incident) via HTTP POST, not WS.
```

## Build Order Dependencies

This is the critical sequencing for a 72-hour solo build. Each item depends on all items above it in its chain.

### Chain 1: Core Pipeline (must exist before anything else)

```
1. Pydantic schemas (PaymentVerdict, AgentVerdict, VerdictBoard, GateDecision)
   └── No dependencies. Build first. All other components import from here.

2. VerdictBoardEngine
   └── Depends on: schemas only
   └── Fully testable with fixture dicts before any agents exist

3. SafetyGate (hardcoded rules only)
   └── Depends on: schemas, VerdictBoardEngine
   └── Test with fixture VerdictBoard inputs

4. RuleRegistry + exec() infrastructure
   └── Depends on: SafetyGate (plugs into it)
   └── TEST THIS 30+ TIMES IN ISOLATION (per PROJECT.md)

5. Sub-agents (Risk, Compliance, Forensics)
   └── Depends on: schemas (AgentVerdict contract)
   └── Each independently testable with fixture PaymentVerdict

6. SupervisorAgent + asyncio.gather()
   └── Depends on: all three sub-agents, VerdictBoardEngine, SafetyGate
   └── End-to-end pipeline now complete
```

### Chain 2: Persistence (Aerospike)

```
7. AerospikeClient (connection pool, namespace constants)
   └── Depends on: nothing (external dep only)

8. EpisodeStore, RuleStore, TrustStore
   └── Depends on: AerospikeClient, schemas
   └── Wire into SupervisorAgent after Chain 1 completes
```

### Chain 3: API + Real-Time Dashboard

```
9. FastAPI skeleton + ConnectionManager
   └── Depends on: nothing
   └── Can build in parallel with Chain 1/2

10. WebSocket event bus wired into pipeline
    └── Depends on: ConnectionManager, SupervisorAgent

11. React frontend + WebSocket client
    └── Depends on: WebSocket event bus (schema of events)
    └── Can mock events with a fixture broadcaster during frontend dev
```

### Chain 4: Self-Improvement Loop

```
12. RuleGenerator (Opus prompt + rule generation)
    └── Depends on: RuleRegistry (Chain 1, step 4)
    └── MUST be tested in isolation before wiring
    └── Verify generated rules exercise exec() path end-to-end

13. Wire RuleGenerator into /confirm-incident endpoint
    └── Depends on: RuleGenerator, EpisodeStore, WebSocket bus
```

### Chain 5: Voice + Auth (post-core)

```
14. Bland AI webhook endpoint
    └── Depends on: SupervisorAgent (for answer_operator_question)
    └── Implement after core pipeline is stable

15. Okta token introspection
    └── Depends on: Bland AI webhook route
    └── ~30 min implementation; add only after voice works
```

## Interface Contracts

### PaymentVerdict (input to investigation)

```python
class PaymentVerdict(BaseModel):
    episode_id: str           # UUID, generated by Supervisor
    agent_id: str             # identity of the payment agent
    amount: Decimal
    beneficiary_name: str
    account_number: str
    confidence: float         # 0.0–1.0
    steps_taken: list[str]    # ordered list of action descriptions
    claims: dict[str, str]    # arbitrary claim key→value ("kyc_verified": "true")
    document_urls: list[str]  # URLs for documents Forensics will scan
    timestamp: datetime
```

### AgentVerdict (output from each sub-agent)

```python
class FieldFinding(BaseModel):
    field: str
    payment_claim: str | None
    investigator_finding: str | None
    status: Literal["match", "mismatch", "unable_to_verify"]
    severity: Literal["critical", "high", "medium", "low"]
    evidence: str  # human-readable explanation

class AgentVerdict(BaseModel):
    agent: Literal["risk", "compliance", "forensics"]
    confidence: float          # agent's confidence in its own findings
    findings: list[FieldFinding]
    summary: str               # 1-sentence human-readable summary
    raw_evidence: dict         # arbitrary structured evidence for logging
```

### VerdictBoard (output from VerdictBoardEngine)

```python
class VerdictBoard(BaseModel):
    episode_id: str
    payment_verdict: PaymentVerdict
    fields: list[FieldVerdict]  # merged, deduplicated from all agents
    mismatch_count: int
    unable_to_verify_count: int
    overall_severity: Literal["critical", "high", "medium", "low", "clean"]
```

### GateDecision (output from SafetyGate)

```python
class RuleFire(BaseModel):
    rule_id: str
    rule_type: Literal["hardcoded", "generated"]
    source_episode_id: str | None  # None for hardcoded
    description: str

class GateDecision(BaseModel):
    episode_id: str
    decision: Literal["GO", "NO_GO", "ESCALATE"]
    rules_fired: list[RuleFire]
    attribution: str           # human-readable: "Blocked by Generated Rule #001 (from invoice attack)"
    evaluated_at: datetime
```

### Generated Rule Function Contract

```python
# Prompt instructs Opus to generate exactly this signature:
def detect_<attack_pattern>(verdict_board: dict) -> bool:
    """
    Docstring: attack type, source episode, behavioral pattern description.
    Returns True if this rule fires (block the payment).
    """
    # verdict_board keys: fields (list of dicts with keys:
    #   field, payment_claim, investigator_finding, status, severity)
    ...
    return bool
```

### BlandWebhookPayload / BlandWebhookResponse

```python
class BlandWebhookPayload(BaseModel):
    call_id: str
    variables: dict[str, str]  # custom vars set in Bland AI pathway
    # Expected keys in variables:
    #   operator_question: str
    #   episode_id: str
    #   override_requested: str  ("true"/"false")

class BlandWebhookResponse(BaseModel):
    response: str   # spoken by Bland AI
    # Optional routing vars (Bland AI pathway conditions read these)
    identity_verified: str | None = None  # "true"/"false" for override flow
```

## Anti-Patterns

### Anti-Pattern 1: LLM in the Enforcement Path

**What people do:** Route the VerdictBoard back through an LLM to make the block/allow decision ("ask Claude if this should be blocked").

**Why it's wrong:** Non-deterministic. Cannot be audited. Cannot be attributed. Fails under adversarial prompting. Violates the project's architectural invariant and the core judge talking point.

**Do this instead:** All enforcement is deterministic Python in SafetyGate. LLMs only generate the rule source code, which a human (or operator) can read and verify before it fires.

### Anti-Pattern 2: Passing Raw Dicts Between Pipeline Stages

**What people do:** Return `dict` from sub-agents, pass `dict` to VerdictBoardEngine, pass `dict` to SafetyGate.

**Why it's wrong:** No schema validation at boundaries, silent field omissions, impossible to test in isolation, errors surface late.

**Do this instead:** Pydantic models as return types at every boundary. `AgentVerdict.model_validate(data)` catches contract violations immediately. `VerdictBoard.model_dump()` for the exec() boundary where you need a plain dict.

### Anti-Pattern 3: Sequential Sub-Agent Execution

**What people do:** `risk = await risk_agent.analyze()`, then `compliance = await compliance_agent.validate()`, then `forensics = await forensics_agent.scan()`.

**Why it's wrong:** 3x latency increase. Sub-agents do completely independent investigations — there is no data dependency between them. Sequential execution means investigation takes 9–15 seconds instead of 3–5 seconds.

**Do this instead:** `asyncio.gather(risk, compliance, forensics, return_exceptions=True)`.

### Anti-Pattern 4: WebSocket Full-State Broadcast

**What people do:** On any change, serialize the entire investigation state and send it to all clients.

**Why it's wrong:** Dashboard panels that haven't changed re-render. Large payloads for incremental updates. Frontend can't animate individual transitions.

**Do this instead:** Emit specific named events (`agent_completed`, `rule_fired`) with only the data relevant to that event. Frontend components subscribe to the events they care about.

### Anti-Pattern 5: Aerospike Schema Discovery in Hot Path

**What people do:** `client.get()` call inside the investigation loop to check what bins exist on a record, then conditionally write.

**Why it's wrong:** Schema is defined at build time, not runtime. Discovery adds latency. Aerospike is schema-less by design but you should treat your own schema as fixed.

**Do this instead:** Define all bin names as constants in `aerospike_client.py`. Every `put()` call always writes the same set of bins. Missing fields use sentinel values (`None` or empty string), never omitted.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| Anthropic API | `AsyncAnthropic` client, one per agent class | Opus 4.6 for Supervisor + RuleGenerator; Sonnet 4.6 for sub-agents |
| Aerospike | `aerospike` Python client, connection pool at startup | All writes in episode store, all reads in trust/rule store |
| Bland AI | Inbound POST webhook during call pathway | Synchronous — Bland AI blocks on response; 8s timeout budget |
| Okta | Token introspection REST call on override request | One HTTP call per override; no session state |

### Internal Boundaries

| Boundary | Communication | Schema |
|----------|---------------|--------|
| SupervisorAgent → Sub-agents | Direct async call (asyncio.gather) | `PaymentVerdict` in, `AgentVerdict` out |
| SupervisorAgent → VerdictBoardEngine | Direct sync call | `List[AgentVerdict]` in, `VerdictBoard` out |
| VerdictBoardEngine → SafetyGate | Direct sync call | `VerdictBoard` in, `GateDecision` out |
| SafetyGate → RuleRegistry | Direct sync call (in-memory) | `dict` (VerdictBoard.model_dump()) in, `bool` out per rule |
| Any component → ConnectionManager | Direct async call | `(event_name: str, payload: dict)` |
| Any component → AerospikeStore | Direct async call | Pydantic model → `model_dump()` → bins |
| FastAPI route → SupervisorAgent | Direct async call | HTTP payload validated to Pydantic, returns `GateDecision` |
| FastAPI bland route → SupervisorAgent | Direct async call (≤8s) | `BlandWebhookPayload` → `str` |

## Sources

- [asyncio.gather docs — Python 3 official](https://docs.python.org/3/library/asyncio-task.html)
- [Using asyncio Queues for AI Task Orchestration (2026)](https://dasroot.net/posts/2026/02/using-asyncio-queues-ai-task-orchestration/)
- [Anthropic multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system)
- [FastAPI WebSocket docs](https://fastapi.tiangolo.com/advanced/websockets/)
- [Real-time Dashboard with FastAPI and WebSockets — TestDriven.io](https://testdriven.io/blog/fastapi-postgres-websockets/)
- [RestrictedPython PyPI](https://pypi.org/project/RestrictedPython/)
- [Python exec() — Real Python](https://realpython.com/python-exec/)
- [Aerospike Python Client docs](https://aerospike-python-client.readthedocs.io/en/latest/index.html)
- [Aerospike architecture overview](https://aerospike.com/docs/server/architecture/overview)
- [Bland AI webhooks tutorial](https://docs.bland.ai/tutorials/webhooks)

---
*Architecture research for: Sentinel — multi-agent payment supervision system*
*Researched: 2026-03-24*
