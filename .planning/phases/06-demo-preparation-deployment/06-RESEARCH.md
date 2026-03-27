# Phase 6: Demo Preparation + Deployment - Research

**Researched:** 2026-03-26
**Domain:** Demo hardening, deployment, docker-compose, validation scripting, screen recording
**Confidence:** HIGH

## Summary

Phase 6 is the final hardening phase before the live demo. All five core phases are complete. The system already runs: FastAPI serves both the API and the pre-built React frontend as a SPA (via the quick-260326-07t fix), Aerospike runs in Docker, and the full investigation arc is wired end-to-end. This phase has three distinct workstreams: (1) local docker-compose startup so the full stack starts in one command, (2) a demo_check.py validation script that confirms every integration is live before stepping on stage, (3) deployment with a public URL so Bland AI webhooks can reach the backend.

The critical deployment constraint is that the deadline is 2026-03-27 (tomorrow). There is no Docker runtime installed on this machine — Docker Desktop, OrbStack, Rancher Desktop, and colima are all absent. This means docker-compose cannot be tested locally during plan execution. The deployment target must be a platform that runs the Dockerfile in the cloud, not localhost. The pragmatic path for the hackathon deadline is: write the Dockerfile + docker-compose.yml (for documentation and future local use), deploy the backend to Railway (simplest Docker-based cloud with WebSocket support and drag-to-import docker-compose), and use ngrok as the fallback public URL if Railway takes too long. Aerospike runs as a Docker sidecar service on Railway alongside FastAPI.

The frontend is already built (`frontend/dist/` exists) and is already served as static files by FastAPI at the SPA catch-all route. No separate frontend deployment is needed — the single FastAPI container serves everything.

**Primary recommendation:** Write Dockerfile + docker-compose.yml first, then deploy FastAPI+Aerospike to Railway as two services (FastAPI service + Aerospike service imported from docker-compose). Use ngrok as a 30-minute fallback if Railway deployment stalls. Capture screen recording with ffmpeg avfoundation (device index 2, already verified available).

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INFRA-06 | Deployment configured with public URL for Bland AI webhooks | Railway or ngrok provides public HTTPS URL; webhook URL injected via PUBLIC_HOST env var already wired in bland_call.py |
| DEMO-01 | docker-compose.yml runs full stack (FastAPI, Aerospike, React) in one command | Dockerfile for FastAPI (builds frontend + runs uvicorn), Aerospike sidecar from existing aerospike.conf + image |
| DEMO-02 | demo_check.py validates all components before demo | httpx for HTTP/health checks, websockets library (v16.0 already in venv) for WS test, aerospike client for namespace check, httpx for Bland AI reachability |
| DEMO-04 | Full demo arc end-to-end without intervention under 3 minutes | Dry-run script that fires Attack 1, confirms, fires Attack 2, confirms — measuring elapsed time; state reset between runs |
| DEMO-05 | Screen recording of full demo arc as local file | ffmpeg avfoundation device "[2] Capture screen 0" verified available; record to MP4 |
</phase_requirements>

## User Constraints (from Phase Context)

### Deployment Override (Critical)
- User wants Vercel-style platform instead of AWS EC2/ECS (ROADMAP says EC2/ECS but user overrides this)
- Frontend: already served by FastAPI as static SPA — no separate frontend deployment needed
- Backend: Railway or Render or Fly.io — must support WebSocket + persistent process
- Aerospike: Docker sidecar on backend host, OR Aerospike Cloud
- Priority: SIMPLEST path that meets demo deadline (2026-03-27)
- docker-compose for local dev is still needed in the artifact
- Screen recording fallback is important insurance

### Locked Decisions (from Project)
- Block decision is an if-statement — no LLM in enforcement path
- Aerospike must show real latency on dashboard (cannot be mocked away)
- Bland AI webhooks require a publicly reachable HTTPS URL
- Fallback = text narration if voice fails (dashboard always shows same info)

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Docker | Engine 20+ | Container runtime for Aerospike sidecar | Aerospike runs natively on Linux only; Docker is the only supported macOS/cloud path |
| uvicorn | 0.34.0 | ASGI server inside container | Already in requirements.txt; `--host 0.0.0.0 --port 8000` |
| Railway | current | Cloud deployment platform | Supports Dockerfile, WebSocket persistent connections, drag-drop docker-compose import, $5 free credit covers demo |
| ngrok | latest | Fallback public URL tunnel | `brew install ngrok`, free account, `ngrok http 8000` — 30-second setup if Railway stalls |
| httpx | 0.28.1 | HTTP client in demo_check.py | Already in venv as transitive dep; async-capable for parallel checks |
| websockets | 16.0 | WebSocket client in demo_check.py | Already in venv; `websockets.connect()` API |
| ffmpeg | 4.3.1 | Screen recording | Already installed at /usr/local/bin/ffmpeg; avfoundation device index 2 verified |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| aerospike | 19.1.0 | Namespace validation in demo_check.py | Reuse existing AerospikeClient from sentinel.memory.aerospike_client |
| python-dotenv | 1.0.x | Env var loading in demo_check.py | Already in venv; load .env before checks |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Railway | Render | Render free tier spins down on inactivity (fatal for demo); Railway doesn't sleep |
| Railway | Fly.io | Fly.io requires fly CLI install + more config; Railway has drag-drop docker-compose |
| Railway + Aerospike sidecar | Aerospike Cloud | Aerospike Cloud requires separate account + Python client config changes; sidecar is simpler |
| ngrok | localtunnel | ngrok has stable HTTPS URL with free account; localtunnel URL changes per restart |
| ffmpeg screen recording | QuickTime | QuickTime Player not found on this machine; ffmpeg is already installed |

**Installation:**
```bash
# Deployment tools
brew install ngrok
ngrok config add-authtoken <token>

# Railway CLI (optional — can use web UI drag-drop instead)
npm install -g @railway/cli
railway login

# No new Python deps needed — httpx, websockets, aerospike all in venv
```

## Architecture Patterns

### Deployment Architecture (Simplest Path)

```
Railway Project
├── sentinel-backend (Dockerfile)    # FastAPI + pre-built React SPA
│   ├── POST /investigate
│   ├── POST /confirm
│   ├── POST /bland-call
│   ├── POST /bland-webhook          ← Bland AI calls this
│   ├── GET /ws                      ← WebSocket
│   └── GET /* → frontend/dist/index.html
└── sentinel-aerospike               # aerospike/aerospike-server:latest
    ├── port 3000 (service)
    └── config: aerospike.conf
```

Environment variables on Railway backend service:
```
ANTHROPIC_API_KEY=<from .env>
BLAND_API_KEY=<from .env>
AEROSPIKE_HOST=sentinel-aerospike.railway.internal  (Railway internal DNS)
AEROSPIKE_PORT=3000
AEROSPIKE_NAMESPACE=sentinel
PUBLIC_HOST=https://<railway-generated-url>.up.railway.app
DEMO_PHONE_NUMBER=<phone>
```

### Local dev-compose Architecture

```
docker-compose.yml
├── sentinel-backend   # Dockerfile.dev (uvicorn --reload, mounts source)
│   depends_on: aerospike
└── aerospike          # aerospike/aerospike-server:latest
    volumes: ./aerospike.conf + aerospike-data volume
```

The existing `docker-compose.yml` only has Aerospike. Phase 6 extends it to add the FastAPI service.

### Pattern 1: Dockerfile (Production + Railway)
**What:** Single-stage build — install Python deps, build React frontend, run uvicorn
**When to use:** Railway deployment, docker-compose prod service

```dockerfile
# Source: standard FastAPI + Vite pattern
FROM python:3.12-slim

# Install Node.js for frontend build
RUN apt-get update && apt-get install -y nodejs npm build-essential && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python deps first (cache layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Frontend build
COPY frontend/ ./frontend/
WORKDIR /app/frontend
RUN npm ci && npm run build

# Backend source
WORKDIR /app
COPY sentinel/ ./sentinel/
COPY aerospike.conf .
COPY pyproject.toml .
RUN pip install -e . --no-deps

# Expose and run
EXPOSE 8000
CMD ["uvicorn", "sentinel.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**NOTE on Aerospike C-extension:** The `aerospike==19.1.0` package requires build tools. `python:3.12-slim` needs `build-essential` + `libssl-dev` + `libssl3` at minimum. Add `RUN apt-get install -y build-essential libssl-dev python3-dev` before pip install.

### Pattern 2: docker-compose.yml (Full Stack Local)
**What:** Extends existing docker-compose.yml to add FastAPI service
**When to use:** Local dev, anyone cloning the repo

```yaml
version: "3.8"
services:
  aerospike:
    image: aerospike/aerospike-server:latest
    ports:
      - "3000:3000"
    volumes:
      - ./aerospike.conf:/opt/aerospike/etc/aerospike.conf
      - aerospike-data:/opt/aerospike/data
    command: ["--config-file", "/opt/aerospike/etc/aerospike.conf"]
    healthcheck:
      test: ["CMD", "asinfo", "-v", "status"]
      interval: 5s
      timeout: 3s
      retries: 10

  sentinel:
    build: .
    ports:
      - "8000:8000"
    env_file: .env
    environment:
      - AEROSPIKE_HOST=aerospike
      - AEROSPIKE_PORT=3000
    depends_on:
      aerospike:
        condition: service_healthy

volumes:
  aerospike-data:
```

### Pattern 3: demo_check.py Structure
**What:** Pre-demo validation script; exits 0 if all clear, prints failures and exits 1 if any check fails
**When to use:** Run before every demo presentation

```python
#!/usr/bin/env python3
"""
demo_check.py — Pre-demo validation script (DEMO-02)
Run: python demo_check.py [--host https://your-url.railway.app]
Exits 0 if all checks pass. Prints failures and exits 1 otherwise.
"""
import sys, asyncio, httpx, aerospike, websockets
from dotenv import load_dotenv
import os

async def main():
    load_dotenv()
    host = sys.argv[2] if len(sys.argv) > 2 else "http://localhost:8000"
    failures = []

    # 1. Health endpoint
    # 2. Aerospike namespace accessible (direct client check)
    # 3. API keys valid (ANTHROPIC_API_KEY set and non-empty)
    # 4. BLAND_API_KEY set
    # 5. Bland AI reachable (HEAD to api.bland.ai)
    # 6. WebSocket connects and receives first event (connect + ping)
    # 7. Both fixture sets load (GET /api/fixtures or inline fixture loader)
    # 8. /investigate endpoint responds (smoke POST with Attack 1 fixture)

    if failures:
        for f in failures: print(f"FAIL: {f}")
        sys.exit(1)
    print("All checks passed — demo ready")

asyncio.run(main())
```

### Pattern 4: Demo Reset Between Dry Runs
**What:** Clear Aerospike data between consecutive demo arcs so rules don't pre-exist
**When to use:** Between dry runs (DEMO-04 requires two consecutive clean arcs)

```python
# Reset: truncate episodes and rules sets in Aerospike
client.truncate("sentinel", "episodes", 0)
client.truncate("sentinel", "rules", 0)
client.truncate("sentinel", "trust", 0)
```

The Aerospike Python client `truncate()` method removes all records from a set. This is the correct pattern for resetting demo state without restarting the server.

### Pattern 5: Screen Recording with ffmpeg
**What:** Record the demo screen to MP4 using avfoundation (already verified)
**When to use:** DEMO-05 screen recording capture

```bash
# Device index 2 = "Capture screen 0" (verified on this machine)
# Record to file, no audio (or add ":0" for microphone index 1)
ffmpeg -f avfoundation -r 30 -i "2:" -vcodec libx264 -pix_fmt yuv420p demo_recording.mp4

# With microphone audio
ffmpeg -f avfoundation -r 30 -i "2:1" -vcodec libx264 -pix_fmt yuv420p demo_recording_audio.mp4

# Stop recording: Ctrl+C
# Convert to smaller file for sharing:
ffmpeg -i demo_recording.mp4 -vf scale=1280:720 -crf 28 demo_final.mp4
```

**Permission note:** macOS requires Terminal to have Screen Recording permission in System Preferences > Privacy & Security > Screen Recording. Must grant permission before running.

### Anti-Patterns to Avoid
- **Separate frontend deployment:** Frontend dist is already served by FastAPI SPA catch-all — deploying React to Vercel separately would require CORS config and breaks the single-origin WebSocket pattern
- **Mocking Aerospike in demo_check.py:** The entire point of DEMO-02 is confirming the real Aerospike integration; mock would defeat the purpose
- **Running demo_check.py against a cold server:** Server needs Aerospike connected to pass checks; always start server first, wait for health check, then run demo_check.py
- **Aerospike truncate on startup:** Truncating state at server startup would break the demo arc (rules generated in Attack 1 must persist for Attack 2); only truncate manually between dry runs
- **Using `docker-compose up --build` during demo:** Build time is ~3 minutes; always pre-build and test with `docker-compose up` (no rebuild flag) for demo day

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| WebSocket connectivity check | Custom TCP socket test | `websockets.connect()` with async context | Handles handshake, protocols, TLS negotiation correctly |
| Aerospike health check | Raw TCP port check | Existing `AerospikeClient.health_check()` from sentinel.memory.aerospike_client | Already implements read-after-write validation per INFRA-02 |
| Public HTTPS tunnel | Custom reverse proxy | ngrok | TLS termination, stable URL with free account, 30-second setup |
| Screen video compression | Custom ffmpeg pipeline | Single ffmpeg command with libx264 + crf | Handles keyframes, container format, codec compatibility |
| Demo state reset | New API endpoint | Aerospike `client.truncate()` directly in reset script | No new code surface; truncate is atomic and immediate |

**Key insight:** Every tool needed for Phase 6 is already installed or available via a single brew/npm command. The work is configuration and wiring, not new infrastructure.

## Common Pitfalls

### Pitfall 1: Aerospike C-Extension Build Failure in Docker
**What goes wrong:** `pip install aerospike==19.1.0` fails inside the container with `error: command 'gcc' failed`
**Why it happens:** `python:3.12-slim` omits build tools; aerospike is a C-extension requiring gcc, python headers, and libssl
**How to avoid:** Add before pip install: `RUN apt-get update && apt-get install -y build-essential libssl-dev python3-dev && rm -rf /var/lib/apt/lists/*`
**Warning signs:** Docker build exits at the pip install aerospike step with a C compile error

### Pitfall 2: Aerospike Host Resolution in docker-compose
**What goes wrong:** FastAPI container tries to connect to `localhost:3000` for Aerospike; connection refused
**Why it happens:** `AEROSPIKE_HOST` defaults to `"localhost"` in config.py; in docker-compose the Aerospike container is on a separate network host
**How to avoid:** Set `environment: AEROSPIKE_HOST=aerospike` in the sentinel service (service name = DNS hostname in compose network)
**Warning signs:** Server logs "Failed to connect" for Aerospike at startup; /health returns `"aerospike": false`

### Pitfall 3: Railway Aerospike Service Name for Internal DNS
**What goes wrong:** FastAPI on Railway tries to reach `localhost:3000` for Aerospike
**Why it happens:** Railway uses private network DNS for inter-service communication; the hostname is `<service-name>.railway.internal`
**How to avoid:** Set `AEROSPIKE_HOST=sentinel-aerospike.railway.internal` (or whatever the Railway service is named) as a Railway env var on the backend service
**Warning signs:** Health endpoint returns `"aerospike": false` on the deployed URL

### Pitfall 4: Bland AI Webhook URL Not Set
**What goes wrong:** Voice call initiates but webhook responses are empty; `{{gate_decision}}` placeholders not replaced
**Why it happens:** `public_host` in bland_call.py defaults to `"http://localhost:8000"`; Bland AI can't reach localhost from the cloud
**How to avoid:** Set `PUBLIC_HOST=https://<your-railway-url>.up.railway.app` as env var on the deployed service; the `/bland-call` frontend sends this in the request body via `StartCallRequest.public_host` field
**Warning signs:** Bland AI call starts but voice answers generic questions without investigation data

### Pitfall 5: macOS Screen Recording Permission
**What goes wrong:** ffmpeg avfoundation records a black screen
**Why it happens:** macOS privacy requires explicit Screen Recording permission for Terminal
**How to avoid:** Go to System Preferences > Privacy & Security > Screen Recording, add Terminal.app, restart Terminal, then record
**Warning signs:** ffmpeg runs without error but output file is solid black

### Pitfall 6: Demo State Pollution Between Dry Runs
**What goes wrong:** Attack 2 dry run shows Rule #001 already fired from previous Attack 1 — the "learning moment" is already spent
**Why it happens:** Generated rules persist in Aerospike across server restarts (by design); demo runs on a dirty database
**How to avoid:** Run Aerospike truncate script between dry runs (not between Attack 1 and Attack 2 within a single arc)
**Warning signs:** Dashboard shows "Blocked by Generated Rule #001 (learned from Episode #001)" before clicking "Confirm Attack 1"

### Pitfall 7: Front-End React Build Not Refreshed
**What goes wrong:** Deployed container serves stale frontend; new VoicePanel or QualitativeAnalysisPanel missing
**Why it happens:** Dockerfile copies frontend/dist/ as-is; if npm run build wasn't run before docker build, old dist is used
**How to avoid:** Dockerfile must run `npm ci && npm run build` as part of the build process (not rely on pre-committed dist)
**Warning signs:** Dashboard missing panels added in Phase 4.1 or Phase 5

## Code Examples

Verified patterns from official sources and existing codebase:

### Aerospike truncate (state reset between dry runs)
```python
# Source: Aerospike Python client docs
# Reset all demo state — run between consecutive dry-run arcs
def reset_demo_state(aerospike_host: str = "localhost", port: int = 3000):
    config = {"hosts": [(aerospike_host, port)]}
    client = aerospike.client(config).connect()
    for set_name in ["episodes", "rules", "trust"]:
        try:
            client.truncate("sentinel", set_name, 0)
            print(f"Truncated sentinel.{set_name}")
        except aerospike.exception.InvalidRequest:
            pass  # Set doesn't exist yet — OK
    client.close()
```

### demo_check.py WebSocket check
```python
# Source: websockets library docs (v16.0)
import websockets

async def check_websocket(host: str) -> bool:
    ws_url = host.replace("https://", "wss://").replace("http://", "ws://") + "/ws"
    try:
        async with websockets.connect(ws_url, open_timeout=5) as ws:
            return True  # Connection established
    except Exception as e:
        return False
```

### demo_check.py Bland AI reachability
```python
# Source: httpx docs — simple HEAD request
async def check_bland(api_key: str) -> bool:
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            resp = await client.get(
                "https://api.bland.ai/v1/me",
                headers={"authorization": api_key}
            )
            return resp.status_code in (200, 403)  # 403 = key wrong but API reachable
        except Exception:
            return False
```

### Dockerfile Aerospike C-extension build fix
```dockerfile
# Source: aerospike PyPI page — build dependencies for slim images
FROM python:3.12-slim
RUN apt-get update && apt-get install -y \
    build-essential \
    libssl-dev \
    python3-dev \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*
```

### ffmpeg screen record command (verified device index)
```bash
# Source: ffmpeg avfoundation docs + verified device list on this machine
# Device 2 = "Capture screen 0", Device 1 (audio) = MacBook Pro Microphone
ffmpeg -f avfoundation -r 30 -i "2:1" \
  -vcodec libx264 -pix_fmt yuv420p \
  -preset ultrafast \
  demo_$(date +%Y%m%d_%H%M%S).mp4
```

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Docker | docker-compose local dev, DEMO-01 | ✗ | — | Cannot test locally; write Dockerfile + compose, deploy to Railway for validation |
| ffmpeg | DEMO-05 screen recording | ✓ | 4.3.1 | — |
| ngrok | INFRA-06 fallback public URL | ✗ | — | `brew install ngrok` (2 minutes) |
| websockets (py) | demo_check.py WS check | ✓ | 16.0 | — |
| httpx (py) | demo_check.py HTTP checks | ✓ | 0.28.1 | — |
| aerospike (py) | demo_check.py namespace check | ✓ | 19.1.0 | — |
| Python 3.12 | Backend runtime | ✓ | 3.12.13 (.venv312) | — |
| Node.js | Frontend build in Dockerfile | ✓ | 24.13.1 (local) | In Dockerfile: `apt-get install nodejs npm` |
| Railway CLI | Railway deployment | ✗ | — | Railway web UI drag-drop docker-compose (no CLI needed) |

**Missing dependencies with no fallback:**
- Docker: Cannot test docker-compose locally. Workaround: deploy to Railway (cloud Docker host) for integration testing. For demo day, Railway IS the running environment.

**Missing dependencies with fallback:**
- ngrok: `brew install ngrok` takes 2 minutes. Needed only if Railway deployment isn't ready before demo.
- Railway CLI: web UI is sufficient; CLI not required.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio |
| Config file | pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `python demo_check.py --host http://localhost:8000` |
| Full suite command | `.venv312/bin/pytest tests/ -x -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INFRA-06 | Public URL reachable; Bland webhook fires | smoke | `python demo_check.py --host $DEPLOYED_URL` | ❌ Wave 0 |
| DEMO-01 | docker-compose up starts full stack | manual | `docker compose up --wait && curl localhost:8000/health` | ❌ Wave 0 |
| DEMO-02 | demo_check.py all checks pass | smoke | `python demo_check.py` | ❌ Wave 0 |
| DEMO-04 | Full demo arc < 3 min, no intervention | manual-timed | `python dry_run.py` (timed) | ❌ Wave 0 |
| DEMO-05 | Screen recording exists as .mp4 | manual | `ls demo_*.mp4` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `python demo_check.py` (after server is running)
- **Per wave merge:** Full pytest suite + demo_check.py
- **Phase gate:** Two consecutive timed dry runs under 3 minutes before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `demo_check.py` — covers INFRA-06, DEMO-02 (all pre-demo checks in one script)
- [ ] `dry_run.py` — covers DEMO-04 (timed end-to-end arc automation)
- [ ] `Dockerfile` — covers DEMO-01 (container build for docker-compose)
- [ ] Updated `docker-compose.yml` — covers DEMO-01 (adds sentinel service to existing Aerospike-only compose)
- [ ] `reset_demo.py` — covers DEMO-04 support (state reset between dry run arcs)

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| EC2/ECS deployment (per ROADMAP) | Railway cloud PaaS (per user override) | 2026-03-26 (this phase) | No AWS config needed; deploy via Dockerfile + Railway web UI |
| docker-compose with only Aerospike | docker-compose with Aerospike + FastAPI | Phase 6 | DEMO-01 requires full stack in one command |
| No public URL (local dev only) | ngrok or Railway public URL | Phase 6 | Required for Bland AI webhook delivery |

**Deprecated/outdated:**
- ROADMAP reference to "AWS deployment": superseded by user override to Railway/Render/Fly.io. Railway is the recommended choice.
- INFRA-06 text "EC2/ECS": interpret as "public URL for Bland AI webhooks" — the platform doesn't matter, the public HTTPS URL does.

## Open Questions

1. **Aerospike data persistence on Railway**
   - What we know: Railway services have ephemeral storage by default; volume mounts require Railway's persistent volume feature ($0.15/GB/month)
   - What's unclear: Whether the demo needs Aerospike data to survive Railway restarts between demo dry runs
   - Recommendation: For the demo, persistent volume is not required — Aerospike starts fresh each deploy, which is fine (demo arc generates its own rules). If dry runs need state persistence between Railway deploys, add a Railway volume mount for `/opt/aerospike/data`.

2. **Railway internal DNS for Aerospike**
   - What we know: Railway uses `<service-name>.railway.internal` for private networking between services in a project
   - What's unclear: Exact service name assigned when importing from docker-compose
   - Recommendation: After importing docker-compose to Railway, read the generated service name from the Railway UI and set `AEROSPIKE_HOST` env var accordingly.

3. **Bland API key configuration for demo_check.py**
   - What we know: BLAND_API_KEY is not set in local .env (only ANTHROPIC_API_KEY is set)
   - What's unclear: Whether a Bland API key is available for the demo
   - Recommendation: Add BLAND_API_KEY to .env before running demo_check.py. The `/bland-call` route already returns 503 if the key is a placeholder — demo_check.py should surface this same check.

## Sources

### Primary (HIGH confidence)
- Existing codebase: `sentinel/api/main.py` — SPA static serving already implemented; confirmed frontend/dist exists
- Existing codebase: `sentinel/api/routes/bland_call.py` — PUBLIC_HOST injection pattern; phone number from env
- Existing codebase: `sentinel/config.py` — AEROSPIKE_HOST/PORT/NAMESPACE env var names
- Existing codebase: `docker-compose.yml` — current Aerospike-only compose; needs FastAPI service added
- Environment probe: `ffmpeg -f avfoundation -list_devices` — device index 2 = Capture screen 0, confirmed
- Environment probe: `python -c "import websockets"` — v16.0 available in venv
- Environment probe: `python -c "import httpx"` — v0.28.1 available in venv

### Secondary (MEDIUM confidence)
- [Railway FastAPI Guide](https://docs.railway.com/guides/fastapi) — Dockerfile deployment, WebSocket support confirmed
- [Railway Docker Compose Support](https://station.railway.com/questions/how-to-deploy-using-docker-compose-064a6c6d) — drag-drop docker-compose import confirmed
- [ngrok Homebrew](https://formulae.brew.sh/cask/ngrok) — `brew install ngrok` confirmed

### Tertiary (LOW confidence)
- Railway Aerospike internal DNS pattern `<service>.railway.internal` — inferred from Railway networking docs; verify after service creation

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all tools verified present or available via brew
- Architecture: HIGH — deployment pattern is standard Dockerfile + Railway; Aerospike host env var pattern is already in config.py
- Pitfalls: HIGH — Aerospike C-extension build failure is a well-known issue; docker network hostname is a standard compose gotcha
- demo_check.py patterns: HIGH — websockets + httpx already in venv, both tested

**Research date:** 2026-03-26
**Valid until:** 2026-03-27 (demo day — this is the final phase before presentation)
