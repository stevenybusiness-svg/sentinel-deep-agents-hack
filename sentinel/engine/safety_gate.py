"""
SafetyGate — ENGN-02 through ENGN-06.

The Safety Gate is the deterministic enforcement boundary. No LLM in this path.

Architecture:
- Tier 1: Hardcoded rules (immutable, loaded from sentinel/gate/rules/rule_*.py)
- Tier 2: Generated rules (registered via register_rule(), compiled via RestrictedPython)
- Composite score >= 1.0 -> NO-GO | >= 0.6 -> ESCALATE | else -> GO

The block decision is an if-statement. Generated scoring functions are sandboxed via
RestrictedPython compile_restricted — no system calls, no file access, no network.
"""
from __future__ import annotations

import importlib.util
import signal
from pathlib import Path
from typing import Callable

from RestrictedPython import compile_restricted


class _ExecTimeout(Exception):
    """Raised when exec() exceeds the 5-second budget."""


def _timeout_handler(signum: int, frame: object) -> None:
    raise _ExecTimeout("Rule execution exceeded 5-second timeout")

from sentinel.schemas.verdict_board import VerdictBoard


# Safe builtins for generated rule execution — only pure computation primitives
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

# Static source pre-check — reject tokens that should never appear in scoring functions
_FORBIDDEN_TOKENS: list[str] = ["import", "__", "open", "exec", "eval"]


def _pre_check_source(source: str) -> None:
    """Static pre-check: reject rule source containing forbidden tokens.

    This is defense-in-depth before RestrictedPython compilation. The check
    runs against the raw source string, not the AST.

    Args:
        source: Python source string for the generated scoring function.

    Raises:
        ValueError: If a forbidden token is found in the source.
    """
    for token in _FORBIDDEN_TOKENS:
        if token in source:
            raise ValueError(f"Rule source contains forbidden token: {token!r}")


class SafetyGate:
    """Deterministic gate that applies scoring rules and outputs GO/NO-GO/ESCALATE.

    Usage:
        gate = SafetyGate()
        gate.load_rules_from_directory(Path("sentinel/gate/rules"))
        result = gate.evaluate(verdict_board)
    """

    def __init__(self) -> None:
        self._hardcoded_rules: dict[str, Callable[[dict], float]] = {}
        self._generated_rules: dict[str, Callable[[dict], float]] = {}

    def load_rules_from_directory(self, rules_dir: Path) -> None:
        """Load hardcoded scoring rules from rule_*.py files — ENGN-02, D-19.

        Rules are imported via importlib; each file must expose:
            def score(verdict_board: dict) -> float

        This method is idempotent and replaces all previously loaded hardcoded rules.
        Generated rules (rule_generated_*.py) are excluded — they must be registered
        via register_rule() to ensure correct is_generated classification.

        Args:
            rules_dir: Path to directory containing rule_*.py files.
        """
        self._hardcoded_rules = {}
        rule_files = [
            f for f in sorted(rules_dir.glob("rule_*.py"))
            if not f.stem.startswith("rule_generated_")
        ]
        for rule_file in rule_files:
            rule_id = rule_file.stem  # e.g. "rule_hidden_text"
            spec = importlib.util.spec_from_file_location(rule_id, rule_file)
            if spec is None or spec.loader is None:
                continue
            module = importlib.util.module_from_spec(spec)
            try:
                spec.loader.exec_module(module)  # type: ignore[arg-type]
                score_fn = getattr(module, "score", None)
                if callable(score_fn):
                    self._hardcoded_rules[rule_id] = score_fn
            except Exception:
                # Malformed rule file — skip rather than crash the gate
                pass

    def register_rule(self, rule_id: str, python_source: str) -> None:
        """Register a generated scoring function via RestrictedPython sandbox — ENGN-03, ENGN-05.

        CRITICAL: Uses compile_restricted from RestrictedPython, NOT plain compile().
        This is an explicit architectural invariant per CLAUDE.md.

        Pre-check rejects sources containing: import, __, open, exec, eval
        RestrictedPython compile_restricted provides additional compile-time safety.

        The compiled function executes with only SAFE_BUILTINS available — no system
        calls, no file access, no network access.

        Args:
            rule_id: Unique identifier for this rule (e.g. "gen_rule_001").
            python_source: Python source code for the scoring function. Must define
                           def score(verdict_board): ...

        Raises:
            ValueError: If source contains forbidden tokens or fails compilation.
            SyntaxError: If RestrictedPython rejects the source.
        """
        # 1. Static pre-check for forbidden tokens
        _pre_check_source(python_source)

        # 2. Compile via RestrictedPython compile_restricted (NOT plain compile())
        code = compile_restricted(python_source, f"<generated_rule:{rule_id}>", "exec")

        # 3. Execute with restricted globals — only SAFE_BUILTINS, no system access
        safe_globals: dict = {
            "__builtins__": SAFE_BUILTINS,
            "_getattr_": getattr,
            "_getiter_": iter,
            "_getitem_": lambda obj, key: obj[key],
            "_write_": lambda obj: obj,
            "_inplacevar_": lambda op, x, y: x + y if op == "+=" else x - y,
        }
        namespace: dict = {}

        # 5-second timeout per ENGN-05
        old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
        signal.alarm(5)
        try:
            exec(code, safe_globals, namespace)  # noqa: S102
        except _ExecTimeout:
            raise ValueError(f"Generated rule {rule_id!r} exceeded 5-second execution timeout")
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)

        # 4. Extract score() function from namespace
        score_fn = namespace.get("score")
        if not callable(score_fn):
            raise ValueError(f"Generated rule {rule_id!r} does not define a callable score() function")

        # 5. Store in generated rules registry
        self._generated_rules[rule_id] = score_fn

    def evaluate(self, verdict_board: VerdictBoard) -> dict:
        """Evaluate verdict board against all rules and compute GO/NO-GO/ESCALATE.

        Hardcoded rules run first (always, immutably — ENGN-02).
        Generated rules run second (ENGN-03).
        Composite score determines decision (ENGN-06).
        Full attribution is returned (ENGN-04).

        Args:
            verdict_board: Assembled VerdictBoard from VerdictBoardEngine.

        Returns:
            dict with keys:
                - decision: "GO" | "NO-GO" | "ESCALATE"
                - composite_score: float (rounded to 4 decimal places)
                - rule_contributions: list[dict] with rule_id, score, is_generated
                - attribution: str (human-readable explanation of the decision)
        """
        vb_dict = verdict_board.model_dump()
        contributions: list[dict] = []

        # 1. Run hardcoded rules first — immutable, always run (ENGN-02)
        hardcoded_fired = False
        for rule_id, score_fn in self._hardcoded_rules.items():
            try:
                score_val = float(score_fn(vb_dict))
                if score_val > 0:
                    contributions.append({
                        "rule_id": rule_id,
                        "score": score_val,
                        "is_generated": False,
                    })
                    hardcoded_fired = True
            except Exception:
                # Rule errors must never block the gate — skip silently
                pass

        # Update hardcoded_rule_fired so generated rules can condition on it (Bug 2 fix)
        vb_dict["hardcoded_rule_fired"] = hardcoded_fired

        # 2. Run generated rules (ENGN-03) with 5-second timeout per ENGN-05
        for rule_id, score_fn in self._generated_rules.items():
            try:
                old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
                signal.alarm(5)
                try:
                    score_val = float(score_fn(vb_dict))
                finally:
                    signal.alarm(0)
                    signal.signal(signal.SIGALRM, old_handler)
                if score_val > 0:
                    contributions.append({
                        "rule_id": rule_id,
                        "score": score_val,
                        "is_generated": True,
                    })
            except Exception:
                pass

        # 3. Compute composite score (ENGN-06)
        composite = sum(c["score"] for c in contributions)

        # 4. Decision thresholds — per ENGN-06 (these are the exact thresholds, never LLM)
        if composite >= 1.0:
            decision = "NO-GO"
        elif composite >= 0.6:
            decision = "ESCALATE"
        else:
            decision = "GO"

        # 5. Build attribution text (ENGN-04) — fully inspectable, no black box
        sorted_contributions = sorted(contributions, key=lambda x: x["score"], reverse=True)
        attribution_parts = []
        for c in sorted_contributions:
            prefix = "Generated Rule" if c["is_generated"] else "Rule"
            attribution_parts.append(f"{prefix} {c['rule_id']}: {c['score']:.2f}")

        if attribution_parts:
            attribution = (
                f"{decision} (composite: {composite:.2f}) | "
                + "; ".join(attribution_parts)
            )
        else:
            attribution = f"{decision} (composite: {composite:.2f}) | No rules fired"

        # Update hardcoded_rule_fired on the board (informational — not enforced here)
        # The caller may use this for logging/display purposes
        _ = hardcoded_fired  # available to callers via rule_contributions filtering

        return {
            "decision": decision,
            "composite_score": round(composite, 4),
            "rule_contributions": contributions,
            "attribution": attribution,
        }
