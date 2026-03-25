import { useStore } from '../store'

export function AnomalyScoreBar() {
  const gateDecision = useStore((s) => s.gateDecision)

  const composite = gateDecision?.composite_score ?? 0
  const rule_contributions = gateDecision?.rule_contributions ?? []

  // Maximum value for scaling — at least 1.0 so bar fills proportionally
  const maxVal = Math.max(composite, 1.0)

  // Threshold line position
  const thresholdPct = (1.0 / maxVal) * 100

  return (
    <div className="bg-surface rounded-lg border border-border-muted p-4 space-y-2">
      {/* Section label + score value */}
      <div className="flex items-center justify-between">
        <span className="text-[11px] font-semibold uppercase tracking-wider text-text-muted">
          Anomaly Score
        </span>
        <span className="text-[12px] font-mono text-text-main">
          {composite.toFixed(3)}
        </span>
      </div>

      {/* Segmented bar */}
      <div className="relative h-6 bg-bg-dark rounded overflow-hidden">
        <div className="flex h-full">
          {rule_contributions.map((contribution, idx) => {
            const widthPct = (contribution.score / maxVal) * 100
            const segmentColor = contribution.is_generated ? 'bg-danger' : 'bg-primary'
            return (
              <div
                key={idx}
                className={`h-full transition-all duration-500 ease-out ${segmentColor}`}
                style={{ width: `${widthPct}%` }}
                title={`${contribution.rule_id}: ${contribution.score?.toFixed(3)}`}
              />
            )
          })}
        </div>

        {/* Threshold line at score = 1.0 */}
        <div
          className="absolute top-0 bottom-0 w-0.5 bg-accent"
          style={{ left: `${thresholdPct}%` }}
          title="Threshold (1.0)"
        />
      </div>

      {/* Rule contribution labels */}
      {rule_contributions.length > 0 && (
        <div className="flex flex-wrap gap-x-3 gap-y-0.5">
          {rule_contributions.map((contribution, idx) => (
            <span key={idx} className="text-[10px] font-mono text-text-muted">
              {contribution.rule_id}: {contribution.score?.toFixed(3)}
            </span>
          ))}
        </div>
      )}

      {/* Empty state: threshold line only, no rules yet */}
      {rule_contributions.length === 0 && (
        <p className="text-[11px] text-text-muted">No rule contributions yet.</p>
      )}
    </div>
  )
}
