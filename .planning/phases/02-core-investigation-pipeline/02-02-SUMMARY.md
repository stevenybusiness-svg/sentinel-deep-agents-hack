---
phase: "02"
plan: "02"
subsystem: payment-agent
tags: [payment-agent, tool-use, vision, base64, sonnet-4-6, d-01, d-02, d-03, d-04, d-05, pipe-01, pipe-07]
dependency_graph:
  requires: [02-01]
  provides: [PAYMENT_TOOLS, PAYMENT_AGENT_SYSTEM_PROMPT, handle_tool_call, parse_payment_decision]
  affects: [02-06]
tech_stack:
  added: [sentinel.agents.payment_agent]
  patterns: [tool-use-definitions, base64-vision-encoding, json-response-parsing]
key_files:
  created:
    - sentinel/agents/payment_agent.py
    - tests/test_payment_agent.py
  modified: []
decisions:
  - "Payment Agent module exposes building blocks only (PAYMENT_TOOLS, handle_tool_call, parse_payment_decision) -- no autonomous loop per D-03; Supervisor (Plan 02-06) drives the conversation turn-by-turn"
  - "read_invoice returns 2-block list (image + text annotation) so Claude vision API receives both image data and descriptive text in same tool_result"
  - "parse_payment_decision handles both raw JSON and markdown code-fenced JSON, plus JSON embedded in prose -- covers all realistic LLM output formats"
metrics:
  duration_minutes: 2
  tasks_completed: 2
  files_created: 2
  files_modified: 0
  completed_date: "2026-03-25"
---

# Phase 2 Plan 2: Payment Agent Module Summary

**One-liner:** Payment Agent building blocks for Sonnet 4.6 -- 3 tool definitions (check_counterparty, verify_kyc, read_invoice with base64 PNG vision encoding), tool call handler against fixtures, and JSON response parser producing PaymentDecision -- no autonomous loop, Supervisor drives per D-03.

## What Was Built

### Task 1: Payment Agent Tool Definitions, Handler, and Parser

Created `sentinel/agents/payment_agent.py` with all required exports:

**`PAYMENT_AGENT_SYSTEM_PROMPT`** — System prompt for the Sonnet 4.6 Payment Agent. Instructs the agent to analyze payment requests using available tools and output a structured JSON decision with decision/amount/beneficiary/account/rationale/confidence/claims fields.

**`PAYMENT_TOOLS`** — List of 3 tool definitions per D-01:
- `check_counterparty`: looks up `{"name": str}` in counterparty_db fixture; returns entry or `{"found": false}`
- `verify_kyc`: looks up `{"beneficiary": str}` in kyc_ledger fixture; returns entry or `{"status": "not_found"}`
- `read_invoice`: takes `{"invoice_id": str}`, reads the invoice PNG from disk; returns base64-encoded image content block per D-02

**`handle_tool_call(tool_name, tool_input, fixtures, invoice_path)`** — Executes a single tool call against fixtures and returns content blocks for tool_result messages:
- counterparty/kyc lookups: returns `[{"type": "text", "text": json_result}]`
- read_invoice: returns `[{"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": img_b64}}, {"type": "text", "text": "Invoice document attached for analysis."}]`
- Case-insensitive key matching for both counterparty and KYC lookups

**`parse_payment_decision(response_text, episode_id, steps_taken)`** — Extracts PaymentDecision from the Payment Agent's final text response:
- Handles raw JSON, markdown code-fenced JSON (```json...```), and JSON embedded in prose
- Raises `ValueError` with descriptive message if JSON cannot be extracted
- Populates episode_id and steps_taken from parameters (not from LLM response)

**Critical D-03 compliance:** The module contains NO autonomous multi-turn loop. No `while` loop calls `client.messages.create`. The Supervisor (Opus 4.6, Plan 02-06) manages the full conversation and calls these functions as needed.

### Task 2: Payment Agent Unit Tests

Created `tests/test_payment_agent.py` with 14 unit tests:

| Test | What It Verifies |
|------|-----------------|
| test_payment_tools_count | PAYMENT_TOOLS has exactly 3 entries |
| test_payment_tools_names | check_counterparty, verify_kyc, read_invoice names present |
| test_payment_agent_system_prompt_not_empty | PAYMENT_AGENT_SYSTEM_PROMPT is non-empty string |
| test_handle_tool_call_counterparty_found | Returns fixture entry as JSON text block |
| test_handle_tool_call_counterparty_not_found | Returns {found: false} |
| test_handle_tool_call_counterparty_case_insensitive | Case-insensitive name matching works |
| test_handle_tool_call_kyc_found | Returns KYC record when beneficiary known |
| test_handle_tool_call_kyc_not_found | Returns {status: not_found} for Meridian Logistics (intentional gap) |
| test_handle_tool_call_read_invoice | Image block with correct base64 data + text annotation |
| test_handle_tool_call_read_invoice_no_path | Error block returned when invoice_path is None |
| test_parse_payment_decision_basic | Plain JSON response parsed correctly |
| test_parse_payment_decision_from_markdown | Markdown code-fenced JSON extracted |
| test_parse_payment_decision_json_embedded_in_text | JSON in prose extracted |
| test_parse_payment_decision_invalid_raises | ValueError raised on non-JSON text |

All 14 tests pass without any API calls (no ANTHROPIC_API_KEY required).

## Decisions Made

1. **No autonomous loop per D-03**: Module is pure library code — tool definitions, a handler function, and a parser. The Supervisor (Plan 02-06) is responsible for the conversation loop.

2. **Two-block read_invoice response**: Returning `[image_block, text_block]` in a single tool_result ensures Claude vision API receives both the image data and a text annotation in the same turn — matches Claude's tool_result content format.

3. **Flexible JSON extraction in parse_payment_decision**: LLMs frequently wrap JSON in markdown fences or add prose. The parser handles all three formats (raw JSON, `\`\`\`json...\`\`\``, embedded in text) using a regex cascade. This prevents brittle failures in the demo path.

## Deviations from Plan

None — plan executed exactly as written.

## Commits

| Task | Commit | Message |
|------|--------|---------|
| Task 1 | b739990 | feat(02-02): implement Payment Agent tool definitions, handler, and parser |
| Task 2 | 84854aa | test(02-02): add Payment Agent unit tests with mocked fixtures |

## Self-Check: PASSED

- sentinel/agents/payment_agent.py: FOUND
- tests/test_payment_agent.py: FOUND
- Commit b739990: FOUND
- Commit 84854aa: FOUND
