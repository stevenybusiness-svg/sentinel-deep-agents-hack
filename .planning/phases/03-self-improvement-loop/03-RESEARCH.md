# Phase 3: Self-Improvement Loop - Research

**Researched:** 2026-03-25
**Domain:** LLM-generated Python code, Safety Gate rule lifecycle, Aerospike rule persistence, WebSocket streaming
**Confidence:** HIGH

## Summary

Phase 3 implements the core value proposition of Sentinel: after an operator confirms an attack, Opus 4.6 generates an inspectable Python scoring function from the episode's prediction errors, validates it against a 4-check harness, deploys it live to the Safety Gate, and the rule fires on the next attack — then evolves after a second confirmation. All infrastructure from Phase 2 is already in place: `SafetyGate.register_rule()`, `load_rules_from_directory()`, `store_prediction_history()`, `get_episode()`, and the WebSocket broadcast system all exist and are tested.

The two highest-risk implementation decisions are: (1) the Opus 4.6 rule generation prompt — it must consistently produce syntactically correct Python using only VerdictBoard fields, returning a float, with no forbidden tokens; and (2) hot-reloading generated rules into the in-memory SafetyGate without restarting the server. Both have clear solutions given the existing infrastructure.

The self-improvement demo arc runs in three steps: `/investigate` Phase 1 attack → `/confirm` (rule generated, streamed live) → `/investigate` Phase 2 attack → hardcoded rules insufficient but generated rule pushes over threshold, attribution reads "Blocked by Generated Rule #001 (learned from Episode #001) | Deployed Xs ago" → `/confirm` Phase 2 attack → rule evolves to v2.

**Primary recommendation:** Build `POST /confirm` as a thin route that calls a `RuleGenerator` service class; stream Opus 4.6 output token-by-token via the existing `ws_manager.broadcast` pattern; write the validated `.py` file to `sentinel/gate/rules/` and call `gate.load_rules_from_directory()` for hot reload; store provenance in Aerospike `sentinel.rules` set using the identical `put()`/`get()` pattern already established for `episodes` and `trust` sets.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01:** `POST /confirm` accepts `{ episode_id: str, attack_type: str }` — `attack_type` drives rule generation prompt framing (e.g., `"prompt_injection"`, `"identity_spoofing"`).

**D-02:** `POST /confirm` returns `202 Accepted` immediately; rule generation streams token-by-token to the dashboard via WebSocket. Judges watch Python code appear in real time. WebSocket event type: `rule_generating` with streaming content, followed by `rule_deployed` on success or `rule_generation_failed` on all-retry failure.

**D-03:** On validation pass, write the generated rule as a `.py` file to `sentinel/gate/rules/` (e.g., `rule_generated_001.py`) AND store in Aerospike `sentinel.rules` set. Filesystem is the execution path (picked up immediately by `SafetyGate.load_rules_from_directory()`); Aerospike is the source of truth for provenance.

**D-04:** Aerospike `sentinel.rules` record bins: `rule_id` (str), `source` (str, full Python function source), `episode_ids` (JSON list), `prediction_errors` (JSON), `timestamp` (int ms), `version` (int, starts at 1). Rule key = `rule_id`.

**D-05:** 4 validation checks in order:
1. RestrictedPython `compile_restricted()` parses and compiles without error
2. Static string scan: reject source containing `import`, `__`, `open`, `exec`, `eval`
3. `score(attack_fixture_verdict_board) > 0.6` — fires on the confirmed attack's VerdictBoard
4. `score(clean_baseline_verdict_board) < 0.2` — does not fire on a clean baseline fixture
All 4 must pass for deployment.

**D-06:** On validation failure, inject the specific failure reason back into the Opus 4.6 generation prompt and retry. Up to 3 attempts total. If all 3 fail, emit `rule_generation_failed` WebSocket event. Do NOT deploy a rule that fails validation.

**D-07:** Clean baseline fixture = hard-coded `CLEAN_BASELINE_VERDICT_BOARD` dict in the validation harness (confidence ~0.55, z_score ~0.8, empty behavioral_flags, no mismatches, no unable_to_verify).

**D-08:** Evolution triggers automatically when `POST /confirm` is called and `generated_rules_fired` in the episode is non-empty. No extra operator endpoint needed.

**D-09:** Evolution prompt includes: Rule v1 source + both episodes' VerdictBoards + both episodes' prediction error sets. Instructs Opus 4.6 to drop conditions from only one incident, strengthen conditions in both.

**D-10:** Evolved rule (v2) overwrites existing `.py` file on disk AND writes new Aerospike record with `version=2`, `episode_ids=[ep1_id, ep2_id]`, combined prediction errors. v1 not preserved.

### Claude's Discretion
- Exact Opus 4.6 system prompt and user prompt structure for rule generation
- Rule file naming convention (e.g., `rule_generated_001.py` vs `rule_auto_001.py`)
- `rule_id` assignment scheme (counter-based from Aerospike scan, or UUID prefix)
- Exact `CLEAN_BASELINE_VERDICT_BOARD` values for validation harness
- Aerospike `sentinel.rules` set name
- WebSocket event schema for `rule_generating` streaming tokens vs. `rule_deployed` complete event

### Deferred Ideas (OUT OF SCOPE)
- Manual `/evolve/{rule_id}` endpoint
- Preserving v1 as a separate firing rule alongside v2
- Multiple generated rules per incident
- Rule deprecation / rollback endpoint
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| LEARN-01 | On operator-confirmed attack, extract prediction errors from episode | `get_episode()` and `trust_store.get()` with key `prediction_{episode_id}` already exist; prediction_report stored in episode record |
| LEARN-02 | Generated scoring function is behavioral — VerdictBoard fields only, returns float, has docstring | Prompt engineering for Opus 4.6; the 8 existing hardcoded rules serve as exact few-shot examples; function signature `def score(verdict_board: dict) -> float` is the established contract |
| LEARN-03 | Generated function passes 4-check validation harness before deployment | `SafetyGate.register_rule()` already implements checks 1+2 (compile_restricted + forbidden token scan); checks 3+4 are new test execution against fixture VerdictBoards |
| LEARN-04 | Validated function deployed to Safety Gate registry with Aerospike provenance | `SafetyGate.register_rule()` for in-memory; `gate.load_rules_from_directory()` for hot reload; `AerospikeClient.put()` for provenance in `sentinel.rules` set |
| LEARN-05 | Phase 2 attack blocked by generated rule from Phase 1; attribution format exact | `SafetyGate.evaluate()` returns `rule_contributions` with `is_generated=True`; attribution string must be constructed in the confirm route or a post-processing step |
| LEARN-06 | Rule evolution: second confirmed incident generates refined v2 function | Reads `generated_rules_fired` from episode (already stored in Episode.generated_rules_fired); evolution prompt feeds both VerdictBoards + prediction errors to Opus 4.6 |
| MEM-02 | Rule source, provenance, version history in Aerospike `sentinel.rules` set; fire_count atomic increment; load at startup via scan() | `AerospikeClient.put()`/`get()` pattern established; need `scan()` implementation for startup load; need `increment()` or read-modify-write for fire_count |
| MEM-05 | Aerospike write latency measured per operation, exposed via API, shown on dashboard | Pattern from `write_episode()` using `time.perf_counter()` — identical approach for rule writes; new `/metrics` or extended `/health` endpoint |
| API-03 | POST /confirm triggers scoring function generation pipeline after confirmed attack | New FastAPI route in `sentinel/api/routes/confirm.py`; returns 202, spawns background task via `asyncio.create_task()` |
</phase_requirements>

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| anthropic (AsyncAnthropic) | 0.86.0 (installed, verified) | Opus 4.6 rule generation with streaming | `client.messages.stream()` context manager yields `text` events token-by-token; already used in Phase 2 supervisor |
| RestrictedPython | 8.2 (installed, verified) | Compile-time sandboxing of generated rules | Already used in `SafetyGate.register_rule()`; `compile_restricted()` is the project's hard constraint |
| aerospike | 19.1.0 (installed) | Rule provenance persistence in `sentinel.rules` set | Same client pattern as `episodes` and `trust` sets; `ThreadPoolExecutor` pattern already established |
| FastAPI / asyncio | 0.115.x / stdlib | POST /confirm route + background task dispatch | `asyncio.create_task()` for non-blocking rule generation; lifespan-scoped `app_state` for gate access |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pydantic v2 | 2.x (installed) | Request/response schemas for /confirm endpoint | `ConfirmRequest`, `ConfirmResponse` models per existing pattern |
| time.perf_counter | stdlib | Aerospike write latency measurement (MEM-05) | Already used in `write_episode()`; apply same pattern in `write_rule()` |
| ast (stdlib) | stdlib | Additional AST-level validation beyond RestrictedPython | `ast.parse()` before compile_restricted for early error detection |
| json (stdlib) | stdlib | Serialize `episode_ids` and `prediction_errors` bins for Aerospike | Same pattern as all existing stores |

**No new dependencies required.** All libraries for Phase 3 are already installed.

---

## Architecture Patterns

### Recommended Project Structure

New files Phase 3 adds:
```
sentinel/
├── api/routes/
│   └── confirm.py               # POST /confirm route (API-03)
├── engine/
│   └── rule_generator.py        # RuleGenerator class: generate, validate, deploy
├── memory/
│   └── rule_store.py            # write_rule(), load_rules_from_aerospike(), increment_fire_count()
├── gate/rules/
│   └── rule_generated_001.py    # Written at runtime by RuleGenerator (D-03)
tests/
└── test_rule_generator.py       # Unit tests for RuleGenerator: LEARN-01 through LEARN-06
```

### Pattern 1: POST /confirm — 202 + Background Task

`POST /confirm` must return `202 Accepted` immediately (D-02). Rule generation is long-running (Opus 4.6 streaming). Use `asyncio.create_task()` to spawn the background pipeline:

```python
# sentinel/api/routes/confirm.py
from fastapi import APIRouter, BackgroundTasks
import asyncio

router = APIRouter()

@router.post("/confirm", status_code=202)
async def confirm(req: ConfirmRequest) -> ConfirmResponse:
    from sentinel.api.main import app_state
    episode = app_state["active_episodes"].get(req.episode_id)
    # Spawn background rule generation — does not block the 202 response
    asyncio.create_task(
        _run_rule_generation(req, episode, app_state)
    )
    return ConfirmResponse(episode_id=req.episode_id, status="accepted")
```

The background task updates the episode's `operator_confirmation` and `attack_type`, then calls `RuleGenerator`.

### Pattern 2: Opus 4.6 Streaming → WebSocket Relay

The `client.messages.stream()` context manager yields `text` delta events. Each delta broadcasts a `rule_generating` event to connected dashboard clients:

```python
# Source: anthropic SDK 0.86.0, messages.stream() API
async with llm_client.messages.stream(
    model=models["supervisor"],   # claude-opus-4-6
    max_tokens=1024,
    system=RULE_GEN_SYSTEM_PROMPT,
    messages=[{"role": "user", "content": user_prompt}],
) as stream:
    full_source = ""
    async for text in stream.text_stream:
        full_source += text
        await ws.broadcast(
            event="rule_generating",
            episode_id=episode_id,
            data={"token": text, "accumulated": full_source},
        )
    # stream.get_final_message() available after context exit
```

**Important:** The EventType Literal in `sentinel/schemas/events.py` currently has 7 values. Phase 3 adds `rule_generating` and `rule_generation_failed` — the Literal must be extended. Current values: `investigation_started`, `agent_completed`, `verdict_board_assembled`, `gate_evaluated`, `episode_written`, `rule_generated`, `rule_deployed`. Need to add: `rule_generating`, `rule_generation_failed`.

### Pattern 3: 4-Check Validation Harness

Validation runs sequentially; failure at any check injects the error reason into the retry prompt:

```python
# sentinel/engine/rule_generator.py
CLEAN_BASELINE_VERDICT_BOARD = {
    "mismatches": [],
    "behavioral_flags": [],
    "agent_confidence": 0.55,
    "confidence_z_score": 0.8,
    "step_sequence_deviation": False,
    "hardcoded_rule_fired": False,
    "unable_to_verify": [],
    "prediction_errors": None,
}

def validate_rule(source: str, attack_vb: dict) -> tuple[bool, str]:
    """Returns (passed, failure_reason). failure_reason is '' on pass."""
    # Check 1: Static forbidden token scan (matches SafetyGate._pre_check_source)
    for token in ["import", "__", "open", "exec", "eval"]:
        if token in source:
            return False, f"Source contains forbidden token: {token!r}"
    # Check 2: RestrictedPython compile
    try:
        code = compile_restricted(source, "<validate>", "exec")
    except Exception as e:
        return False, f"compile_restricted failed: {e}"
    # Check 3+4: Execute against fixtures
    namespace = {}
    exec(code, {"__builtins__": SAFE_BUILTINS, ...}, namespace)
    score_fn = namespace["score"]
    attack_score = score_fn(attack_vb)
    if attack_score <= 0.6:
        return False, f"Attack fixture score {attack_score:.3f} must be > 0.6"
    clean_score = score_fn(CLEAN_BASELINE_VERDICT_BOARD)
    if clean_score >= 0.2:
        return False, f"Clean baseline score {clean_score:.3f} must be < 0.2"
    return True, ""
```

Note: The static scan runs before `compile_restricted` because `__` is a forbidden token but `compile_restricted` may not catch it as a compile error. Order matches D-05.

### Pattern 4: Hot-Reload After File Write

After writing `rule_generated_001.py` to disk, call `load_rules_from_directory()` on the in-memory `SafetyGate` instance:

```python
# After writing the .py file:
gate: SafetyGate = app_state["safety_gate"]
rules_dir = Path("sentinel/gate/rules")
gate.load_rules_from_directory(rules_dir)
# Generated rule is now live for all subsequent evaluate() calls
```

`load_rules_from_directory()` is idempotent — it resets `_hardcoded_rules` and reloads all `rule_*.py` files. Generated rules deployed as `.py` files are picked up here because they follow the `rule_*.py` naming pattern. **However**, generated rules are also registered in `_generated_rules` via `register_rule()` at deploy time. To avoid double-firing, the file naming must NOT use the `rule_generated_*.py` pattern, OR the `load_rules_from_directory()` must filter them. The cleanest approach: write the file as `rule_generated_001.py` (matches glob `rule_*.py`) and rely on `load_rules_from_directory()` exclusively for loading — do NOT also call `register_rule()` at deploy time. Use `register_rule()` only at startup when loading from Aerospike (MEM-02).

### Pattern 5: Aerospike Rule Store

Follow the identical pattern used by `episode_store.py` and `trust_store.py`:

```python
# sentinel/memory/rule_store.py
RULES_SET = "rules"

async def write_rule(rule_id: str, source: str, episode_ids: list[str],
                     prediction_errors: dict, version: int,
                     client: AerospikeClient) -> float:
    """Write rule to Aerospike sentinel.rules set. Returns write latency ms (MEM-05)."""
    start = time.perf_counter()
    bins = {
        "rule_id": rule_id,
        "source": source,
        "episode_ids": json.dumps(episode_ids),
        "prediction_errors": json.dumps(prediction_errors),
        "timestamp": int(time.time() * 1000),
        "version": version,
        "fire_count": 0,
    }
    await client.put(RULES_SET, rule_id, bins)
    return round((time.perf_counter() - start) * 1000, 2)

async def load_all_rules(client: AerospikeClient) -> list[dict]:
    """Scan Aerospike sentinel.rules set. Called at startup for MEM-02."""
    # AerospikeClient needs a scan() method — see Open Questions
    ...

async def increment_fire_count(rule_id: str, client: AerospikeClient) -> None:
    """Atomic increment of fire_count bin via read-modify-write."""
    try:
        bins = await client.get(RULES_SET, rule_id)
        bins["fire_count"] = bins.get("fire_count", 0) + 1
        await client.put(RULES_SET, rule_id, bins)
    except Exception:
        pass  # Non-critical — fire_count is telemetry only
```

### Pattern 6: Aerospike Scan for Startup Rule Load (MEM-02)

`AerospikeClient` currently only exposes `put()` and `get()`. MEM-02 requires loading all rules from Aerospike at startup via `scan()`. Two options:

**Option A (recommended):** Add an `async_scan()` method to `AerospikeClient` using the same `run_in_executor` pattern:
```python
async def scan(self, set_name: str) -> list[dict]:
    loop = asyncio.get_running_loop()
    def _do_scan():
        scan = self._client.scan(self.namespace, set_name)
        records = []
        scan.foreach(lambda key, meta, bins: records.append(bins))
        return records
    return await loop.run_in_executor(self._executor, _do_scan)
```

**Option B (simpler for demo):** Maintain a `__rules_index__` key in the `rules` set (same pattern as `__episode_index__` in `episodes` set). At startup, read the index to get all rule IDs, then `get()` each one.

Option B is consistent with the established project pattern and avoids modifying `AerospikeClient`. Use Option B.

### Pattern 7: Rule ID Assignment

Use a counter stored in Aerospike under key `__rule_counter__` in the `rules` set:
```python
async def next_rule_id(client: AerospikeClient) -> str:
    """Assign next sequential rule ID."""
    try:
        bins = await client.get(RULES_SET, "__rule_counter__")
        n = bins.get("count", 0) + 1
    except Exception:
        n = 1
    await client.put(RULES_SET, "__rule_counter__", {"count": n})
    return f"rule_{n:03d}"  # -> "rule_001", "rule_002", etc.
```

### Pattern 8: Evolution Trigger Detection

Read `generated_rules_fired` from the confirmed episode (already stored in `Episode.generated_rules_fired`). If non-empty, spawn evolution instead of fresh generation:

```python
episode = app_state["active_episodes"].get(req.episode_id)
if episode.generated_rules_fired:
    # Evolution path: existing rule fired on this episode
    await _evolve_rule(episode, req.attack_type, ...)
else:
    # New rule generation path
    await _generate_new_rule(episode, req.attack_type, ...)
```

### Pattern 9: Attribution String Format (LEARN-05)

REQUIREMENTS.md specifies the exact attribution string:
```
"Blocked by Generated Rule #001 (learned from Episode #001) | Deployed [X]s ago"
```

The current `SafetyGate.evaluate()` attribution format does not produce this string. It produces:
```
"NO-GO (composite: 1.20) | Generated Rule gen_rule_001: 0.80; Rule rule_z_score: 0.30"
```

Phase 3 must either: (a) post-process the attribution string in the confirm/investigate route to prepend the specific generated rule attribution, OR (b) store the deploy timestamp with the rule and compute "Xs ago" dynamically. The deploy timestamp is already stored in Aerospike (`timestamp` bin). Use approach (a): the `/confirm` response and the WebSocket `rule_deployed` event carry the structured attribution; the `/investigate` response's `attribution` field is supplemented with the generated rule contribution from `rule_contributions[is_generated=True]` entries.

### Anti-Patterns to Avoid

- **Double-registering generated rules:** Writing the `.py` file AND calling `register_rule()` at deploy time puts the rule in both `_hardcoded_rules` (after reload) and `_generated_rules`. This causes double-scoring. Choose one path: at deploy time, write the file and call `load_rules_from_directory()` only. On startup with existing Aerospike rules, call `register_rule()` only (not the file).
- **Blocking the FastAPI event loop during Opus 4.6 streaming:** The `stream()` context manager is async; never call synchronous blocking code inside the stream loop.
- **Calling `signal.SIGALRM` from a background task on macOS:** SIGALRM works on Linux but behavior on macOS in background threads is undefined. The existing `register_rule()` timeout uses SIGALRM — this is fine for the main thread but could misbehave in background tasks. Keep validation in the main async context (it's fast — no timeout needed for validation, only for eval-time execution in `SafetyGate.evaluate()`).
- **Hardcoding episode VerdictBoard in the prompt:** The prompt must pass the actual VerdictBoard dict from the confirmed episode, not a static example.
- **Forgetting to extend EventType Literal:** Adding new WebSocket event types without updating the `EventType` Literal in `sentinel/schemas/events.py` will cause Pydantic validation errors at broadcast time.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Python sandboxing for generated rules | Custom exec namespace | `compile_restricted` from RestrictedPython (already in codebase) | Already validates AST + restricts builtins; re-implementing would miss edge cases |
| Async Anthropic streaming | Manual HTTP chunked reads | `client.messages.stream()` context manager | Official SDK; token buffer management, error handling, retry included |
| Aerospike async wrapper | Direct threading | `AerospikeClient.put()`/`get()` with `run_in_executor` | Already implemented and tested in Phase 2; consistent with project pattern |
| WebSocket event broadcasting | New connection management | `ws_manager.broadcast()` singleton | Already implemented with dead-connection pruning |
| Rule compilation safety | `compile()` + `exec()` directly | `compile_restricted()` always | CLAUDE.md hard constraint; `compile()` never used for generated rules |

**Key insight:** Phase 3 is predominantly wiring — connecting existing infrastructure (`SafetyGate`, `AerospikeClient`, `ws_manager`, `get_episode()`, streaming LLM) through a new `RuleGenerator` service class and `POST /confirm` route. The primary implementation work is the Opus 4.6 prompt design and the validation harness.

---

## Common Pitfalls

### Pitfall 1: EventType Literal Not Extended
**What goes wrong:** `ws_manager.broadcast(event="rule_generating", ...)` raises Pydantic `ValidationError` because `rule_generating` is not in the `EventType` Literal.
**Why it happens:** `sentinel/schemas/events.py` EventType is a strict Literal with 7 values. Phase 3 adds 2 new event types not yet in the schema.
**How to avoid:** Extend EventType in `sentinel/schemas/events.py` to add `"rule_generating"` and `"rule_generation_failed"` as first task of Wave 1.
**Warning signs:** Pydantic validation error at broadcast time with message `Input should be 'investigation_started' | 'agent_completed' | ...`.

### Pitfall 2: Double-Fired Generated Rules
**What goes wrong:** Generated rule scores twice — contributing 2x the intended score — causing every subsequent investigation to be a false NO-GO.
**Why it happens:** Rule deployed as a `.py` file (picked up by `load_rules_from_directory()` into `_hardcoded_rules`) AND also registered via `register_rule()` into `_generated_rules`. Both sets are iterated in `evaluate()`.
**How to avoid:** At deploy time: write `.py` file + call `load_rules_from_directory()` only. At startup (loading from Aerospike): call `register_rule()` only, do not write `.py` files during startup. Maintain the invariant that a rule lives in exactly one set.
**Warning signs:** `rule_contributions` shows the same rule ID appearing twice, or composite scores doubling unexpectedly.

### Pitfall 3: Opus 4.6 Generates Non-Compliant Python
**What goes wrong:** Generated source contains `__builtins__`, uses `import`, or defines helper functions with `__` names. Validation check 1 or 2 fails. With 3 retries exhausted, `rule_generation_failed` fires.
**Why it happens:** Without explicit few-shot examples and constraints in the system prompt, Opus 4.6 will sometimes generate idiomatic Python with forbidden tokens.
**How to avoid:** System prompt must include: (a) 2-3 few-shot examples from the existing hardcoded rules (`rule_z_score.py`, `rule_mismatch.py`), (b) explicit "forbidden tokens" list, (c) instruction to return only the function body with no imports. The retry prompt must include the specific failure reason from validation.
**Warning signs:** Repeated validation failures during initial prompt testing.

### Pitfall 4: Generated Rule Doesn't Fire on Phase 2 VerdictBoard
**What goes wrong:** The rule generated from Phase 1 (invoice attack) fires on the Phase 1 VerdictBoard but returns near-zero on the Phase 2 (identity spoofing) VerdictBoard. LEARN-05 fails.
**Why it happens:** If the rule prompt frames the function around document-specific features (`hidden_text_detected` flag), it won't generalize to identity spoofing.
**How to avoid:** Prompt must explicitly instruct Opus 4.6 to avoid attack-mechanism-specific conditions and instead target behavioral invariants (anomalous confidence, z-score deviation, unable_to_verify patterns, step deviation). The prediction_errors input is key — it highlights which VerdictBoard fields had the largest expected-vs-actual gap. Both Phase 1 and Phase 2 attacks share behavioral signals (confidence anomaly, z-score deviation) that a well-written rule can detect.
**Warning signs:** Generated rule source references `hidden_text_detected` or document-specific flags.

### Pitfall 5: Evolution Path Not Triggered
**What goes wrong:** After Phase 2 attack is confirmed, fresh rule generation fires instead of evolution. No v2 is created.
**Why it happens:** `episode.generated_rules_fired` is empty because the Phase 2 investigation did not populate this field, or `app_state["active_episodes"]` was cleared between Phase 1 and Phase 2.
**How to avoid:** Verify in Phase 2 investigation flow that `generated_rules_fired` is populated in the Episode when a generated rule contributes to the composite score. Check `SafetyGate.evaluate()` — it returns `rule_contributions` with `is_generated` flag; the supervisor must map this back to `episode.generated_rules_fired`. Also verify `active_episodes` cache is not cleared between investigations.
**Warning signs:** Evolution never fires; rule v2 never appears.

### Pitfall 6: Aerospike `scan()` Not Available
**What goes wrong:** At startup, `rule_store.load_all_rules()` fails because `AerospikeClient` has no `scan()` method.
**Why it happens:** Phase 2 only implemented `put()` and `get()`. MEM-02 requires scanning all rules.
**How to avoid:** Use the `__rules_index__` pattern (same as `__episode_index__` in `episode_store.py`) rather than implementing a true scan. Write the index key on each rule write; read it on startup.

### Pitfall 7: SIGALRM in Background Task on macOS
**What goes wrong:** `register_rule()` uses `signal.SIGALRM` for the 5-second timeout. On macOS, SIGALRM can only be set in the main thread. Background `asyncio.create_task()` may run in a different thread context.
**Why it happens:** `signal.signal()` raises `ValueError: signal only works in main thread of the main interpreter` when called from a non-main thread.
**How to avoid:** The validation harness (called from the background task) should NOT call `register_rule()` for validation purposes — it should execute the compiled code directly with a try/except and `asyncio.wait_for()` timeout instead of SIGALRM. Only call `register_rule()` for final deployment to store in `_generated_rules` / file path. On macOS, the background task is still on the asyncio event loop (not a separate OS thread), so SIGALRM should work in practice — but verify early.

---

## Code Examples

### Rule Generation System Prompt Structure

```python
RULE_GEN_SYSTEM_PROMPT = """You are a behavioral security rule generator for the Sentinel system.
Your task: analyze prediction errors from a confirmed attack episode and generate a Python
scoring function that detects the same BEHAVIORAL PATTERN — not the specific attack mechanism.

CRITICAL CONSTRAINTS:
1. The function MUST be named exactly: score(verdict_board: dict) -> float
2. Return a float between 0.0 and 2.0 (anomaly score; 0.0 = clean, higher = more suspicious)
3. Use ONLY these verdict_board fields:
   - mismatches: list[dict] (each has: field, agent_claimed, independently_found, match, severity, agent_id)
   - behavioral_flags: list[str]
   - agent_confidence: float (0.0-1.0)
   - confidence_z_score: float | None
   - step_sequence_deviation: bool
   - unable_to_verify: list[str]
   - prediction_errors: dict | None
4. NEVER use: import, __, open, exec, eval, or any system access
5. Include a docstring explaining what behavioral pattern the function detects
6. Return ONLY the function — no imports, no helper functions, no class definitions

EXAMPLES of valid scoring functions:
---
def score(verdict_board: dict) -> float:
    \"\"\"Detects anomalously high agent confidence during identity verification failure.
    Agent claiming certainty when verification is incomplete is a manipulation signal.\"\"\"
    confidence = verdict_board.get("agent_confidence", 0.5)
    unable = verdict_board.get("unable_to_verify", [])
    if confidence > 0.85 and len(unable) > 0:
        return 0.7
    return 0.0
---
def score(verdict_board: dict) -> float:
    \"\"\"Confidence z-score anomaly detection.
    Agent confidence far from behavioral baseline is a manipulation signal.\"\"\"
    z = verdict_board.get("confidence_z_score")
    if z is None:
        return 0.0
    abs_z = abs(z)
    if abs_z > 3.0:
        return 0.6
    if abs_z > 2.0:
        return 0.3
    return 0.0
---
"""
```

### Rule Generation User Prompt Structure

```python
def build_rule_gen_prompt(attack_type: str, verdict_board: dict,
                           prediction_errors: dict) -> str:
    return f"""A confirmed {attack_type} attack has been detected.

PREDICTION ERRORS (fields where expected behavior diverged most from actual findings):
{json.dumps(prediction_errors, indent=2)}

VERDICT BOARD from the confirmed attack episode:
{json.dumps(verdict_board, indent=2)}

Generate a Python scoring function that captures the BEHAVIORAL ANOMALIES visible in
these prediction errors. Focus on patterns that would be present in other {attack_type}
attacks regardless of the specific target, amount, or document involved.

The function must generalize — it should detect similar manipulation attempts in future
transactions, not just replay this exact scenario.

Return ONLY the Python function with no surrounding text."""
```

### Validation Harness Execution

```python
# Source: established SafetyGate.register_rule() pattern in sentinel/engine/safety_gate.py
def _exec_rule(source: str) -> Callable:
    """Compile and exec a rule source, returning the score() function."""
    code = compile_restricted(source, "<rule_validate>", "exec")
    safe_globals = {
        "__builtins__": SAFE_BUILTINS,
        "_getattr_": getattr,
        "_getiter_": iter,
        "_getitem_": lambda obj, key: obj[key],
        "_write_": lambda obj: obj,
        "_inplacevar_": lambda op, x, y: x + y if op == "+=" else x - y,
    }
    namespace = {}
    exec(code, safe_globals, namespace)
    return namespace["score"]
```

### Aerospike Rule Write with Latency

```python
# Source: established write_episode() pattern in sentinel/memory/episode_store.py
async def write_rule(rule_id: str, source: str, episode_ids: list[str],
                     prediction_errors: dict, version: int,
                     client: AerospikeClient) -> float:
    start = time.perf_counter()
    bins = {
        "rule_id": rule_id,
        "source": source,
        "episode_ids": json.dumps(episode_ids),
        "prediction_errors": json.dumps(prediction_errors),
        "timestamp": int(time.time() * 1000),
        "version": version,
        "fire_count": 0,
    }
    await client.put("rules", rule_id, bins)
    latency_ms = round((time.perf_counter() - start) * 1000, 2)
    await _update_rules_index(rule_id, client)
    return latency_ms
```

### WebSocket Streaming Event Schema

```python
# rule_generating events (one per token):
{
    "event": "rule_generating",
    "episode_id": "...",
    "timestamp": "...",
    "data": {
        "token": "    z = verdict_board",   # partial token
        "accumulated": "def score(verdict_board: dict)...",  # full so far
        "attempt": 1  # which retry attempt (1-3)
    }
}

# rule_deployed event (on success):
{
    "event": "rule_deployed",
    "episode_id": "...",
    "timestamp": "...",
    "data": {
        "rule_id": "rule_001",
        "version": 1,
        "source": "def score(verdict_board: dict) -> float:...",
        "episode_ids": ["ep-uuid-001"],
        "write_latency_ms": 3.2,
        "attribution": "Blocked by Generated Rule #001 (learned from Episode #001) | Deployed 0s ago"
    }
}

# rule_generation_failed event (after 3 failed attempts):
{
    "event": "rule_generation_failed",
    "episode_id": "...",
    "timestamp": "...",
    "data": {
        "attempts": 3,
        "last_failure_reason": "Attack fixture score 0.45 must be > 0.6"
    }
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Binary rule output (True/False) | Weighted float score (0.0-2.0) | Phase 2 design revision | Individually weak signals compound; composite scoring above threshold |
| Static hardcoded rules only | Hardcoded + generated scoring functions | Phase 3 (this phase) | Self-improvement loop; system learns from confirmed incidents |
| `aioaerospike` async library | `aerospike` sync + `ThreadPoolExecutor` | Aug 2025 (archived) | Official supported pattern; archived library is not safe to use |

**Deprecated/outdated:**
- `asyncio.gather()` for agent dispatch: replaced by `asyncio.TaskGroup` in project (CLAUDE.md constraint)
- `register_rule()` for all generated rule loading: at startup, use `load_rules_from_directory()` for file-based rules; `register_rule()` for in-memory-only rules loaded from Aerospike during startup scan

---

## Open Questions

1. **SIGALRM in background asyncio task on macOS**
   - What we know: `signal.SIGALRM` works in main thread; existing `register_rule()` uses it
   - What's unclear: Does `asyncio.create_task()` on macOS run in the main OS thread context?
   - Recommendation: Test `register_rule()` from a background task early in development. If it fails, wrap the exec in `asyncio.wait_for()` with a TimeoutError fallback instead of SIGALRM.

2. **Episode VerdictBoard availability at confirm time**
   - What we know: `app_state["active_episodes"]` caches the full episode dict after `/investigate` returns
   - What's unclear: The cache stores the raw episode object — does it include the final `prediction_report` with prediction errors, or is that stored separately in Aerospike only?
   - Recommendation: Verify in `supervisor.py` that `prediction_report` is populated on the episode before caching in `active_episodes`. If not, read from Aerospike via `get_episode()`.

3. **Rule file naming — glob collision**
   - What we know: `load_rules_from_directory()` picks up all `rule_*.py` files
   - What's unclear: If generated rules are written as `rule_generated_001.py` (matches `rule_*.py` glob), they will be loaded as hardcoded rules, not generated rules. The `is_generated` flag in `evaluate()` won't be set correctly.
   - Recommendation: Write generated rules as `rule_generated_001.py` and accept they load as "hardcoded" in the gate's internal classification — the external provenance tracking (Aerospike + `rule_id` naming convention) is the authoritative source of whether a rule is generated. Alternatively, write them as `rule_gen_001.py` to distinguish visually.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| anthropic SDK | Opus 4.6 rule generation + streaming | Yes | 0.86.0 | None (required) |
| RestrictedPython | compile_restricted for validation | Yes | 8.2 | None (required) |
| aerospike client | Rule provenance persistence | Yes | 19.1.0 | Graceful degradation (rules work without Aerospike, just no provenance) |
| asyncio TaskGroup | Parallel sub-agent dispatch (Phase 2) | Yes (Python 3.12) | stdlib | N/A |
| FastAPI | POST /confirm route | Yes | 0.115.x | N/A |

All dependencies are installed and verified. No new packages required.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio 0.86.0 |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (asyncio_mode = "auto") |
| Quick run command | `source .venv/bin/activate && python -m pytest tests/test_rule_generator.py -x -q` |
| Full suite command | `source .venv/bin/activate && python -m pytest tests/ -x -q --ignore=tests/test_claude_api.py` |

Current suite: 129 tests passing, 2 skipped (live API tests). Phase 3 adds approximately 12-15 new tests.

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| LEARN-01 | Extract prediction errors from confirmed episode | unit | `pytest tests/test_rule_generator.py::test_prediction_error_extraction -x` | Wave 0 |
| LEARN-02 | Generated function uses VerdictBoard fields, returns float, has docstring | unit | `pytest tests/test_rule_generator.py::test_generated_rule_structure -x` | Wave 0 |
| LEARN-03 | 4-check validation harness: compile, tokens, attack score >0.6, clean score <0.2 | unit | `pytest tests/test_rule_generator.py::TestValidationHarness -x` | Wave 0 |
| LEARN-04 | Validated rule deployed to gate registry + Aerospike with provenance | unit | `pytest tests/test_rule_generator.py::test_rule_deployment -x` | Wave 0 |
| LEARN-05 | Phase 2 VerdictBoard blocked by generated rule; hardcoded rules insufficient alone | unit | `pytest tests/test_rule_generator.py::test_generated_rule_fires_on_phase2 -x` | Wave 0 |
| LEARN-06 | Second confirmed incident generates v2 rule; evolution prompt uses both VerdictBoards | unit | `pytest tests/test_rule_generator.py::test_rule_evolution -x` | Wave 0 |
| MEM-02 | Rule written to Aerospike `sentinel.rules` set with all D-04 bins | unit | `pytest tests/test_rule_generator.py::test_aerospike_rule_persistence -x` | Wave 0 |
| MEM-05 | Write latency measured and exposed via API | unit | `pytest tests/test_rule_generator.py::test_write_latency_measured -x` | Wave 0 |
| API-03 | POST /confirm returns 202, spawns background task | unit | `pytest tests/test_rule_generator.py::test_confirm_returns_202 -x` | Wave 0 |
| EventType | rule_generating and rule_generation_failed in EventType Literal | unit | `pytest tests/test_schemas.py -x -q` | Partial (schema file exists, needs update) |

### Sampling Rate
- **Per task commit:** `source .venv/bin/activate && python -m pytest tests/test_rule_generator.py -x -q`
- **Per wave merge:** `source .venv/bin/activate && python -m pytest tests/ -x -q --ignore=tests/test_claude_api.py`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_rule_generator.py` — covers LEARN-01 through LEARN-06, MEM-02, MEM-05, API-03
- [ ] `sentinel/engine/rule_generator.py` — `RuleGenerator` class (stub required for test import)
- [ ] `sentinel/memory/rule_store.py` — `write_rule()`, `load_all_rules()` stubs
- [ ] `sentinel/api/routes/confirm.py` — `POST /confirm` route stub
- [ ] Update `sentinel/schemas/events.py` EventType Literal — add `rule_generating`, `rule_generation_failed`

---

## Sources

### Primary (HIGH confidence)
- `sentinel/engine/safety_gate.py` — existing `register_rule()`, `load_rules_from_directory()`, `evaluate()`, `SAFE_BUILTINS`, `_FORBIDDEN_TOKENS` — verified by reading source
- `sentinel/memory/episode_store.py` — `write_episode()` pattern, `AerospikeClient.put()/get()`, latency measurement — verified by reading source
- `sentinel/memory/trust_store.py` — `store_prediction_history(episode_id)` pattern, key naming `prediction_{episode_id}` — verified by reading source
- `sentinel/schemas/events.py` — EventType Literal 7 values, WSEvent schema — verified by reading source
- `sentinel/schemas/episode.py` — `generated_rules_fired`, `generated_rule_source`, `prediction_report` fields — verified by reading source
- `sentinel/schemas/verdict_board.py` — all VerdictBoard fields available to generated rules — verified by reading source
- `sentinel/api/websocket.py` — `ws_manager.broadcast(event, episode_id, data)` signature — verified by reading source
- `sentinel/api/main.py` — `app_state["safety_gate"]`, `app_state["active_episodes"]` access patterns — verified by reading source
- anthropic SDK 0.86.0 — `client.messages.stream()` context manager, `.text_stream` async iterator — verified by installed package introspection
- Python `signal.SIGALRM` — used in existing `register_rule()` and `evaluate()` — verified by reading `safety_gate.py`
- pytest configuration — `pyproject.toml` asyncio_mode="auto", testpaths=["tests"] — verified by reading file
- Test suite — 129 tests passing (verified by running `pytest`)

### Secondary (MEDIUM confidence)
- `.planning/phases/03-self-improvement-loop/03-CONTEXT.md` — D-01 through D-10 locked decisions — project-specific design document
- `.planning/REQUIREMENTS.md` — LEARN-01 through LEARN-06, MEM-02, MEM-05, API-03 — project requirements
- CLAUDE.md §Safety Gate — `compile_restricted` hard constraint, forbidden tokens list — project instructions

### Tertiary (LOW confidence)
- asyncio background task + SIGALRM interaction on macOS — needs empirical verification early in development

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all packages verified installed and working
- Architecture patterns: HIGH — directly derived from reading existing Phase 2 code
- Pitfalls: HIGH — derived from code analysis and known constraints; SIGALRM/macOS item is MEDIUM
- Test requirements: HIGH — existing test patterns and infrastructure are clear

**Research date:** 2026-03-25
**Valid until:** 2026-04-24 (stable domain; all libraries are pinned in project)
