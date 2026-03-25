# Phase 3: Self-Improvement Loop - Context

**Gathered:** 2026-03-25
**Status:** Ready for planning

<domain>
## Phase Boundary

After an operator confirms a Phase 1 attack: extract prediction errors from the confirmed episode → Opus 4.6 generates a behavioral Python scoring function → validate it (4 checks) → deploy to Safety Gate (disk + Aerospike) → scoring function fires on the Phase 2 identity-spoofing VerdictBoard (proof of behavioral generalization) → after Phase 2 attack confirmed, scoring function evolves using prediction errors from both incidents → evolved rule stored as v2.

</domain>

<decisions>
## Implementation Decisions

### Confirm API Design
- **D-01:** `POST /confirm` accepts `{ episode_id: str, attack_type: str }` — `attack_type` drives rule generation prompt framing (e.g., `"prompt_injection"`, `"identity_spoofing"`)
- **D-02:** `POST /confirm` returns `202 Accepted` immediately; rule generation streams token-by-token to the dashboard via WebSocket. Judges watch Python code appear in real time. WebSocket event type: `rule_generating` with streaming content, followed by `rule_deployed` on success or `rule_generation_failed` on all-retry failure.

### Generated Rule Persistence
- **D-03:** On validation pass, write the generated rule as a `.py` file to `sentinel/gate/rules/` (e.g., `rule_generated_001.py`) AND store in Aerospike `sentinel.rules` set. Filesystem is the execution path (picked up immediately by `SafetyGate.load_rules_from_directory()`); Aerospike is the source of truth for provenance.
- **D-04:** Aerospike `sentinel.rules` record bins: `rule_id` (str, e.g. `"rule_001"`), `source` (str, full Python function source), `episode_ids` (JSON list of episode IDs that contributed to this rule), `prediction_errors` (JSON — prediction error dict from source episode), `timestamp` (int ms), `version` (int, starts at 1). Rule key = `rule_id`.

### Rule Validation Harness
- **D-05:** 4 validation checks in order:
  1. RestrictedPython `compile_restricted()` parses and compiles without error
  2. Static string scan: reject source containing `import`, `__`, `open`, `exec`, `eval`
  3. `score(attack_fixture_verdict_board) > 0.6` — fires on the confirmed attack's VerdictBoard
  4. `score(clean_baseline_verdict_board) < 0.2` — does not fire on a clean baseline fixture
  All 4 must pass for deployment.
- **D-06:** On validation failure, inject the specific failure reason back into the Opus 4.6 generation prompt and retry. Up to 3 attempts total. If all 3 fail, emit `rule_generation_failed` WebSocket event with the error details and surface to operator. Do NOT deploy a rule that fails validation.
- **D-07:** Clean baseline fixture = a hard-coded `CLEAN_BASELINE_VERDICT_BOARD` dict in the validation harness (e.g., confidence=0.55, z_score=0.8, no behavioral_flags, no mismatches, no unable_to_verify). Claude's discretion on exact values — must represent a normal, un-suspicious transaction.

### Rule Evolution
- **D-08:** Evolution triggers automatically — when `POST /confirm` is called and an existing generated rule (`generated_rules_fired` in the episode) already fired on this episode, the system automatically spawns evolution. No extra operator endpoint or action needed. Clean demo flow.
- **D-09:** Evolution prompt includes: Rule v1 source + both episodes' VerdictBoards + both episodes' prediction error sets. Prompt instructs Opus 4.6 to: drop conditions that appear in only one incident (artifacts of a single attack), strengthen conditions present in both (behavioral invariants). Output: a refined `score(verdict_board: dict) -> float` function.
- **D-10:** Evolved rule (v2) overwrites the existing `.py` file on disk AND writes a new Aerospike record with `version=2`, `episode_ids=[ep1_id, ep2_id]`, combined prediction errors. v1 is not preserved as a separate firing rule — v2 replaces it. Dashboard shows evolution history via Aerospike version field.

### Claude's Discretion
- Exact Opus 4.6 system prompt and user prompt structure for rule generation — must constrain output to behavioral VerdictBoard fields, weighted float return, no attack-specific entity names
- Rule file naming convention (e.g., `rule_generated_001.py` vs `rule_auto_001.py`)
- `rule_id` assignment scheme (counter-based from Aerospike scan, or UUID prefix)
- Exact `CLEAN_BASELINE_VERDICT_BOARD` values for validation harness
- Aerospike `sentinel.rules` set name (consistent with existing `episodes`/`trust` naming)
- WebSocket event schema for `rule_generating` streaming tokens vs. `rule_deployed` complete event

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 2 foundations (READ FIRST)
- `.planning/phases/02-core-investigation-pipeline/02-CONTEXT.md` — Phase 2 decisions D-01 through D-21; all decisions still in force
- `sentinel/gate/rules/rule_z_score.py` — Example hardcoded rule; generated rules must use identical interface: `def score(verdict_board: dict) -> float`
- `sentinel/gate/rules/rule_hidden_text.py` — Another example; shows scoring weight conventions
- `sentinel/memory/episode_store.py` — `write_episode()`, `get_episode()`, prediction_report storage pattern
- `sentinel/memory/trust_store.py` — `store_prediction_history()` writes `prediction_{episode_id}` key; Phase 3 reads this

### Core schemas
- `sentinel/schemas/episode.py` — `Episode.generated_rule_source`, `Episode.new_rules_deployed`, `Episode.prediction_report` fields already exist
- `sentinel/schemas/verdict_board.py` — `VerdictBoard.prediction_errors`, `VerdictBoard.behavioral_flags`, `VerdictBoard.confidence_z_score` — these are the fields generated rules operate on

### Gate infrastructure
- `sentinel/engine/safety_gate.py` — `SafetyGate.load_rules_from_directory()`, `SafetyGate.register_rule()` — generated rules plug into these
- `sentinel/api/main.py` — `app_state["safety_gate"]` — how gate is loaded at startup; generated rules must be hot-loadable without restart

### Requirements
- `.planning/REQUIREMENTS.md` — LEARN-01 through LEARN-06 (self-improvement loop), MEM-02 (rule storage with provenance), MEM-05 (prediction history), API-03 (Aerospike latency endpoint)
- `.planning/ROADMAP.md` §Phase 3 — Success criteria: rule generation prompt consistency, validation harness thresholds, attribution string format

### Tech stack constraints
- `CLAUDE.md` §Safety Gate — `compile_restricted` from RestrictedPython; static string scan for prohibited constructs; exec() sandboxing pattern
- `CLAUDE.md` §Component-by-Component — Aerospike sync+ThreadPoolExecutor pattern; AsyncAnthropic streaming pattern

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `SafetyGate.load_rules_from_directory(rules_dir)` — already loads all `.py` files from `gate/rules/`; generated rule files plug straight in
- `SafetyGate.register_rule(source: str)` — already exists from Phase 2; used for runtime registration without filesystem write
- `trust_store.store_prediction_history(episode_id, prediction_errors, client)` — writes `prediction_{episode_id}` to Aerospike; Phase 3 reads this via `client.get("trust", f"prediction_{episode_id}")`
- `episode_store.get_episode(episode_id, client)` — returns full episode dict including `verdict_board` and `prediction_report`; Phase 3 uses this to extract prediction errors for rule generation
- `AerospikeClient.put()` / `AerospikeClient.get()` — async wrappers; Phase 3 writes to a new `sentinel.rules` set using same pattern
- `ws_manager` (WebSocket manager) — existing broadcast infrastructure; Phase 3 adds new event types for rule streaming

### Established Patterns
- Aerospike set pattern: `episodes` set uses string keys (episode UUIDs); `trust` set uses string keys (`behavioral_baselines`, `prediction_{episode_id}`); `rules` set should follow same pattern (`rule_001`, `rule_002`, etc.)
- Rule `.py` interface contract: `def score(verdict_board: dict) -> float` — all 8 hardcoded rules follow this; generated rules must match exactly
- WebSocket event flow: `ws_manager.broadcast(WSEvent(...))` is the pattern from Phase 2; Phase 3 adds `rule_generating` streaming events
- `Episode.generated_rule_source` (str | None) — field already exists; update to store the committed source after validation passes

### Integration Points
- `POST /confirm` → new route in `sentinel/api/routes/` → calls rule generation pipeline → updates episode record in Aerospike → writes `.py` file to `gate/rules/` → calls `gate.load_rules_from_directory()` to hot-reload
- `app_state["safety_gate"]` lives in memory; after new rule file is written, `gate.load_rules_from_directory()` must be called to pick it up for next transaction
- `active_episodes` cache in `app_state` — the confirmed episode's full dict (including `verdict_board` and `prediction_report`) is accessible here immediately after investigation completes; no Aerospike round-trip needed for rule generation
- Phase 2 `generated_rules_fired` field in Episode — populated by SafetyGate after scoring; Phase 3 reads this to detect when evolution should trigger

</code_context>

<specifics>
## Specific Ideas

- The WebSocket streaming of rule generation is the demo's most dramatic moment: judges watch Opus 4.6 write Python code in real time on the dashboard's rule panel. The streaming event type should carry the partial source text as tokens arrive.
- The attribution string for Attack 2 block should read: `"Blocked by Generated Rule #001 (from invoice attack, deployed Xs ago)"` — this is spelled out in ROADMAP success criteria and must be reproduced exactly.
- The validation harness `clean_baseline_verdict_board` should use values that represent a normal Acme Corp → TrustBank transaction: confidence ~0.55, z_score ~0.8, empty behavioral_flags, no mismatches.
- When evolution fires, the dashboard should show the rule panel update from v1 to v2 with a visual indicator (e.g., version badge changes from "v1" to "v2 (evolved)").

</specifics>

<deferred>
## Deferred Ideas

- Manual `/evolve/{rule_id}` endpoint — not needed; automatic evolution on second confirmed incident is sufficient for demo
- Preserving v1 as a separate firing rule alongside v2 — would double-count behavioral signals; v2 replaces v1
- Multiple generated rules per incident — v1 is a single composite function; one rule per incident confirmed for simplicity
- Rule deprecation / rollback endpoint — post-demo feature

</deferred>

---

*Phase: 03-self-improvement-loop*
*Context gathered: 2026-03-25*
