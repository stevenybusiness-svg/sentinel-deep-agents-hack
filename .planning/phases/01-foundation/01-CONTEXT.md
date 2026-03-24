# Phase 1: Foundation - Context

**Gathered:** 2026-03-24 (discuss mode)
**Status:** Ready for planning

<domain>
## Phase Boundary

Frozen schemas, validated infrastructure, and committed demo fixtures — nothing downstream can fail due to missing schemas, wrong Aerospike namespace, or Claude API rate limits. Delivers: Python project initialized, Aerospike health-checked via Docker, Claude API tier confirmed with prompt caching, React frontend scaffolded, Pydantic schemas frozen, and both Phase 1 + Phase 2 demo fixture sets committed and loadable.

</domain>

<decisions>
## Implementation Decisions

### Demo Fixtures
- **D-01:** Invoice fixtures = two PNG files: `sentinel/fixtures/invoice_clean.png` (white text on white background — hidden to human eye) and `sentinel/fixtures/invoice_forensic.png` (same document with hidden text highlighted in red — shown in forensic scan panel side-by-side on dashboard)
- **D-02:** Data fixtures = JSON files loaded at startup into in-memory dicts via fixture loader: `sentinel/fixtures/kyc_ledger.json` (Meridian Logistics intentionally absent — exposes Phase 2 spoofed pre-clearance), `sentinel/fixtures/counterparty_db.json` (authorization records for legitimate counterparties), `sentinel/fixtures/behavioral_baselines.json` (mean/std confidence values for Risk Agent z-score: mean=0.52, std=0.11)
- **D-03:** Fixture loader is a single `load_fixtures()` function in `sentinel/fixtures/__init__.py` that returns a typed dict; called once at startup and passed to agents as dependency

### Project Structure
- **D-04:** Python package is `sentinel/` at repo root — imports read `from sentinel.schemas import Verdict`; React app is `frontend/` at repo root; `.env`, `docker-compose.yml`, `demo_check.py` live at repo root
- **D-05:** Internal layout of `sentinel/`: `schemas/`, `agents/`, `fixtures/`, `api/`, `memory/` (Aerospike client), `gate/` (Safety Gate)

### Schema Validation Strictness
- **D-06:** Strict Pydantic validators on Safety Gate fields only — `severity: Literal["critical", "warning", "info"]`, `confidence: float = Field(ge=0.0, le=1.0)`, `match: bool`, gate decision `Literal["GO", "NO-GO", "ESCALATE"]` — these are deterministic enforcement paths; incorrect values here corrupt the verdict board silently
- **D-07:** All other schema fields (step descriptions, claims text, agent reasoning, metadata) are loosely typed (`str`, `list`, `dict`) — tighten in Phase 2 if a sub-agent returns bad data

### Claude's Discretion
- Exact Aerospike namespace TTL values (episodes, rules, trust sets)
- Pydantic base class structure (whether to use a shared `SentinelBase` model)
- React scaffolding tooling (Vite vs CRA — Vite preferred per ecosystem, but either works)
- Docker Compose service ordering and health check retry config

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Schema specifications
- `REQUIREMENTS.md` §Schemas — SCHEMA-01 through SCHEMA-04: exact field lists for Verdict, VerdictBoard, Episode, and WebSocket event taxonomy
- `REQUIREMENTS.md` §Infrastructure — INFRA-01 through INFRA-05: dependency versions and configuration requirements

### Demo fixture requirements
- `REQUIREMENTS.md` §Demo Preparation — DEMO-03: full list of fixture assets required for Phase 1 and Phase 2

### Tech stack constraints
- `CLAUDE.md` §Technology Stack — pinned versions (aerospike 19.1.0, anthropic 0.86.0, @xyflow/react 12.4.4, RestrictedPython 8.2), integration gotchas, what NOT to use
- `CLAUDE.md` §Component-by-Component Guidance — Aerospike sync+executor pattern, AsyncAnthropic module-level client, Safety Gate exec() sandboxing

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- None — greenfield project, no existing code

### Established Patterns
- None yet — patterns established in this phase become the baseline for all subsequent phases

### Integration Points
- Fixture loader output feeds directly into Phase 2 sub-agents (Compliance Agent queries `kyc_ledger`, Risk Agent reads `behavioral_baselines`)
- Frozen schemas are the contract between all phases — any change to SCHEMA-01 through SCHEMA-04 after Phase 1 is a breaking change
- Aerospike namespace names (`sentinel.episodes`, `sentinel.trust`, `sentinel.rules`) established here must match Phase 2 write calls exactly

</code_context>

<specifics>
## Specific Ideas

- The forensic invoice panel needs both assets at fixture commit time: `invoice_clean.png` (what the human operator sees) and `invoice_forensic.png` (what the dashboard shows with red highlights). These are created together as a matched pair — same document, different rendering.
- The KYC ledger's intentional gap (Meridian Logistics absent) is the mechanism that exposes the Phase 2 identity spoofing attack. The ledger must be realistic enough to be credible but clearly missing the target entity.

</specifics>

<deferred>
## Deferred Ideas

- Airbyte sync for counterparty DB / KYC ledger (DATA-01, DATA-02) — v2 requirement; Phase 1 commits JSON fixtures as the data source; Airbyte replaces the loader later if time permits
- SQLite or Postgres for fixture data — not needed; JSON + in-memory dict is sufficient for the demo and avoids an extra dependency

</deferred>

---
*Phase: 01-foundation*
*Context gathered: 2026-03-24*
