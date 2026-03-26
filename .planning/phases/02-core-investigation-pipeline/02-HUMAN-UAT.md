---
status: partial
phase: 02-core-investigation-pipeline
source: [02-VERIFICATION.md]
started: 2026-03-25T00:00:00Z
updated: 2026-03-25T00:00:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Hidden-text invoice attack end-to-end
expected: With live ANTHROPIC_API_KEY, the hidden-text invoice attack causes the Payment Agent (Sonnet 4.6) to be genuinely manipulated while Sentinel detects it and returns a BLOCK decision.
result: [pending]

### 2. Aerospike write latency visible in response
expected: With a running Aerospike cluster, the API response contains `write_latency_ms > 0.0` (non-mock value).
result: [pending]

## Summary

total: 2
passed: 0
issues: 0
pending: 2
skipped: 0
blocked: 0

## Gaps
