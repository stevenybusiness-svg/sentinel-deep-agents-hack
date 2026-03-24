# Stack Research

**Domain:** Real-time multi-agent AI supervision system for financial payments
**Researched:** 2026-03-24
**Confidence:** MEDIUM-HIGH (core SDK and async patterns HIGH; Bland AI real-time specifics LOW due to sparse public docs)

---

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python | 3.11+ | Runtime | TaskGroup (3.11) for structured concurrency is the correct primitive for parallel sub-agent dispatch; asyncio.timeout() replaces fragile wait_for() pattern |
| FastAPI | 0.115.x | HTTP + WebSocket server | Native async, WebSocket support out of the box, OpenAPI auto-docs for judge walkthroughs; starlette WebSocket is production-grade |
| anthropic SDK | 0.86.0 | Claude API client | Official SDK, AsyncAnthropic client supports concurrent awaits; `[aiohttp]` extra recommended for better concurrency under load |
| aerospike | 19.1.0 | Episodic memory / persistent storage | Official Python client; synchronous C-extension bindings with sub-ms operations at hardware level; 3 Aerospike judges require real integration |
| React | 18.x | Frontend UI | Concurrent features (useTransition, Suspense) handle rapid state updates from WebSocket; 19 is available but introduces breaking changes not worth debugging in 72h |
| @xyflow/react | 12.4.4 | Pipeline node graph | Production-ready, React-native (no D3 DOM conflict), built-in animated edges, customizable nodes — exact match for investigation tree requirement |
| okta-jwt-verifier | 0.4.0 | Okta token introspection | Official Okta library, async support, AccessTokenVerifier handles Okta-issued tokens; v0.4.0 released Jan 2026 |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| uvicorn | 0.34.x | ASGI server | `--workers 1` with asyncio loop; single-worker keeps WebSocket state in-process for demo simplicity |
| pydantic | 2.x | Data validation | FastAPI native; use for verdict board schemas, gate decision models — prevents silent field mismatches |
| asyncio (stdlib) | 3.11 built-in | Parallel sub-agent dispatch | `asyncio.TaskGroup` for parallel Risk/Compliance/Forensics; cancels siblings on first exception |
| aiohttp | 3.x | AsyncAnthropic HTTP backend | `pip install anthropic[aiohttp]`; better connection reuse than default httpx under concurrent load |
| websockets | 14.x | Low-level WS client | For Bland AI server-side WebSocket bridging if needed; FastAPI uses starlette WS natively for browser connections |
| RestrictedPython | 8.2 | Safety Gate code sandboxing | Compile-time restriction of generated Python functions; does NOT replace policy review but adds defense layer |
| python-jose or PyJWT | 3.3.x | JWT decode fallback | For local JWT verification if Okta introspection latency is unacceptable in demo path |
| asyncpg | 0.30.x | Async Postgres driver | For Airbyte-synced counterparty DB queries; pure async, fastest Python Postgres driver |
| pyairbyte | latest | Airbyte Python integration | If implementing Airbyte sync programmatically vs. pre-configured; for hackathon, pre-load fixtures and skip if time-constrained |
| python-dotenv | 1.0.x | Secrets management | Load API keys from .env; never hardcode Anthropic/Okta/Aerospike credentials |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| uvicorn --reload | Dev server with hot reload | Use `uvicorn main:app --reload --port 8000`; essential for rapid iteration |
| pytest-asyncio | Async test runner | Required for testing async FastAPI routes and agent coroutines |
| httpx | Test HTTP client | FastAPI's TestClient uses httpx; already a transitive dep of anthropic SDK |

---

## Component-by-Component Guidance

### 1. Anthropic SDK — Parallel Sub-Agent Dispatch

**Pattern: AsyncAnthropic + asyncio.TaskGroup**

```python
from anthropic import AsyncAnthropic
import asyncio

client = AsyncAnthropic()  # reuse across requests — one client, not one per call

async def run_supervisor_investigation(payment_request: dict) -> dict:
    async with asyncio.TaskGroup() as tg:
        risk_task = tg.create_task(run_risk_agent(payment_request))
        compliance_task = tg.create_task(run_compliance_agent(payment_request))
        forensics_task = tg.create_task(run_forensics_agent(payment_request))
    # TaskGroup raises ExceptionGroup if any task fails — handle with except*
    return synthesize(risk_task.result(), compliance_task.result(), forensics_task.result())

async def run_risk_agent(payload: dict) -> dict:
    response = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        messages=[{"role": "user", "content": build_risk_prompt(payload)}],
        timeout=30.0,  # explicit per-agent timeout, not the 10-min default
    )
    return parse_agent_response(response)
```

Key points:
- `AsyncAnthropic` is a single shared client — instantiate once at module level, not per-request
- TaskGroup (3.11+) cancels remaining tasks if one raises, preventing zombie agent calls
- Set explicit `timeout=` per call — the default 10-minute timeout will hang your demo if an agent stalls
- Supervisor uses `claude-opus-4-6`; Risk/Compliance/Forensics use `claude-sonnet-4-6` — specify model per call
- For `anthropic[aiohttp]`: use `DefaultAioHttpClient` as the http_client for better connection pooling under parallel load
- Streaming (`client.messages.stream`) is useful for Supervisor's reasoning — stream tokens to frontend via WebSocket for live "thinking" display

**Rule generation call pattern:**
```python
# Use streaming for rule generation — long output, judges watch it appear
async with client.messages.stream(
    model="claude-opus-4-6",
    max_tokens=4096,
    messages=[{"role": "user", "content": rule_gen_prompt}],
) as stream:
    async for text in stream.text_stream:
        await ws.send_json({"type": "rule_gen_chunk", "text": text})
```

### 2. Aerospike Python Client — Sub-5ms Write Patterns

**Client version:** 19.1.0 (March 2026)
**Key constraint:** The Python client uses C-extension bindings and is **synchronous only** in the standard package. There is no official async Aerospike Python client as of this writing.

**Integration approach for FastAPI async context:**
```python
import aerospike
from concurrent.futures import ThreadPoolExecutor
import asyncio

# Module-level: configure once
config = {
    'hosts': [('your-aerospike-host', 3000)],
    'policies': {
        'write': {
            'total_timeout': 50,   # 50ms total — well above sub-5ms hardware but protects against hangs
            'socket_timeout': 20,  # 20ms socket idle timeout
            'max_retries': 0,      # no retries for latency-critical writes
        },
        'read': {
            'total_timeout': 30,
            'socket_timeout': 15,
            'max_retries': 1,
        }
    }
}
client = aerospike.client(config).connect()

# Thread pool for running sync Aerospike calls from async FastAPI context
_aerospike_pool = ThreadPoolExecutor(max_workers=4)

async def write_episode(episode_id: str, data: dict) -> None:
    key = ('sentinel', 'episodes', episode_id)
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        _aerospike_pool,
        lambda: client.put(key, data)
    )
```

**Key put() pattern for episode records:**
```python
def write_episode_sync(episode_id: str, verdict_board: dict, gate_decision: str, rule_src: str = None):
    key = ('sentinel', 'episodes', episode_id)
    bins = {
        'verdict': verdict_board,
        'gate': gate_decision,
        'ts': int(time.time() * 1000),  # epoch ms
        'rule_src': rule_src or '',
    }
    # Per-operation policy override — copy don't modify shared policy
    write_policy = {
        'total_timeout': 50,
        'max_retries': 0,
    }
    client.put(key, bins, policy=write_policy)
```

**Context store reads (trust postures, behavioral baselines):**
```python
def get_trust_context(agent_id: str) -> dict:
    key = ('sentinel', 'trust', agent_id)
    try:
        _, _, record = client.get(key)
        return record or {}
    except aerospike.exception.RecordNotFound:
        return {}
```

**Latency visibility for dashboard:** Record write start/end timestamps and push the delta to frontend via WebSocket. Aerospike's Metrics module (official) can expose client-side histograms if needed for deeper judge demos.

**Critical gotcha:** Aerospike bins store values up to the bin value size limit (1MB for blobs). Generated rule source code as a string bin is fine; do not store large document binary blobs as standard bins — use Aerospike Blob type or truncate.

### 3. Bland AI — FastAPI Integration

**Architecture reality:** Bland AI is a phone-call AI platform. Integration means:
1. Your FastAPI server calls Bland's REST API to initiate an outbound call
2. Bland AI calls the operator's phone
3. Operator talks to Bland AI's voice agent (which is your configured persona/pathway)
4. Post-call, Bland sends a webhook to your FastAPI server with transcript

**There is no confirmed public WebSocket API for bidirectional audio streaming** from your server to Bland in the public docs as of this research date. The "Listen to Active Call" endpoint exists but full specs were not publicly accessible.

**Integration pattern for demo (FastAPI side):**

```python
import httpx
from fastapi import APIRouter, Request

router = APIRouter()
BLAND_API_KEY = os.getenv("BLAND_API_KEY")
BLAND_BASE = "https://api.bland.ai/v1"

async def initiate_supervisor_voice_call(operator_phone: str, investigation_context: str) -> str:
    async with httpx.AsyncClient() as http:
        response = await http.post(
            f"{BLAND_BASE}/calls",
            headers={"authorization": BLAND_API_KEY},
            json={
                "phone_number": operator_phone,
                "task": f"You are the Sentinel supervisor AI. {investigation_context}. Answer operator questions about the investigation. Be concise.",
                "voice": "nat",
                "interruption_threshold": 100,  # responsive to barge-in (lower = more responsive)
                "block_interruptions": False,    # MUST be False for barge-in support
                "webhook": f"https://your-server.com/bland/callback",
                "webhook_events": ["call_ended"],  # add call_started if available
                "record": False,
            }
        )
    return response.json()["call_id"]

@router.post("/bland/callback")
async def bland_callback(request: Request):
    payload = await request.json()
    # payload contains: call_id, transcript, call_length, etc.
    # Push summary to dashboard via WebSocket
    await broadcast_to_dashboard({"type": "voice_complete", "transcript": payload.get("corrected_transcript")})
    return {"status": "ok"}
```

**Barge-in configuration:** Set `interruption_threshold` to a low value (50-100ms) and `block_interruptions: False`. This is Bland's built-in barge-in — the voice AI will stop speaking when it detects the operator speaking. This is hardware-level on Bland's side; no custom WebSocket audio needed.

**72-hour gotcha:** Bland AI phone calls require a real phone number for the operator. In a demo context, use your own phone. If judges want to hear the call live, you'll need audio playback from the phone or a SIP endpoint. Test the call initiation and webhook receipt end-to-end before building anything else — webhook receipt requires a public URL (use ngrok during development, EC2 in prod).

**Fallback strategy:** If Bland AI proves intractable — text-on-dashboard overlay showing "voice transcript" driven by the same webhook callback is sufficient for demo continuity.

### 4. React Frontend — Real-Time WebSocket + Node Graph

**WebSocket state management:**
```javascript
// Simple hook — no third-party WS library needed for this scale
function useInvestigationWS() {
  const [pipeline, setPipeline] = useState({ nodes: [], edges: [] });

  useEffect(() => {
    const ws = new WebSocket('ws://localhost:8000/ws/investigation');
    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.type === 'agent_activated') {
        setPipeline(prev => activateNode(prev, msg.agent_id));
      }
      if (msg.type === 'verdict_ready') {
        setPipeline(prev => updateNodeResult(prev, msg.agent_id, msg.verdict));
      }
    };
    return () => ws.close();
  }, []);

  return pipeline;
}
```

Do NOT use Socket.io — it adds ~50KB overhead and fallback complexity. Native WebSocket is sufficient for this demo. Do NOT use SWR or React Query for WebSocket — they are HTTP-polling tools.

**Node graph: @xyflow/react (formerly reactflow)**

Use `@xyflow/react` v12.4.4 (npm package name changed from `reactflow` to `@xyflow/react`).

```javascript
import { ReactFlow, useNodesState, useEdgesState } from '@xyflow/react';
import '@xyflow/react/dist/style.css';

// Animated edges light up as agents activate
const initialEdges = [
  { id: 'sup-risk', source: 'supervisor', target: 'risk', animated: false },
  { id: 'sup-compliance', source: 'supervisor', target: 'compliance', animated: false },
  { id: 'sup-forensics', source: 'supervisor', target: 'forensics', animated: false },
];

// On WebSocket message: setEdges(edges => edges.map(e =>
//   e.id === `sup-${agentId}` ? {...e, animated: true} : e
// ))
```

Custom node types for agent cards with status indicators (idle/active/complete/flagged) are straightforward in React Flow — each node is a React component.

**Do NOT use D3 for the pipeline graph.** D3 directly mutates the DOM, conflicting with React's virtual DOM reconciliation. You'd be fighting two rendering systems. D3 is appropriate for the trust score sparkline chart (simple SVG, no React integration needed) but not for the node graph.

**Do NOT use HTML5 Canvas** for the node graph despite the PROJECT.md mention. Canvas requires manual hit-testing, no accessibility, and significant boilerplate. React Flow handles all of this. Canvas is appropriate for the forensics document overlay (highlighting hidden text regions with overlaid rectangles) — use `<canvas>` directly for that specific panel only.

### 5. Safety Gate — exec() Sandboxing

**Architecture mandate:** The Safety Gate is deterministic Python. No LLM in the enforcement path. This is an explicit invariant.

**Recommended approach: RestrictedPython 8.2 + tight allowlist**

```python
from RestrictedPython import compile_restricted, safe_globals, limited_builtins

def load_rule(rule_source: str, rule_id: str) -> callable:
    """Compile and register a generated rule. Raises on compilation failure."""
    # Compile with RestrictedPython — this catches import attempts, attribute access, etc.
    byte_code = compile_restricted(rule_source, filename=f"<rule_{rule_id}>", mode='exec')

    # Minimal safe globals — only what a verdict board checker needs
    rule_globals = {
        **safe_globals,
        '_print_': lambda *a: None,  # disable print side effects
        '__builtins__': {
            'True': True, 'False': False, 'None': None,
            'len': len, 'str': str, 'int': int, 'float': float,
            'dict': dict, 'list': list, 'isinstance': isinstance,
            'abs': abs, 'round': round,
        }
    }

    exec(byte_code, rule_globals)
    fn = rule_globals.get('evaluate_verdict')
    if not callable(fn):
        raise ValueError(f"Rule {rule_id} must define evaluate_verdict(verdict_board) -> bool")
    return fn

def apply_rules(verdict_board: dict, rule_registry: dict) -> dict:
    """Apply all rules. Returns {rule_id: triggered} dict."""
    results = {}
    for rule_id, rule_fn in rule_registry.items():
        try:
            results[rule_id] = bool(rule_fn(verdict_board))
        except Exception as e:
            results[rule_id] = False  # failed rule = did not trigger, logged
    return results
```

**Generated rule contract** — prompt Opus 4.6 to generate exactly this shape:
```python
def evaluate_verdict(verdict_board: dict) -> bool:
    """
    Rule #001: Confident agent with claims that evaporate under scrutiny.
    Source: Episode abc123, 2026-03-25T14:22:00Z, attack_type=invoice_hidden_text
    """
    confidence = verdict_board.get('payment_agent_confidence', 0)
    verified_fields = verdict_board.get('verified_field_count', 0)
    total_fields = verdict_board.get('total_field_count', 1)
    verification_rate = verified_fields / total_fields
    return confidence > 0.8 and verification_rate < 0.5
```

**Security caveats (flag for judges as a feature, not a bug):**
- RestrictedPython is NOT a full sandbox — a determined attacker could escape it via CPython internals
- For this demo, the threat model is: Opus 4.6 occasionally generates unexpected Python, not a hostile attacker
- The real security is: rules operate ONLY on `verdict_board` dict fields (no system calls, no file access, no network)
- Add a pre-execution static check: reject any rule source containing `import`, `__`, `open`, `exec`, `eval` as strings
- For a production system, use a subprocess sandbox with seccomp (Linux only) or a container — not needed for hackathon

**72-hour gotcha:** The rule generation prompt is the most failure-prone component per PROJECT.md. Test it 30+ times in isolation BEFORE wiring into the loop. Common failure modes:
1. Opus generates overly complex rules with multiple functions — enforce single function contract in prompt
2. Opus generates rules with imports — catch at compile_restricted step
3. Opus generates rules that always return True — add a test harness that runs the rule against known-clean verdicts
4. Field name drift — the prompt must include the exact verdict_board schema; if it drifts, rules silently never fire

### 6. Okta — Token Introspection

**Library:** `okta-jwt-verifier` 0.4.0 (Jan 2026), or direct HTTPS introspection call

**Recommended approach for 72-hour build: Direct HTTP introspection via httpx** (simpler than the full JWT verifier library for this use case)

```python
import httpx
import os

OKTA_DOMAIN = os.getenv("OKTA_DOMAIN")  # e.g. dev-123456.okta.com
OKTA_CLIENT_ID = os.getenv("OKTA_CLIENT_ID")
OKTA_CLIENT_SECRET = os.getenv("OKTA_CLIENT_SECRET")

async def introspect_token(access_token: str) -> bool:
    """Returns True if token is active. False on any failure."""
    introspect_url = f"https://{OKTA_DOMAIN}/oauth2/default/v1/introspect"
    async with httpx.AsyncClient() as http:
        response = await http.post(
            introspect_url,
            data={"token": access_token, "token_type_hint": "access_token"},
            auth=(OKTA_CLIENT_ID, OKTA_CLIENT_SECRET),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=5.0,
        )
    if response.status_code != 200:
        return False
    return response.json().get("active", False)

# FastAPI dependency for override endpoint
from fastapi import Depends, HTTPException, Header

async def require_okta_identity(authorization: str = Header(...)) -> str:
    token = authorization.removeprefix("Bearer ")
    is_valid = await introspect_token(token)
    if not is_valid:
        raise HTTPException(status_code=401, detail="Identity verification failed")
    return token
```

**Using the okta-jwt-verifier library instead:**
```python
from okta_jwt_verifier import AccessTokenVerifier

verifier = AccessTokenVerifier(issuer=f"https://{OKTA_DOMAIN}/oauth2/default")

async def verify_okta_token(token: str) -> bool:
    try:
        await verifier.verify(token)
        return True
    except Exception:
        return False
```

**72-hour gotcha:** As of May 2025, the Okta Developer Edition was replaced by the Okta Integrator Free Plan. If you're setting up a new Okta org, follow the current setup flow. The `okta-jwt-verifier` library's `BaseJWTVerifier` is deprecated — use `AccessTokenVerifier` directly. The introspection endpoint requires the token to be issued by your specific Okta authorization server — check the issuer URL matches.

### 7. Airbyte — Google Sheets → Postgres Sync

**Risk assessment for 72-hour timeline: LOW priority, HIGH setup friction**

Airbyte Cloud or self-hosted adds significant setup overhead (OAuth for Google Sheets, Postgres credentials, connection configuration). For a hackathon where judges are watching the demo, not the ETL pipeline, pre-loaded fixtures are a valid fallback.

**If implementing:**
- Use Airbyte Cloud (no self-hosting overhead)
- Configure Google Sheets source → Postgres destination via UI, not API — the UI is faster
- Set sync schedule to "manual" and trigger sync once before demo
- PyAirbyte (`pip install airbyte`) offers a Python-native alternative for simple pipelines

**Fallback:** Populate counterparty DB and KYC ledger with `INSERT` statements from a seed script. The Airbyte integration is a sponsor integration, but it's listed as "if time permits" in PROJECT.md — treat it as such.

---

## Installation

```bash
# Core backend
pip install fastapi uvicorn[standard] anthropic[aiohttp] aerospike pydantic asyncpg

# Security and identity
pip install okta-jwt-verifier httpx

# Safety Gate
pip install RestrictedPython

# Dev
pip install python-dotenv pytest pytest-asyncio

# Optional: Airbyte
pip install airbyte
```

```bash
# Frontend
npm create vite@latest frontend -- --template react
cd frontend
npm install @xyflow/react
# No additional WS library needed — browser native WebSocket
```

---

## Alternatives Considered

| Recommended | Alternative | Why Not |
|-------------|-------------|---------|
| `@xyflow/react` | D3.js force graph | D3 mutates DOM directly, conflicts with React's virtual DOM; 2x the code for same result |
| `@xyflow/react` | HTML5 Canvas custom | Canvas requires manual hit-testing, no accessibility, 5x boilerplate for 72h build |
| `asyncio.TaskGroup` | `asyncio.gather()` | gather doesn't cancel remaining tasks on first exception; TaskGroup gives structured concurrency with automatic cleanup |
| Direct httpx introspection | `okta-jwt-verifier` library | Direct call is 10 lines vs. library setup; sufficient for hackathon; avoids library quirks |
| RestrictedPython + allowlist | subprocess/container sandbox | Container sandbox is correct for production but requires Docker orchestration overhead; overkill for hackathon threat model |
| `aerospike` sync + ThreadPoolExecutor | `aioaerospike` community library | `aioaerospike` is unmaintained (archived Aug 2025); official sync client + executor is the supported pattern |
| Native browser WebSocket | Socket.io | Socket.io adds reconnection/fallback complexity unnecessary for a demo; native WS is 5 lines |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `asyncio.gather()` for agent dispatch | Does not cancel sibling tasks on exception; stale agent calls can block demo | `asyncio.TaskGroup` (Python 3.11+) |
| `reactflow` (old package name) | Rebranded to `@xyflow/react`; old package still works but misses v12 features and updates | `@xyflow/react` |
| `aioaerospike` | Archived/unmaintained as of August 2025 | Official `aerospike` sync client + `run_in_executor` |
| Pydantic v1 | FastAPI 0.115 requires Pydantic v2; mixing causes runtime errors | Pydantic v2 (default with current pip install) |
| Socket.io (python-socketio) | Overkill for demo; adds namespace/room complexity; not needed when you control both client and server | FastAPI native WebSocket + browser WebSocket |
| `eval()` for Safety Gate rules | eval() executes in the current namespace with full Python access | `exec()` with RestrictedPython's `compile_restricted` + minimal safe_globals |
| LangChain / LlamaIndex | Heavyweight orchestration frameworks that abstract away the exact behavior judges need to see in the Investigation Tree; you need transparent, attributable agent calls | Direct `anthropic` SDK calls with explicit prompts |
| `BaseJWTVerifier` (okta) | Deprecated in okta-jwt-verifier library | `AccessTokenVerifier` directly |

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| anthropic 0.86.0 | Python 3.9+ | Use 3.11+ for TaskGroup |
| aerospike 19.1.0 | Python 3.9-3.13 | C-extension; requires build tools on some platforms; use pre-built wheels from PyPI |
| RestrictedPython 8.2 | Python 3.9-3.13 | Does NOT support PyPy; CPython only |
| okta-jwt-verifier 0.4.0 | Python 3.6+ | async support built-in |
| @xyflow/react 12.4.4 | React 17, 18; React 19 support via UI components update Oct 2025 | Use React 18 for stability |
| FastAPI 0.115.x | Pydantic v2 required | Pydantic v1 will cause runtime errors |

---

## Integration Gotchas for 72-Hour Solo Build

### P0 — Could kill the demo

1. **Aerospike async gap:** The official Python client is synchronous. In an async FastAPI handler, every `client.put()` call blocks the event loop. Wrap ALL Aerospike calls in `run_in_executor` or the event loop stalls under concurrent requests. Missing this makes the dashboard freeze during investigations.

2. **Rule generation prompt reliability:** Opus 4.6 will occasionally generate Python that references undefined variables or uses non-allowlisted builtins. `compile_restricted` will raise; catch it and log — do not let it crash the Safety Gate. Test the prompt against the exact verdict_board schema 30+ times before wiring.

3. **Bland AI public URL requirement:** Bland's webhook delivery requires a publicly accessible URL. During development on localhost, use ngrok (`ngrok http 8000`). Forgetting this means the voice callback never fires and the demo voice flow silently fails.

4. **AsyncAnthropic client per-request:** If you instantiate `AsyncAnthropic()` inside a request handler, you create a new HTTP connection pool on every request. Instantiate once at module level and share the client instance across all handlers.

### P1 — Will cost hours

5. **Aerospike write policy shared mutation:** Do NOT modify the default policy dict; create a new policy dict per operation. Modifying shared policy causes thread-safety failures and mysterious write failures.

6. **React Flow package name:** The npm package is now `@xyflow/react`, not `reactflow`. The old package still installs but the import paths differ. Lock to one or the other; mixing causes duplicate React context errors.

7. **Okta issuer URL:** The introspection endpoint URL must match the authorization server that issued the token. If you use the default auth server, the URL is `https://{domain}/oauth2/default/v1/introspect`. Custom auth servers use a different path. Mismatched issuer = all tokens invalid.

8. **RestrictedPython `__builtins__` override:** If you pass `safe_globals` directly without setting `__builtins__` to your allowlist, code can still access Python's full builtins through the `safe_globals` defaults. Always explicitly set `__builtins__` in the exec namespace.

9. **WebSocket broadcast from async background tasks:** When pushing investigation updates from a background task (e.g., after agent response) to a browser WebSocket, ensure the WebSocket connection is tracked in a shared connection registry. FastAPI's WebSocket is not accessible after the initial connect handler exits without explicit tracking.

10. **Airbyte Google Sheets OAuth:** Google Sheets source in Airbyte requires OAuth 2.0 setup (service account preferred for automation). If you don't have this pre-configured, it takes 30-60 minutes. Pre-load with fixtures instead.

---

## Sources

- [anthropic-sdk-python GitHub](https://github.com/anthropics/anthropic-sdk-python) — current version 0.86.0, async patterns verified
- [Anthropic Python SDK official docs](https://platform.claude.com/docs/en/api/sdks/python) — AsyncAnthropic, aiohttp extra, streaming patterns — HIGH confidence
- [Aerospike Python Client PyPI / community forum](https://discuss.aerospike.com/t/aerospike-python-client-release-18-1-0-december-16-2025/12666) — version 19.1.0 confirmed — HIGH confidence
- [Aerospike policy blog](https://aerospike.com/blog/using-aerospike-policies-correctly/) — write policy copy-not-modify pattern — MEDIUM confidence
- [RestrictedPython docs](https://restrictedpython.readthedocs.io/en/latest/) — v8.2, compile_restricted pattern — HIGH confidence
- [Bland AI docs](https://docs.bland.ai/) — webhook and call initiation patterns — MEDIUM confidence; real-time WebSocket specifics LOW (not publicly documented)
- [okta-jwt-verifier GitHub](https://github.com/okta/okta-jwt-verifier-python) — v0.4.0, AccessTokenVerifier pattern — HIGH confidence
- [xyflow/xyflow GitHub + reactflow.dev](https://reactflow.dev) — @xyflow/react v12.4.4, animated edges — HIGH confidence
- [Python asyncio docs](https://docs.python.org/3/library/asyncio-task.html) — TaskGroup structured concurrency — HIGH confidence

---

*Stack research for: Sentinel — real-time multi-agent payment supervision system*
*Researched: 2026-03-24*
