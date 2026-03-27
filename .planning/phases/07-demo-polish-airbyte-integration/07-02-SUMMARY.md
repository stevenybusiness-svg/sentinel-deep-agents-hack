---
phase: 07-demo-polish-airbyte-integration
plan: "02"
subsystem: integrations
tags: [airbyte, slack, duckdb, frontend, demo-polish]
dependency_graph:
  requires:
    - "07-01"
  provides:
    - airbyte-duckdb-cache
    - slack-webhook-reporter
    - report-delivery-panel
  affects:
    - sentinel/agents/supervisor.py
    - sentinel/schemas/events.py
    - frontend/src/App.jsx
    - frontend/src/store.js
    - frontend/src/hooks/useWebSocket.js
tech_stack:
  added:
    - duckdb==1.1.3
    - airbyte (PyAirbyte)
  patterns:
    - PyAirbyte DuckDB default cache with direct duckdb fallback
    - Block Kit Slack Incoming Webhook via httpx.AsyncClient
    - report_delivered WS event bridging backend delivery status to frontend
key_files:
  created:
    - sentinel/integrations/__init__.py
    - sentinel/integrations/airbyte_cache.py
    - sentinel/integrations/slack_reporter.py
    - tests/test_airbyte_slack.py
    - frontend/src/components/AirbyteReportPanel.jsx
  modified:
    - sentinel/agents/supervisor.py
    - sentinel/schemas/events.py
    - frontend/src/App.jsx
    - frontend/src/store.js
    - frontend/src/hooks/useWebSocket.js
    - requirements.txt
    - .env.example
decisions:
  - "PyAirbyte DuckDB fallback to direct duckdb: PyAirbyte cache API varies across versions; try ab.get_default_cache().get_duckdb_conn(), fall back to duckdb.connect() on failure"
  - "duckdb pinned to 1.1.3: latest duckdb had import error (TimestampMillisecondValue name mismatch in value/constant module)"
  - "report_delivered added to EventType Literal: required for pydantic WSEvent validation; would raise ValidationError without it"
  - "VoicePanel replaced fully, not kept alongside: judges want Airbyte story front and center; voice state removed cleanly"
metrics:
  duration: "~5 minutes"
  completed_date: "2026-03-27"
  tasks_completed: 2
  files_changed: 12
---

# Phase 07 Plan 02: Airbyte+Slack Report Delivery and AirbyteReportPanel Summary

**One-liner:** PyAirbyte DuckDB episode cache + Slack Block Kit webhook reporter wired into investigation pipeline, with AirbyteReportPanel replacing VoicePanel on the dashboard.

## What Was Built

### Airbyte Cache Module (`sentinel/integrations/airbyte_cache.py`)

Writes episode investigation data to a local DuckDB file after each gate evaluation. Uses PyAirbyte's default cache when available, falls back to direct duckdb. The `episodes` table stores `episode_id`, `decision`, `composite_score`, `attribution`, and `created_at`. Non-blocking — failures return False and do not affect the investigation pipeline.

### Slack Reporter Module (`sentinel/integrations/slack_reporter.py`)

Sends Block Kit formatted investigation reports to a Slack Incoming Webhook after each gate evaluation. Returns False silently when `SLACK_WEBHOOK_URL` is unset or a placeholder. Formats a header block with decision, a section block with episode ID / score / attribution, and a context block crediting the Airbyte pipeline.

### Pipeline Wiring (`sentinel/agents/supervisor.py`)

After the `gate_evaluated` broadcast, the supervisor now:
1. Calls `write_episode_to_cache(...)` — persists to DuckDB
2. Calls `send_investigation_report(...)` — POSTs to Slack
3. Broadcasts `report_delivered` WS event with `{channel: "slack", success: bool}`

### EventType Updated (`sentinel/schemas/events.py`)

Added `"report_delivered"` to the `EventType` Literal so the `WSEvent` pydantic model validates the broadcast without raising errors.

### AirbyteReportPanel (`frontend/src/components/AirbyteReportPanel.jsx`)

Replaces VoicePanel. Shows idle / sending / delivered / failed status driven by the `reportStatus` store field. Displays a report preview with decision, score, attribution, and a note about PyAirbyte persisting to DuckDB cache.

### Store + WebSocket (`frontend/src/store.js`, `frontend/src/hooks/useWebSocket.js`)

- Replaced `voiceCallId`/`voiceCallStatus` in store with `reportStatus`/`reportChannel`
- `resetInvestigation` resets `reportStatus: 'idle'`
- `gate_evaluated` case sets `reportStatus` to `'sending'`
- New `report_delivered` case sets `reportStatus` to `'delivered'` or `'failed'`

## Verification Results

```
python -c "from sentinel.integrations.slack_reporter import send_investigation_report" => OK
python -c "from sentinel.integrations.airbyte_cache import write_episode_to_cache"    => OK
pytest tests/test_airbyte_slack.py -x -q                                              => 4 passed
cd frontend && npm run build                                                            => 186 modules, built in 320ms
grep "AirbyteReportPanel" frontend/src/App.jsx                                         => 2 matches (import + usage)
grep "VoicePanel" frontend/src/App.jsx                                                 => 0 matches
grep "voiceCall" frontend/src/hooks/useWebSocket.js                                    => 0 matches
grep "report_delivered" frontend/src/hooks/useWebSocket.js                             => 1 match
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] duckdb import error with latest version**
- **Found during:** Task 1 — install verification
- **Issue:** `duckdb` latest version had `ImportError: cannot import name 'TimestampMillisecondValue'` — a broken release
- **Fix:** Pinned `duckdb==1.1.3` which imports cleanly
- **Files modified:** requirements.txt (added `duckdb==1.1.3`)
- **Commit:** cfa53a0

**2. [Rule 2 - Missing critical] report_delivered not in EventType**
- **Found during:** Task 1 — wiring into supervisor.py
- **Issue:** WSEvent uses pydantic Literal validation; broadcasting `report_delivered` without adding it to EventType would cause runtime ValidationError during demo
- **Fix:** Added `"report_delivered"` to EventType Literal in `sentinel/schemas/events.py`
- **Files modified:** sentinel/schemas/events.py
- **Commit:** cfa53a0

## Known Stubs

None — all wiring is live. The Slack webhook returns False (silently) when `SLACK_WEBHOOK_URL` is not configured, which is expected behavior, not a stub.

## Self-Check: PASSED

All files created and verified:
- FOUND: sentinel/integrations/airbyte_cache.py
- FOUND: sentinel/integrations/slack_reporter.py
- FOUND: tests/test_airbyte_slack.py
- FOUND: frontend/src/components/AirbyteReportPanel.jsx

Commits verified:
- cfa53a0: feat(07-02): add Airbyte DuckDB cache, Slack reporter, wire into pipeline
- dc4f215: feat(07-02): replace VoicePanel with AirbyteReportPanel, add report state
