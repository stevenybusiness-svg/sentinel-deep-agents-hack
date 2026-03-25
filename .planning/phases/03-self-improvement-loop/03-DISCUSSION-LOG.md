# Phase 3: Self-Improvement Loop - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-25
**Phase:** 03-self-improvement-loop
**Areas discussed:** Confirm API + rule generation UX, Generated rule persistence, Rule validation failure strategy, Evolution trigger + approach

---

## Confirm API + Rule Generation UX

| Option | Description | Selected |
|--------|-------------|----------|
| Stream via WebSocket | POST /confirm returns 202 immediately, rule generation streams token-by-token to dashboard via WebSocket. Judges watch Python code appear in real time. | ✓ |
| Sync response | POST /confirm blocks until rule is generated, validated, and deployed. Returns completed rule source in response body. | |
| Fire-and-forget + polling | POST /confirm returns 202, client polls GET /rule/{episode_id} until ready. | |

**User's choice:** Stream via WebSocket

| Body option | Description | Selected |
|-------------|-------------|----------|
| episode_id + attack_type | POST /confirm { episode_id, attack_type }. attack_type drives prompt framing. | ✓ |
| episode_id only | attack_type inferred from episode data. | |
| episode_id + attack_type + operator_notes | Allows freeform context injection into rule generation prompt. | |

**User's choice:** episode_id + attack_type

---

## Generated Rule Persistence

| Option | Description | Selected |
|--------|-------------|----------|
| Write .py file to disk + store in Aerospike | Rule written as .py file in gate/rules/ AND stored in Aerospike sentinel.rules set with provenance. Filesystem = execution path; Aerospike = source of truth for provenance. | ✓ |
| Aerospike only, reload at startup | Rule source stored only in Aerospike; fetched and re-registered at startup lifespan. No filesystem writes. | |

**User's choice:** Write .py file to disk + store in Aerospike

| Bins option | Description | Selected |
|-------------|-------------|----------|
| rule_id, source, episode_ids, prediction_errors, timestamp, version | Full provenance for dashboard display. | ✓ |
| rule_id, source, episode_id, timestamp | Minimal provenance — no prediction_errors or version. | |

**User's choice:** Full provenance bins (rule_id, source, episode_ids, prediction_errors, timestamp, version)

---

## Rule Validation Failure Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Retry up to 3x with error context injected | On failure, inject specific error back into Opus 4.6 prompt and retry. Up to 3 attempts. If all fail, emit rule_generation_failed WebSocket event. | ✓ |
| Retry up to 3x silently (same prompt) | Retry identical prompt 3x. May hit same failure. | |
| Fail immediately, surface to operator | One attempt only. Simplest code but breaks demo reliability. | |

**User's choice:** Retry up to 3x with error context injected

| Validation checks | Description | Selected |
|-------------------|-------------|----------|
| AST parse + compile_restricted + fires on attack fixture + clean on baseline | 4 checks: (1) compile_restricted, (2) static string scan, (3) score > 0.6 on attack, (4) score < 0.2 on clean. All 4 must pass. | ✓ |
| AST parse + compile_restricted + fires on attack fixture | 3 checks — skip clean baseline test. | |
| compile_restricted only | Minimal — just verify compilation. | |

**User's choice:** All 4 checks

---

## Evolution Trigger + Approach

| Option | Description | Selected |
|--------|-------------|----------|
| Automatic when ≥2 confirmed incidents share a generated rule | When /confirm detects generated_rules_fired in the episode, automatically spawn evolution. No extra operator action. | ✓ |
| Operator manually triggers via POST /evolve/{rule_id} | Separate endpoint for explicit evolution trigger. | |
| Always evolve when confirming a 2nd attack | Any second confirmed attack triggers evolution of all generated rules. | |

**User's choice:** Automatic when ≥2 confirmed incidents share a generated rule

| Evolution prompt | Description | Selected |
|-----------------|-------------|----------|
| Rule v1 source + both VerdictBoards + both prediction error sets | Provides current rule source + both episodes' data. Instructs: drop single-incident conditions, strengthen both-incident conditions. | ✓ |
| Both prediction error sets only (no Rule v1 source) | Fresh rule from both sets without building on v1. | |
| Both VerdictBoards only | Raw VerdictBoard data without structured prediction errors. | |

**User's choice:** Rule v1 source + both VerdictBoards + both prediction error sets

| v2 storage | Description | Selected |
|------------|-------------|----------|
| Replace Rule v1 .py file + new Aerospike record (version=2) | Overwrites .py file on disk AND writes new Aerospike record with version=2, both episode_ids. v2 replaces v1. | ✓ |
| New .py file (rule_001_v2.py) + new Aerospike record | Both v1 and v2 coexist in rules/ directory and both fire. May double-count. | |

**User's choice:** Replace Rule v1 .py file + new Aerospike record (version=2)

---

## Claude's Discretion

- Exact Opus 4.6 system/user prompt structure for rule generation
- Rule file naming convention
- `rule_id` assignment scheme
- `CLEAN_BASELINE_VERDICT_BOARD` exact values for validation harness
- Aerospike `sentinel.rules` set name
- WebSocket event schema for streaming tokens vs. `rule_deployed` event

## Deferred Ideas

- Manual `/evolve/{rule_id}` endpoint — not needed for demo
- Preserving v1 alongside v2 — scoring overlap risk
- Multiple generated rules per incident
- Rule deprecation / rollback endpoint
