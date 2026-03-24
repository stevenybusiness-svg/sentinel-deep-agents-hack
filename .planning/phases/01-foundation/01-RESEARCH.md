# Phase 1: Foundation - Research

**Researched:** 2026-03-24
**Domain:** Project scaffolding, schema definition, infrastructure validation, demo fixtures
**Confidence:** HIGH

## Summary

Phase 1 is a greenfield scaffolding phase: initialize the Python backend package, React frontend, Docker-based Aerospike, freeze Pydantic schemas, validate the Claude API client with prompt caching, and commit demo fixture files. All decisions are locked via CONTEXT.md with narrow discretion areas. The primary technical risks are (1) Docker is not installed on the development machine -- required for Aerospike, (2) the default `python3` is 3.9 but `python3.12` is available and should be used explicitly, and (3) RestrictedPython 8.2 (cited in CLAUDE.md) does not exist on PyPI -- 8.1 is latest.

**Primary recommendation:** Install Docker Desktop immediately (blocks Aerospike), use `python3.12` explicitly for the venv, pin RestrictedPython to 8.1 (latest available), and use Tailwind CSS v3 (CDN-based per the design guide, not v4).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Invoice fixtures = two PNG files: `sentinel/fixtures/invoice_clean.png` (white text on white background -- hidden to human eye) and `sentinel/fixtures/invoice_forensic.png` (same document with hidden text highlighted in red -- shown in forensic scan panel side-by-side on dashboard)
- **D-02:** Data fixtures = JSON files loaded at startup into in-memory dicts via fixture loader: `sentinel/fixtures/kyc_ledger.json` (Meridian Logistics intentionally absent -- exposes Phase 2 spoofed pre-clearance), `sentinel/fixtures/counterparty_db.json` (authorization records for legitimate counterparties), `sentinel/fixtures/behavioral_baselines.json` (mean/std confidence values for Risk Agent z-score: mean=0.52, std=0.11)
- **D-03:** Fixture loader is a single `load_fixtures()` function in `sentinel/fixtures/__init__.py` that returns a typed dict; called once at startup and passed to agents as dependency
- **D-04:** Python package is `sentinel/` at repo root -- imports read `from sentinel.schemas import Verdict`; React app is `frontend/` at repo root; `.env`, `docker-compose.yml`, `demo_check.py` live at repo root
- **D-05:** Internal layout of `sentinel/`: `schemas/`, `agents/`, `fixtures/`, `api/`, `memory/` (Aerospike client), `gate/` (Safety Gate)
- **D-06:** Strict Pydantic validators on Safety Gate fields only -- `severity: Literal["critical", "warning", "info"]`, `confidence: float = Field(ge=0.0, le=1.0)`, `match: bool`, gate decision `Literal["GO", "NO-GO", "ESCALATE"]` -- these are deterministic enforcement paths; incorrect values here corrupt the verdict board silently
- **D-07:** All other schema fields (step descriptions, claims text, agent reasoning, metadata) are loosely typed (`str`, `list`, `dict`) -- tighten in Phase 2 if a sub-agent returns bad data

### Claude's Discretion
- Exact Aerospike namespace TTL values (episodes, rules, trust sets)
- Pydantic base class structure (whether to use a shared `SentinelBase` model)
- React scaffolding tooling (Vite vs CRA -- Vite preferred per ecosystem, but either works)
- Docker Compose service ordering and health check retry config

### Deferred Ideas (OUT OF SCOPE)
- Airbyte sync for counterparty DB / KYC ledger (DATA-01, DATA-02) -- v2 requirement; Phase 1 commits JSON fixtures as the data source; Airbyte replaces the loader later if time permits
- SQLite or Postgres for fixture data -- not needed; JSON + in-memory dict is sufficient for the demo and avoids an extra dependency
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INFRA-01 | Python 3.11+ project initialized with FastAPI, AsyncAnthropic, Aerospike Python client (19.1.0), RestrictedPython | Python 3.12 available on machine; all packages verified on PyPI; RestrictedPython 8.1 is latest (not 8.2) |
| INFRA-02 | Aerospike running via Docker with startup health check (read-after-write validates namespace) | Docker NOT installed -- must install first; Aerospike Community Edition image supports arm64; namespace configured via env var or custom config |
| INFRA-03 | Claude API Tier 2 access confirmed; prompt caching enabled for all agent system prompts | Anthropic SDK 0.86.0 confirmed; cache_control: {"type": "ephemeral"} on system message blocks; verify via response.usage.cache_creation_input_tokens |
| INFRA-04 | React 18+ frontend initialized with @xyflow/react (12.4.x), Zustand, Tailwind CSS | React 18.3.1, @xyflow/react 12.4.4, Zustand 5.0.12 all available; Tailwind CDN v3 per design guide |
| INFRA-05 | Environment configuration via .env (ANTHROPIC_API_KEY, AEROSPIKE_HOST, etc.) | python-dotenv 1.0.x; .env at repo root per D-04 |
| SCHEMA-01 | Verdict schema frozen -- agent_id, claims_checked[], behavioral_flags[], agent_confidence, confidence_z_score, unable_to_verify | Pydantic v2 (2.12.5 latest); strict validators on Safety Gate fields per D-06 |
| SCHEMA-02 | Verdict Board schema frozen -- mismatches[], behavioral_flags[], agent_confidence, confidence_z_score, step_sequence_deviation, hardcoded_rule_fired, unable_to_verify[] | Same Pydantic approach; loosely typed non-gate fields per D-07 |
| SCHEMA-03 | Episode schema frozen -- id, timestamp, action_request, agent_verdicts, verdict_board, gate_decision, gate_rationale, rules_fired, generated_rules_fired, operator_confirmation, attack_type, generated_rule_source, new_rules_deployed | Nested Pydantic models; gate_decision uses Literal["GO", "NO-GO", "ESCALATE"] |
| SCHEMA-04 | WebSocket event taxonomy defined -- 9 named events | Pydantic discriminated unions or simple type field; FastAPI native WebSocket |
| DEMO-03 | Demo fixtures committed: Phase 1 (invoice images, counterparty DB, behavioral baselines), Phase 2 (spoofed KYC, empty KYC for Meridian) | JSON files + PNG images per D-01 and D-02; fixture loader per D-03 |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- **Safety Gate invariant:** Deterministic Python exec() for generated rules -- no LLM in enforcement decision path
- **No LangChain/LlamaIndex:** Direct anthropic SDK calls with explicit prompts
- **No asyncio.gather():** Use asyncio.TaskGroup (Python 3.11+) for parallel dispatch
- **No reactflow (old package):** Use @xyflow/react
- **No Pydantic v1:** FastAPI requires Pydantic v2
- **No Socket.io:** Native browser WebSocket + FastAPI WebSocket
- **Aerospike sync client + run_in_executor:** Not aioaerospike (archived)
- **Single uvicorn worker:** `--workers 1` keeps WebSocket state in-process
- **AsyncAnthropic instantiated once at module level:** Not per-request
- **Model assignment:** Opus 4.6 for Supervisor, Sonnet 4.6 for sub-agents

## Standard Stack

### Core (verified against PyPI/npm registries 2026-03-24)

| Library | Pin Version | Latest Available | Purpose | Why Standard |
|---------|-------------|------------------|---------|--------------|
| Python | 3.12.13 | 3.13.12 | Runtime | 3.12 preferred over 3.13 for broader C-extension compatibility (Aerospike); TaskGroup available since 3.11 |
| FastAPI | 0.115.14 | 0.135.2 | HTTP + WS server | CLAUDE.md pins 0.115.x; use latest 0.115.x for stability |
| anthropic | 0.86.0 | 0.86.0 | Claude API client | Exact version match -- latest IS 0.86.0 |
| aerospike | 19.1.0 | 19.1.0 | Persistent storage | Exact version match -- released March 6 2026; pre-built arm64 wheels available |
| pydantic | 2.12.x | 2.12.5 | Schema validation | FastAPI requires v2; latest stable |
| RestrictedPython | 8.1 | 8.1 | Safety Gate sandbox | CLAUDE.md says 8.2 but 8.2 does NOT exist on PyPI; 8.1 is latest; docs site shows "8.2" as dev version |
| React | 18.3.1 | 19.2.4 | Frontend UI | CLAUDE.md specifies React 18; 19 has breaking changes |
| @xyflow/react | 12.4.4 | 12.10.1 | Pipeline node graph | Pin to 12.4.4 per CLAUDE.md; 12.10.1 available but untested |
| zustand | 5.0.x | 5.0.12 | Frontend state | Lightweight, works with React 18 |
| tailwindcss | 3.x (CDN) | 4.2.2 | Styling | Design guide uses Tailwind CDN v3 config syntax; do NOT use v4 |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| uvicorn | 0.34.x | ASGI server | Dev server with --reload; single worker |
| python-dotenv | 1.0.x | Env loading | Load .env at startup |
| aiohttp | 3.x | HTTP backend | `pip install anthropic[aiohttp]` for better connection pooling |
| pytest-asyncio | latest | Async tests | Testing async routes and agent coroutines |
| httpx | latest | Test client | FastAPI TestClient; transitive dep of anthropic |
| vite | 6.x | Frontend bundler | Scaffold React app; `npm create vite@latest` |

### Version Corrections from CLAUDE.md

| CLAUDE.md States | Actual | Action |
|------------------|--------|--------|
| RestrictedPython 8.2 | 8.1 is latest on PyPI | Pin to 8.1; functionally equivalent |
| FastAPI 0.115.x | 0.115.14 is latest 0.115.x | Use 0.115.14 |
| @xyflow/react 12.4.4 | 12.4.4 exists, 12.10.1 is latest | Pin 12.4.4 as specified |

**Installation:**

```bash
# Create venv with Python 3.12
python3.12 -m venv .venv
source .venv/bin/activate

# Core backend
pip install "fastapi==0.115.14" "uvicorn[standard]>=0.34,<0.35" "anthropic[aiohttp]==0.86.0" "aerospike==19.1.0" "RestrictedPython==8.1" "pydantic>=2.12,<3" "python-dotenv>=1.0,<2"

# Dev
pip install pytest pytest-asyncio httpx

# Frontend
npm create vite@latest frontend -- --template react
cd frontend
npm install @xyflow/react@12.4.4 zustand@latest
# Tailwind: use CDN in index.html per design guide (NOT npm install)
```

## Architecture Patterns

### Recommended Project Structure (per D-04 and D-05)

```
sentinel-project/
├── sentinel/                    # Python package
│   ├── __init__.py
│   ├── schemas/                 # Pydantic models (SCHEMA-01..04)
│   │   ├── __init__.py
│   │   ├── verdict.py           # Verdict, ClaimCheck
│   │   ├── verdict_board.py     # VerdictBoard
│   │   ├── episode.py           # Episode
│   │   └── events.py            # WebSocket event taxonomy
│   ├── agents/                  # Sub-agent dispatch (Phase 2)
│   │   └── __init__.py
│   ├── fixtures/                # Demo data + loader
│   │   ├── __init__.py          # load_fixtures() function
│   │   ├── invoice_clean.png
│   │   ├── invoice_forensic.png
│   │   ├── kyc_ledger.json
│   │   ├── counterparty_db.json
│   │   └── behavioral_baselines.json
│   ├── api/                     # FastAPI routes (Phase 2)
│   │   └── __init__.py
│   ├── memory/                  # Aerospike client wrapper
│   │   └── __init__.py
│   └── gate/                    # Safety Gate (Phase 2)
│       └── __init__.py
├── frontend/                    # React app (Vite)
│   ├── src/
│   │   ├── App.jsx
│   │   └── ...
│   ├── index.html               # Tailwind CDN script tag here
│   ├── package.json
│   └── vite.config.js
├── tests/                       # pytest tests
│   ├── __init__.py
│   ├── test_schemas.py
│   ├── test_fixtures.py
│   └── test_aerospike.py
├── .env                         # Secrets (gitignored)
├── .env.example                 # Template (committed)
├── docker-compose.yml           # Aerospike + optional services
├── demo_check.py                # Pre-demo validation script
├── pyproject.toml               # Python project config
└── requirements.txt             # Pinned deps
```

### Pattern 1: Pydantic Schema with Strict Safety Gate Fields

**What:** Mix strict validators on gate-critical fields with loose typing elsewhere
**When to use:** All schema definitions in this phase

```python
# Source: Pydantic v2 docs + D-06/D-07 decisions
from pydantic import BaseModel, Field
from typing import Literal, Optional
from datetime import datetime

class ClaimCheck(BaseModel):
    field: str
    agent_claimed: str
    independently_found: str
    match: bool  # Strict -- gate reads this
    severity: Literal["critical", "warning", "info"]  # Strict -- gate reads this

class Verdict(BaseModel):
    agent_id: str
    claims_checked: list[ClaimCheck]
    behavioral_flags: list[str]  # Loose -- tighten in Phase 2
    agent_confidence: float = Field(ge=0.0, le=1.0)  # Strict
    confidence_z_score: float | None = None
    unable_to_verify: bool = False
```

### Pattern 2: Aerospike Sync Client with run_in_executor

**What:** Official sync client called from async FastAPI via ThreadPoolExecutor
**When to use:** All Aerospike operations

```python
# Source: CLAUDE.md component guidance + Aerospike Python docs
import aerospike
from concurrent.futures import ThreadPoolExecutor
import asyncio

# Module-level: configure once
config = {"hosts": [("localhost", 3000)]}
aero_client = aerospike.client(config).connect()
executor = ThreadPoolExecutor(max_workers=4)

async def aero_put(namespace: str, set_name: str, key: str, bins: dict):
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(
        executor,
        lambda: aero_client.put((namespace, set_name, key), bins)
    )

async def aero_get(namespace: str, set_name: str, key: str) -> dict:
    loop = asyncio.get_running_loop()
    _, _, bins = await loop.run_in_executor(
        executor,
        lambda: aero_client.get((namespace, set_name, key))
    )
    return bins
```

### Pattern 3: AsyncAnthropic with Prompt Caching

**What:** Single shared client, cache_control on system prompts
**When to use:** Claude API client initialization

```python
# Source: Anthropic SDK docs + prompt caching docs
from anthropic import AsyncAnthropic

# Module-level: instantiate once
client = AsyncAnthropic()  # Reads ANTHROPIC_API_KEY from env

async def test_api_connection():
    """Verify API access and prompt caching."""
    response = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=100,
        timeout=30.0,
        system=[
            {
                "type": "text",
                "text": "You are a test assistant. Respond with 'OK'.",
                "cache_control": {"type": "ephemeral"}
            }
        ],
        messages=[{"role": "user", "content": "Ping"}],
    )
    # Verify cache headers
    cache_write = response.usage.cache_creation_input_tokens
    # First call: cache_write > 0 means caching is active
    return {
        "status": "ok",
        "cache_creation_tokens": cache_write,
        "cache_read_tokens": response.usage.cache_read_input_tokens,
    }
```

### Pattern 4: Fixture Loader (per D-03)

**What:** Single function returning typed dict, called once at startup
**When to use:** Application startup

```python
# sentinel/fixtures/__init__.py
import json
from pathlib import Path
from typing import TypedDict

FIXTURES_DIR = Path(__file__).parent

class FixtureData(TypedDict):
    kyc_ledger: dict          # company_name -> KYC record
    counterparty_db: dict     # counterparty_id -> authorization record
    behavioral_baselines: dict  # agent_type -> {mean, std}

def load_fixtures() -> FixtureData:
    """Load all demo fixtures from JSON files. Called once at startup."""
    def _load(name: str) -> dict:
        with open(FIXTURES_DIR / name) as f:
            return json.load(f)

    return FixtureData(
        kyc_ledger=_load("kyc_ledger.json"),
        counterparty_db=_load("counterparty_db.json"),
        behavioral_baselines=_load("behavioral_baselines.json"),
    )
```

### Anti-Patterns to Avoid

- **Creating Aerospike client per-request:** Instantiate once at module level; connect once; reuse
- **Using asyncio.gather for agent dispatch:** Use TaskGroup (structured concurrency, auto-cancel on exception)
- **Importing reactflow (old package):** Use @xyflow/react
- **Installing Tailwind v4 via npm:** Design guide uses CDN v3 config syntax; v4 has different config API
- **Mixing Pydantic v1 and v2 syntax:** model_validator replaces root_validator; field_validator replaces validator

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Schema validation | Custom dict validation | Pydantic v2 BaseModel | Handles coercion, error messages, JSON serialization |
| Aerospike health check | Custom TCP probe | aerospike.client().connect() + put/get round trip | Tests actual data path, not just connectivity |
| Environment loading | os.getenv() everywhere | python-dotenv + .env file | Centralized, documented, .env.example as template |
| React project setup | Manual webpack config | Vite scaffold | `npm create vite@latest` gives working React setup in 30 seconds |
| WebSocket event types | String constants | Pydantic model with Literal type field | Type safety, auto-serialization, IDE support |

## Common Pitfalls

### Pitfall 1: Docker Not Installed

**What goes wrong:** Aerospike requires Docker; `docker` command not found on this machine.
**Why it happens:** Development machine does not have Docker Desktop installed.
**How to avoid:** Install Docker Desktop for macOS before any Aerospike work. Verify with `docker info`.
**Warning signs:** `docker: command not found` when running docker-compose.

### Pitfall 2: Python 3.9 Default

**What goes wrong:** `python3` resolves to 3.9.1 which lacks TaskGroup (requires 3.11+) and may have Aerospike wheel issues.
**Why it happens:** Default system Python is outdated; Python 3.12 and 3.13 are installed but not the default.
**How to avoid:** Always use `python3.12` explicitly. Create venv with `python3.12 -m venv .venv`.
**Warning signs:** ImportError on `asyncio.TaskGroup`, Aerospike compilation failures.

### Pitfall 3: Aerospike C-Extension on Apple Silicon

**What goes wrong:** Aerospike Python client is a C-extension; compilation may fail without proper architecture flags.
**Why it happens:** Apple Silicon (arm64) needs specific build flags if no pre-built wheel matches.
**How to avoid:** Pre-built arm64 wheels exist for 19.1.0 + Python 3.12. Use `pip install aerospike==19.1.0` (not `--no-binary`). If wheel install fails, set `ARCHFLAGS="-arch arm64"`.
**Warning signs:** `error: ... architecture` during pip install.

### Pitfall 4: Tailwind v3 vs v4 Confusion

**What goes wrong:** FRONTEND-DESIGN-GUIDE.md uses Tailwind CDN v3 config syntax (`tailwind.config = {}`). Tailwind v4 (current latest: 4.2.2) has a completely different config API.
**Why it happens:** npm defaults to latest (v4); design guide expects v3 CDN.
**How to avoid:** Use `<script src="https://cdn.tailwindcss.com">` in index.html. Do NOT `npm install tailwindcss`.
**Warning signs:** `tailwind.config` object has no effect; custom colors don't work.

### Pitfall 5: RestrictedPython Version Mismatch

**What goes wrong:** CLAUDE.md specifies RestrictedPython 8.2 but PyPI only has 8.1 as latest.
**Why it happens:** 8.2 appears in ReadTheDocs (development docs) but is not yet released.
**How to avoid:** Pin to `RestrictedPython==8.1`. Functionally equivalent for compile_restricted usage.
**Warning signs:** `pip install RestrictedPython==8.2` fails with "no matching distribution."

### Pitfall 6: Aerospike Namespace Must Exist Before App Starts

**What goes wrong:** Aerospike Community Edition requires namespaces to be defined in config file at server start; they cannot be created dynamically.
**Why it happens:** Unlike key-value stores that auto-create collections, Aerospike namespaces are pre-configured.
**How to avoid:** Mount a custom `aerospike.conf` via Docker volume that defines the `sentinel` namespace. The health check must verify the namespace exists via read-after-write.
**Warning signs:** `AEROSPIKE_ERR_NAMESPACE_NOT_FOUND` errors.

### Pitfall 7: Prompt Caching Minimum Token Requirement

**What goes wrong:** Cache_control is set but caching never activates; cache_creation_input_tokens is always 0.
**Why it happens:** Anthropic requires minimum 1024 tokens for Sonnet models, 2048 for Haiku models in the cached content block.
**How to avoid:** System prompts for agents must exceed the minimum token threshold. For a validation test, use a sufficiently long system prompt or accept that short test prompts won't cache.
**Warning signs:** `cache_creation_input_tokens: 0` on every request.

## Code Examples

### Aerospike Docker Compose with Custom Namespace

```yaml
# docker-compose.yml
# Source: Aerospike Docker Hub + community docs
version: "3.8"
services:
  aerospike:
    image: aerospike/aerospike-server:latest
    ports:
      - "3000:3000"   # Client connections
      - "3001:3001"   # Fabric (inter-node)
      - "3002:3002"   # Mesh heartbeat
      - "3003:3003"   # Info
    volumes:
      - ./aerospike.conf:/opt/aerospike/etc/aerospike.conf
      - aerospike-data:/opt/aerospike/data
    command: ["--config-file", "/opt/aerospike/etc/aerospike.conf"]
    healthcheck:
      test: ["CMD", "asinfo", "-v", "status"]
      interval: 5s
      timeout: 3s
      retries: 10

volumes:
  aerospike-data:
```

### Aerospike Configuration File

```conf
# aerospike.conf
service {
    proto-fd-max 1024
}

logging {
    console {
        context any info
    }
}

network {
    service {
        address any
        port 3000
    }
    heartbeat {
        mode mesh
        port 3002
        interval 150
        timeout 10
    }
    fabric {
        port 3001
    }
    info {
        port 3003
    }
}

namespace sentinel {
    replication-factor 1
    memory-size 256M
    default-ttl 0
    storage-engine device {
        file /opt/aerospike/data/sentinel.dat
        filesize 1G
    }
}
```

### WebSocket Event Taxonomy (SCHEMA-04)

```python
# sentinel/schemas/events.py
from pydantic import BaseModel
from typing import Literal, Any
from datetime import datetime

EventType = Literal[
    "investigation_started",
    "agent_completed",        # sent 3x (risk, compliance, forensics)
    "verdict_board_assembled",
    "gate_evaluated",
    "episode_written",
    "rule_generated",
    "rule_deployed",
]

class WSEvent(BaseModel):
    event: EventType
    timestamp: datetime
    episode_id: str
    data: dict[str, Any]  # Loose -- payload varies by event type
```

### .env.example

```bash
# .env.example -- copy to .env and fill in values
ANTHROPIC_API_KEY=sk-ant-...
AEROSPIKE_HOST=localhost
AEROSPIKE_PORT=3000
AEROSPIKE_NAMESPACE=sentinel
BLAND_API_KEY=
OKTA_DOMAIN=
OKTA_CLIENT_ID=
```

### React Frontend Scaffolding with Tailwind CDN

```html
<!-- frontend/index.html (key additions to Vite template) -->
<head>
  <!-- Tailwind CDN v3 per design guide -->
  <script src="https://cdn.tailwindcss.com?plugins=forms,container-queries"></script>
  <script>
    tailwind.config = {
      darkMode: "class",
      theme: {
        extend: {
          colors: {
            "primary":      "#57abff",
            "success":      "#3fb950",
            "danger":       "#f85149",
            "warning":      "#e3b341",
            "bg-dark":      "#0d1117",
            "surface":      "#161b22",
            "border-muted": "#30363d",
            "text-main":    "#c9d1d9",
            "text-muted":   "#8b949e",
          },
          fontFamily: {
            "display": ["Inter", "sans-serif"],
            "mono":    ["Roboto Mono", "SFMono-Regular", "Menlo", "monospace"],
          },
        },
      },
    }
  </script>
  <!-- Fonts per design guide -->
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Roboto+Mono:wght@400;500&display=swap" />
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@24,400,0,0" />
</head>
```

## Discretion Recommendations

### Aerospike Namespace TTL Values

**Recommendation:** Use `default-ttl 0` (no expiry) for all sets. This is a demo -- data should persist across restarts for reproducibility. Individual sets (`episodes`, `rules`, `trust`) are within the same `sentinel` namespace and differentiated by set name, not separate namespaces.

**Confidence:** HIGH -- Aerospike sets within a namespace share TTL config; per-record TTL can override if needed later.

### Pydantic Base Class

**Recommendation:** Use a minimal `SentinelBase` model:

```python
from pydantic import BaseModel, ConfigDict

class SentinelBase(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={"examples": []},
    )
```

This provides a single place to add shared config (e.g., JSON serialization settings) without over-engineering. All schema classes inherit from it.

**Confidence:** MEDIUM -- minor convenience; no strong technical reason for or against.

### React Scaffolding Tooling

**Recommendation:** Use Vite. `npm create vite@latest frontend -- --template react` gives a working scaffold in seconds. Vite is the ecosystem standard (CRA is deprecated). Current Vite version is 6.x (verified: 8.0.2 on npm -- actually this is Vite 6.x lineage; check with `npm create vite@latest`).

**Confidence:** HIGH -- Vite is universally recommended over CRA.

### Docker Compose Health Check

**Recommendation:** Use `asinfo -v status` as the Docker healthcheck command, with 5s interval and 10 retries. Application-level health check should be a Python read-after-write test that runs at startup before accepting traffic.

**Confidence:** HIGH -- standard Aerospike health check pattern.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| CRA (create-react-app) | Vite | CRA deprecated 2023 | Use Vite for React scaffolding |
| Pydantic v1 validators | Pydantic v2 field_validator/model_validator | Pydantic 2.0, June 2023 | Different decorator syntax; v1 code won't work |
| asyncio.gather() | asyncio.TaskGroup | Python 3.11 | Structured concurrency with auto-cancel |
| Tailwind v3 (config object) | Tailwind v4 (CSS-first config) | Jan 2025 | Design guide uses v3 syntax; stay on v3 CDN |
| reactflow package | @xyflow/react | 2024 rebrand | Old package name still works but misses v12 features |

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12 | INFRA-01 (TaskGroup, Aerospike) | Yes | 3.12.13 | python3.13 also available |
| Node.js | INFRA-04 (React frontend) | Yes | 24.13.1 | -- |
| npm | INFRA-04 (package management) | Yes | 11.8.0 | -- |
| Docker | INFRA-02 (Aerospike) | **NO** | -- | **BLOCKING -- must install Docker Desktop** |
| pip (Python 3.12) | INFRA-01 (package install) | Yes | 26.0 | -- |

**Missing dependencies with no fallback:**
- **Docker** -- Required for Aerospike. Must install Docker Desktop for macOS before any INFRA-02 work. Download from https://www.docker.com/products/docker-desktop/

**Missing dependencies with fallback:**
- None

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio (latest) |
| Config file | none -- Wave 0 creates pyproject.toml [tool.pytest.ini_options] |
| Quick run command | `python3.12 -m pytest tests/ -x -q` |
| Full suite command | `python3.12 -m pytest tests/ -v` |

### Phase Requirements to Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INFRA-01 | All Python deps importable | smoke | `python3.12 -c "import fastapi, anthropic, aerospike, RestrictedPython, pydantic"` | No -- Wave 0 |
| INFRA-02 | Aerospike read-after-write succeeds | integration | `python3.12 -m pytest tests/test_aerospike.py -x` | No -- Wave 0 |
| INFRA-03 | Claude API responds without 429; cache headers present | integration | `python3.12 -m pytest tests/test_claude_api.py -x` | No -- Wave 0 |
| INFRA-04 | React app builds without errors | smoke | `cd frontend && npm run build` | No -- Wave 0 |
| INFRA-05 | .env loads all required keys | unit | `python3.12 -m pytest tests/test_config.py -x` | No -- Wave 0 |
| SCHEMA-01 | Verdict model validates correctly | unit | `python3.12 -m pytest tests/test_schemas.py::test_verdict -x` | No -- Wave 0 |
| SCHEMA-02 | VerdictBoard model validates correctly | unit | `python3.12 -m pytest tests/test_schemas.py::test_verdict_board -x` | No -- Wave 0 |
| SCHEMA-03 | Episode model validates correctly | unit | `python3.12 -m pytest tests/test_schemas.py::test_episode -x` | No -- Wave 0 |
| SCHEMA-04 | WSEvent model validates all 9 event types | unit | `python3.12 -m pytest tests/test_schemas.py::test_ws_events -x` | No -- Wave 0 |
| DEMO-03 | Fixture loader returns all expected data | unit | `python3.12 -m pytest tests/test_fixtures.py -x` | No -- Wave 0 |

### Sampling Rate

- **Per task commit:** `python3.12 -m pytest tests/ -x -q`
- **Per wave merge:** `python3.12 -m pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `pyproject.toml` -- project config with [tool.pytest.ini_options] asyncio_mode = "auto"
- [ ] `tests/__init__.py` -- test package init
- [ ] `tests/test_schemas.py` -- covers SCHEMA-01, SCHEMA-02, SCHEMA-03, SCHEMA-04
- [ ] `tests/test_fixtures.py` -- covers DEMO-03
- [ ] `tests/test_aerospike.py` -- covers INFRA-02 (requires Docker)
- [ ] `tests/test_claude_api.py` -- covers INFRA-03 (requires API key)
- [ ] `tests/test_config.py` -- covers INFRA-05
- [ ] Framework install: `pip install pytest pytest-asyncio`

## Open Questions

1. **Docker Desktop Installation**
   - What we know: Docker is not installed; Aerospike requires it
   - What's unclear: Whether the user has Docker Desktop license / can install it
   - Recommendation: First task in the plan must be "install Docker Desktop" or flag as blocker

2. **Invoice PNG Creation**
   - What we know: D-01 requires two PNG files with specific characteristics (hidden white-on-white text, red-highlighted forensic version)
   - What's unclear: How to create these programmatically vs. manually
   - Recommendation: Create with Python (PIL/Pillow) -- generate a fake invoice PNG with white text overlay, then a second version with red highlights. Simple enough for fixtures.

3. **Aerospike Namespace TTL Granularity**
   - What we know: Single `sentinel` namespace with sets `episodes`, `rules`, `trust`
   - What's unclear: Whether different sets need different TTLs
   - Recommendation: Use default-ttl 0 (no expiry) at namespace level; override per-record if needed in Phase 2+

## Sources

### Primary (HIGH confidence)
- [PyPI: aerospike](https://pypi.org/project/aerospike/) -- version 19.1.0 confirmed, arm64 wheels available
- [PyPI: anthropic](https://pypi.org/project/anthropic/) -- version 0.86.0 confirmed as latest
- [PyPI: RestrictedPython](https://pypi.org/project/RestrictedPython/) -- version 8.1 is latest (NOT 8.2)
- [PyPI: FastAPI](https://pypi.org/project/fastapi/) -- 0.115.14 is latest 0.115.x
- [Anthropic prompt caching docs](https://platform.claude.com/docs/en/build-with-claude/prompt-caching) -- cache_control pattern, min token requirements, usage fields
- [React Flow installation docs](https://reactflow.dev/learn/getting-started/installation-and-requirements) -- @xyflow/react 12.4.4 setup
- [Aerospike Docker Hub](https://hub.docker.com/_/aerospike) -- Community Edition image, namespace env config
- [Aerospike Python Client release notes](https://discuss.aerospike.com/t/aerospike-python-client-release-19-1-0-march-6-2026/12741) -- 19.1.0 release March 2026
- npm registry -- all frontend package versions verified via `npm view`
- Local environment -- Python/Node versions verified via CLI

### Secondary (MEDIUM confidence)
- [Aerospike Docker server repo](https://github.com/aerospike/aerospike-server.docker) -- namespace config via custom conf file
- [arm64v8/aerospike Docker image](https://hub.docker.com/r/arm64v8/aerospike/) -- native ARM64 image exists

### Tertiary (LOW confidence)
- RestrictedPython 8.2 documentation site (https://restrictedpython.readthedocs.io/) -- shows "8.2" but this version is not released on PyPI; likely dev docs

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all versions verified against live registries
- Architecture: HIGH -- project structure and patterns locked by CONTEXT.md decisions
- Pitfalls: HIGH -- environment tested directly; Docker absence confirmed; version discrepancies found and documented
- Fixtures: HIGH -- requirements and decisions are detailed and unambiguous

**Research date:** 2026-03-24
**Valid until:** 2026-04-07 (14 days -- fast-moving hackathon; package versions stable)
