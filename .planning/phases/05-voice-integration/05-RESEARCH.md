# Phase 5: Voice Integration - Research

**Researched:** 2026-03-25
**Domain:** Bland AI voice API, FastAPI webhook handler, in-memory context caching
**Confidence:** MEDIUM (Bland AI dynamic_data timing during call is underdocumented; core API contract is HIGH)

---

## Summary

Phase 5 wires Bland AI voice into the Sentinel demo. The core contract is: (1) initiate a call via POST `https://api.bland.ai/v1/calls` with a `task` that instructs the Supervisor to answer Q&A about a blocked payment, and (2) use `dynamic_data` with `cache: false` to inject the pre-computed investigation context into the agent's knowledge at call start and before each AI utterance. The `dynamic_data` webhook is a GET/POST call Bland AI makes to your server — the handler reads from `app_state["active_episodes"]` in memory and returns JSON that Bland AI maps into named variables available in the task prompt.

The 8-second response budget constraint comes from Bland AI's `dynamic_data` timeout default (2000ms documented, but 8s is the CLAUDE.md hard limit for our handler). The solution is already in place: `active_episodes` is populated by `POST /investigate` before the voice demo starts, so the webhook handler does zero I/O — it reads a dict and returns JSON in microseconds.

Barge-in is configured by setting `interruption_threshold` to a low value (100–200ms) and `block_interruptions: false`. No SDK work is required — these are call-initiation parameters.

**Primary recommendation:** One new route (`POST /bland-call`) initiates the call; one new route (`POST /bland-webhook`) serves `dynamic_data` requests during the call. Both are thin — no LLM calls in the webhook path. Add a frontend "Start Voice Q&A" button that calls `/bland-call` and displays the voice transcript on the dashboard as it arrives via post-call webhook.

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| VOICE-01 | Bland AI call initiated; Supervisor answers "Why did you block that?" grounded in actual scores and rule attribution | dynamic_data injects pre-computed context; task prompt instructs Supervisor persona |
| VOICE-02 | Barge-in configured via interruption_threshold and block_interruptions: false | Confirmed parameter names and behavior from official Bland AI API docs |
| VOICE-03 | All investigation context pre-computed and cached before voice demo; webhook handler reads from memory cache only | active_episodes dict already in app_state; handler returns pre-built JSON |
| VOICE-04 | Dashboard always shows same information as voice narration — text fallback always present | Already complete (DASH-07, DASH-11 etc. per REQUIREMENTS.md); no new work needed |
| API-04 | POST /bland-webhook handles Bland AI Q&A turns; responds within 8s; reads from in-memory cache | New FastAPI route; no Aerospike per-turn; microsecond read from dict |
</phase_requirements>

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| requests (sync) | 2.32.5 (already installed) | Initiate Bland AI call from FastAPI background task | Simple POST; no async needed for outbound call initiation |
| aiohttp | 3.13.3 (already installed) | Alternative for async outbound call initiation | Already installed; use if called from async context |
| fastapi | 0.115.x (already installed) | New routes: /bland-call, /bland-webhook | Already in project |
| pydantic v2 | already installed | Request/response models for both new routes | Already in project |

### No New Dependencies
All required libraries are already installed. Phase 5 adds zero new `pip install` requirements.

**Installation:**
```bash
# No new packages needed
```

**Version verification:** All packages confirmed present via pip show above.

---

## Architecture Patterns

### Recommended Project Structure

```
sentinel/
├── api/
│   ├── main.py                   # Add BLAND_API_KEY to app_state at startup
│   └── routes/
│       ├── bland_call.py         # POST /bland-call  — initiates voice call
│       └── bland_webhook.py      # POST /bland-webhook — dynamic_data handler
```

### Pattern 1: Bland AI Call Initiation

**What:** POST to `https://api.bland.ai/v1/calls` with a task that instructs the AI to answer investigative Q&A about the last blocked payment. The `dynamic_data` array tells Bland to call our `/bland-webhook` before each AI utterance with `cache: false` to get fresh investigation context.

**When to use:** When operator clicks "Start Voice Q&A" on dashboard after an investigation completes.

**Key parameters:**
```python
# Source: https://docs.bland.ai/api-v1/post/calls (verified)
call_payload = {
    "phone_number": "+1XXXXXXXXXX",  # From request or env var
    "task": (
        "You are the Sentinel Supervisor — an AI security system that blocked a payment. "
        "Answer questions about why the payment was blocked. "
        "Use the investigation context variables provided:\n"
        "- Decision: {{gate_decision}}\n"
        "- Composite anomaly score: {{composite_score}}\n"
        "- Attribution: {{attribution}}\n"
        "- Rules fired: {{rules_fired}}\n"
        "- Prediction errors: {{prediction_errors}}\n"
        "Speak in plain language. Be specific about scores and rule names."
    ),
    "voice": "maya",  # or "josh" — natural, clear
    "model": "base",  # base supports dynamic_data; turbo has limited capabilities
    "interruption_threshold": 150,  # ms — low = responsive to barge-in (VOICE-02)
    "block_interruptions": False,   # false = barge-in enabled (VOICE-02)
    "max_duration": 5,              # minutes — demo is 3 min total
    "dynamic_data": [
        {
            "url": "https://{YOUR_PUBLIC_HOST}/bland-webhook",
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
            "body": {"episode_id": "{{call_id}}"},  # or pass episode_id via request_data
            "timeout": 3000,        # ms — well within 8s CLAUDE.md budget
            "cache": False,         # refresh before each AI utterance
            "response_data": [
                {"name": "gate_decision",    "data": "$.gate_decision",    "context": "Gate decision: {{gate_decision}}"},
                {"name": "composite_score",  "data": "$.composite_score",  "context": "Composite anomaly score: {{composite_score}}"},
                {"name": "attribution",      "data": "$.attribution",      "context": "Attribution: {{attribution}}"},
                {"name": "rules_fired",      "data": "$.rules_fired",      "context": "Rules fired: {{rules_fired}}"},
                {"name": "prediction_errors","data": "$.prediction_errors","context": "Prediction errors: {{prediction_errors}}"},
            ]
        }
    ],
    "webhook": "https://{YOUR_PUBLIC_HOST}/bland-call-complete",  # post-call data
    "metadata": {"episode_id": "{episode_id}"},
    "request_data": {"episode_id": "{episode_id}"},  # available as {{episode_id}} in task + dynamic_data body
}
```

**Confidence:** HIGH for parameter names and behavior. MEDIUM for `dynamic_data` exact timing semantics (confirmed cache: false refreshes before each AI response; exact HTTP call timing is not fully documented).

### Pattern 2: dynamic_data Webhook Handler (POST /bland-webhook)

**What:** Bland AI calls this endpoint before each AI utterance (when `cache: false`). Handler reads pre-computed context from `app_state["active_episodes"]` and returns JSON that Bland maps to variables.

**Critical constraint:** Must respond in under 3s (our timeout in dynamic_data config); reads from memory dict only (zero I/O).

```python
# Source: Bland AI dynamic_data docs + FastAPI patterns
# sentinel/api/routes/bland_webhook.py

from fastapi import APIRouter, Request
from sentinel.api.main import app_state

router = APIRouter()

@router.post("/bland-webhook")
async def bland_webhook(request: Request) -> dict:
    """Serve investigation context to Bland AI dynamic_data requests.

    Bland AI calls this before each AI utterance (cache: false).
    Must respond < 3s. Reads from in-memory cache only (VOICE-03).
    """
    body = await request.json()
    episode_id = body.get("episode_id")

    # Find most recent episode if no specific ID
    if not episode_id or episode_id not in app_state.get("active_episodes", {}):
        episode_id = _get_latest_episode_id(app_state)

    episode = app_state.get("active_episodes", {}).get(episode_id)
    if episode is None:
        return _empty_context()

    # Extract fields from Episode object (Pydantic model or dict)
    return _build_voice_context(episode)


def _build_voice_context(episode) -> dict:
    """Build voice context dict from Episode — zero I/O, pure in-memory."""
    if hasattr(episode, "gate_decision"):
        # Pydantic Episode model
        gate_decision = episode.gate_decision
        gate_rationale = episode.gate_rationale or ""
        rules_fired = ", ".join(episode.rules_fired or [])
        generated_fired = ", ".join(episode.generated_rules_fired or [])
        prediction_report = episode.prediction_report or {}
    else:
        # Raw dict fallback
        gate_decision = episode.get("gate_decision", "UNKNOWN")
        gate_rationale = episode.get("gate_rationale", "")
        rules_fired = ", ".join(episode.get("rules_fired", []))
        generated_fired = ", ".join(episode.get("generated_rules_fired", []))
        prediction_report = episode.get("prediction_report") or {}

    # Extract composite score from rationale or prediction report
    composite_score = prediction_report.get("summary_score", "unknown")

    return {
        "gate_decision": gate_decision,
        "composite_score": str(composite_score),
        "attribution": gate_rationale,
        "rules_fired": f"Hardcoded: {rules_fired}; Generated: {generated_fired}" if (rules_fired or generated_fired) else "None",
        "prediction_errors": _summarize_prediction_errors(prediction_report),
    }
```

**Confidence:** HIGH — pattern derived from official dynamic_data docs + existing codebase.

### Pattern 3: Call Initiation Route (POST /bland-call)

**What:** Frontend button hits this to start the voice session. Returns `call_id` for tracking.

```python
# sentinel/api/routes/bland_call.py

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

BLAND_API_URL = "https://api.bland.ai/v1/calls"

class StartCallRequest(BaseModel):
    episode_id: str
    phone_number: str  # E.164 format
    public_host: str   # e.g. "https://abc123.ngrok.io" for demo

class StartCallResponse(BaseModel):
    call_id: str
    status: str

@router.post("/bland-call", response_model=StartCallResponse)
async def start_bland_call(req: StartCallRequest) -> StartCallResponse:
    """Initiate a Bland AI voice call grounded in the investigation context."""
    from sentinel.api.main import app_state

    episode = app_state.get("active_episodes", {}).get(req.episode_id)
    if episode is None:
        raise HTTPException(404, f"Episode {req.episode_id} not in cache")

    api_key = app_state.get("bland_api_key") or os.getenv("BLAND_API_KEY")
    payload = _build_call_payload(req, episode)

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            BLAND_API_URL,
            headers={"authorization": api_key},
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()

    return StartCallResponse(call_id=data.get("call_id", ""), status="initiated")
```

**Note:** Use `httpx` (already a transitive dependency of the `anthropic` SDK) for async HTTP. No new dependency.

**Confidence:** HIGH — httpx is already available; Bland API call initiation is well-documented.

### Pattern 4: Episode ID Threading Through dynamic_data

**Problem:** Bland AI calls `/bland-webhook` with only the variables you configured in the `body` field of `dynamic_data`. The `{{call_id}}` variable is a Bland built-in. To tie the webhook call back to the right episode, use `request_data` when initiating the call to pass the `episode_id` as a Bland variable, then reference it in the dynamic_data body.

```python
# In call payload:
"request_data": {"episode_id": req.episode_id},
# In dynamic_data body:
"body": {"episode_id": "{{episode_id}}"},
```

Alternatively: store the latest active episode ID under a well-known key in `app_state["active_episodes"]["__latest__"]` and have the webhook handler default to that key when no valid episode_id is provided. This is the simpler fallback.

**Confidence:** MEDIUM — `request_data` is documented but variable interpolation in dynamic_data body needs verification against live Bland API. The `__latest__` fallback is a safe backup.

### Pattern 5: Voice Transcript as Dashboard Text Fallback (VOICE-04)

**What:** VOICE-04 is already COMPLETE per REQUIREMENTS.md traceability (Phase 4). The dashboard panels (GateDecisionPanel, AnomalyScoreBar, VerdictBoardTable, RuleSourcePanel) always display the investigation data. No additional work needed for text fallback.

**Remaining work:** Add a "Voice Q&A" section to the dashboard that shows:
1. A "Start Voice Q&A" button (calls POST /bland-call)
2. The voice_context object as text (what the AI will say, so judges can read it)

This is minimal — a single new panel or appending to GateDecisionPanel.

### Anti-Patterns to Avoid

- **LLM in the webhook path:** Never call Anthropic API from within `/bland-webhook`. All grounding must be pre-computed text strings in `active_episodes`.
- **Aerospike per-turn read:** Never hit Aerospike in `/bland-webhook`. The 8s budget exists precisely because network I/O is prohibited on this path.
- **Storing episode_id in call metadata and fetching from Aerospike at webhook time:** That would require an Aerospike read per utterance. Use in-memory only.
- **`model: "turbo"` with dynamic_data:** Turbo model has limited capabilities. Use `model: "base"` for dynamic_data support.
- **`block_interruptions: true`:** This disables barge-in (VOICE-02). Must be `false`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Voice synthesis | Custom TTS pipeline | Bland AI API | Full voice infrastructure already managed |
| Real-time transcript display | WebSocket streaming from Bland | Post-call webhook + dashboard update | Bland doesn't support real-time WS streaming per REQUIREMENTS.md out-of-scope |
| Barge-in detection | Custom audio VAD | `interruption_threshold` parameter | Bland handles this natively |
| Context grounding | Per-turn LLM call in webhook | Pre-computed dict in active_episodes | Already built; LLM-free enforcement path |

**Key insight:** Bland AI handles all voice infrastructure. The integration surface is one outbound HTTP call to initiate and one inbound HTTP handler for dynamic_data. Both are thin — the heavy work (investigation, scoring, context) was done in previous phases.

---

## Common Pitfalls

### Pitfall 1: dynamic_data Body Variable Not Interpolated

**What goes wrong:** Bland AI does not interpolate `{{episode_id}}` in the dynamic_data `body` if the variable was not populated by a prior `request_data` or earlier `dynamic_data` response. The literal string `"{{episode_id}}"` is sent to your webhook.

**Why it happens:** Bland variable interpolation only works for variables that exist at call-time. If `request_data` was not set, the variable is empty.

**How to avoid:** Always set `request_data: {"episode_id": "<actual_id>"}` when initiating the call. Also implement the `__latest__` fallback in the webhook handler: if the received `episode_id` doesn't resolve, use `app_state["active_episodes"].get("__latest__")`.

**Warning signs:** Webhook handler receives `"{{episode_id}}"` as a string literal; returns empty context; Supervisor AI says "I don't have the investigation details."

### Pitfall 2: dynamic_data timeout Defaults to 2000ms (Not 8s)

**What goes wrong:** Bland AI's `dynamic_data` timeout defaults to 2000ms. CLAUDE.md says 8s budget, but Bland will time out the dynamic_data request at 2000ms by default if you don't override it.

**Why it happens:** The 8s budget in CLAUDE.md is a ceiling, not the Bland default. Bland's documented default is 2000ms.

**How to avoid:** Explicitly set `"timeout": 3000` (or up to 7000 for safety margin) in the dynamic_data config. The webhook handler itself must still respond in milliseconds — the budget exists for network latency variance, not computation.

**Warning signs:** AI responds without investigation context (silent timeout); blank variables in utterances.

### Pitfall 3: model: "turbo" Breaks dynamic_data

**What goes wrong:** Bland AI's turbo model has limited capabilities and does not support all `dynamic_data` features.

**Why it happens:** "turbo" is optimized for latency, not full feature support.

**How to avoid:** Always use `model: "base"` for dynamic_data integration.

**Warning signs:** Call succeeds but variables are never populated; AI response is generic.

### Pitfall 4: CORS / Public URL Required for Webhooks

**What goes wrong:** During local development, Bland AI cannot reach `localhost:8000`. The dynamic_data webhook call fails silently.

**Why it happens:** Bland AI's webhook calls originate from Bland's servers — they need a public HTTPS URL.

**How to avoid:** Use `ngrok` (or similar) for local testing: `ngrok http 8000`. For demo day, use the AWS deployment URL (Phase 6). INFRA-06 is the deployment phase, but ngrok is sufficient for Phase 5 development.

**Warning signs:** Call initiates successfully but AI answers without investigation context.

### Pitfall 5: active_episodes Cache Not Populated at Voice Demo Time

**What goes wrong:** `/bland-webhook` called but no episode in `active_episodes` — call was made before an investigation ran, or the server restarted.

**Why it happens:** `active_episodes` is in-memory only; it doesn't survive server restart. Also the webhook may be called for a prior episode ID that was evicted.

**How to avoid:** (1) Demo script always runs investigation first, then starts voice. (2) Implement `__latest__` key in active_episodes: set it in investigate.py after each investigation. (3) The webhook handler returns a "no investigation context available" string rather than an error — Bland AI continues the call.

**Warning signs:** Voice Q&A works first call; fails after server restart or second investigation.

---

## Code Examples

### Initiate Bland AI Call

```python
# Source: https://docs.bland.ai/api-v1/post/calls (verified parameters)
import httpx

async def initiate_bland_call(
    phone_number: str,
    episode_id: str,
    public_host: str,  # e.g. "https://abc.ngrok.io" or production URL
    api_key: str,
) -> dict:
    payload = {
        "phone_number": phone_number,
        "task": (
            "You are the Sentinel Supervisor — an AI security system. "
            "A payment was just investigated and a gate decision was reached. "
            "Answer questions about why the payment was blocked. "
            "You have these investigation details:\n"
            "Decision: {{gate_decision}}\n"
            "Anomaly score: {{composite_score}}\n"
            "Attribution: {{attribution}}\n"
            "Rules fired: {{rules_fired}}\n"
            "Prediction errors: {{prediction_errors}}\n\n"
            "Speak confidently. Use exact numbers. Do not make up information."
        ),
        "voice": "maya",
        "model": "base",
        "interruption_threshold": 150,
        "block_interruptions": False,
        "max_duration": 5,
        "dynamic_data": [
            {
                "url": f"{public_host}/bland-webhook",
                "method": "POST",
                "headers": {"Content-Type": "application/json"},
                "body": {"episode_id": "{{episode_id}}"},
                "timeout": 3000,
                "cache": False,
                "response_data": [
                    {"name": "gate_decision",     "data": "$.gate_decision"},
                    {"name": "composite_score",   "data": "$.composite_score"},
                    {"name": "attribution",       "data": "$.attribution"},
                    {"name": "rules_fired",       "data": "$.rules_fired"},
                    {"name": "prediction_errors", "data": "$.prediction_errors"},
                ],
            }
        ],
        "request_data": {"episode_id": episode_id},
        "webhook": f"{public_host}/bland-call-complete",
        "metadata": {"episode_id": episode_id},
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            "https://api.bland.ai/v1/calls",
            headers={"authorization": api_key, "Content-Type": "application/json"},
            json=payload,
        )
        resp.raise_for_status()
        return resp.json()  # {"call_id": "...", "status": "queued"}
```

### dynamic_data Webhook Handler

```python
# Source: architecture derived from Bland AI dynamic_data docs + codebase analysis
# sentinel/api/routes/bland_webhook.py

from fastapi import APIRouter, Request
from sentinel.api.main import app_state

router = APIRouter()

@router.post("/bland-webhook")
async def bland_webhook(request: Request) -> dict:
    """Serve investigation context to Bland AI dynamic_data (VOICE-03, API-04).

    Bland AI calls this before each AI utterance with cache: false.
    Zero I/O — reads from in-memory active_episodes dict only.
    Response time target: < 100ms (budget: 3000ms timeout configured).
    """
    try:
        body = await request.json()
    except Exception:
        body = {}

    episode_id = body.get("episode_id", "")

    # Resolve episode: specific ID or fall back to latest
    active = app_state.get("active_episodes", {})
    episode = active.get(episode_id)
    if episode is None:
        # Try __latest__ sentinel key
        latest_id = active.get("__latest__")
        episode = active.get(latest_id) if latest_id else None

    if episode is None:
        return {
            "gate_decision": "NO-GO",
            "composite_score": "unavailable",
            "attribution": "Investigation context not available",
            "rules_fired": "unknown",
            "prediction_errors": "unavailable",
        }

    return _build_voice_context(episode)


def _build_voice_context(episode) -> dict:
    if hasattr(episode, "gate_decision"):
        gate_decision = episode.gate_decision
        gate_rationale = episode.gate_rationale or ""
        rules_fired = ", ".join(episode.rules_fired or [])
        generated_fired = ", ".join(episode.generated_rules_fired or [])
        prediction_report = episode.prediction_report or {}
    else:
        gate_decision = episode.get("gate_decision", "UNKNOWN")
        gate_rationale = episode.get("gate_rationale", "")
        rules_fired = ", ".join(episode.get("rules_fired", []))
        generated_fired = ", ".join(episode.get("generated_rules_fired", []))
        prediction_report = episode.get("prediction_report") or {}

    composite_score = prediction_report.get("summary_score", "computed at gate")
    prediction_summary = _summarize_prediction_errors(prediction_report)

    rules_summary = []
    if rules_fired:
        rules_summary.append(f"hardcoded: {rules_fired}")
    if generated_fired:
        rules_summary.append(f"generated: {generated_fired}")

    return {
        "gate_decision": gate_decision,
        "composite_score": str(composite_score),
        "attribution": gate_rationale,
        "rules_fired": "; ".join(rules_summary) or "none",
        "prediction_errors": prediction_summary,
    }


def _summarize_prediction_errors(prediction_report: dict) -> str:
    if not prediction_report:
        return "none recorded"
    parts = []
    z = prediction_report.get("predicted_z_score")
    if z is not None:
        parts.append(f"z-score={z:.2f}")
    deviation = prediction_report.get("step_deviation")
    if deviation:
        parts.append("step deviation detected")
    errors = prediction_report.get("investigation_outcome_errors", {})
    if errors:
        mismatches = [k for k, v in errors.items() if not v]
        if mismatches:
            parts.append(f"outcome mismatches: {', '.join(mismatches)}")
    return "; ".join(parts) if parts else "within normal range"
```

### Registering Routes in main.py

```python
# Add to sentinel/api/main.py imports and app setup:
from sentinel.api.routes.bland_call import router as bland_call_router
from sentinel.api.routes.bland_webhook import router as bland_webhook_router

app.include_router(bland_call_router)
app.include_router(bland_webhook_router)

# In lifespan startup, add after existing app_state setup:
import os
app_state["bland_api_key"] = os.getenv("BLAND_API_KEY", "")
app_state["public_host"] = os.getenv("PUBLIC_HOST", "http://localhost:8000")
```

### Track Latest Episode ID for Fallback

```python
# In sentinel/api/routes/investigate.py, after caching episode:
app_state["active_episodes"][result["episode_id"]] = result["episode"]
app_state["active_episodes"]["__latest__"] = result["episode_id"]  # Add this line
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Bland AI webhook = post-call only | dynamic_data = per-utterance real-time data injection | 2023-2024 | Enables grounded Q&A during call |
| Block interruptions = no barge-in | interruption_threshold (ms) + block_interruptions: false | Current | Fine-grained barge-in control |
| Streaming transcripts to frontend | Post-call webhook with full transcript | Current | Real-time WS not supported; post-call data only |

**Deprecated/outdated:**
- `webhook` parameter alone: This sends data only AFTER the call ends. Use `dynamic_data` with `cache: false` for real-time grounding during the call. The post-call `webhook` is still useful for receiving the full transcript for dashboard display.

---

## Open Questions

1. **Variable interpolation in dynamic_data body**
   - What we know: `request_data` variables are available as `{{variable_name}}` in task prompts; dynamic_data body interpolation is documented but not exhaustively tested
   - What's unclear: Whether `{{episode_id}}` in the dynamic_data `body` field is reliably interpolated before the HTTP call is made
   - Recommendation: Implement `__latest__` episode_id fallback in webhook handler as primary strategy; treat request_data variable threading as secondary

2. **dynamic_data call timing**
   - What we know: `cache: false` refreshes "before each AI response"; default timeout 2000ms
   - What's unclear: Exact timing — does it call before every utterance including the opening sentence, or only before responses to user input?
   - Recommendation: Set `first_sentence` in call payload to a static opening line so the AI can speak immediately; dynamic_data populates context for subsequent Q&A turns

3. **ngrok / public URL for Phase 5 development**
   - What we know: Bland AI requires HTTPS public URL for dynamic_data webhooks; Phase 6 handles AWS deployment
   - What's unclear: Whether ngrok free tier is fast/stable enough for demo rehearsals
   - Recommendation: Use ngrok for development testing; note `PUBLIC_HOST` env var in the call initiation code so it's easy to swap to production URL in Phase 6

4. **BLAND_API_KEY env var**
   - What we know: `BLAND_API_KEY` is already in `conftest.py` with a test placeholder; present in CLAUDE.md tech stack section
   - What's unclear: Whether a real Bland API key is configured in `.env` (depends on demo environment)
   - Recommendation: Add null-check in `/bland-call` route: if `BLAND_API_KEY` is the test placeholder, return a 503 with clear message; avoids silent auth failures

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| httpx | /bland-call outbound HTTP | Yes (transitive dep of anthropic SDK) | installed | aiohttp (also installed) |
| requests | sync HTTP if needed | Yes | 2.32.5 | httpx |
| aiohttp | async HTTP | Yes | 3.13.3 | httpx |
| BLAND_API_KEY env var | /bland-call route | Unknown (test placeholder in conftest) | — | 503 response with clear error |
| Public HTTPS URL | Bland dynamic_data webhook | Unknown (localhost only during dev) | — | ngrok for development |
| FastAPI | All routes | Yes | 0.115.x | — |

**Missing dependencies with no fallback:**
- Real `BLAND_API_KEY` — required for live call; test placeholder will fail auth. Not a code issue, a configuration issue.
- Public HTTPS URL — required for Bland to reach our webhook. Use ngrok for Phase 5 dev; AWS URL for Phase 6 demo.

**Missing dependencies with fallback:**
- None — all library dependencies are present.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio |
| Config file | pytest.ini or pyproject.toml (existing) |
| Quick run command | `pytest tests/test_bland_webhook.py -x` |
| Full suite command | `pytest tests/ -x` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| API-04 | /bland-webhook returns correct context from active_episodes | unit | `pytest tests/test_bland_webhook.py::test_webhook_returns_context -x` | ❌ Wave 0 |
| API-04 | /bland-webhook returns fallback when episode not found | unit | `pytest tests/test_bland_webhook.py::test_webhook_fallback -x` | ❌ Wave 0 |
| VOICE-03 | Webhook handler reads from memory cache, not Aerospike | unit | `pytest tests/test_bland_webhook.py::test_webhook_no_aerospike_call -x` | ❌ Wave 0 |
| VOICE-01 | /bland-call builds correct payload with dynamic_data | unit | `pytest tests/test_bland_call.py::test_call_payload_structure -x` | ❌ Wave 0 |
| VOICE-02 | Call payload has interruption_threshold <= 200 and block_interruptions=False | unit | `pytest tests/test_bland_call.py::test_barge_in_params -x` | ❌ Wave 0 |
| VOICE-01 | Voice context dict contains all 5 required fields | unit | `pytest tests/test_bland_webhook.py::test_context_fields_complete -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_bland_webhook.py tests/test_bland_call.py -x`
- **Per wave merge:** `pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_bland_webhook.py` — covers API-04, VOICE-03
- [ ] `tests/test_bland_call.py` — covers VOICE-01, VOICE-02

---

## Project Constraints (from CLAUDE.md)

- **Bland AI webhook timeout:** 8-second budget — pre-compute all voice context at gate evaluation time; webhook handler must read from memory cache only
- **No LLM in enforcement path:** The block decision is an if-statement. The webhook handler is also not allowed to make LLM calls.
- **Real voice required:** 2 Bland AI judges require real integration; fallback to text-on-dashboard only if SDK proves intractable
- **Tech stack locked:** Python/FastAPI backend, React frontend, Claude API (Opus 4.6 for Supervisor, Sonnet 4.6 for sub-agents)
- **Timeline pressure:** 72-hour solo build — minimal implementation; no over-engineering
- **Aerospike:** No Aerospike reads in the webhook handler per-turn
- **anthropic SDK:** `claude-opus-4-6` for Supervisor persona in task prompt; but the task is a string — no SDK call during voice
- **VOICE-04:** Already complete (Phase 4 delivered all dashboard panels); no rework needed

---

## Sources

### Primary (HIGH confidence)
- [https://docs.bland.ai/api-v1/post/calls](https://docs.bland.ai/api-v1/post/calls) — Full parameter list: phone_number, task, voice, model, interruption_threshold, block_interruptions, dynamic_data, request_data, webhook, max_duration verified
- [https://docs.bland.ai/tutorials/dynamic-data](https://docs.bland.ai/tutorials/dynamic-data) — dynamic_data array structure, response_data mapping, cache behavior, timeout default 2000ms
- Existing codebase (sentinel/api/main.py, supervisor.py, safety_gate.py) — active_episodes cache structure, gate_result dict shape, Episode schema fields confirmed by direct inspection

### Secondary (MEDIUM confidence)
- [https://docs.bland.ai/tutorials/post-call-webhooks](https://docs.bland.ai/tutorials/post-call-webhooks) — Post-call webhook payload structure; webhook_events parameter for in-call events
- WebSearch results on interruption_threshold — confirmed 150ms example from Bland university materials; parameter is milliseconds

### Tertiary (LOW confidence)
- Variable interpolation in dynamic_data body — `{{episode_id}}` threading via request_data: documented separately, not directly verified in a combined scenario; needs live testing

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already installed, no new dependencies
- Architecture: HIGH — Bland API parameters confirmed from official docs; endpoint patterns derived from existing codebase
- Pitfalls: MEDIUM — dynamic_data timing behavior is partially underdocumented; public URL requirement is HIGH confidence

**Research date:** 2026-03-25
**Valid until:** 2026-04-25 (Bland AI API is stable; dynamic_data behavior unlikely to change)
