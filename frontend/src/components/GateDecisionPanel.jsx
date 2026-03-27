import { useStore } from '../store'

export function GateDecisionPanel() {
  const gateDecision = useStore((s) => s.gateDecision)
  const trustScore = useStore((s) => s.trustScore)
  const ruleSources = useStore((s) => s.ruleSources)

  if (!gateDecision) {
    return (
      <div className="bg-surface rounded-lg border border-border-muted p-4">
        <span className="text-text-muted text-[13px]">No verdict yet.</span>
      </div>
    )
  }

  const { decision, composite_score, attribution } = gateDecision

  let verdictColorClass = 'text-success'
  if (decision === 'NO-GO') verdictColorClass = 'text-danger'
  else if (decision === 'ESCALATE') verdictColorClass = 'text-warning'

  const trustColor =
    trustScore >= 0.8 ? '#3fb950' : trustScore >= 0.4 ? '#e3b341' : '#f85149'

  return (
    <div className="bg-surface rounded-lg border border-border-muted p-4 space-y-2">
      {/* Verdict row */}
      <div className="flex items-center justify-between">
        <span className={`text-xl font-semibold ${verdictColorClass}`}>{decision}</span>
        <span className="text-[13px] text-text-muted font-mono">
          Score: {(composite_score ?? 0).toFixed(2)} &gt; threshold
        </span>
      </div>

      {/* Attribution */}
      {attribution && (
        <p className="text-[12px] text-text-main">
          {Array.isArray(attribution)
            ? attribution.map((a) => `${a.rule_id} (+${a.contribution?.toFixed(2) ?? '?'})`).join(', ')
            : attribution}
        </p>
      )}

      {/* Trust score inline (DASH-06) */}
      <div className="flex items-center gap-2 mt-2">
        <span className="text-[11px] uppercase text-text-muted">Trust</span>
        <div className="flex-1 h-3 bg-bg-dark rounded overflow-hidden">
          <div
            className="h-full rounded transition-all duration-500 ease-out"
            style={{
              width: `${trustScore * 100}%`,
              backgroundColor: trustColor,
            }}
          />
        </div>
        <span className="text-[11px] font-mono text-text-main w-8 text-right">
          {trustScore.toFixed(2)}
        </span>
      </div>

      {/* Autonomous learning status — no human action needed */}
      {decision === 'NO-GO' && (
        <div className="pt-1 flex items-center gap-2 text-[11px]">
          {ruleSources.length > 0 ? (
            <>
              <span className="material-symbols-outlined text-warning text-[14px]">auto_awesome</span>
              <span className="text-warning font-semibold">Autonomous learning complete — scoring function deployed</span>
            </>
          ) : (
            <>
              <span className="material-symbols-outlined text-primary text-[14px] animate-spin">sync</span>
              <span className="text-text-muted">Autonomously generating scoring function...</span>
            </>
          )}
        </div>
      )}
    </div>
  )
}
