import { useStore } from '../store'

export function AirbyteReportPanel() {
  const gateDecision = useStore((s) => s.gateDecision)
  const reportStatus = useStore((s) => s.reportStatus)

  const statusLabel = {
    idle: 'Waiting for investigation...',
    sending: 'Delivering report to Slack...',
    delivered: 'Report delivered to Slack',
    failed: 'Delivery failed — check SLACK_WEBHOOK_URL',
  }

  const statusColor = {
    idle: 'text-text-muted',
    sending: 'text-warning',
    delivered: 'text-success',
    failed: 'text-danger',
  }

  return (
    <div className="bg-surface rounded-lg border border-border-muted p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <span className="material-symbols-outlined text-[16px] text-accent">send</span>
          <span className="text-[13px] font-semibold text-text-main uppercase tracking-wider">
            Airbyte Report Delivery
          </span>
        </div>
        <span className={`text-[12px] font-mono ${statusColor[reportStatus] || statusColor.idle}`}>
          {statusLabel[reportStatus] || statusLabel.idle}
        </span>
      </div>

      {gateDecision ? (
        <div className="rounded bg-bg-dark border border-border-muted px-3 py-2 space-y-1">
          <p className="text-[11px] uppercase text-text-muted font-semibold">
            Report Preview
          </p>
          <p className="text-[12px] text-text-main font-mono">
            Decision:{' '}
            <span className={
              gateDecision.decision === 'NO-GO' ? 'text-danger'
              : gateDecision.decision === 'ESCALATE' ? 'text-warning'
              : 'text-success'
            }>
              {gateDecision.decision}
            </span>
            {' '}&middot; Score:{' '}
            <span className="text-text-main">
              {(gateDecision.composite_score ?? 0).toFixed(2)}
            </span>
          </p>
          {gateDecision.attribution && (
            <p className="text-[12px] text-text-muted leading-snug">
              {gateDecision.attribution}
            </p>
          )}
          <p className="text-[10px] text-text-muted mt-1 italic">
            PyAirbyte persists episode to DuckDB cache, then delivers to Slack automatically
          </p>
        </div>
      ) : (
        <div className="rounded bg-bg-dark border border-border-muted px-3 py-2">
          <p className="text-[12px] text-text-muted italic">
            Run an investigation to generate a report.
          </p>
        </div>
      )}
    </div>
  )
}
