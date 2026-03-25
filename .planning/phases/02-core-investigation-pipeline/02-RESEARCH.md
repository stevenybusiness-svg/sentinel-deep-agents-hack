# Phase 02: Core Investigation Pipeline - Research

**Researched:** 2026-03-24
**Domain:** Multi-agent investigation pipeline — LLM agents, parallel execution, Safety Gate, Aerospike episodic memory, FastAPI WebSocket
**Confidence:** HIGH (stack verified from installed venv; patterns from Phase 1 codebase; architecture from ARCHITECTURE.md)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Payment Agent Design**
- D-01: Payment Agent is a real Sonnet 4.6 LLM with tool-use via Claude API — tools include `check_counterparty`, `verify_kyc`, `read_invoice`; agent decides which to call and in what order
- D-02: Agent receives invoice as raw PNG via Claude vision API — hidden text in the invoice is invisible to humans but readable by model, enabling genuine prompt injection manipulation
- D-03: Agent runs in a multi-turn conversation with the Supervisor — Supervisor feeds one step at a time, agent responds, Supervisor decides next step; more control over flow
- D-04: Agent's self-assessed confidence is unconstrained — let the LLM naturally respond to prompt injection; don't hardcode confidence values
- D-05: Agent output schema is a dedicated `PaymentDecision` schema (not reusing Verdict) that captures: decision (approve/deny), amount, beneficiary, account, rationale, steps_taken, confidence, claims about what it found

**Prediction Step**
- D-06: Two prediction dimensions: (1) confidence z-score from behavioral baselines, (2) step sequence deviation from expected tool-call order
- D-07: Expected step sequence defined in `behavioral_baselines.json` fixture — e.g., `['verify_counterparty', 'check_kyc', 'review_document', 'compute_risk']`; deviation = skipped or reordered steps
- D-08: Prediction executes BEFORE investigation dispatch — blind to investigation results
- D-09: Predictions include expected investigation outcomes — prediction error includes both agent behavior deviation AND investigation confirmation mismatches
- D-10: Separate `PredictionEngine` module (not embedded in Verdict Board Engine)
- D-11: Prediction errors stored as summary score + top deviations (compact, dashboard-displayable)
- D-12: Prediction errors do NOT influence Safety Gate decision in Phase 2 — stored in Episode for Phase 3 to consume

**Sub-Agent Investigation**
- D-13: All three sub-agents dispatch in parallel via `asyncio.TaskGroup` — cancel-on-first-exception
- D-14: Risk Agent receives: Payment Agent's output + behavioral baselines + original payment request
- D-15: Forensics Agent performs independent vision analysis on raw invoice PNG via Claude vision API
- D-16: Compliance Agent performs KYC ledger lookup + counterparty DB cross-reference
- D-17: Hidden text detection uses both: (1) `hidden_text_detected` in `behavioral_flags` for gate scoring, (2) structured `hidden_content` field in Verdict for rule generation

**Safety Gate Scoring**
- D-18: Comprehensive hardcoded rule set: confidence z-score threshold, claims_checked mismatches, hidden_text_detected flag, unable_to_verify count, step sequence deviation, amount threshold, beneficiary not in counterparty_db, multiple behavioral flags
- D-19: Rules are Python functions in a `rules/` directory — each rule is a `.py` file with a `score()` function returning weighted anomaly score. Gate dynamically loads all rules from directory. Same format Phase 3 will generate.
- D-20: Generated rules (Phase 3) plug into the same `rules/` directory and scoring mechanism
- D-21: Composite score threshold and scoring formula are Claude's discretion

### Claude's Discretion
- Payment Agent output schema design (D-05 gives guidance, exact fields flexible)
- Composite scoring formula — weighted sum vs max-of-criticals vs hybrid (D-20, D-21)
- Generated rules layer separation — same pipeline or visually distinct for dashboard (D-20)
- Attribution text assembly for gate rationale
- Rule file naming convention and interface contract
- Prediction error summary format details

### Deferred Ideas (OUT OF SCOPE)
- Prediction error influence on gate decision — Phase 3
- Additional prediction dimensions beyond confidence + step sequence — Phase 3
- Rule evolution across incidents — Phase 3 self-improvement loop
- Dashboard visualization of investigation tree — Phase 4
- Voice integration for live narration — Phase 5
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PIPE-01 | Payment Agent parses payment request, queries counterparty fixture DB, returns verdict with amount/beneficiary/account/confidence/steps_taken/claims_made | D-01 through D-05; Claude tool_use API with base64 vision; PaymentDecision schema |
| PIPE-02 | Supervisor dispatches Risk, Compliance, Forensics in parallel via asyncio.TaskGroup; return_exceptions=True | D-13; asyncio.TaskGroup pattern in CLAUDE.md; gather with exception handling |
| PIPE-03 | Risk Agent computes confidence z-score against behavioral baseline (mean 0.52, std 0.11); detects step-sequence deviations | D-14; behavioral_baselines.json fixture has mean/std; z-score = (x - mean) / std |
| PIPE-04 | Compliance Agent independently queries KYC ledger and agent activity log; validates agent identity claims | D-16; kyc_ledger.json and counterparty_db.json fixtures loaded via load_fixtures() |
| PIPE-05 | Forensics Agent independently scans invoice via vision model; detects hidden content | D-15; base64-encode PNG → Claude vision API; invoice_forensic.png has hidden text |
| PIPE-06 | Forensics Agent returns clean result with "no documents available" when no attachments | Handle optional document_urls list; if empty list → return clean no-docs verdict |
| PIPE-07 | Payment Agent is real Sonnet 4.6 LLM instance — not hardcoded | D-01; get_async_client() + get_model_ids()["agent"] already wired |
| ENGN-01 | Verdict Board Engine performs field-level comparison; produces mismatch list with severity tags | Existing VerdictBoard schema; deterministic comparison of agent claims vs investigator findings |
| ENGN-02 | Safety Gate applies hardcoded rules first and immutably | D-18/D-19; rules/ directory with score() functions; hardcoded = highest priority, no override |
| ENGN-03 | Safety Gate loads all generated scoring functions from rule registry; exec via RestrictedPython | D-19; RestrictedPython 8.1 installed; compile_restricted + exec pattern from ARCHITECTURE.md |
| ENGN-04 | Safety Gate outputs GO/NO-GO/ESCALATE with full attribution | GateDecision schema already defines this structure |
| ENGN-05 | exec() sandbox enforces: builtins whitelist, compile() before exec(), 5-second timeout, AST pre-check | RestrictedPython 8.1 + SAFE_BUILTINS pattern; string pre-check for import/__ |
| ENGN-06 | Safety Gate computes composite anomaly score; >=1.0 → NO-GO, >=0.6 → ESCALATE | Weighted sum pattern; thresholds from ARCHITECTURE.md |
| ENGN-07 | Prediction step computes expected VerdictBoard values from baselines before investigation; stores prediction errors | D-06 through D-12; PredictionEngine module; separate from VerdictBoardEngine |
| MEM-01 | Episode records written to Aerospike sentinel.episodes set; write latency measured | AerospikeClient.put() with time.perf_counter(); episodes set; existing health_check pattern |
| MEM-03 | Behavioral baselines in Aerospike sentinel.trust set; queried at investigation start | Trust store; baselines fixture pre-loaded on startup; query before prediction step |
| MEM-04 | Recent episodes and prediction errors queried from Aerospike at investigation start; injected into Supervisor context | scan() on sentinel.episodes with limit; inject into supervisor prompt context |
| API-01 | FastAPI server with WebSocket endpoint (/ws) emitting named investigation events | ConnectionManager class; broadcast typed WSEvent; existing EventType schema |
| API-02 | POST /investigate accepts payment request; triggers full investigation pipeline; caches active episode state | FastAPI route → supervisor; in-memory episode cache for voice Q&A; return episode_id + decision |
</phase_requirements>

---

## Summary

Phase 2 builds the complete end-to-end investigation pipeline on top of the schemas, fixtures, and infrastructure from Phase 1. The work spans five distinct subsystems: (1) a real Payment Agent that gets genuinely manipulated by hidden invoice text, (2) a Prediction Engine that forms baseline expectations before investigation, (3) three parallel sub-agents (Risk/Compliance/Forensics) dispatched via asyncio.TaskGroup, (4) a deterministic Verdict Board Engine and Safety Gate with file-based scoring rules, and (5) Aerospike episode persistence plus a FastAPI WebSocket server.

All Python package dependencies are already installed in the project's `.venv` (anthropic 0.86.0, aerospike 19.1.0, RestrictedPython 8.1, FastAPI 0.115.14, pydantic 2.12.5). The existing schemas (Verdict, VerdictBoard, Episode, WSEvent) are correct and test-proven. Phase 2 extends them rather than replacing them. The key integration points — `get_async_client()`, `get_model_ids()`, `AerospikeClient`, `load_fixtures()`, and `get_invoice_paths()` — are all ready to import.

The critical risk is the asyncio.TaskGroup dispatch: CLAUDE.md mandates TaskGroup (not gather) for cancel-on-first-exception behavior, but the existing ARCHITECTURE.md patterns show gather() with return_exceptions=True as the preferred pattern for this specific case (3 fixed agents where one failure should not abort the others). This tension must be resolved in the plan — D-13 locks TaskGroup but the requirement says `return_exceptions=True` semantics. The recommended resolution is TaskGroup with individual per-task try/except wrapping, which gives both cancel-on-critical-exception AND graceful unable_to_verify on individual agent failure.

**Primary recommendation:** Build in wave order — (1) PaymentDecision schema + Payment Agent + Prediction Engine first (pure Python, testable without Aerospike or FastAPI), (2) three sub-agents + VerdictBoardEngine + SafetyGate as the deterministic core, (3) Aerospike episode writes + trust store reads, (4) FastAPI WebSocket server wiring everything together. Each wave produces a working unit before the next depends on it.

---

## Standard Stack

### Core (all already installed in .venv)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| anthropic | 0.86.0 | Payment Agent + sub-agent LLM calls + vision | Official SDK; AsyncAnthropic instantiated once at module level; vision via base64-encoded content blocks |
| aerospike | 19.1.0 | Episode persistence, trust store, rule registry | Official sync client + ThreadPoolExecutor pattern; already wired in AerospikeClient |
| RestrictedPython | 8.1 | Safety Gate exec() sandboxing for generated rules | Installed; compile_restricted pattern; builtins whitelist |
| fastapi | 0.115.14 | HTTP routes + WebSocket /ws endpoint | Already installed; starlette WebSocket native |
| pydantic | 2.12.5 | Schema validation at every pipeline boundary | Already used for all schemas; model_dump() for exec() boundary |
| uvicorn | 0.34.x | ASGI server for FastAPI | Already in requirements; single worker for demo |
| python-dotenv | 1.0.x | Env var loading | Already used in config.py |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| asyncio (stdlib) | 3.11+ built-in | TaskGroup for parallel sub-agent dispatch | Use asyncio.TaskGroup for D-13; NOTE: Python 3.12 in venv — TaskGroup fully supported |
| base64 (stdlib) | built-in | Encode PNG invoice for Claude vision API | Used in Forensics Agent and Payment Agent for image reading |
| json (stdlib) | built-in | Serialize bins for Aerospike put() | For nested VerdictBoard serialization |
| time (stdlib) | built-in | Write latency measurement for MEM-01/MEM-05 | time.perf_counter() already used in AerospikeClient.health_check() |

### Note on Python Version

The `.venv` uses Python 3.12.13 (confirmed: `/usr/local/opt/python@3.12/bin/python3.12`). `asyncio.TaskGroup` is available in Python 3.11+ and fully supported here. All code should target 3.11+ patterns.

**Version verification (confirmed from .venv):**
- anthropic: 0.86.0 (matches CLAUDE.md spec)
- aerospike: 19.1.0 (matches CLAUDE.md spec)
- RestrictedPython: 8.1 (pyproject.toml has 8.1, CLAUDE.md says 8.2 — 8.1 is what's installed, use 8.1 patterns)
- fastapi: 0.115.14 (compatible)
- pydantic: 2.12.5 (v2, required)

---

## Architecture Patterns

### Recommended File Structure for Phase 2

```
sentinel/
├── agents/
│   ├── __init__.py              # already exists (empty)
│   ├── payment_agent.py         # NEW: Payment Agent (Sonnet 4.6, tool-use + vision)
│   ├── supervisor.py            # NEW: Supervisor (Opus 4.6, orchestrates TaskGroup)
│   ├── risk.py                  # NEW: Risk Agent (z-score, step sequence)
│   ├── compliance.py            # NEW: Compliance Agent (KYC, counterparty DB)
│   └── forensics.py             # NEW: Forensics Agent (vision, hidden text)
├── engine/
│   ├── __init__.py              # NEW
│   ├── verdict_board.py         # NEW: VerdictBoardEngine (deterministic comparison)
│   ├── prediction.py            # NEW: PredictionEngine (D-10: separate module)
│   └── safety_gate.py           # NEW: SafetyGate (hardcoded + generated rules)
├── gate/
│   ├── __init__.py              # already exists (empty)
│   └── rules/                   # NEW: hardcoded scoring rule files
│       ├── __init__.py
│       ├── rule_hidden_text.py  # hidden_text_detected → NO-GO
│       ├── rule_z_score.py      # confidence z-score anomaly
│       ├── rule_mismatch.py     # field mismatch count + severity
│       └── rule_unverifiable.py # unable_to_verify count
├── memory/
│   ├── __init__.py              # already exists
│   ├── aerospike_client.py      # already exists — no changes
│   ├── episode_store.py         # NEW: write/read episodes to sentinel.episodes
│   └── trust_store.py           # NEW: read/write baselines to sentinel.trust
├── api/
│   ├── __init__.py              # already exists (empty)
│   ├── main.py                  # NEW: FastAPI app + lifespan
│   ├── websocket.py             # NEW: ConnectionManager + /ws endpoint
│   └── routes/
│       ├── __init__.py
│       └── investigate.py       # NEW: POST /investigate
└── schemas/
    ├── __init__.py              # already exists
    ├── verdict.py               # already exists — Verdict, ClaimCheck
    ├── verdict_board.py         # already exists — VerdictBoard (needs prediction_errors field added)
    ├── episode.py               # already exists — Episode (needs prediction_report field added)
    ├── events.py                # already exists — WSEvent, EventType
    └── payment.py               # NEW: PaymentDecision schema
```

### Pattern 1: Payment Agent with Tool-Use and Vision

The Payment Agent uses Claude's tool_use feature to call `check_counterparty`, `verify_kyc`, and `read_invoice` — these are Python functions that the agent can invoke, returning fixture data. For invoice reading, the tool returns the base64-encoded image content which Claude processes via vision. The Supervisor feeds one turn at a time (D-03), then extracts the final PaymentDecision.

```python
# Source: CONTEXT.md D-01 through D-05, CLAUDE.md SDK patterns
PAYMENT_TOOLS = [
    {
        "name": "check_counterparty",
        "description": "Check if a counterparty is authorized in the counterparty database",
        "input_schema": {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"]
        }
    },
    {
        "name": "verify_kyc",
        "description": "Look up KYC verification status for a beneficiary",
        "input_schema": {
            "type": "object",
            "properties": {"beneficiary": {"type": "string"}},
            "required": ["beneficiary"]
        }
    },
    {
        "name": "read_invoice",
        "description": "Read and analyze the attached invoice document",
        "input_schema": {
            "type": "object",
            "properties": {"invoice_id": {"type": "string"}},
            "required": ["invoice_id"]
        }
    }
]

async def run_payment_agent(
    payment_request: dict,
    fixtures: FixtureData,
    invoice_path: Path,
    client: AsyncAnthropic,
    model: str,
) -> PaymentDecision:
    """Run the Payment Agent multi-turn conversation until decision reached."""
    messages = []
    # Tool result handlers map tool_name -> callable
    tool_handlers = {
        "check_counterparty": lambda args: fixtures["counterparty_db"].get(args["name"], {"found": False}),
        "verify_kyc": lambda args: fixtures["kyc_ledger"].get(args["beneficiary"], {"status": "not_found"}),
        "read_invoice": lambda args: _read_invoice_for_agent(invoice_path),
    }

    # Initial user message
    messages.append({"role": "user", "content": _format_payment_request(payment_request)})

    for _ in range(10):  # max turns
        response = await client.messages.create(
            model=model,
            max_tokens=2048,
            tools=PAYMENT_TOOLS,
            messages=messages,
            system=PAYMENT_AGENT_SYSTEM_PROMPT,
        )
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            return _extract_payment_decision(response, payment_request)

        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = tool_handlers[block.name](block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result),
                    })
            messages.append({"role": "user", "content": tool_results})

    raise RuntimeError("Payment Agent reached max turns without decision")
```

**Invoice vision encoding** (for `read_invoice` tool):
```python
import base64

def _read_invoice_for_agent(invoice_path: Path) -> dict:
    """Return base64-encoded invoice for Claude vision consumption."""
    with open(invoice_path, "rb") as f:
        data = base64.standard_b64encode(f.read()).decode("utf-8")
    return {
        "type": "image",
        "source": {"type": "base64", "media_type": "image/png", "data": data}
    }
```

Note: The tool result containing an image dict is passed back as the tool_result content — Claude's vision model processes embedded images in tool results.

### Pattern 2: asyncio.TaskGroup with Graceful unable_to_verify

D-13 mandates TaskGroup. PIPE-02 mandates `return_exceptions=True` semantics (one failure → unable_to_verify, not abort). These are reconciled by wrapping each task internally and letting TaskGroup cancel on unhandled exceptions only:

```python
# Source: CONTEXT.md D-13, REQUIREMENTS.md PIPE-02, CLAUDE.md asyncio.TaskGroup guidance
async def dispatch_investigators(
    payment_decision: PaymentDecision,
    fixtures: FixtureData,
    invoice_path: Path,
    ws_bus: ConnectionManager,
) -> list[Verdict]:
    """Dispatch all three sub-agents in parallel via TaskGroup."""
    results: list[Verdict | None] = [None, None, None]

    async def run_risk():
        try:
            results[0] = await risk_agent.analyze(payment_decision, fixtures)
        except Exception as e:
            results[0] = Verdict(
                agent_id="risk", claims_checked=[], behavioral_flags=[],
                agent_confidence=0.0, unable_to_verify=True
            )
        await ws_bus.broadcast("agent_completed", {
            "agent": "risk", "verdict": results[0].model_dump()
        })

    async def run_compliance():
        try:
            results[1] = await compliance_agent.validate(payment_decision, fixtures)
        except Exception as e:
            results[1] = Verdict(
                agent_id="compliance", claims_checked=[], behavioral_flags=[],
                agent_confidence=0.0, unable_to_verify=True
            )
        await ws_bus.broadcast("agent_completed", {
            "agent": "compliance", "verdict": results[1].model_dump()
        })

    async def run_forensics():
        try:
            results[2] = await forensics_agent.scan(payment_decision, invoice_path)
        except Exception as e:
            results[2] = Verdict(
                agent_id="forensics", claims_checked=[], behavioral_flags=[],
                agent_confidence=0.0, unable_to_verify=True
            )
        await ws_bus.broadcast("agent_completed", {
            "agent": "forensics", "verdict": results[2].model_dump()
        })

    async with asyncio.TaskGroup() as tg:
        tg.create_task(run_risk())
        tg.create_task(run_compliance())
        tg.create_task(run_forensics())

    return results  # all three, some may be unable_to_verify
```

### Pattern 3: Forensics Agent Vision Analysis

The Forensics Agent receives the raw invoice PNG, encodes it as base64, and sends it directly to Claude via vision API — completely independent of what the Payment Agent reported. This independence is the structural check.

```python
# Source: CONTEXT.md D-15, D-17
async def scan_invoice(
    invoice_path: Path,
    payment_claims: dict,
    client: AsyncAnthropic,
    model: str,
) -> Verdict:
    with open(invoice_path, "rb") as f:
        img_data = base64.standard_b64encode(f.read()).decode("utf-8")

    response = await client.messages.create(
        model=model,
        max_tokens=2048,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {"type": "base64", "media_type": "image/png", "data": img_data}
                },
                {
                    "type": "text",
                    "text": FORENSICS_PROMPT.format(claims=json.dumps(payment_claims))
                }
            ]
        }],
        system=FORENSICS_SYSTEM_PROMPT,
    )
    return _parse_forensics_response(response.content[0].text)
```

The Forensics system prompt instructs the model to:
1. Extract all visible text fields (amount, beneficiary, account)
2. Look for any text that appears in unusual colors (near-white on white, near-black on black)
3. Report any text that instructs overriding or bypassing security checks
4. Return structured JSON with `fields_found`, `hidden_content` (if any), and `hidden_text_detected` (bool)

### Pattern 4: Safety Gate Rule Loading

Rules in `gate/rules/` are standalone Python files. Each must define `score(verdict_board: dict) -> float`. The SafetyGate loads them at startup by iterating the directory:

```python
# Source: CONTEXT.md D-19, ARCHITECTURE.md Pattern 3
import importlib.util
from pathlib import Path

SAFE_BUILTINS = {
    "len": len, "any": any, "all": all, "min": min, "max": max,
    "abs": abs, "round": round, "sum": sum,
    "isinstance": isinstance, "dict": dict, "list": list,
    "str": str, "int": int, "bool": bool, "float": float,
    "True": True, "False": False, "None": None,
}

GATE_GLOBALS = {"__builtins__": SAFE_BUILTINS}

def _pre_check_source(source: str) -> None:
    """AST-level pre-check: reject any source with forbidden tokens."""
    forbidden = ["import", "__", "open", "exec", "eval"]
    for token in forbidden:
        if token in source:
            raise ValueError(f"Rule source contains forbidden token: {token!r}")

def register_rule(rule_id: str, python_source: str) -> None:
    _pre_check_source(python_source)
    namespace = dict(GATE_GLOBALS)
    compiled = compile(python_source, f"<rule_{rule_id}>", "exec")
    exec(compiled, namespace)
    fn = namespace.get("score")
    if fn is None:
        raise ValueError(f"Rule {rule_id}: no score() function found")
    _registry[rule_id] = fn

def load_rules_from_directory(rules_dir: Path) -> None:
    """Load hardcoded rules from .py files at startup."""
    for rule_file in sorted(rules_dir.glob("rule_*.py")):
        source = rule_file.read_text()
        rule_id = rule_file.stem  # e.g., "rule_hidden_text"
        register_rule(rule_id, source)
```

**Hardcoded rule file example** (`gate/rules/rule_hidden_text.py`):

```python
# score() — fires on hidden_text_detected in behavioral_flags
def score(verdict_board: dict) -> float:
    """
    Critical: hidden adversarial content detected in invoice document.
    Behavioral signature: agent was manipulated via embedded prompt injection.
    """
    flags = verdict_board.get("behavioral_flags", [])
    if "hidden_text_detected" in flags:
        return 1.5  # immediate NO-GO threshold breach
    return 0.0
```

### Pattern 5: Prediction Engine

PredictionEngine runs before investigation dispatch (D-08). It reads behavioral baselines and forms two predictions:

```python
# Source: CONTEXT.md D-06 through D-12
class PredictionEngine:
    def predict(
        self,
        payment_decision: PaymentDecision,
        baselines: dict,
        expected_step_sequence: list[str],
    ) -> PredictionReport:
        # 1. Confidence z-score prediction
        mean = baselines["payment_agent"]["mean"]  # 0.52
        std = baselines["payment_agent"]["std"]    # 0.11
        z_score = (payment_decision.confidence - mean) / std

        # 2. Step sequence deviation
        actual_steps = payment_decision.steps_taken
        expected_steps = expected_step_sequence
        deviation = self._compute_step_deviation(actual_steps, expected_steps)

        # 3. Expected investigation outcomes (for prediction error computation post-investigation)
        expected_findings = self._predict_investigation_outcomes(payment_decision)

        return PredictionReport(
            predicted_z_score=z_score,
            step_sequence_deviation=deviation,
            expected_findings=expected_findings,
            summary_score=abs(z_score) * 0.3 + (0.5 if deviation else 0.0),
        )
```

### Pattern 6: WebSocket ConnectionManager

```python
# Source: ARCHITECTURE.md Pattern 2
import json
import time
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        self.connections: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.connections.append(ws)

    def disconnect(self, ws: WebSocket):
        self.connections.remove(ws)

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

# Module-level singleton
ws_manager = ConnectionManager()
```

**FastAPI WebSocket route:**
```python
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()  # keep alive
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
```

### Pattern 7: Aerospike Episode Write

```python
# Source: ARCHITECTURE.md Pattern 4, existing AerospikeClient
import time as time_module

async def write_episode(
    episode: Episode,
    client: AerospikeClient,
) -> float:
    """Write episode to Aerospike; return write latency in ms."""
    start = time_module.perf_counter()
    bins = {
        "episode_id": episode.id,
        "timestamp": int(episode.timestamp.timestamp() * 1000),
        "action_request": json.dumps(episode.action_request),
        "gate_decision": episode.gate_decision,
        "gate_rationale": episode.gate_rationale,
        "rules_fired": json.dumps(episode.rules_fired),
        "verdict_board": json.dumps(episode.verdict_board.model_dump()),
        "prediction_report": json.dumps(episode.prediction_report) if episode.prediction_report else None,
    }
    await client.put("episodes", episode.id, bins)
    return (time_module.perf_counter() - start) * 1000
```

### Pattern 8: PaymentDecision Schema

New schema needed for Phase 2 (per D-05). Distinct from existing Verdict (which is sub-agent output):

```python
# NEW: sentinel/schemas/payment.py
from pydantic import BaseModel, Field
from typing import Literal

class PaymentDecision(BaseModel):
    """Output from the Payment Agent — what gets investigated."""
    episode_id: str
    decision: Literal["approve", "deny"]
    amount: float
    beneficiary: str
    account: str
    rationale: str          # Agent's explanation (may be corrupted by prompt injection)
    steps_taken: list[str]  # Ordered tool calls the agent made
    confidence: float = Field(ge=0.0, le=1.0)
    claims: dict[str, str]  # e.g., {"kyc_verified": "true", "counterparty_authorized": "true"}
    document_urls: list[str] = []
```

### Schema Extensions Needed

Two existing schemas need new fields (per CONTEXT.md code_context):

**VerdictBoard** — add `prediction_errors` field:
```python
# sentinel/schemas/verdict_board.py — add field
prediction_errors: dict | None = None  # PredictionReport dict, set after investigation
```

**Episode** — add `prediction_report` field:
```python
# sentinel/schemas/episode.py — add field
prediction_report: dict | None = None  # PredictionReport, stored for Phase 3 rule generation
```

### Anti-Patterns to Avoid

- **Sequential sub-agent execution:** Never `await risk_agent()` then `await compliance_agent()` sequentially — 3x latency. Use TaskGroup.
- **LLM in Safety Gate enforcement path:** Gate evaluates Python score functions, never asks Claude whether to block.
- **Hardcoding PaymentDecision fields:** Payment Agent is a real LLM (D-04) — never set confidence = 0.95 in code; let the model respond naturally to prompt injection.
- **Passing raw dicts between pipeline stages:** Use Pydantic models at every boundary; only call `.model_dump()` at the exec() boundary for the rule runner.
- **Aerospike schema discovery in hot path:** All bin names are constants; every put() writes the same fixed set of bins.
- **Using restrictedpython's compile_restricted for hardcoded rules:** Hardcoded rules are trusted Python source in the codebase. Only use compile_restricted / exec for generated (Phase 3) rules loaded from Aerospike. For Phase 2, direct file loading with standard compile() is correct.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Vision API image encoding | Custom multipart encoder | Standard `base64.standard_b64encode()` + Anthropic content block format | Anthropic SDK handles the transport; just provide correct base64 dict structure |
| asyncio timeout per agent | Custom signal/threading timeout | `asyncio.wait_for(coro, timeout=30)` wrapped around each agent call | Stdlib; TaskGroup doesn't provide per-task timeout natively |
| WebSocket state management | Custom message queuing system | Simple list of WebSocket connections in ConnectionManager | FastAPI starlette WebSocket is production-grade; no queue needed for push-only |
| z-score calculation | Custom stats library | Inline arithmetic: `(x - mean) / std` | Two-line formula; no scipy needed |
| Rule file discovery | Custom module loader | `pathlib.Path.glob("rule_*.py")` + `compile()` + `exec()` | Already established pattern in ARCHITECTURE.md |
| JSON serialization of Pydantic models | Custom serializer | `model.model_dump()` then `json.dumps()` | Pydantic v2 model_dump() handles datetime, Decimal, nested models |

**Key insight:** This pipeline is deliberately transparent and simple in its enforcement path. The complexity is in the LLM interactions and the scoring rule logic — not in the infrastructure. Avoid abstracting the deterministic parts.

---

## Common Pitfalls

### Pitfall 1: Tool Result Content Type for Vision

**What goes wrong:** When `read_invoice` tool returns image data as a dict, the tool_result content must be structured correctly. Passing the image dict as a string (json.dumps of the dict) won't trigger vision processing.

**Why it happens:** Claude expects tool_result content to be a list of content blocks (text or image), not a plain string, when the tool result contains an image.

**How to avoid:** Return tool_result with `content` as a list:
```python
{
    "type": "tool_result",
    "tool_use_id": block.id,
    "content": [
        {
            "type": "image",
            "source": {"type": "base64", "media_type": "image/png", "data": img_b64}
        }
    ]
}
```
**Warning signs:** Agent reports "could not read invoice" or describes a blank/missing image when the file exists.

### Pitfall 2: asyncio.TaskGroup Exception Propagation

**What goes wrong:** If any task in a TaskGroup raises an unhandled exception, TaskGroup cancels all other tasks. If the try/except inside each task function doesn't catch the exception before it bubbles to TaskGroup, a single agent failure kills all three agents.

**Why it happens:** TaskGroup is designed for structured concurrency with exception escalation — unlike gather(return_exceptions=True), it escalates by default.

**How to avoid:** Wrap the entire agent call in a try/except inside the task function (Pattern 2 above). The task function itself never raises — it sets the result to an unable_to_verify Verdict instead.

**Warning signs:** Investigation completes with all three agents as unable_to_verify even when only one agent call failed.

### Pitfall 3: VerdictBoard prediction_errors Field Timing

**What goes wrong:** prediction_errors are computed AFTER investigation completes (comparing expected vs actual findings). If the VerdictBoard is constructed before prediction errors are computed, the field is None at write time.

**Why it happens:** The Prediction Engine runs BEFORE investigation (D-08) to form expectations, but prediction errors (expected vs actual comparison) are only computable AFTER investigation returns findings.

**How to avoid:** Build VerdictBoard without prediction_errors first → compute prediction errors by comparing PredictionReport.expected_findings against actual findings → update VerdictBoard.prediction_errors before writing to Aerospike. Use `model_copy(update={"prediction_errors": errors})` to create updated immutable copy.

**Warning signs:** prediction_errors always None in Aerospike records even when the attack was detected.

### Pitfall 4: RestrictedPython vs Standard compile() for Hardcoded Rules

**What goes wrong:** Using `compile_restricted` (RestrictedPython's restricted compile) on hardcoded rules in the `gate/rules/` directory breaks them because RestrictedPython rewrites attribute access as `_getattr_()` calls that require a full `safe_globals` setup.

**Why it happens:** compile_restricted is designed for untrusted generated code. Hardcoded rules are trusted source — use standard `compile()`.

**How to avoid:** Phase 2 hardcoded rules: use standard `compile()` + `exec()` with SAFE_BUILTINS namespace. Phase 3 generated rules: use `compile_restricted` or standard compile with extra AST pre-check. Keep the loading mechanism consistent but the compile step configurable by rule type.

**Warning signs:** `AttributeError: _getattr_` or `NameError` when executing hardcoded rules.

### Pitfall 5: Aerospike scan() for Trust Store on Startup

**What goes wrong:** `AerospikeClient` only has `put()` and `get()` methods — no `scan()`. Trust store reads (MEM-03) and rule loading (ENGN-03, Phase 3) require scan.

**Why it happens:** Phase 1 AerospikeClient was scoped to Phase 1 requirements (INFRA-02 health check only).

**How to avoid:** Add `scan(set_name, bins)` method to AerospikeClient (or add to TrustStore/EpisodeStore wrappers):
```python
async def scan(self, set_name: str, select_bins: list[str] | None = None) -> list[dict]:
    loop = asyncio.get_running_loop()
    def _do_scan():
        scan = self._client.scan(self.namespace, set_name)
        if select_bins:
            scan.select(*select_bins)
        results = []
        scan.foreach(lambda key, meta, bins: results.append(bins))
        return results
    return await loop.run_in_executor(self._executor, _do_scan)
```
**Warning signs:** AttributeError on `client.scan()` call during startup.

### Pitfall 6: Fixture Fixture Mismatch Between conftest and Real Data

**What goes wrong:** The `conftest.py` test fixture uses "ACME Corp" and "Global Trade Partners" — these are NOT in the real `kyc_ledger.json` or `counterparty_db.json` fixtures. Tests that use `conftest.fixture_data` will not match the attack scenario.

**Why it happens:** conftest uses placeholder data from Phase 1 that pre-dates real fixtures.

**How to avoid:** New Phase 2 tests should import `load_fixtures()` directly for integration tests, and only use conftest.fixture_data for pure unit tests that don't need to match real fixture contents. The attack scenario uses "Meridian Logistics" (absent from kyc_ledger.json — this is intentional per Phase 1 STATE.md).

**Warning signs:** Compliance Agent returns "verified" for Meridian Logistics in tests but "not_found" in live demo.

### Pitfall 7: PaymentDecision confidence Field — Let the LLM Set It

**What goes wrong:** Extracting agent confidence from the response and defaulting it to a hardcoded value if parsing fails undermines the entire threat model (D-04).

**Why it happens:** Defensive coding that provides fallback values.

**How to avoid:** If the Payment Agent doesn't return a confidence value parseable as float in [0,1], raise an error — don't substitute a default. An unparseable confidence is itself a signal. Fail loudly during development so the prompt can be fixed.

**Warning signs:** confidence always 0.52 (baseline mean) — this means the extraction fallback is silently firing.

---

## Code Examples

### Supervisor Orchestration Flow

```python
# Source: ARCHITECTURE.md Primary Investigation Flow
async def run_investigation(
    payment_request: dict,
    ws_bus: ConnectionManager,
    fixtures: FixtureData,
    aerospike: AerospikeClient,
) -> Episode:
    episode_id = str(uuid.uuid4())
    await ws_bus.broadcast("investigation_started", {
        "episode_id": episode_id,
        "payment_summary": payment_request,
        "timestamp": time.time(),
    })

    # Step 1: Load baselines from trust store (MEM-03, MEM-04)
    baselines = await trust_store.get_baselines(aerospike)
    recent_episodes = await episode_store.get_recent(aerospike, limit=5)

    # Step 2: Run Payment Agent
    payment_decision = await payment_agent.run(payment_request, fixtures, client)

    # Step 3: Prediction step BEFORE investigation (D-08)
    prediction_report = prediction_engine.predict(
        payment_decision, baselines, EXPECTED_STEP_SEQUENCE
    )

    # Step 4: Parallel sub-agent dispatch (D-13, PIPE-02)
    verdicts = await dispatch_investigators(payment_decision, fixtures, invoice_path, ws_bus)

    # Step 5: Compute prediction errors (expected vs actual)
    prediction_errors = prediction_engine.compute_errors(prediction_report, verdicts)

    # Step 6: Verdict Board Engine (ENGN-01)
    verdict_board = verdict_board_engine.assemble(payment_decision, verdicts, prediction_errors)
    await ws_bus.broadcast("verdict_board_assembled", {"board": verdict_board.model_dump()})

    # Step 7: Safety Gate (ENGN-02 through ENGN-06)
    gate_result = safety_gate.evaluate(verdict_board)
    await ws_bus.broadcast("gate_evaluated", {
        "decision": gate_result.decision,
        "rules_fired": gate_result.rules_fired,
        "attribution": gate_result.attribution,
        "composite_score": gate_result.composite_score,
    })

    # Step 8: Write episode to Aerospike (MEM-01)
    episode = Episode(
        id=episode_id,
        action_request=payment_request,
        agent_verdicts=verdicts,
        verdict_board=verdict_board,
        gate_decision=gate_result.decision,
        gate_rationale=gate_result.attribution,
        rules_fired=gate_result.rules_fired,
        prediction_report=prediction_errors,
    )
    latency_ms = await episode_store.write(aerospike, episode)
    await ws_bus.broadcast("episode_written", {
        "episode_id": episode_id,
        "aerospike_write_latency_ms": latency_ms,
    })

    return episode
```

### Safety Gate Composite Scoring

```python
# Source: ARCHITECTURE.md Pattern 3; thresholds from ARCHITECTURE.md Layer 4
# Composite score: >= 1.0 → NO-GO | >= 0.6 → ESCALATE | else → GO
from typing import Literal

NOGO_THRESHOLD = 1.0
ESCALATE_THRESHOLD = 0.6

@dataclass
class RuleContribution:
    rule_id: str
    rule_type: Literal["hardcoded", "generated"]
    score: float
    description: str

def evaluate(self, verdict_board: VerdictBoard) -> GateEvaluation:
    board_dict = verdict_board.model_dump()
    contributions: list[RuleContribution] = []

    for rule_id, (fn, rule_type) in self._registry.items():
        try:
            score = fn(board_dict)
            if not isinstance(score, (int, float)):
                score = 0.0
        except Exception:
            score = 0.0
        contributions.append(RuleContribution(
            rule_id=rule_id,
            rule_type=rule_type,
            score=float(score),
            description=getattr(fn, "__doc__", rule_id) or rule_id,
        ))

    composite = sum(c.score for c in contributions)
    if composite >= NOGO_THRESHOLD:
        decision = "NO-GO"
    elif composite >= ESCALATE_THRESHOLD:
        decision = "ESCALATE"
    else:
        decision = "GO"

    attribution = self._build_attribution(contributions, decision)
    return GateEvaluation(
        decision=decision,
        composite_score=composite,
        contributions=contributions,
        attribution=attribution,
        rules_fired=[c.rule_id for c in contributions if c.score > 0],
    )
```

### FastAPI App with Lifespan

```python
# Source: FastAPI docs — lifespan events for startup/shutdown
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    aerospike_client = get_aerospike_client()
    aerospike_client.connect()
    await load_generated_rules_from_aerospike(aerospike_client)
    yield
    # Shutdown
    aerospike_client.close()

app = FastAPI(title="Sentinel", lifespan=lifespan)
app.include_router(investigate_router)
app.include_router(ws_router)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `asyncio.gather()` for parallel agents | `asyncio.TaskGroup` (3.11+) | Python 3.11 (2022) | Structured concurrency with cancel-on-exception; CLAUDE.md mandates TaskGroup |
| Full WebSocket state broadcast | Named event push (per-event payloads) | React 18 era (2022+) | Smaller payloads; frontend can animate individual transitions |
| `reactflow` package name | `@xyflow/react` package name | 2023 (v12 rebranding) | New features (v12.4.4); old package still works but CLAUDE.md says use @xyflow/react |
| `aioaerospike` async library | Official sync client + ThreadPoolExecutor | Aug 2025 (aioaerospike archived) | CLAUDE.md mandates sync + executor; Phase 1 already uses this pattern |
| Pydantic v1 | Pydantic v2 | FastAPI 0.115 requirement | .model_dump() replaces .dict(); model_validate() replaces parse_obj() |

**Deprecated/outdated:**
- `asyncio.wait_for()` with `asyncio.shield()` for timeout/cancel: Use `asyncio.timeout()` context manager (3.11+) instead
- `datetime.utcnow()`: Deprecated in 3.12; use `datetime.now(datetime.UTC)` (tests have this warning)
- `reactflow` npm package: Use `@xyflow/react` (already in frontend)

---

## Open Questions

1. **Tool result vision content format — multi-turn tool use**
   - What we know: Anthropic supports image content blocks in messages. Tool results can have list content.
   - What's unclear: Whether Claude processes image content inside a tool_result block the same way as a direct user message image. The tool result format for vision hasn't been explicitly verified via live API call.
   - Recommendation: Test the Payment Agent's `read_invoice` tool in isolation first (a standalone test that calls the API with a tool_result containing an image block) before integrating into the multi-turn conversation. Have a fallback: if vision-in-tool-result doesn't work, pass the invoice image as a separate user message after the tool result.

2. **asyncio.TaskGroup per-task timeout**
   - What we know: TaskGroup cancels all tasks if any raises. asyncio.wait_for() provides per-coroutine timeout.
   - What's unclear: Whether wrapping each agent call in `asyncio.wait_for(coro, timeout=30)` inside the task function interacts cleanly with TaskGroup's cancellation semantics.
   - Recommendation: Use `asyncio.wait_for()` per agent call inside the task wrapper. If it times out, it raises `asyncio.TimeoutError`, which the per-task try/except catches and converts to unable_to_verify. This is clean.

3. **VerdictBoard schema — prediction_errors field type**
   - What we know: D-11 says "summary score + top deviations". Phase 3 needs to read prediction_errors from Aerospike to generate rules.
   - What's unclear: Whether prediction_errors should be a nested Pydantic model or `dict | None`. The CONTEXT.md says "compact, dashboard-displayable."
   - Recommendation: Use `dict | None` for Phase 2 (loose per D-07 pattern) with a defined shape: `{"summary_score": float, "top_deviations": list[str], "z_score": float, "step_deviation": bool}`. Phase 3 can define a strict model if needed.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12 (.venv) | All backend code | ✓ | 3.12.13 | — |
| anthropic SDK | Payment Agent, sub-agents | ✓ | 0.86.0 | — |
| aerospike Python client | MEM-01, MEM-03, MEM-04 | ✓ | 19.1.0 | — |
| RestrictedPython | ENGN-05 | ✓ | 8.1 | — |
| fastapi | API-01, API-02 | ✓ | 0.115.14 | — |
| pydantic v2 | All schemas | ✓ | 2.12.5 | — |
| Aerospike Docker container | MEM-01, MEM-03, MEM-04 | UNKNOWN | — | Tests without Aerospike use mock; demo requires running container |
| Docker | Aerospike container startup | UNKNOWN | — | Manual Aerospike install if Docker absent |
| ANTHROPIC_API_KEY | All LLM calls | UNKNOWN (env var) | — | Tests mock; demo requires real key |

**Missing dependencies with no fallback:**
- Aerospike Docker container must be running for MEM-01/MEM-03/MEM-04 integration. docker-compose.yml exists in repo — planners should include a "start Aerospike" step in Wave 0 of any plan touching memory.
- ANTHROPIC_API_KEY must be set for Payment Agent and sub-agent tests that make real API calls.

**Missing dependencies with fallback:**
- Docker: if unavailable, Aerospike can be run natively; docker-compose.yml is the standard path per DEMO-01.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio 0.24 |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (asyncio_mode = "auto") |
| Quick run command | `.venv/bin/pytest tests/ -x -q --tb=short` |
| Full suite command | `.venv/bin/pytest tests/ -v` |
| Venv activation | `.venv/bin/pytest` (direct invocation, no activate needed) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PIPE-01 | PaymentDecision schema valid/invalid construction | unit | `.venv/bin/pytest tests/test_payment_agent.py -x` | ❌ Wave 0 |
| PIPE-02 | Sub-agents complete with overlapping timestamps (parallel) | integration | `.venv/bin/pytest tests/test_supervisor.py::test_parallel_dispatch -x` | ❌ Wave 0 |
| PIPE-03 | Risk Agent z-score computation for confidence 0.92 (attack fixture) | unit | `.venv/bin/pytest tests/test_risk_agent.py::test_z_score -x` | ❌ Wave 0 |
| PIPE-04 | Compliance Agent detects Meridian Logistics KYC gap | unit | `.venv/bin/pytest tests/test_compliance_agent.py::test_meridian_gap -x` | ❌ Wave 0 |
| PIPE-05 | Forensics Agent extracts hidden_text_detected from invoice_forensic.png | integration | `.venv/bin/pytest tests/test_forensics_agent.py::test_hidden_text -x` | ❌ Wave 0 |
| PIPE-06 | Forensics Agent returns clean result when no documents | unit | `.venv/bin/pytest tests/test_forensics_agent.py::test_no_docs -x` | ❌ Wave 0 |
| PIPE-07 | Payment Agent schema construction + confidence in valid range | unit | `.venv/bin/pytest tests/test_payment_agent.py::test_schema -x` | ❌ Wave 0 |
| ENGN-01 | VerdictBoardEngine produces mismatch list with severity tags | unit | `.venv/bin/pytest tests/test_verdict_board.py -x` | ❌ Wave 0 |
| ENGN-02 | Hardcoded rule fires on hidden_text_detected, overrides composite | unit | `.venv/bin/pytest tests/test_safety_gate.py::test_hidden_text_nogo -x` | ❌ Wave 0 |
| ENGN-03 | Safety Gate loads .py rule files from rules/ directory | unit | `.venv/bin/pytest tests/test_safety_gate.py::test_rule_loading -x` | ❌ Wave 0 |
| ENGN-04 | Gate outputs NO-GO with attribution naming rules and mismatches | unit | `.venv/bin/pytest tests/test_safety_gate.py::test_attribution -x` | ❌ Wave 0 |
| ENGN-05 | exec() sandbox rejects rule source containing "import" | unit | `.venv/bin/pytest tests/test_safety_gate.py::test_sandbox -x` | ❌ Wave 0 |
| ENGN-06 | Composite score ≥1.0 → NO-GO; ≥0.6 → ESCALATE; else → GO | unit | `.venv/bin/pytest tests/test_safety_gate.py::test_thresholds -x` | ❌ Wave 0 |
| ENGN-07 | PredictionEngine produces z-score and step_deviation before investigation | unit | `.venv/bin/pytest tests/test_prediction.py -x` | ❌ Wave 0 |
| MEM-01 | Episode written to Aerospike; latency_ms returned | integration | `.venv/bin/pytest tests/test_episode_store.py -x` | ❌ Wave 0 |
| MEM-03 | Behavioral baselines readable from trust store | integration | `.venv/bin/pytest tests/test_trust_store.py -x` | ❌ Wave 0 |
| MEM-04 | Recent episodes queryable from Aerospike at investigation start | integration | `.venv/bin/pytest tests/test_episode_store.py::test_scan_recent -x` | ❌ Wave 0 |
| API-01 | WebSocket /ws accepts connection and receives investigation_started event | integration | `.venv/bin/pytest tests/test_api.py::test_ws_events -x` | ❌ Wave 0 |
| API-02 | POST /investigate returns 200 with episode_id and decision | integration | `.venv/bin/pytest tests/test_api.py::test_investigate_endpoint -x` | ❌ Wave 0 |

Note: PIPE-05 (Forensics vision test) and MEM-01/MEM-03/MEM-04 (Aerospike tests) require live services. Mark with `@pytest.mark.integration` and skip in CI without Aerospike.

### Sampling Rate

- **Per task commit:** `.venv/bin/pytest tests/ -x -q --tb=short -m "not integration"`
- **Per wave merge:** `.venv/bin/pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

All Phase 2 test files must be created before implementation:
- [ ] `tests/test_payment_agent.py` — covers PIPE-01, PIPE-07
- [ ] `tests/test_supervisor.py` — covers PIPE-02 (parallel dispatch timing)
- [ ] `tests/test_risk_agent.py` — covers PIPE-03
- [ ] `tests/test_compliance_agent.py` — covers PIPE-04
- [ ] `tests/test_forensics_agent.py` — covers PIPE-05, PIPE-06
- [ ] `tests/test_verdict_board.py` — covers ENGN-01
- [ ] `tests/test_safety_gate.py` — covers ENGN-02 through ENGN-06
- [ ] `tests/test_prediction.py` — covers ENGN-07
- [ ] `tests/test_episode_store.py` — covers MEM-01, MEM-04
- [ ] `tests/test_trust_store.py` — covers MEM-03
- [ ] `tests/test_api.py` — covers API-01, API-02
- [ ] `tests/conftest.py` update — add `fixture_data_real` fixture using `load_fixtures()` for attack scenario tests

Existing infrastructure: `conftest.py`, `asyncio_mode = "auto"`, pytest 8.x, pytest-asyncio 0.24 — all ready. No new framework install needed.

---

## Project Constraints (from CLAUDE.md)

These apply to all Phase 2 implementation and must not be violated:

| Constraint | Enforcement |
|------------|-------------|
| Python 3.11+ — use asyncio.TaskGroup | All agent dispatch uses TaskGroup (not gather) |
| asyncio.TaskGroup cancels siblings on exception | Wrap each agent task body in try/except to prevent escalation |
| AsyncAnthropic client: instantiate once at module level | One shared client instance in agents/ package __init__ or supervisor |
| Safety Gate: no LLM in enforcement path | Gate evaluates Python score() functions only |
| Aerospike: sync client + ThreadPoolExecutor | Use existing AerospikeClient pattern; never import aioaerospike |
| RestrictedPython for exec() safety | Use SAFE_BUILTINS whitelist + AST pre-check for "import", "__" |
| Pydantic v2 — no v1 patterns | Use model_dump() not .dict(), model_validate() not parse_obj() |
| Demo reliability first | Core pipeline must be bulletproof before any polish; no voice until pipeline is stable |
| Payment Agent must be real Sonnet 4.6 LLM | No hardcoded decision values; agent reasoning must be authentic |
| Aerospike latency must be visible on dashboard | Emit aerospike_write_latency_ms in episode_written WS event |
| LangChain / LlamaIndex forbidden | Direct anthropic SDK calls only |
| `eval()` forbidden for Safety Gate rules | Use `exec()` with `compile()` and restricted namespace |
| @xyflow/react not reactflow | Frontend already uses @xyflow/react@12.4.4 |
| aioaerospike forbidden (archived Aug 2025) | Use official aerospike + ThreadPoolExecutor |

---

## Sources

### Primary (HIGH confidence)
- `sentinel/schemas/` — All existing Pydantic models (Verdict, VerdictBoard, Episode, WSEvent) verified by reading source
- `sentinel/memory/aerospike_client.py` — AerospikeClient API verified by reading source
- `sentinel/llm_client.py` — get_async_client(), get_model_ids() verified by reading source
- `sentinel/fixtures/__init__.py` — load_fixtures(), get_invoice_paths() verified by reading source
- `.planning/phases/02-core-investigation-pipeline/02-CONTEXT.md` — All decisions D-01 through D-21 locked
- `.planning/research/ARCHITECTURE.md` — Complete pattern library verified (asyncio.gather pattern, ConnectionManager, exec() sandbox, Aerospike schema)
- `.venv/bin/pip show output` — Package versions confirmed: anthropic 0.86.0, aerospike 19.1.0, RestrictedPython 8.1, fastapi 0.115.14, pydantic 2.12.5
- `pyproject.toml` — Test configuration (asyncio_mode=auto, testpaths=tests) verified
- `tests/conftest.py` — Existing test infrastructure verified (40 tests pass)

### Secondary (MEDIUM confidence)
- `.planning/research/FEATURES.md` — Feature prioritization and anti-features for planning guidance
- `CLAUDE.md §Technology Stack` — SDK patterns, gotchas, forbidden patterns
- `sentinel/fixtures/*.json` — Fixture data shapes verified (Meridian Logistics absent from kyc_ledger.json confirmed)

### Tertiary (informational)
- `.planning/STATE.md` — Phase 1 decisions and accumulated context
- `.planning/REQUIREMENTS.md` — Full requirement set for cross-reference

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all packages verified installed in .venv
- Architecture: HIGH — patterns verified from ARCHITECTURE.md and existing codebase
- Pitfalls: HIGH for tool/runtime pitfalls (based on code inspection); MEDIUM for Anthropic tool_result vision format (needs live API verification)
- Test infrastructure: HIGH — test framework operational (40 tests passing)

**Research date:** 2026-03-24
**Valid until:** 2026-04-24 (stable stack — packages pinned, no fast-moving deps)
