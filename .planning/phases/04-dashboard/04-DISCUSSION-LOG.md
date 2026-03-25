# Phase 4: Dashboard - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-25
**Phase:** 04-dashboard
**Areas discussed:** Layout architecture, Demo trigger UX, Confirm / operator action, Rule source presentation

---

## Layout Architecture

**Q: How should the dashboard panels be arranged?**
- Options: Fixed multi-column grid / Single-column scrollable / Tabbed panels
- **Selected: Fixed multi-column grid**
- Rationale: Live demo needs all panels visible simultaneously — no scrolling, judges see everything animate in real time.

**Q: Tree full-height left vs. split with rule source below?**
- Options: Tree full-height left / Tree top-left + rule source bottom-left
- **Selected: Tree full-height left, rule source right-bottom**
- Rationale: Maximum node graph space for the tree as it grows with agent completions and rule nodes.

---

## Demo Trigger UX

**Q: How does the operator start an investigation?**
- Options: Two hardcoded buttons / Scenario selector + Run / Free-form form
- **Selected: Two big buttons: Attack 1 / Attack 2**
- Rationale: Zero fumble risk on stage. Judges see exactly what's being demonstrated.

**Q: Where do the Attack buttons live?**
- Options: Header bar / Top of left column / Floating panel
- **Selected: Header bar — always visible**
- Rationale: One click from anywhere during the demo, never hidden behind content.

---

## Confirm / Operator Action

**Q: How does the operator confirm an attack?**
- Options: Button in gate decision panel / Modal / Separate confirm panel
- **Selected: Button in gate decision panel**
- Rationale: Contextually obvious — you see the block, you confirm it right there. No extra navigation.

**Q: Feedback while rule generation runs (10-30s)?**
- Options: Rule panel streams tokens live / Spinner / Both
- **Selected: Rule source panel streams tokens live**
- Rationale: Streaming live generation is the demo moment. Watching the rule being written is the "the system is learning right now" visual.

---

## Rule Source Presentation

**Q: How to display the generated Python?**
- Options: Syntax-highlighted + provenance / Plain monospace / v1→v2 diff
- **Selected: Syntax-highlighted monospace + provenance**
- Rationale: Maximum readability, makes the "inspectable Python" claim tangible. Provenance shows where the rule came from.

**Q: After evolution (v2), how to show the update?**
- Options: Replace with v2 + version badge / v1 crossed out + v2 / Animated fade transition
- **Selected: Replace with v2 + version badge**
- Rationale: Clean and clear. Provenance text ("Evolved from: ep1 + ep2") tells the story without visual clutter.
