# Phase 1: Foundation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the discussion.

**Date:** 2026-03-24
**Phase:** 01-foundation
**Mode:** discuss
**Areas discussed:** Fixture realism & format, Project directory structure, Schema validation strictness

## Gray Areas Presented

| Area | Description |
|------|-------------|
| Fixture realism & format | Invoice image type (real steganographic vs. mock) + counterparty/KYC data format |
| Counterparty/KYC data format | Covered in fixture discussion |
| Project directory structure | `sentinel/` + `frontend/` vs. `backend/` + `frontend/` vs. `app/` + `frontend/` |
| Schema validation strictness | Strict everywhere vs. minimal vs. hybrid (strict on Safety Gate fields only) |

## Decisions Made

### Fixture realism & format
- **Choice:** White-on-white invoice PNG (real steganographic approach) + JSON fixture files
- **Detail added by user:** Two matched invoice assets needed — `invoice_clean.png` (hidden text invisible) and `invoice_forensic.png` (hidden text highlighted in red) for the forensic scan panel side-by-side view
- **User clarification:** Confirmed JSON fixtures are the *legitimate* data stores the Compliance Agent queries to catch spoofing (not a data poisoning mechanism); KYC ledger's absence of Meridian Logistics is what exposes the fabricated pre-clearance

### Project directory structure
- **Choice:** `sentinel/` (Python package) + `frontend/` at repo root
- **Rationale confirmed:** Imports read `from sentinel.schemas import Verdict`; package name matches demo narrative

### Schema validation strictness
- **Choice:** Hybrid — strict on Safety Gate fields only
- **Strict fields:** `severity: Literal["critical", "warning", "info"]`, `confidence: float Field(ge=0, le=1)`, `match: bool`, gate decision `Literal["GO", "NO-GO", "ESCALATE"]`
- **Loose fields:** Step descriptions, claims text, agent reasoning, metadata
- **Rationale:** Safety Gate correctness depends on these types; loose elsewhere avoids slowing Phase 1

## Corrections / Clarifications

- Initial fixture question conflated counterparty DB format with data poisoning (Phase 2 attack). User clarified: JSON fixtures represent the *correct* ground truth; the attack is the spoofed agent message, not corrupted fixture data. This distinction matters for how the Compliance Agent is framed in Phase 2 planning.
