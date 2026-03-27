"""
RuleGenerator — Phase 3 self-improvement loop core engine.

Generates composite scoring functions from confirmed incident prediction errors.
Uses Opus 4.6 to write inspectable Python that runs deterministically in the Safety Gate.

Key exports:
    RuleGenerator          — async generate() + evolve() with retry + streaming
    validate_rule()        — 4-check validation harness per D-05
    _exec_rule()           — compile + exec with RestrictedPython sandbox
    CLEAN_BASELINE_VERDICT_BOARD — realistic clean transaction baseline for check 4
    RULE_GEN_SYSTEM_PROMPT — system prompt constraining Opus to behavioral VerdictBoard fields
    build_rule_gen_prompt() — user prompt with incident VerdictBoard + prediction errors
    build_evolution_prompt() — user prompt for rule evolution across two incidents
"""
from __future__ import annotations

import json
import re
from typing import Any, Callable

from RestrictedPython import compile_restricted

# ---------------------------------------------------------------------------
# Safe builtins — duplicated from safety_gate.py to avoid circular imports.
# Keep in sync with sentinel/engine/safety_gate.py SAFE_BUILTINS.
# ---------------------------------------------------------------------------
SAFE_BUILTINS: dict = {
    "len": len,
    "any": any,
    "all": all,
    "min": min,
    "max": max,
    "abs": abs,
    "round": round,
    "sum": sum,
    "isinstance": isinstance,
    "dict": dict,
    "list": list,
    "str": str,
    "int": int,
    "bool": bool,
    "float": float,
    "True": True,
    "False": False,
    "None": None,
}

# Forbidden tokens — static scan before RestrictedPython compilation.
# Duplicated from safety_gate.py to keep validation harness self-contained.
_FORBIDDEN_TOKENS: list[str] = ["import", "__", "open", "exec", "eval"]

# ---------------------------------------------------------------------------
# Baseline fixture for validation check 4 — realistic clean transaction.
# A generated rule must NOT fire on this board (score must be < 0.2).
# Values chosen from behavioral baseline mean ± 1 std (low anomaly signal).
# ---------------------------------------------------------------------------
CLEAN_BASELINE_VERDICT_BOARD: dict = {
    "mismatches": [],
    "behavioral_flags": [],
    "agent_confidence": 0.55,
    "confidence_z_score": 0.8,
    "step_sequence_deviation": False,
    "hardcoded_rule_fired": False,
    "unable_to_verify": [],
    "prediction_errors": None,
}

# ---------------------------------------------------------------------------
# System prompt for Opus 4.6 rule generation.
# Constrains the model to behavioral VerdictBoard fields only — no attack-specific
# entity names, amounts, or hard-coded conditions that would fail to generalize.
# ---------------------------------------------------------------------------
RULE_GEN_SYSTEM_PROMPT = """\
You are a security detection engineer writing Python scoring functions for an AI agent
safety system. Your job is to write a single Python function that scores how anomalous
an AI agent's behavior was, based on signals in a VerdictBoard dict.

## CONTRACT

Write EXACTLY this function signature:

def score(verdict_board: dict) -> float:
    \"\"\"[One-sentence docstring describing what behavioral pattern you are scoring.]\"\"\"""
    ...

The function MUST:
- Accept a single argument `verdict_board: dict`
- Return a float between 0.0 and 2.0 (0.0 = normal, higher = more anomalous)
- Use only `verdict_board.get(...)` to access fields — no positional indexing
- Include a docstring explaining the behavioral pattern detected
- Be a standalone function with NO helpers, NO nested classes, NO imports

## AVAILABLE VerdictBoard FIELDS

- mismatches: list[dict] — each dict has keys: field, agent_claimed, independently_found, match, severity ("critical"|"warning"|"info"), agent_id
- behavioral_flags: list[str] — union of flags from all agents (e.g. "hidden_text_detected", "amount_deviation_extreme")
- agent_confidence: float (0.0–1.0) — claimed confidence level
- confidence_z_score: float | None — deviation from behavioral baseline (mean=0.52, std=0.11)
- step_sequence_deviation: bool — agent skipped or reordered required verification steps
- hardcoded_rule_fired: bool — a Tier 1 hardcoded rule has already fired
- unable_to_verify: list[str] — agent IDs that could not confirm the agent's claims
- prediction_errors: dict | None — prediction report: {"summary_score": float, "top_deviations": list[dict]}

## CRITICAL CONSTRAINTS

NEVER use: import, __, open, exec, eval — these will cause immediate rejection.
DO NOT hardcode: specific amounts, entity names, account numbers, document types.
DO NOT reference attack-specific details — write BEHAVIORAL generalizations only.
Return float, NOT bool. Use min() to cap the return value at 2.0.

## EXAMPLES

### Example 1 — Confidence z-score anomaly:
def score(verdict_board: dict) -> float:
    \"\"\"Confidence far from behavioral baseline is a manipulation signal.\"\"\"
    z = verdict_board.get("confidence_z_score")
    if z is None:
        return 0.0
    abs_z = abs(z)
    if abs_z > 3.0:
        return 0.6
    if abs_z > 2.0:
        return 0.3
    return 0.0

### Example 2 — Critical field mismatches:
def score(verdict_board: dict) -> float:
    \"\"\"Each critical mismatch between agent claims and ground truth is a strong anomaly signal.\"\"\"
    mismatches = verdict_board.get("mismatches", [])
    total = 0.0
    for m in mismatches:
        severity = m.get("severity", "info")
        if severity == "critical":
            total += 0.4
        elif severity == "warning":
            total += 0.15
    return min(total, 2.0)

## OUTPUT FORMAT

Output ONLY the Python function. No explanation, no markdown fences, no preamble.
Start directly with `def score(`.
"""


# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------

def build_rule_gen_prompt(
    attack_type: str,
    verdict_board: dict,
    prediction_errors: dict,
) -> str:
    """Build the user prompt for initial rule generation from a confirmed incident.

    The prompt injects the actual VerdictBoard and prediction errors from the
    confirmed episode. The model is instructed to generalize behaviorally —
    not to encode attack-specific conditions.

    Args:
        attack_type: Human-readable attack category (e.g. "prompt_injection_hidden_text").
        verdict_board: The incident's VerdictBoard as a dict.
        prediction_errors: The prediction error report from the incident.

    Returns:
        User prompt string ready for Opus 4.6.
    """
    vb_json = json.dumps(verdict_board, indent=2, default=str)
    pe_json = json.dumps(prediction_errors, indent=2, default=str)

    return f"""\
A confirmed attack has been detected. Attack type: {attack_type}

## Incident VerdictBoard

```json
{vb_json}
```

## Prediction Errors

The system predicted normal behavior and found these deviations from baseline:

```json
{pe_json}
```

## Your Task

Write a scoring function that captures the BEHAVIORAL PATTERN of this incident.

Key signals to consider:
- Which VerdictBoard fields showed the strongest anomaly?
- What combination of signals distinguishes this compromised behavior from normal behavior?
- How can these signals be weighted to produce a score that fires on this incident but NOT on normal transactions?

Remember: Write BEHAVIORAL generalizations. The function must generalize to future
incidents with different attack vectors but the same behavioral fingerprint.

Output ONLY the Python function. Start with `def score(`.
"""


def build_evolution_prompt(
    v1_source: str,
    attack_type: str,
    vb1: dict,
    vb2: dict,
    pe1: dict,
    pe2: dict,
) -> str:
    """Build the user prompt for rule evolution after a second confirmed incident.

    The evolution prompt provides both VerdictBoards and both prediction error sets.
    The model is instructed to:
    - Drop conditions that appeared in only one incident (attack artifacts)
    - Strengthen conditions that appeared in both (true behavioral signals)

    Args:
        v1_source: The v1 scoring function source code.
        attack_type: Human-readable attack category.
        vb1: VerdictBoard from the first confirmed incident.
        vb2: VerdictBoard from the second confirmed incident.
        pe1: Prediction errors from the first incident.
        pe2: Prediction errors from the second incident.

    Returns:
        User prompt string for rule evolution.
    """
    vb1_json = json.dumps(vb1, indent=2, default=str)
    vb2_json = json.dumps(vb2, indent=2, default=str)
    pe1_json = json.dumps(pe1, indent=2, default=str)
    pe2_json = json.dumps(pe2, indent=2, default=str)

    return f"""\
A second confirmed attack has been detected. Attack type: {attack_type}

You previously wrote the following scoring function (v1) based on the first incident:

```python
{v1_source}
```

Now you have data from TWO incidents. Your task is to write an EVOLVED scoring
function (v2) that is sharper and more general.

## Incident 1 VerdictBoard

```json
{vb1_json}
```

## Incident 1 Prediction Errors

```json
{pe1_json}
```

## Incident 2 VerdictBoard

```json
{vb2_json}
```

## Incident 2 Prediction Errors

```json
{pe2_json}
```

## Evolution Rules

1. **DROP** conditions that appeared in only one incident — these are attack artifacts, not behavioral patterns.
2. **STRENGTHEN** conditions (tighter thresholds, higher weights) that appeared in BOTH incidents.
3. **ADD** new conditions from incident 2 that are also consistent with incident 1.
4. The evolved function must score HIGHER on both incident VerdictBoards than on clean baselines.

## Output

Write the evolved v2 scoring function. Output ONLY the Python function. Start with `def score(`.
"""


# ---------------------------------------------------------------------------
# Internal execution helper
# ---------------------------------------------------------------------------

def _exec_rule(source: str) -> Callable[[dict], float]:
    """Compile and exec a scoring function source string via RestrictedPython.

    Uses SAFE_BUILTINS + RestrictedPython guards to restrict execution to pure
    computation over the verdict_board dict. No system calls, no file access,
    no network.

    Args:
        source: Python source code defining `def score(verdict_board: dict) -> float`.

    Returns:
        The compiled `score` callable.

    Raises:
        ValueError: If source fails to compile or does not define a callable score().
        SyntaxError: If RestrictedPython rejects the source syntax.
    """
    try:
        code = compile_restricted(source, "<rule_generator:validate>", "exec")
    except SyntaxError as exc:
        raise ValueError(f"compile_restricted failed: {exc}") from exc
    except Exception as exc:
        raise ValueError(f"compile_restricted failed: {exc}") from exc

    safe_globals: dict = {
        "__builtins__": SAFE_BUILTINS,
        "_getattr_": getattr,
        "_getiter_": iter,
        "_getitem_": lambda obj, key: obj[key],
        "_write_": lambda obj: obj,
        "_inplacevar_": lambda op, x, y: x + y if op == "+=" else x - y,
    }
    namespace: dict = {}
    exec(code, safe_globals, namespace)  # noqa: S102

    score_fn = namespace.get("score")
    if not callable(score_fn):
        raise ValueError("Generated rule does not define a callable score() function")

    return score_fn  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Validation harness — 4 checks per D-05
# ---------------------------------------------------------------------------

def validate_rule(source: str, attack_vb: dict) -> tuple[bool, str]:
    """Run the 4-check validation harness on a generated scoring function.

    Checks are executed in order per D-05:
        1. compile_restricted() — catches syntax errors and restricted constructs
        2. Forbidden token scan — rejects import, __, open, exec, eval
        3. Fires on attack fixture — score(attack_vb) must be > 0.6
        4. Clean on baseline — score(CLEAN_BASELINE_VERDICT_BOARD) must be < 0.2

    Args:
        source: Python source code for the scoring function.
        attack_vb: VerdictBoard dict from the confirmed incident (attack fixture).

    Returns:
        (True, "") on success.
        (False, reason_string) on any failure.
    """
    # Check 1: RestrictedPython compilation
    try:
        compile_restricted(source, "<validate>", "exec")
    except SyntaxError as exc:
        return False, f"compile_restricted failed: {exc}"
    except Exception as exc:
        return False, f"compile_restricted failed: {exc}"

    # Check 2: Static forbidden token scan
    for token in _FORBIDDEN_TOKENS:
        if token in source:
            return False, f"forbidden token: {token!r}"

    # Check 3: Must fire on attack fixture (score > 0.6)
    try:
        score_fn = _exec_rule(source)
        attack_score = float(score_fn(attack_vb))
    except Exception as exc:
        return False, f"execution failed: {exc}"

    if attack_score <= 0.6:
        return False, f"attack score {attack_score:.3f} must be > 0.6 to demonstrate detection"

    # Check 4: Must not fire on clean baseline (score < 0.2)
    try:
        clean_score = float(score_fn(CLEAN_BASELINE_VERDICT_BOARD))
    except Exception as exc:
        return False, f"clean baseline execution failed: {exc}"

    if clean_score >= 0.2:
        return False, f"clean baseline score {clean_score:.3f} must be < 0.2 to avoid false positives"

    return True, ""


# ---------------------------------------------------------------------------
# RuleGenerator — async wrapper with streaming + retry
# ---------------------------------------------------------------------------

def _strip_markdown_fences(text: str) -> str:
    """Remove markdown code fences from LLM output if present."""
    # Match ```python ... ``` or ``` ... ``` blocks
    fence_pattern = re.compile(r"```(?:python)?\s*\n(.*?)```", re.DOTALL)
    match = fence_pattern.search(text)
    if match:
        return match.group(1).strip()
    # If no fences found, return stripped text
    return text.strip()


class RuleGenerator:
    """Async engine for generating and evolving Safety Gate scoring functions.

    Uses Opus 4.6 (via streaming) to write Python scoring functions from confirmed
    incident prediction errors. Validates each attempt before returning.

    Usage:
        rg = RuleGenerator(llm_client=async_anthropic_client, model="claude-opus-4-6")
        source, error = await rg.generate(
            attack_type="prompt_injection_hidden_text",
            verdict_board=vb_dict,
            prediction_errors=pe_dict,
        )
    """

    MAX_ATTEMPTS = 3

    def __init__(self, llm_client: Any, model: str = "claude-opus-4-6") -> None:
        """Initialize RuleGenerator.

        Args:
            llm_client: An AsyncAnthropic client instance (shared, module-level).
            model: Model ID for rule generation (default: claude-opus-4-6).
        """
        self._client = llm_client
        self._model = model

    async def generate(
        self,
        attack_type: str,
        verdict_board: dict,
        prediction_errors: dict,
        ws_broadcast: Any = None,
        episode_id: str = "",
    ) -> tuple[str | None, str | None]:
        """Generate a scoring function from a confirmed incident.

        Streams Opus 4.6 output and validates each attempt. Injects failure
        reason into subsequent attempts on retry.

        Args:
            attack_type: Human-readable attack category.
            verdict_board: The incident's VerdictBoard as a dict.
            prediction_errors: Prediction error report from the incident.
            ws_broadcast: Optional async callable(event_type, data, episode_id) for streaming tokens.
            episode_id: Episode ID for WebSocket event context.

        Returns:
            (source, None) on success — validated Python source code.
            (None, reason) on failure after all retries.
        """
        last_failure_reason: str = ""

        for attempt in range(1, self.MAX_ATTEMPTS + 1):
            # Build user prompt — inject failure reason on retry
            user_prompt = build_rule_gen_prompt(attack_type, verdict_board, prediction_errors)
            if attempt > 1 and last_failure_reason:
                user_prompt += (
                    f"\n\n## Previous Attempt Failed\n\nAttempt {attempt - 1} was rejected: "
                    f"{last_failure_reason}\n\nPlease fix this issue in your response."
                )

            # Stream from Opus 4.6
            accumulated = ""
            try:
                async with self._client.messages.stream(
                    model=self._model,
                    max_tokens=1024,
                    system=RULE_GEN_SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": user_prompt}],
                ) as stream:
                    async for text in stream.text_stream:
                        accumulated += text
                        if ws_broadcast is not None:
                            try:
                                await ws_broadcast(
                                    "rule_generating",
                                    {
                                        "token": text,
                                        "accumulated": accumulated,
                                        "attempt": attempt,
                                    },
                                    episode_id,
                                )
                            except Exception:
                                pass  # Non-fatal — streaming is best-effort
            except Exception as exc:
                last_failure_reason = f"LLM streaming failed: {exc}"
                continue

            # Strip markdown fences if present
            source = _strip_markdown_fences(accumulated)

            # Validate the generated source
            valid, reason = validate_rule(source, verdict_board)
            if valid:
                return source, None

            last_failure_reason = reason

        # All attempts exhausted
        if ws_broadcast is not None:
            try:
                await ws_broadcast(
                    "rule_generation_failed",
                    {"reason": last_failure_reason, "attempts": self.MAX_ATTEMPTS},
                    episode_id,
                )
            except Exception:
                pass

        return None, last_failure_reason

    async def evolve(
        self,
        v1_source: str,
        attack_type: str,
        vb1: dict,
        vb2: dict,
        pe1: dict,
        pe2: dict,
        ws_broadcast: Any = None,
        episode_id: str = "",
    ) -> tuple[str | None, str | None]:
        """Evolve a scoring function after a second confirmed incident.

        Uses both VerdictBoards and prediction error sets to write a refined
        scoring function per D-09. Validates against vb2 (attack fixture) and
        CLEAN_BASELINE_VERDICT_BOARD.

        Args:
            v1_source: The existing v1 scoring function source code.
            attack_type: Human-readable attack category.
            vb1: VerdictBoard from the first confirmed incident.
            vb2: VerdictBoard from the second confirmed incident.
            pe1: Prediction errors from the first incident.
            pe2: Prediction errors from the second incident.
            ws_broadcast: Optional async callable for streaming tokens.
            episode_id: Episode ID for WebSocket event context.

        Returns:
            (source, None) on success — validated evolved Python source code.
            (None, reason) on failure after all retries.
        """
        last_failure_reason: str = ""

        for attempt in range(1, self.MAX_ATTEMPTS + 1):
            user_prompt = build_evolution_prompt(
                v1_source, attack_type, vb1, vb2, pe1, pe2
            )
            if attempt > 1 and last_failure_reason:
                user_prompt += (
                    f"\n\n## Previous Attempt Failed\n\nAttempt {attempt - 1} was rejected: "
                    f"{last_failure_reason}\n\nPlease fix this issue in your response."
                )

            accumulated = ""
            try:
                async with self._client.messages.stream(
                    model=self._model,
                    max_tokens=1024,
                    system=RULE_GEN_SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": user_prompt}],
                ) as stream:
                    async for text in stream.text_stream:
                        accumulated += text
                        if ws_broadcast is not None:
                            try:
                                await ws_broadcast(
                                    "rule_generating",
                                    {
                                        "token": text,
                                        "accumulated": accumulated,
                                        "attempt": attempt,
                                    },
                                    episode_id,
                                )
                            except Exception:
                                pass
            except Exception as exc:
                last_failure_reason = f"LLM streaming failed: {exc}"
                continue

            source = _strip_markdown_fences(accumulated)

            # Validate evolved source against vb2 (second attack fixture)
            valid, reason = validate_rule(source, vb2)
            # Also verify it still fires on vb1 — the evolved function must score
            # both incidents, not just the latest one (Bug 5 fix)
            if valid and vb1:
                valid_vb1, reason_vb1 = validate_rule(source, vb1)
                if not valid_vb1:
                    valid = False
                    reason = f"regresses on incident 1: {reason_vb1}"
            if valid:
                return source, None

            last_failure_reason = reason

        # All attempts exhausted
        if ws_broadcast is not None:
            try:
                await ws_broadcast(
                    "rule_generation_failed",
                    {"reason": last_failure_reason, "attempts": self.MAX_ATTEMPTS},
                    episode_id,
                )
            except Exception:
                pass

        return None, last_failure_reason
