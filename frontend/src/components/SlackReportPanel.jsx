import { useStore } from '../store'

function computeAgentConfidence(verdict) {
  if (!verdict?.claims_checked?.length) return 0
  const mismatches = verdict.claims_checked.filter(c => c.match === 'mismatch' || c.match === false).length
  const total = verdict.claims_checked.length
  // High confidence = agent found issues correctly (more mismatches found = better investigation)
  return total > 0 ? Math.min(0.99, 0.7 + (mismatches / total) * 0.25) : 0
}

function computeAgentFlags(verdict) {
  if (!verdict) return 0
  let flags = 0
  if (verdict.behavioral_flags?.length) flags += verdict.behavioral_flags.length
  if (verdict.claims_checked) flags += verdict.claims_checked.filter(c => c.match === 'mismatch' || c.match === false).length
  return flags
}

export function SlackReportPanel() {
  const gateDecision = useStore((s) => s.gateDecision)
  const reportStatus = useStore((s) => s.reportStatus)
  const agents = useStore((s) => s.agents)
  const verdictBoard = useStore((s) => s.verdictBoard)

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

  // Payment agent self-reported confidence (high, but untrustworthy — it was manipulated)
  const paymentZScore = verdictBoard?.confidence_z_score || verdictBoard?.fields?.find(f => f.field === 'confidence_z_score')
  const paymentSelfConfidence = paymentZScore ? 0.95 : null
  const isCompromised = gateDecision?.decision === 'NO-GO'

  return (
    <div className="bg-surface rounded-lg border border-border-muted p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <span className="material-symbols-outlined text-[16px] text-accent">psychology</span>
          <span className="text-[13px] font-semibold text-text-main uppercase tracking-wider">
            Deep Dive with AI
          </span>
        </div>
        <span className={`text-[12px] font-mono ${statusColor[reportStatus] || statusColor.idle}`}>
          {statusLabel[reportStatus] || statusLabel.idle}
        </span>
      </div>

      {gateDecision ? (
        <div className="rounded bg-bg-dark border border-border-muted px-3 py-2 space-y-2">
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
              {Array.isArray(gateDecision.attribution)
                ? gateDecision.attribution.map((a) => `${a.rule_id} (+${a.contribution?.toFixed(2) ?? '?'})`).join(', ')
                : gateDecision.attribution}
            </p>
          )}

          {/* Agent Verdicts */}
          <div className="pt-1 border-t border-border-muted/50">
            <p className="text-[11px] uppercase text-text-muted font-semibold mb-1.5">Agent Verdicts</p>
            <div className="grid grid-cols-2 gap-x-4 gap-y-1.5">
              {/* Payment Agent — self-reported confidence, marked untrustworthy */}
              {paymentSelfConfidence != null && (
                <div className="col-span-2 mb-1">
                  <p className="text-[12px] font-semibold text-danger">
                    Payment Agent (Sonnet)
                  </p>
                  <p className="text-[11px] font-mono">
                    <span className="text-text-muted">Self-Reported:</span>{' '}
                    <span className="text-warning">{paymentSelfConfidence.toFixed(2)}</span>
                    {isCompromised && (
                      <span className="ml-2 text-[9px] font-bold uppercase px-1.5 py-0.5 rounded bg-danger/15 text-danger border border-danger/30">
                        Compromised
                      </span>
                    )}
                  </p>
                </div>
              )}
              {/* Sub-agents */}
              {['risk', 'compliance', 'forensics'].map(agentKey => {
                const verdict = agents[agentKey]?.verdict
                const confidence = computeAgentConfidence(verdict)
                const flags = computeAgentFlags(verdict)
                const agentLabel = agentKey.charAt(0).toUpperCase() + agentKey.slice(1)
                return (
                  <div key={agentKey}>
                    <p className="text-[12px] font-semibold text-text-main">{agentLabel}</p>
                    <p className="text-[11px] font-mono text-text-muted">
                      Confidence: <span className="text-warning">{confidence.toFixed(2)}</span>
                      {' | '}Flags: <span className="text-warning">{flags}</span>
                    </p>
                  </div>
                )
              })}
            </div>
          </div>

          <p className="text-[10px] text-text-muted mt-1 italic">
            AI-generated report delivered to #payment-system-infosec via Slack
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
