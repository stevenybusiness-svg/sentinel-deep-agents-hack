<!-- GSD:project-start source:PROJECT.md -->
## Project

**Sentinel**

Sentinel is a runtime multi-agent supervision system for autonomous payment agents. It investigates payment actions in real time using three parallel sub-agents (Risk, Compliance, Forensics), blocks irreversible transfers when agent behavior can't be independently verified, and generates executable Python detection rules from confirmed incidents — so the next attack it catches can be one it has never seen before. Built for the AWS Deep Agents Hackathon (72-hour solo build, deadline ~2026-03-27).

**Core Value:** The self-improvement loop: a rule learned from one attack type must demonstrably catch a completely different attack — live, on stage, in 3 minutes.

### Constraints

- **Timeline**: 72 hours, solo — build priority order from spec must be followed ruthlessly; voice + Okta + Airbyte are post-core
- **Tech Stack**: Python/FastAPI backend, React frontend, Claude API (Opus 4.6 for Supervisor, Sonnet 4.6 for sub-agents), Aerospike, Bland AI webhooks, HTML5 Canvas animation (per design guide)
- **Safety Gate**: Must use deterministic Python exec() for generated rules — no LLM in the enforcement decision path; this is an explicit architectural invariant and a judge talking point
- **Demo reliability**: The self-improvement loop (incident 1 → rule generation → incident 2 → rule fires) must be bulletproof before any polish work begins; fallback = text narration if voice fails
- **Aerospike**: Real persistent storage required — 3 Aerospike judges; latency must be visible on dashboard
- **Bland AI**: Real voice required — 2 Bland AI judges; fallback to text-on-dashboard only if SDK proves intractable in timeline
<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->
## Technology Stack

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
## Component-by-Component Guidance
### 1. Anthropic SDK — Parallel Sub-Agent Dispatch
- `AsyncAnthropic` is a single shared client — instantiate once at module level, not per-request
- TaskGroup (3.11+) cancels remaining tasks if one raises, preventing zombie agent calls
- Set explicit `timeout=` per call — the default 10-minute timeout will hang your demo if an agent stalls
- Supervisor uses `claude-opus-4-6`; Risk/Compliance/Forensics use `claude-sonnet-4-6` — specify model per call
- For `anthropic[aiohttp]`: use `DefaultAioHttpClient` as the http_client for better connection pooling under parallel load
- Streaming (`client.messages.stream`) is useful for Supervisor's reasoning — stream tokens to frontend via WebSocket for live "thinking" display
# Use streaming for rule generation — long output, judges watch it appear
### 2. Aerospike Python Client — Sub-5ms Write Patterns
# Module-level: configure once
# Thread pool for running sync Aerospike calls from async FastAPI context
### 3. Bland AI — FastAPI Integration
### 4. React Frontend — Real-Time WebSocket + Node Graph
### 5. Safety Gate — exec() Sandboxing
- RestrictedPython is NOT a full sandbox — a determined attacker could escape it via CPython internals
- For this demo, the threat model is: Opus 4.6 occasionally generates unexpected Python, not a hostile attacker
- The real security is: rules operate ONLY on `verdict_board` dict fields (no system calls, no file access, no network)
- Add a pre-execution static check: reject any rule source containing `import`, `__`, `open`, `exec`, `eval` as strings
- For a production system, use a subprocess sandbox with seccomp (Linux only) or a container — not needed for hackathon
### 6. Okta — Token Introspection
# FastAPI dependency for override endpoint
### 7. Airbyte — Google Sheets → Postgres Sync
- Use Airbyte Cloud (no self-hosting overhead)
- Configure Google Sheets source → Postgres destination via UI, not API — the UI is faster
- Set sync schedule to "manual" and trigger sync once before demo
- PyAirbyte (`pip install airbyte`) offers a Python-native alternative for simple pipelines
## Installation
# Core backend
# Security and identity
# Safety Gate
# Dev
# Optional: Airbyte
# Frontend
# No additional WS library needed — browser native WebSocket
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
## Version Compatibility
| Package | Compatible With | Notes |
|---------|-----------------|-------|
| anthropic 0.86.0 | Python 3.9+ | Use 3.11+ for TaskGroup |
| aerospike 19.1.0 | Python 3.9-3.13 | C-extension; requires build tools on some platforms; use pre-built wheels from PyPI |
| RestrictedPython 8.2 | Python 3.9-3.13 | Does NOT support PyPy; CPython only |
| okta-jwt-verifier 0.4.0 | Python 3.6+ | async support built-in |
| @xyflow/react 12.4.4 | React 17, 18; React 19 support via UI components update Oct 2025 | Use React 18 for stability |
| FastAPI 0.115.x | Pydantic v2 required | Pydantic v1 will cause runtime errors |
## Integration Gotchas for 72-Hour Solo Build
### P0 — Could kill the demo
### P1 — Will cost hours
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
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd:quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd:debug` for investigation and bug fixing
- `/gsd:execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd:profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
