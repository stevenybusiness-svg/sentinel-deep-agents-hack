# Phase 7: Demo Polish & Airbyte Integration — Research

**Researched:** 2026-03-27
**Domain:** React frontend polish, @xyflow/react edge animations, FastAPI static file serving, PyAirbyte, Slack webhooks, pipeline latency
**Confidence:** HIGH (all findings verified against codebase, installed packages, and official docs)

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DEMO-POLISH-01 | Fix broken invoice images | Root cause confirmed: FastAPI only mounts `/assets` as StaticFiles; root-level `dist/` files (PNGs) are caught by the SPA catch-all which returns `index.html`. Fix: add a second `StaticFiles` mount for root-level dist files, or serve images from a named route. |
| DEMO-POLISH-02 | Reduce pipeline latency below 10s | Phase 4.1 already implemented batched tools + prompt caching + streaming. Current documented target is 8-15s. Remaining gains: Aerospike async pattern audit, reducing sub-agent max_tokens where over-provisioned, confirming cache warm on second run. |
| DEMO-POLISH-03 | Dynamic edge animations showing real-time agent activity | `@xyflow/react` supports `animated: true` (CSS dash animation) and custom edge `style` prop at runtime. Zustand `setEdgeAnimated` already exists. Enhancement: add colored stroke + per-edge style update correlated to WS events. |
| DEMO-POLISH-04 | Airbyte→Slack autonomous report delivery (replaces Bland AI voice Q&A) | PyAirbyte not installed; `requests` (via httpx in venv) can call Slack Incoming Webhook directly. Simplest viable path: after `gate_evaluated` WS event, backend calls Slack webhook URL with investigation report JSON → Block Kit message. Airbyte angle: pipe investigation episodes from Aerospike → PyAirbyte → Slack for the "autonomous report delivery" narrative. |
| DEMO-POLISH-05 | Rename attack buttons (drop "Run" prefix) | Single JSX text change in `App.jsx` lines 90 and 96. `"Run Attack 1 — Invoice Injection"` → `"Attack 1: Invoice Injection"`. |
| DEMO-POLISH-06 | Intro screen: forensic scan comparison as landing page | Add a React state flag (`showIntro`) in `App.jsx`; render full-screen `ForensicIntroScreen` component when true, transition to dashboard on button click or auto-advance after attack button press. |
</phase_requirements>

---

## Summary

Phase 7 is a polish-and-integration sprint with six distinct tasks. Four are small (button rename, image fix, latency tuning, edge animation upgrade) and two are medium-size (Airbyte→Slack integration, intro screen). All six are independent — they can be planned as separate tasks in any order.

The broken invoice images are a known FastAPI static serving gap: the current code mounts `/assets` as StaticFiles but the catch-all `/{full_path:path}` route intercepts `/invoice_clean.png` and `/invoice_forensic.png` before they can be served from `frontend/dist/`. The fix is a targeted `StaticFiles` mount for the `dist/` root-level files executed before the catch-all is registered.

The Airbyte→Slack requirement is best interpreted as: demonstrate Airbyte as the delivery mechanism for autonomous investigation reports. The most practical path for the demo is to use PyAirbyte (install it, add to requirements) to write investigation data to a local DuckDB cache, then use the Slack Incoming Webhook API to post a formatted Block Kit report to a demo channel. This satisfies both the Airbyte judge requirement and the Slack delivery narrative without requiring a managed Airbyte Cloud connection during a live demo.

Pipeline latency is already partially optimized by Phase 4.1 (batched tool calls, prompt caching, Supervisor streaming). The remaining path to a consistent sub-10s gate decision is: (1) confirm Sonnet sub-agent `max_tokens` values are not over-provisioned, and (2) add explicit timing instrumentation to identify which sub-agent is the bottleneck.

**Primary recommendation:** Implement in this order: DEMO-POLISH-05 (button rename, 5 minutes) → DEMO-POLISH-01 (image fix, 30 minutes) → DEMO-POLISH-03 (edge animations, 1 hour) → DEMO-POLISH-06 (intro screen, 1.5 hours) → DEMO-POLISH-02 (latency audit, 1 hour) → DEMO-POLISH-04 (Airbyte+Slack, 2 hours).

---

## Project Constraints (from CLAUDE.md)

- **Safety Gate**: The block decision is an if-statement. No LLM in the enforcement path.
- **Tech Stack**: Python/FastAPI backend, React frontend (React 19 confirmed in package.json), @xyflow/react 12.4.x, Zustand, Tailwind CSS
- **Aerospike**: Real persistent storage required — latency must remain visible on dashboard
- **Demo reliability**: Self-improvement loop must remain bulletproof; no regressions
- **Bland AI**: Phase 7 swaps Bland AI voice Q&A out entirely; backend routes (`/bland-call`, `/bland-webhook`) can remain but VoicePanel is replaced by AirbyteReportPanel
- **GSD Workflow**: All file edits must go through GSD commands

---

## Standard Stack

### Core (installed, verified)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| @xyflow/react | 12.4.4 (installed) | Investigation tree edge animations | Already in use; `animated` prop + `style` prop on edge objects handle all animation needs |
| Zustand | 5.0.12 (installed) | Frontend state | `setEdgeAnimated` already exists in store.js; extend for per-edge color |
| FastAPI StaticFiles | 0.115.x (installed) | Serve PNG images | `app.mount()` with `StaticFiles` is the correct FastAPI primitive |
| requests / httpx | httpx 0.28.1 (venv) | Slack webhook HTTP POST | `httpx` is already installed as an anthropic SDK transitive dep; use it for Slack call |
| airbyte (PyAirbyte) | 0.x (not installed) | Airbyte demo integration | `pip install airbyte`; DuckDB cache as local destination, no Airbyte Cloud needed |
| slack_sdk | 3.41.0 (system pip) | Slack WebhookClient | Not in .venv312; use `requests`/`httpx` with raw Slack Incoming Webhook URL instead to avoid adding dependency |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| DuckDB (via PyAirbyte default) | auto | Local destination for Airbyte demo | Installed automatically by `pip install airbyte`; no config needed |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| httpx for Slack POST | slack_sdk WebhookClient | slack_sdk is not in .venv312; adding it is one more dep for a one-line call; httpx already present |
| PyAirbyte + DuckDB | Airbyte Cloud | Airbyte Cloud requires managed connection setup during live demo — too fragile; PyAirbyte local is demo-safe |
| Custom animated edge component | `animated: true` built-in | Custom SVG animateMotion is more complex; `animated` prop + `style.stroke` covers the judge-visible demo need |

**Installation:**
```bash
# Add to requirements.txt and install in .venv312
pip install airbyte
```

Note: `airbyte` package installs DuckDB as a dependency automatically.

---

## Architecture Patterns

### DEMO-POLISH-01: Fix Broken Invoice Images

**Root cause (confirmed by code inspection):**
`sentinel/api/main.py` mounts only:
```python
app.mount("/assets", StaticFiles(directory=str(_FRONTEND_DIST / "assets")), name="assets")
```
The files `invoice_clean.png` and `invoice_forensic.png` live in `frontend/dist/` (root of dist, not in `assets/`). The catch-all route `@app.get("/{full_path:path}")` intercepts `GET /invoice_clean.png` and returns `index.html` instead.

**Fix pattern:**
```python
# In main.py, BEFORE the catch-all route, mount root-level dist files:
if _FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=str(_FRONTEND_DIST / "assets")), name="assets")
    # Serve root-level static files (favicons, invoice PNGs, etc.)
    # Using a named path prefix or direct routes:

    @app.get("/invoice_clean.png", include_in_schema=False)
    async def serve_invoice_clean():
        return FileResponse(str(_FRONTEND_DIST / "invoice_clean.png"))

    @app.get("/invoice_forensic.png", include_in_schema=False)
    async def serve_invoice_forensic():
        return FileResponse(str(_FRONTEND_DIST / "invoice_forensic.png"))

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_catch_all(full_path: str) -> FileResponse:
        return FileResponse(str(_FRONTEND_DIST / "index.html"))
```

Alternative: mount `_FRONTEND_DIST` directly as a second StaticFiles before the catch-all, using a different prefix, and update the `ForensicScanPanel.jsx` image `src` values accordingly. However, explicit named routes for the two known images are simpler and less likely to accidentally shadow API routes.

**Verification:** `curl http://localhost:8000/invoice_clean.png` must return `image/png` Content-Type.

### DEMO-POLISH-02: Pipeline Latency Below 10s

**Current baseline (from Phase 4.1 supervisor.py docstring):**
- Total time to gate decision: 8-15s (down from ~30s)
- Bottleneck: sub-agents parallel Sonnet calls (4-8s)

**Remaining levers:**

1. **Confirm cache warm on demo runs** — prompt caching only fires after the first call per server start. The demo always runs two attacks; Attack 2 should benefit from cached sub-agent system prompts. Verify with `usage.cache_read_input_tokens > 0` in API responses.

2. **Audit sub-agent `max_tokens`** — if Risk/Compliance/Forensics are set to large `max_tokens` (e.g., 4096), the API waits for the full token budget even when the agent finishes early. Reduce to 1024 for sub-agents; their structured JSON output is short.

3. **Explicit timing probe** — add `time.monotonic()` before/after each parallel task in `asyncio.TaskGroup` to identify which sub-agent is slowest. Log to console during demo dry run.

**What NOT to do:** Do not swap Supervisor from Opus 4.6 to Sonnet (CLAUDE.md constraint). Do not remove the prediction step.

### DEMO-POLISH-03: Dynamic Edge Animations

**Current state (from store.js and InvestigationTree.jsx):**
- `setEdgeAnimated(edgeId, animated)` action already exists in Zustand
- WS handler for `agent_completed` already calls `setEdgeAnimated('e-sup-risk', true)` etc.
- Default `animated: true` produces a CSS dash animation (grey, thin)

**Enhancement pattern — colored active edges:**

In `store.js`, extend `setEdgeAnimated` to also accept a `style` payload:
```javascript
setEdgeActive: (edgeId, color = '#3b82f6') => set((s) => ({
  edges: s.edges.map((e) =>
    e.id === edgeId
      ? { ...e, animated: true, style: { stroke: color, strokeWidth: 2 } }
      : e
  ),
})),
```

Then in `useWebSocket.js`, when `agent_completed` fires:
- Risk agent active: edge `e-sup-risk` → accent blue (`#3b82f6`)
- Compliance agent active: edge `e-sup-comp` → accent blue
- Forensics agent active: edge `e-sup-for` → accent blue
- Gate evaluating: edges `e-risk-gate`, `e-comp-gate`, `e-for-gate` → gold (`#e3b341`)
- Gate blocked: all gate-bound edges → danger red (`#f85149`)

On `investigation_started`, `resetInvestigation()` already clears all edges.

**@xyflow/react edge `style` prop (HIGH confidence — official docs verified):**
The `style` prop on an edge object accepts React CSSProperties. `stroke` and `strokeWidth` are standard SVG properties. The `animated` prop adds the `react-flow__edge-path` CSS animation. Both work together.

### DEMO-POLISH-04: Airbyte→Slack Autonomous Report Delivery

**Architecture:**

This requirement serves two goals: (1) demonstrate Airbyte integration for Airbyte judges, and (2) replace the Bland AI voice Q&A panel with something the team controls completely.

**Recommended approach — two-layer:**

**Layer 1 (Airbyte):** After an investigation completes and is written to Aerospike, use PyAirbyte to read from a local "source" (a synthetic source wrapping the investigation JSON) and write to a local DuckDB cache. This demonstrates PyAirbyte in the investigation path.

In practice, the simplest path for the demo: use PyAirbyte's `get_source("source-faker")` pattern adapted to create a local source from the episode data, write to DuckDB, then query DuckDB for the Slack payload. This is 15-20 lines of Python.

Alternatively (simpler, lower risk): write episode data directly to a DuckDB file from the FastAPI backend using `duckdb` directly, then read it with PyAirbyte to demonstrate the sync. DuckDB is installed as PyAirbyte's default cache anyway.

**Layer 2 (Slack):** POST to a Slack Incoming Webhook URL. Requires creating a Slack app with Incoming Webhooks enabled and adding `SLACK_WEBHOOK_URL` to `.env`.

```python
# sentinel/integrations/slack_reporter.py
import httpx
import json

async def send_investigation_report(
    episode_id: str,
    decision: str,
    composite_score: float,
    attribution: str,
    slack_webhook_url: str,
) -> bool:
    """Send investigation report to Slack via Incoming Webhook."""
    color = "#f85149" if decision == "NO-GO" else "#e3b341" if decision == "ESCALATE" else "#3fb950"
    payload = {
        "text": f"Sentinel Investigation Report — Episode {episode_id}",
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"Sentinel: {decision}"}
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"*Episode:* `{episode_id}`\n"
                        f"*Decision:* `{decision}` (score: `{composite_score:.2f}`)\n"
                        f"*Attribution:* {attribution}"
                    )
                }
            },
            {
                "type": "context",
                "elements": [{"type": "mrkdwn", "text": "Generated by Sentinel autonomous investigation pipeline"}]
            }
        ]
    }
    async with httpx.AsyncClient() as client:
        r = await client.post(slack_webhook_url, json=payload, timeout=5.0)
        return r.status_code == 200
```

**Frontend replacement for VoicePanel:**
Replace `VoicePanel.jsx` with `AirbyteReportPanel.jsx`:
- Shows "Report sent to Slack" status after gate_evaluated
- Displays the Slack message preview (same fields as the webhook payload)
- Has a "Send Report" button for demo control (auto-send also acceptable)
- No phone number input, no public host URL input needed

**New WS event:** `report_delivered` — fired after Slack webhook succeeds, carries `{episode_id, channel, timestamp}`. Frontend panel shows confirmation.

**Env var additions:**
```
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
```

### DEMO-POLISH-05: Button Rename

Single text change in `frontend/src/App.jsx`:

| Current (line ~90) | New |
|---|---|
| `Run Attack 1 &mdash; Invoice Injection` | `Attack 1: Invoice Injection` |
| `Run Attack 2 &mdash; Identity Spoofing` | `Attack 2: Identity Spoofing` |

Use a colon separator (`:`) instead of em-dash for cleaner display. No logic changes.

### DEMO-POLISH-06: Intro Screen

**Goal:** Judges see the forensic scan comparison before the main dashboard, understanding the attack scenario before the investigation runs.

**Pattern — React state flag:**

```jsx
// App.jsx addition
const [showIntro, setShowIntro] = useState(true)

// Render branch
if (showIntro) {
  return <ForensicIntroScreen onContinue={() => setShowIntro(false)} />
}
return <MainDashboard ... />
```

`ForensicIntroScreen` is a new component (or inline JSX) that renders:
- Full-screen dark background
- Side-by-side clean invoice vs. forensic scan (reuses the image paths)
- "Attack 1: Invoice Injection" headline with explanation text
- "Launch Dashboard" / "Start Demo" button that calls `onContinue()`
- Optional: auto-advance when attack button is pressed (call `setShowIntro(false)` from `runAttack()`)

**Transition:** No animation needed; instant state swap is fine for a demo. If desired, a CSS `opacity` transition via Tailwind `transition-opacity` is sufficient.

**Key constraint:** The forensic images must be loading correctly (DEMO-POLISH-01 fix must be complete first) for the intro screen to display them.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead |
|---------|-------------|-------------|
| Slack message sending | Custom HTTP client with retry logic | `httpx.AsyncClient.post()` one-shot — no retries needed for demo; 5s timeout catches failures |
| Edge animation timing | Custom JS animation loop | `@xyflow/react` `animated` prop + WS event timing already drives the sequence |
| Airbyte data pipeline config | Airbyte Cloud connection with UI setup | PyAirbyte local with DuckDB cache — zero infrastructure during live demo |
| Intro screen routing | React Router | Single `useState` flag in App.jsx — one component, no routing needed |

---

## Common Pitfalls

### Pitfall 1: SPA Catch-All Intercepts Static Files

**What goes wrong:** FastAPI's `@app.get("/{full_path:path}")` matches before `StaticFiles` if registered in the wrong order. `invoice_clean.png` returns `index.html` content with `text/html` Content-Type. Browser fails to render `<img>`.

**Why it happens:** FastAPI route registration is order-sensitive. The catch-all pattern `{full_path:path}` is a wildcard that matches everything. `StaticFiles` mounts take priority over path-operation routes only when mounted before they are registered.

**How to avoid:** Either (a) add explicit named routes for each known image file *before* the catch-all, or (b) mount the entire `dist/` root as a StaticFiles mount before the catch-all. Option (a) is safer as it won't accidentally shadow API routes.

**Warning signs:** `<img>` tag renders broken; browser DevTools Network tab shows the response Content-Type as `text/html` for the `.png` request.

### Pitfall 2: PyAirbyte Install Pulls in Conflicting Dependencies

**What goes wrong:** `pip install airbyte` installs DuckDB and other dependencies. If the version of DuckDB conflicts with a transitive dep in the existing venv, install may fail or break existing packages.

**Why it happens:** PyAirbyte has a broad dependency tree.

**How to avoid:** Install in a fresh `pip install airbyte` to venv312 and run `pip check` afterward. If conflicts appear, use `airbyte` in a lightweight subprocess pattern or replace the PyAirbyte layer with a direct `duckdb` insert instead.

**Warning signs:** `pip check` reports conflicts after install; `import airbyte` raises ImportError.

### Pitfall 3: Slack Webhook Rate Limits and Errors

**What goes wrong:** The Slack Incoming Webhook URL is invalid, expired, or the workspace removed the app. The backend POST returns a non-200 status silently.

**How to avoid:** Test the webhook URL manually before demo day with `curl -X POST $SLACK_WEBHOOK_URL -H 'Content-type: application/json' -d '{"text":"test"}'`. `demo_check.py` should include a Slack connectivity check.

**Warning signs:** `send_investigation_report` returns `False`; no message appears in Slack channel.

### Pitfall 4: Intro Screen Blocks Attack Button Event Flow

**What goes wrong:** If the intro screen is rendered as a full-page replacement, clicking "Attack 1" before dismissing the intro has no visible effect. Users may think the system is broken.

**How to avoid:** Make attack buttons on the intro screen themselves dismiss the intro AND trigger the attack in one click. Or auto-dismiss intro on first WS `investigation_started` event.

**Warning signs:** User clicks attack button on intro, nothing happens, confusion.

### Pitfall 5: Edge Color Reset on Re-investigation

**What goes wrong:** After Attack 1 completes with red danger edges, running Attack 2 starts a new investigation but `initInvestigationTree()` re-creates edges with no `style` property (default grey). If previous attack left colored edges in a cached state, they may persist across investigations.

**Why it happens:** `resetInvestigation()` sets `edges: []`, then `initInvestigationTree()` resets edges to default objects without styles. This is correct behavior — but only if `initInvestigationTree` is called *after* `resetInvestigation`.

**How to avoid:** Verify the WS handler sequence in `useWebSocket.js`: `investigation_started` calls `s.resetInvestigation()` then `s.initInvestigationTree()`. This is already correct in the existing code. The new `setEdgeActive` action should only apply styles during an active investigation, not at init time.

---

## Code Examples

### Image Fix — FastAPI Named Routes Before Catch-All

```python
# Source: FastAPI docs + codebase inspection of sentinel/api/main.py
if _FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=str(_FRONTEND_DIST / "assets")), name="assets")

    # Named routes for root-level PNGs — MUST be registered before the catch-all
    @app.get("/invoice_clean.png", include_in_schema=False)
    async def invoice_clean():
        return FileResponse(str(_FRONTEND_DIST / "invoice_clean.png"), media_type="image/png")

    @app.get("/invoice_forensic.png", include_in_schema=False)
    async def invoice_forensic():
        return FileResponse(str(_FRONTEND_DIST / "invoice_forensic.png"), media_type="image/png")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_catch_all(full_path: str) -> FileResponse:
        return FileResponse(str(_FRONTEND_DIST / "index.html"))
```

### Edge Active State with Color — Zustand Store

```javascript
// Source: @xyflow/react docs (style prop) + existing store.js pattern
setEdgeActive: (edgeId, color) => set((s) => ({
  edges: s.edges.map((e) =>
    e.id === edgeId
      ? { ...e, animated: true, style: { stroke: color, strokeWidth: 2 } }
      : e
  ),
})),
```

### Slack Report — httpx Async POST

```python
# Source: Slack Incoming Webhooks API docs
async def send_investigation_report(episode_id, decision, score, attribution, webhook_url):
    payload = {
        "text": f"Sentinel blocked episode {episode_id}",
        "blocks": [
            {"type": "header", "text": {"type": "plain_text", "text": f"Sentinel: {decision}"}},
            {"type": "section", "text": {"type": "mrkdwn",
                "text": f"*Episode:* `{episode_id}`\n*Score:* `{score:.2f}`\n*Why:* {attribution}"}},
        ]
    }
    async with httpx.AsyncClient() as client:
        r = await client.post(webhook_url, json=payload, timeout=5.0)
    return r.status_code == 200
```

### PyAirbyte Local Cache Write (for Airbyte judge demo)

```python
# Source: PyAirbyte docs — source-faker pattern adapted for local episode data
import airbyte as ab

# Write investigation summary to local DuckDB (Airbyte's default cache)
cache = ab.get_default_cache()  # DuckDB at ~/.cache/airbyte/...
# PyAirbyte: use write() with a local source adapter or direct DuckDB insert
# For demo purposes, write the episode record directly to DuckDB via duckdb library,
# then demonstrate PyAirbyte reading it back with cache.get_pandas_dataframe("episodes")
```

Note: The cleanest Airbyte demo narrative is: "After each incident, Sentinel writes the episode to Aerospike (latency badge), then PyAirbyte syncs the investigation record to our analytics cache, and autonomously delivers a Block Kit report to the security team's Slack channel." This three-step flow is judge-visible and autonomous.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `reactflow` package | `@xyflow/react` | v12 (2023) | Already using correct package |
| Socket.io | Native WebSocket | Always (project decision) | No change needed |
| Bland AI voice Q&A | Airbyte→Slack report delivery | Phase 7 | VoicePanel replaced by AirbyteReportPanel |

---

## Open Questions

1. **PyAirbyte dependency conflict risk**
   - What we know: `airbyte` is not installed in .venv312; DuckDB is a heavy transitive dep
   - What's unclear: Whether PyAirbyte's deps conflict with existing packages (anthropic 0.86, pydantic 2.x, fastapi 0.115)
   - Recommendation: `pip install airbyte` in venv312 and run `pip check` as the Wave 0 task; if conflict, fall back to direct DuckDB + `httpx` for Slack (drops Airbyte from the architecture, weakens judge appeal)

2. **Slack workspace and webhook URL availability**
   - What we know: Slack Incoming Webhooks require a Slack app configured for a workspace; the URL is a secret
   - What's unclear: Whether a demo Slack workspace and webhook URL exist or need to be created
   - Recommendation: Add `SLACK_WEBHOOK_URL` to `.env.example`; demo_check.py should test it; if not available, AirbyteReportPanel shows a mock "Report sent" UI with hardcoded JSON preview

3. **Latency floor — is sub-10s actually achievable?**
   - What we know: Phase 4.1 documented 8-15s target; 3 parallel Sonnet calls are 4-8s
   - What's unclear: Whether the Anthropic API latency floor allows consistent sub-10s with Opus 4.6 Supervisor + 3x Sonnet sub-agents in production
   - Recommendation: Run 5 dry_run.py timed arcs and record actual wall-clock times; if 10s is not achievable, the requirement becomes "best effort + streaming display hides latency"

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12 (venv312) | Backend runtime | ✓ | 3.12.x (in .venv312) | — |
| @xyflow/react | Edge animations | ✓ | 12.4.4 (package.json) | — |
| httpx | Slack webhook POST | ✓ | 0.28.1 (in .venv312) | — |
| airbyte (PyAirbyte) | Airbyte demo integration | ✗ | — | Direct duckdb insert + omit Airbyte branding |
| Slack Incoming Webhook URL | Slack report delivery | Unknown | — | Mock UI with "Report Queued" display |
| Invoice PNGs in dist/ | Intro screen + Forensic panel | ✓ | Present in frontend/dist/ and public/ | — |

**Missing dependencies with no fallback:**
- None that block core requirements

**Missing dependencies with fallback:**
- `airbyte`: install in Wave 0; fallback is direct DuckDB + remove Airbyte label
- `SLACK_WEBHOOK_URL`: env var must be configured; fallback is mock panel UI

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio (installed in .venv312) |
| Config file | pyproject.toml (`[tool.pytest.ini_options]`) |
| Quick run command | `.venv312/bin/pytest tests/ -x -q --tb=short` |
| Full suite command | `.venv312/bin/pytest tests/ -q --tb=short` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DEMO-POLISH-01 | `/invoice_clean.png` returns `image/png` Content-Type | integration | `pytest tests/test_api.py -k "invoice" -x` | ❌ Wave 0 |
| DEMO-POLISH-01 | `/invoice_forensic.png` returns `image/png` Content-Type | integration | `pytest tests/test_api.py -k "invoice" -x` | ❌ Wave 0 |
| DEMO-POLISH-02 | Pipeline wall-clock time measurement | manual | `python scripts/dry_run.py` (existing) | ✅ |
| DEMO-POLISH-03 | Edge `animated` and `style` updated on agent_completed WS event | unit (store) | `pytest tests/test_frontend_store.py -x` | ❌ Wave 0 |
| DEMO-POLISH-04 | `send_investigation_report` posts to Slack webhook URL | unit (mock) | `pytest tests/test_slack_reporter.py -x` | ❌ Wave 0 |
| DEMO-POLISH-05 | Button text does not contain "Run" | manual | Visual inspection in browser | — |
| DEMO-POLISH-06 | Intro screen renders before main dashboard | manual | Visual inspection in browser | — |

### Sampling Rate

- **Per task commit:** `.venv312/bin/pytest tests/test_api.py tests/test_slack_reporter.py -x -q`
- **Per wave merge:** `.venv312/bin/pytest tests/ -q --tb=short`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_api.py` — add `test_invoice_images_served_as_png` tests for DEMO-POLISH-01
- [ ] `tests/test_slack_reporter.py` — unit tests for `send_investigation_report` with `httpx` mock for DEMO-POLISH-04
- [ ] `tests/test_frontend_store.py` — if frontend store tests are in scope; otherwise mark as manual

*(Existing test infrastructure covers all other phase requirements; the three items above are the only new test files needed.)*

---

## Sources

### Primary (HIGH confidence)

- Codebase inspection (`sentinel/api/main.py` lines 167-176) — confirmed image serving gap
- Codebase inspection (`frontend/src/store.js` lines 128-133) — `setEdgeAnimated` confirmed
- Codebase inspection (`frontend/src/hooks/useWebSocket.js` lines 44-50) — `agent_completed` handler confirmed
- [reactflow.dev/examples/edges/animating-edges](https://reactflow.dev/examples/edges/animating-edges) — `animated` prop + custom SVG patterns
- [reactflow.dev/learn/customization/theming](https://reactflow.dev/learn/customization/theming) — `style` prop on edges, CSS variables
- [docs.slack.dev/messaging/sending-messages-using-incoming-webhooks](https://docs.slack.dev/messaging/sending-messages-using-incoming-webhooks/) — Block Kit payload format

### Secondary (MEDIUM confidence)

- [docs.airbyte.com/using-airbyte/pyairbyte/getting-started](https://docs.airbyte.com/using-airbyte/pyairbyte/getting-started) — PyAirbyte `get_source` + DuckDB cache pattern verified
- Phase 4.1 RESEARCH.md (project history) — latency baseline 8-15s, confirmed Phase 4.1 optimizations landed

### Tertiary (LOW confidence)

- None. All critical claims verified via codebase or official docs.

---

## Metadata

**Confidence breakdown:**
- Image fix root cause: HIGH — confirmed by reading main.py and dist/ directory listing
- Edge animation patterns: HIGH — verified from reactflow.dev docs
- Airbyte→Slack architecture: MEDIUM — PyAirbyte docs verified, Slack webhook pattern verified, but integration not yet tested in this environment
- Latency target achievability: MEDIUM — depends on Anthropic API latency floor which is not controllable

**Research date:** 2026-03-27
**Valid until:** 2026-04-10 (stable libraries; Slack API and PyAirbyte API are stable)
