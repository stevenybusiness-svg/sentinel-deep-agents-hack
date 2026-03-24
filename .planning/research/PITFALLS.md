# Pitfalls Research

**Domain:** Multi-agent AI supervision system — 72-hour solo hackathon build
**Researched:** 2026-03-24
**Confidence:** HIGH (Claude API, exec(), WebSocket) / MEDIUM (Bland AI, Aerospike) / HIGH (demo patterns)

---

## Critical Pitfalls

### Pitfall 1: Claude API Tier-1 ITPM Wall Kills the Parallel Investigation Demo

**What goes wrong:**
At Tier 1 (default for new API keys), Opus 4.x and Sonnet 4.x share a combined 30,000 input tokens per minute limit. A single Sentinel investigation triggers: 1 Supervisor call (Opus), 3 parallel sub-agent calls (Sonnet), and 1 rule-generation call (Opus). With realistic system prompts + verdict board context, each call costs 3,000–8,000 input tokens. Five calls in rapid sequence can consume 15,000–35,000 tokens in under 10 seconds. A second demo run within the same minute hits a 429 and the entire live demo freezes on stage.

**Why it happens:**
New API accounts start at Tier 1. Hackathon developers test each agent individually (stays under limits), then run the full pipeline for the first time on stage — the burst hits the burst enforcement (described as "1 request per second" smoothing at 60 RPM = token bucket drain). The retry-after can be 30–60 seconds.

**How to avoid:**
1. Confirm your API account tier before building. Advance to Tier 2 ($40 cumulative purchase, 450,000 ITPM) immediately — this is the only fix.
2. Cache the system prompt for all sub-agents using prompt caching (`cache_control: ephemeral`). Cached tokens do NOT count toward ITPM at Tier 2+. A 3,000-token cached system prompt across 3 parallel calls saves 9,000 ITPM.
3. Keep sub-agent (Sonnet) system prompts under 1,000 uncached tokens. The verdict board passed in is the variable part; keep it small.
4. Run two back-to-back full demo cycles in staging and monitor the `anthropic-ratelimit-input-tokens-remaining` response header. If it drops below 20% between cycles, you have a problem.

**Warning signs:**
- 429 error with `retry-after` header during pipeline integration testing
- Sub-agent calls succeed individually but fail when fired in parallel with `asyncio.gather()`
- Token counter in Claude Console shows spikes to near-limit during integration tests

**Phase to address:** Phase 1 (core investigation pipeline). Configure prompt caching and verify tier before any integration testing begins.

**Severity: DEMO-KILLER**

---

### Pitfall 2: exec() Rule Fails Silently — Gate Returns GO When It Should Block

**What goes wrong:**
The generated Python rule is `exec()`'d into a registry dict using a shared namespace. If the function definition fails to compile, or if it raises an unhandled exception at call time, and the gate catches exceptions broadly (bare `except: pass`), the rule is silently skipped. The gate outputs GO. On stage, Phase 2 fires, the generated rule is supposed to catch it, and nothing happens. Attribution panel stays blank. The critical demo moment fails.

**Why it happens:**
`exec()` has non-obvious scoping rules. A function defined inside `exec()` with `locals={}` as the namespace will land in that dict, but calling it from a different scope requires explicitly extracting it: `rule_fn = namespace['check_episode']`. Forgetting this means the function exists in the dict but the caller raises `NameError`. Developers wrap the whole gate in `try/except Exception` to keep it "safe" and accidentally suppress this error. The gate still runs but skips every generated rule.

**Additionally:** Generated functions that reference field names not present in the verdict board dict will raise `KeyError` at runtime. If the rule prompt produces code that uses `.get()` without defaults, or worse uses direct dict access `verdict['field']`, any verdict board missing that field causes the rule to error out and (if exceptions are swallowed) pass silently.

**How to avoid:**
1. Use an explicit namespace extraction pattern:
   ```python
   namespace = {}
   exec(rule_source, namespace)
   rule_fn = namespace['detect']  # Raises KeyError immediately if function not defined
   ```
2. Validate generated rules in a test harness before adding to registry. Run against 3 known-good and 3 known-bad verdict board fixtures. Assert the return value is a bool, not None.
3. In the gate, log every rule evaluation result (rule ID, verdict board key subset, return value, exception if any). Never swallow exceptions silently — wrap each rule call individually and record failures as RULE_ERROR in attribution.
4. The rule generation prompt must specify: function signature `def detect(verdict_board: dict) -> bool`, use only `.get()` with defaults, return bool not raise.
5. Run the rule generation prompt 30+ times in isolation (as PROJECT.md specifies) and check that every output: (a) compiles, (b) returns a bool for an empty dict without raising, (c) returns True for a spoofing-pattern verdict board.

**Warning signs:**
- `exec()` runs without error but `namespace` dict is empty afterward
- Gate returns GO on Phase 2 input even though rule was "registered"
- Attribution panel shows rule was loaded but never evaluated
- `type(result)` returns `NoneType` (function returns implicitly)

**Phase to address:** Phase 2 (self-improvement loop / rule generation). This is the most failure-prone single component. Do not wire into the full pipeline until the exec/registry harness passes 10 consecutive tests.

**Severity: DEMO-KILLER**

---

### Pitfall 3: Rule Generalization Fails — Phase 2 Attack Not Caught

**What goes wrong:**
Rule #001 is generated from the invoice hidden text attack (Phase 1). Phase 2 uses agent identity spoofing. The rule prompt produces code that checks for document forensics findings or specific invoice fields — mechanistic, not behavioral. It never fires on the identity spoofing verdict board because that board has no document scan data. The critical generalization claim ("learned to detect when an agent is lying, not hidden text") fails in front of judges.

**Why it happens:**
LLM-generated code has a strong pull toward the concrete examples it was given. Without explicit constraint in the prompt, Opus will write a rule that checks for the forensic anomaly mechanism (hidden text in image) rather than the behavioral signature (agent claims mismatch independent verification). The verdict board fields for Phase 1 and Phase 2 look different at the leaf level, but share a top-level pattern: high agent confidence + field mismatches from independent investigators.

**How to avoid:**
1. The rule generation prompt is the single most important artifact in the entire system. It must:
   - Explicitly state: "Write a rule that detects the BEHAVIORAL pattern, not the mechanism. The rule must NOT reference `forensics_findings`, `document_scan`, or any attack-specific field."
   - Provide the full verdict board schema with field names and types
   - Include a negative example: a legitimate high-confidence transaction that should return False
   - Include a Phase 2-style verdict board as a labeled positive example ("this should also match")
   - Constrain available fields to: `agent_confidence`, `field_mismatches`, `investigator_agreement_count`, `claims_verified_count`, `claims_total`
2. Test the generated rule against Phase 2 fixtures before the demo loop is considered working. This is a go/no-go gate.
3. If generalization fails in testing, add a section to the prompt: "CRITICAL: this rule will be tested against verdict boards from different attack types. A rule that checks for invoice or document fields will be rejected."

**Warning signs:**
- Generated rule source code contains the string "forensics" or "document" or "invoice"
- Rule passes Phase 1 fixture, fails Phase 2 fixture
- Rule only checks one or two fields instead of the composite confidence/mismatch pattern

**Phase to address:** Phase 2 (self-improvement loop). Test the rule generation prompt in complete isolation before integrating with anything else.

**Severity: DEMO-KILLER**

---

### Pitfall 4: Bland AI Webhook Timeout Stalls the Demo Mid-Investigation

**What goes wrong:**
The voice interface is wired to answer operator questions. During Phase 3 ("Why did you block that?"), the Bland AI call is initiated, the webhook fires back to the FastAPI server to fetch context, but the server is processing a parallel Claude call and the webhook response takes >3 seconds. Bland AI treats this as a webhook failure. The voice agent either speaks garbage, goes silent, or drops the call. In front of Bland AI judges.

**Why it happens:**
Bland AI webhooks retry on 429 and 5xx responses but not on slow responses. Webhook nodes execute synchronously in the call flow. If the webhook handler at `/bland/context` blocks on a live Claude call or Aerospike query that takes >2s, the call stalls. Bland AI has ~800ms average latency on their TTS side, and combined with a slow webhook, the total silence exceeds what sounds natural.

**How to avoid:**
1. Pre-compute all voice context before Phase 3 starts. After the gate fires and the verdict is final, write a `voice_context` record to Aerospike. The webhook handler reads from Aerospike (<5ms) — never from a live Claude call.
2. Make the webhook handler return in under 200ms. Measure it. Add a timeout assertion in tests.
3. Set up the Bland AI call before the demo to test the full webhook loop. Do not assume it works because the API call succeeds — test the full roundtrip including webhook.
4. Fallback plan: if voice fails, the dashboard shows the investigation tree, verdict board, and attribution text. Narrate those visually. Do not waste demo time debugging live voice.

**Warning signs:**
- Webhook response logs show >500ms latency during testing
- Bland AI call logs show retries or failures in the test environment
- Voice agent pauses awkwardly between question and answer

**Phase to address:** Phase 4 (voice interface). Do not add voice until the core investigation loop (Phases 1-3) is complete and bulletproof.

**Severity: DEMO-KILLER (for Bland AI judges) / recoverable with narration fallback**

---

### Pitfall 5: Aerospike Docker Namespace/Set Mismatch Causes Silent Write Loss

**What goes wrong:**
Writes succeed (no exception), but reads return nothing. The dashboard shows "no episodes found" even though the system has processed two full demo scenarios. This is because Aerospike requires the namespace to match the server configuration. The default Docker image uses `test` namespace; code hardcodes `sentinel` or `episodic_memory`. Writes to a non-existent namespace in memory-only mode don't error — they succeed and are dropped.

**Why it happens:**
Aerospike separates namespace configuration (server-side `aerospike.conf`) from client-side namespace references. The client does not validate that a namespace exists before writing. In the Community Edition Docker image, only the `test` namespace is configured by default. Writing to `sentinel` namespace succeeds at the API level but the data never lands.

**Additionally:** The Python client connection pool silently retries on timeout. If Aerospike goes down during a demo and comes back, the client may reconnect without the application noticing — but the first few writes after reconnect drop due to the reconnection window.

**How to avoid:**
1. In Docker setup, either use the `test` namespace (quickest) or mount a custom `aerospike.conf` that declares the `sentinel` namespace. Test the namespace exists with a read-after-write check in the startup health check.
2. Write a startup validation function: write a test record, read it back, assert values match. If this fails, crash loudly. Never let the application start with a broken Aerospike connection.
3. Keep set names and bin names consistent across write and read paths. Aerospike silently ignores unknown bins on write if configured incorrectly.
4. For the demo, use a single Aerospike namespace and log the write latency for each episode record to the dashboard (required by demo spec — 3 Aerospike judges need to see this).

**Warning signs:**
- `client.get(key)` returns `(key, None, None)` tuple after a successful `client.put()`
- No exception thrown but data not visible in AMC (Aerospike Management Console) or `aql`
- Dashboard shows 0 episodes after full pipeline run

**Phase to address:** Phase 1 (episodic memory integration). Set up and validate Aerospike as the first infrastructure task, not the last.

**Severity: DEMO-KILLER (for Aerospike judges)**

---

### Pitfall 6: WebSocket Event Race Condition Makes the Dashboard Lie

**What goes wrong:**
The animated investigation tree shows nodes lighting up in the wrong order, or the verdict board populates before the sub-agent results arrive, or the generated rule panel flashes and then disappears. Judges see a broken, stuttering UI exactly when the demo is at its most important moment.

**Why it happens:**
The FastAPI backend fires WebSocket events as async tasks complete. With `asyncio.gather()` for parallel sub-agents, all three results arrive in rapid succession — often within 50ms of each other. The React frontend receives three state updates in the same JavaScript event loop tick. Without batching or sequencing logic, React re-renders three times in 50ms, each render partially overwriting the previous state. If state is held in separate `useState` hooks, the closure captures stale state and some updates are lost.

**Additionally:** WebSocket reconnection is not automatic in the browser. If the connection drops during the demo (network glitch, server restart) the dashboard freezes on the last state. No error is shown.

**How to avoid:**
1. Use a single state object (Zustand store or useReducer) for the entire dashboard. Never use multiple `useState` hooks for correlated state — they batch poorly under rapid updates.
2. On the backend, sequence events deliberately: emit `AGENT_STARTED` before the call, `AGENT_COMPLETE` after. Do not emit compound state snapshots — emit minimal events and let the frontend build state.
3. Add event sequence numbers to every WebSocket message. The frontend queues out-of-order events and replays in order. This prevents flicker from events arriving in wrong order.
4. Implement automatic WebSocket reconnection in the frontend: exponential backoff with a `reconnecting...` indicator. The demo must survive a dropped connection.
5. Throttle dashboard updates to a minimum 100ms interval per node — fast enough to feel live, slow enough for React to keep up and for judges to see the animation.

**Warning signs:**
- Console shows `Warning: Can't perform a React state update on an unmounted component`
- Dashboard nodes appear and disappear
- Sub-agent results show as "undefined" or blank before filling in
- Dashboard state is correct in DevTools but wrong on screen (stale closure)

**Phase to address:** Phase 3 (dashboard). Build the WebSocket event schema before building any frontend — the event structure is the contract.

**Severity: HIGH (damages demo credibility even if pipeline is correct)**

---

### Pitfall 7: Opus 4.6 Latency Makes the Demo Feel Broken

**What goes wrong:**
The 3-minute demo arc requires Phase 1 to complete in ~75 seconds. Opus 4.6 (Supervisor) generates the investigation tree and synthesizes the verdict. If the Supervisor call takes 15–25 seconds and the three sub-agent Sonnet calls take 8–12 seconds each (but run in parallel), total wall time is ~30–40 seconds before the gate even fires. Add rule generation (another Opus call, 10–20 seconds) and Phase 1 takes 50–60 seconds alone. Silence on stage while the API thinks.

**Why it happens:**
Opus is 2-3x slower than Sonnet in output throughput. For an investigation that produces a detailed verdict board and reasoning, Opus output can be 800–1500 tokens. At ~50 tokens/second for Opus, that's 15–30 seconds per call. Developers test with short prompts during development, then add rich context in the final system and discover the latency problem the night before the demo.

**How to avoid:**
1. Constrain Opus output explicitly. The Supervisor does NOT need to produce prose — it produces a structured verdict board (JSON). Set `max_tokens` to 1024 for the Supervisor synthesis call. Use tool use / structured output mode to avoid the model generating explanatory text before the JSON.
2. Move sub-agent output to Sonnet, not Haiku (Haiku is fast but misses nuance; Sonnet is the sweet spot). Keep sub-agent prompts under 500 output tokens.
3. For rule generation, Opus can take longer (it runs after the gate has already fired, while the dashboard shows the result). Users see the gate decision immediately; the rule appears a few seconds later. This is fine — design the UX to show "Generating rule..." while Opus works.
4. Stream Supervisor output to the dashboard. Even if the full response takes 20 seconds, showing tokens streaming in real time feels alive.
5. Measure end-to-end latency with realistic context sizes in the first integration test. Set a hard budget: Phase 1 must complete in under 60 seconds total.

**Warning signs:**
- Integration test with realistic prompts takes >45 seconds for Phase 1
- `max_tokens` is not set (model generates until it decides to stop)
- Supervisor prompt asks for a narrative explanation rather than structured output

**Phase to address:** Phase 1 (core investigation pipeline). Latency budget must be established before any UI work begins.

**Severity: HIGH (demo pacing breaks; judges disengage)**

---

### Pitfall 8: Live Demo Environment Diverges From Development

**What goes wrong:**
The demo runs fine on the development machine. On the demo machine or EC2 instance (AWS judges expect deployed infrastructure), environment variables are missing, Aerospike is pointing to localhost instead of the Docker container, the Bland AI webhook URL is still `localhost:8000`, or the CORS configuration blocks the React frontend. The first full run on stage is also the first run in the demo environment.

**Why it happens:**
Hackathon velocity means config is hardcoded or in `.env` files that aren't committed. Demo setup is the last task, done when already exhausted. Network differences (hotel WiFi NAT, EC2 security groups) affect Bland AI webhook delivery to local machines.

**How to avoid:**
1. Write a `demo_check.py` script that runs before every demo: verifies Aerospike connection, Claude API key valid, Bland AI API key valid, WebSocket endpoint reachable, read-after-write to Aerospike passes, Phase 1 scenario runs end-to-end in under 90 seconds. Run this at T-1 hour and T-15 minutes before the demo.
2. Use `docker-compose` to bring up the entire stack (FastAPI + Aerospike + React) with a single command. No manual steps.
3. For Bland AI webhooks: if deploying on EC2, ensure the webhook URL is the public EC2 address with port open in security group. Test webhook delivery from Bland AI's servers (not localhost) before the demo.
4. Keep a "demo script" that is the actual sequence of curl commands / button clicks to run Phase 1 → Phase 2. Do a full end-to-end dry run at least twice before going on stage.
5. Fallback: screen-record a successful local demo run. If everything fails on stage, play the recording while narrating live.

**Warning signs:**
- First full end-to-end test happens the night before (too late to fix systemic issues)
- `.env` file contains demo-specific values that differ from development
- No pre-demo validation script exists

**Phase to address:** Phase 5 (demo preparation / deployment). Must exist as an explicit phase — not "left to the end."

**Severity: DEMO-KILLER**

---

## Moderate Pitfalls

### Pitfall 9: Structured Output Breaks on Schema Complexity

**What goes wrong:**
The verdict board schema has nested objects (mismatches per field, per agent). Claude's structured output (with `strict: true`) compiles the schema to a grammar but can fail when schemas are deeply nested or contain `oneOf`/`anyOf` constructs. The call returns a 400 error. Without structured output, Claude sometimes wraps JSON in markdown fences or adds preamble text, breaking the parser.

**Prevention:**
Use structured output in beta (`structured-outputs-2025-11-13` header) for Sonnet sub-agents. Keep the verdict board schema flat: avoid nested objects deeper than 2 levels. If structured output fails, fall back to tool use with `strict: true` on the tool definition — this is more mature and battle-tested than the newer structured outputs API. Test both paths.

**Phase to address:** Phase 1.
**Severity: HIGH if not caught early; moderate if tool-use fallback is ready**

---

### Pitfall 10: Okta Token Introspection Adds 200–500ms Per Override

**What goes wrong:**
Okta token introspection is a synchronous HTTP call to the Okta `/introspect` endpoint. If this call is in the critical demo path for the Phase 3 override, and Okta's servers respond slowly, the voice agent pause before confirming identity feels broken.

**Prevention:**
Cache the introspection result for 30 seconds (sufficient for demo). The override happens once; stale cache risk is zero. Do not put Okta on the hot path of the investigation pipeline — only the override command triggers it.

**Phase to address:** Phase 4 (Okta integration).
**Severity: ANNOYING**

---

### Pitfall 11: React Canvas Animation Blocks the Main Thread

**What goes wrong:**
The investigation tree uses HTML5 Canvas animation. If the animation loop runs on the main thread and processes a complex graph update (multiple nodes lighting up simultaneously), React re-renders stall because the canvas requestAnimationFrame handler takes >16ms. The UI freezes for 200–400ms at the worst possible moment (sub-agents completing).

**Prevention:**
Keep canvas animation logic simple. Do not compute graph layout during animation — pre-compute all node positions when the investigation starts. Use CSS transitions for node state changes (color, opacity) instead of canvas redraws. Only use canvas for the connecting lines/edges. Offload to `requestIdleCallback` for non-critical redraws.

**Phase to address:** Phase 3 (dashboard).
**Severity: MODERATE**

---

### Pitfall 12: Aerospike Python Client Version Mismatch on macOS

**What goes wrong:**
`pip install aerospike` on macOS installs against the system Python. The C extension requires a compatible version of the Aerospike C client library. On Apple Silicon (M1/M2/M3 Macs), older aerospike-python versions fail to compile or install without Homebrew deps. The error message is cryptic.

**Prevention:**
Use Python 3.10–3.12 in a virtual environment. Use `pip install aerospike` only after confirming `python --version` is the venv Python. On Apple Silicon, you may need `ARCHFLAGS="-arch arm64"` set before install. Better: use the Aerospike Docker image for the server and test client connectivity with a minimal script before writing any application code.

**Phase to address:** Phase 1 (infrastructure setup — Day 1, first 2 hours).
**Severity: HIGH time cost if hit late; 30-min fix if caught immediately**

---

## Minor Pitfalls

### Pitfall 13: Generated Rule Source Stored as String, Not Validated on Load

**What goes wrong:**
Rule source is written to Aerospike as a string. On restart, rules are loaded and `exec()`'d at startup. A rule with a syntax error (e.g., caused by truncated output from a previous run) crashes the Safety Gate at startup.

**Prevention:**
After generating a rule, immediately `compile()` it (raises `SyntaxError` before exec). Store only rules that pass compile. On load, compile again before exec. Never exec stored code without re-compiling first.

**Phase to address:** Phase 2.
**Severity: ANNOYING (recoverable by clearing registry)**

---

### Pitfall 14: WebSocket Broadcast Blocks on Disconnected Client

**What goes wrong:**
A browser tab that disconnected without sending a `WebSocketDisconnect` event keeps its entry in the `ConnectionManager` list. The broadcast loop tries to send to it, raises an exception, and if not caught individually, aborts the entire broadcast — no other clients get the update.

**Prevention:**
Wrap each individual `websocket.send_json()` call in try/except. On failure, remove that connection from the list. Use a copy of the connection list for iteration (`list(self.connections)`) to avoid mutation during iteration.

**Phase to address:** Phase 3.
**Severity: MINOR (only matters if judges open multiple tabs)**

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Hardcoded demo scenarios (no dynamic attack input) | Eliminates input validation for Phase 1/2 | Cannot show flexibility; judges ask "what if I try X?" | Acceptable for Phase 1/2 demo; have answer ready |
| In-memory rule registry (not persisted) | Faster to build | Rules lost on server restart; demo fails if server restarts | Never for demo — persist to Aerospike, required anyway |
| Single WebSocket connection per client (no auth) | Simpler code | Anyone who opens the URL sees the demo | Acceptable for 72-hour hackathon |
| `exec()` without process isolation | No Docker-in-Docker complexity | Generated code can access server filesystem | Acceptable for demo; judges know it's a demo; call it out explicitly as a known limitation |
| Blocking Aerospike reads in FastAPI endpoint | Simpler than async | Blocks event loop during demo; creates latency | Never — use `asyncio.run_in_executor()` for Aerospike calls |
| No retry logic on Claude API calls | Faster to build | 429 on demo day is unrecoverable | Never — add exponential backoff, minimum 3 retries |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Claude API (Opus 4.x) | Firing Supervisor + 3 sub-agents + rule gen all at Tier 1 | Advance to Tier 2 before building; cache system prompts; verify ITPM headroom |
| Claude API structured output | Using `output_format` mode with complex nested schema | Use tool use with `strict: true`; flat schema; test against known inputs |
| Aerospike Python client | Writing to namespace that doesn't exist in server config | Startup read-after-write check; match namespace to `aerospike.conf` |
| Aerospike Python client | Blocking I/O in async FastAPI route | Use `loop.run_in_executor(None, client.put, key, bins)` |
| Bland AI webhooks | Webhook URL is `localhost` (not reachable from Bland servers) | Use ngrok in dev; EC2 public URL in demo; test webhook delivery explicitly |
| Bland AI barge-in | Assuming barge-in works without testing interrupt threshold | Test interruption threshold setting; log interrupt events; voice context must be pre-loaded |
| FastAPI WebSocket | Broadcast to disconnected clients raises exception and aborts loop | Individual try/except per send; iterate over copy of connection list |
| Python `exec()` | Function defined in exec namespace not accessible in caller scope | Explicitly extract: `fn = namespace['detect']`; validate return type |
| React + rapid WebSocket | Multiple `useState` hooks with rapid updates lose state | Single Zustand store or `useReducer`; event sequence numbers |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Sequential Claude calls (Supervisor waits for sub-agents one by one) | Phase 1 takes 60+ seconds | `asyncio.gather()` for all three sub-agent calls | Immediately — parallel is a core architectural claim |
| Aerospike reads in WebSocket hot path | Dashboard update latency >100ms | Pre-compute context; read from Aerospike once, cache in memory | Under any non-trivial update rate |
| Opus 4.6 with unbounded `max_tokens` | Supervisor call takes 30+ seconds | Set `max_tokens=1024`; use structured output to suppress prose | Every call |
| Rule exec without compile step | Syntax errors discovered at call time, not load time | `compile()` before `exec()`; fail fast at registration | When Opus truncates output |
| Canvas layout computed per frame | UI freezes during agent completions | Pre-compute all positions at investigation start | With >5 nodes in tree |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| `exec()` without namespace isolation | Generated rule accesses `os`, `subprocess`, filesystem | Always pass explicit `globals={'__builtins__': {}}` dict; allowlist builtins needed (dict, list, len, etc.) |
| Storing raw Claude API key in frontend | Key exposed in browser network tab | API key only in backend `.env`; frontend talks to own FastAPI, not Claude directly |
| No validation of exec'd function signature | Malformed generated function causes SafetyGate crash | Compile → exec → validate return type → run against test fixture before registering |
| Okta token passed to frontend | Token can be replayed | Introspect server-side only; return verified identity claim (name, role), never the token itself |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Trust score collapse happens off-screen | Judges miss the most visual moment | Trust score animation must be visible without scrolling; place it above the fold |
| Attribution text "Generated Rule #001" appears before rule source panel loads | Claim without evidence looks broken | Load rule source first, then show attribution |
| Dashboard shows "Investigating..." with no indication of which sub-agents are running | Feels frozen; judges may think it crashed | Each sub-agent node shows "Active" state as soon as its call fires, before result arrives |
| Generated rule Python displayed as plain text | Hard to read quickly on stage | Syntax highlight the rule source panel (Prism.js); font size 14px minimum |

---

## "Looks Done But Isn't" Checklist

- [ ] **Rule generation:** Runs successfully in isolation — verify it also works when called with the full verdict board from the actual pipeline (fields may differ from test fixtures)
- [ ] **Phase 2 generalization:** Rule #001 fires on Phase 2 verdict board — verify explicitly, not assumed; failure here is the demo's core claim
- [ ] **Aerospike latency on dashboard:** Latency number is visible and real — verify it reads actual write timing, not a hardcoded value
- [ ] **Bland AI barge-in:** Tested with actual interruption (not just successful completion) — mid-sentence override must work
- [ ] **WebSocket reconnection:** Dashboard recovers if server restarts — verify by actually restarting FastAPI during a running dashboard
- [ ] **Rate limit headroom:** Two consecutive Phase 1 → Phase 2 cycles run without 429 — test back-to-back, not spaced out
- [ ] **Demo script:** Written down, rehearsed twice, all button clicks and voice commands scripted — not improvised
- [ ] **Fallback plan:** Screen recording of successful local demo ready to play if live demo fails

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| 429 rate limit on stage | HIGH — 30+ second freeze | Wait for retry-after; narrate what the system is doing; advance to Tier 2 in advance to prevent |
| exec() rule silent failure | HIGH — core demo claim fails | Debug live is impossible; prevention is the only strategy; have a pre-loaded mock rule as fallback |
| Aerospike connection lost | MEDIUM | docker-compose restart recovers in ~5s; keep terminal window visible; restart takes <10s |
| Bland AI voice fails | LOW — with text fallback | Dashboard shows all text output; narrate verbally; pre-warn audience "voice is a bonus integration" |
| WebSocket disconnects | LOW | Browser page refresh reconnects; dashboard state should be reconstructable from Aerospike |
| Opus latency too high | MEDIUM | Show streaming tokens on dashboard while waiting; reframe as "watching the AI think in real time" |
| Demo machine environment issue | HIGH | docker-compose should eliminate this; fallback is screen recording |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| API tier / rate limits | Phase 1 (Day 1) | Two consecutive pipeline runs succeed; ITPM headers logged |
| exec() silent failure | Phase 2 (rule registry) | 10 consecutive rule generations pass test harness |
| Rule generalization failure | Phase 2 (prompt testing) | Phase 2 fixture returns True from generated rule; Phase 1 fixture also True |
| Bland AI webhook timeout | Phase 4 (voice) | Full webhook roundtrip measured; voice context pre-loaded to Aerospike |
| Aerospike namespace mismatch | Phase 1 (infra setup) | Startup health check: write + read + assert; confirmed before any app code written |
| WebSocket race conditions | Phase 3 (dashboard) | Event sequence numbers; React DevTools show no dropped updates |
| Opus latency | Phase 1 (latency budget) | End-to-end Phase 1 completes in <60s with realistic context |
| Demo environment divergence | Phase 5 (demo prep) | `demo_check.py` passes in demo environment T-1 hour before show |
| Structured output schema complexity | Phase 1 (pipeline) | Tool-use fallback path tested before structured output path |
| Canvas main thread blocking | Phase 3 (dashboard) | Profiler shows no frames >16ms during node lighting |

---

## Sources

- [Claude API Rate Limits — Official Documentation](https://platform.claude.com/docs/en/api/rate-limits)
- [Claude API Structured Outputs — Official Documentation](https://platform.claude.com/docs/en/build-with-claude/structured-outputs)
- [Claude API Reducing Latency — Official Documentation](https://platform.claude.com/docs/en/test-and-evaluate/strengthen-guardrails/reduce-latency)
- [Bland AI Review: Latency and Reliability Issues — Retell AI](https://www.retellai.com/blog/bland-ai-reviews)
- [Bland AI Changelog May 2025 — Webhook Retry Behavior](https://docs.bland.ai/changelog/05_12_2025)
- [Aerospike Python Client — Official Documentation](https://aerospike-python-client.readthedocs.io/en/latest/client.html)
- [Aerospike Docker Image — Docker Hub](https://hub.docker.com/r/aerospike/aerospike-server)
- [Aerospike Writing Many Keys — Slow Performance Community Forum](https://discuss.aerospike.com/t/aerospike-learning-writing-many-keys-slow-performance/7932)
- [Python exec() — Real Python Guide](https://realpython.com/python-exec/)
- [Running Untrusted Python Code — Andrew Healey](https://healeycodes.com/running-untrusted-python-code)
- [SandboxedPython — Python Wiki](https://wiki.python.org/moin/SandboxedPython)
- [LLM Code Generation Failure Modes — arXiv 2411.01414](https://arxiv.org/pdf/2411.01414)
- [LLM Engineering Failure Modes 2025 — Medium](https://medium.com/@gbalagangadhar/llm-engineering-in-2025-the-failure-modes-that-actually-matter-and-how-i-fix-them-ad1f6f1da77e)
- [FastAPI WebSocket Multiple Clients — Medium](https://hexshift.medium.com/managing-multiple-websocket-clients-in-fastapi-ce5b134568a2)
- [React WebSocket State Management — Zustand/Jotai recommendation — moldstud.com](https://moldstud.com/articles/p-real-time-state-management-in-react-using-websockets-boost-your-apps-performance)
- [How to Give a Killer Hackathon Demo — GitHub Gist](https://gist.github.com/dabit3/caef5eee4753dd7d23767bc31e70da28)
- [Top 5 Mistakes Developers Make at Hackathons — Medium](https://medium.com/@BizthonOfficial/top-5-mistakes-developers-make-at-hackathons-and-how-to-avoid-them-d7e870746da1)

---

*Pitfalls research for: Multi-agent AI supervision system (Sentinel) — 72-hour solo hackathon*
*Researched: 2026-03-24*
