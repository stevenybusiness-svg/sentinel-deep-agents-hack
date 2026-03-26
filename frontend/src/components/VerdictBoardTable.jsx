import { useStore } from '../store'

const truncate = (s, max = 30) => s && s.length > max ? s.slice(0, max) + '...' : s || '-'

function renderSeverityBadge(severity) {
  const styles = {
    critical: 'bg-danger/20 text-danger border border-danger/30',
    warning: 'bg-warning/20 text-warning border border-warning/30',
    info: 'bg-primary/20 text-primary border border-primary/30',
  }
  return (
    <span className={`text-[11px] uppercase rounded-full px-1.5 py-0.5 ${styles[severity] || styles.info}`}>
      {severity || 'info'}
    </span>
  )
}

function findExpectedValue(field, predictionErrors) {
  if (!predictionErrors) return null

  // Check investigation_outcome_errors for field-specific predicted values
  const outcomeErrors = predictionErrors.investigation_outcome_errors
  if (outcomeErrors && typeof outcomeErrors === 'object') {
    const keys = Object.keys(outcomeErrors)
    const matchKey = keys.find(k => k.toLowerCase().includes(field.toLowerCase()))
    if (matchKey) {
      const val = outcomeErrors[matchKey]
      if (val && typeof val === 'object' && val.predicted !== undefined) {
        return String(val.predicted)
      }
      return String(val)
    }
  }

  // Check deviation_details
  const deviations = predictionErrors.deviation_details
  if (deviations && typeof deviations === 'object') {
    const keys = Object.keys(deviations)
    const matchKey = keys.find(k => k.toLowerCase().includes(field.toLowerCase()))
    if (matchKey) {
      return String(deviations[matchKey])
    }
  }

  // Fall back to summary-level prediction info
  const parts = []
  if (predictionErrors.predicted_z_score !== undefined) {
    parts.push(`z-score: ${predictionErrors.predicted_z_score}`)
  }
  if (predictionErrors.summary_score !== undefined) {
    parts.push(`summary: ${predictionErrors.summary_score}`)
  }
  return parts.length > 0 ? parts.join(', ') : null
}

export function VerdictBoardTable() {
  const verdictBoard = useStore((s) => s.verdictBoard)
  const agents = useStore((s) => s.agents)

  // Collect all claims_checked from all three agent verdicts
  const allClaims = []
  for (const agentKey of ['risk', 'compliance', 'forensics']) {
    const verdict = agents[agentKey]?.verdict
    if (verdict?.claims_checked?.length) {
      allClaims.push(...verdict.claims_checked)
    }
  }

  const predictionErrors = verdictBoard?.prediction_errors || null

  const hasData = allClaims.length > 0

  return (
    <div className="bg-surface rounded-lg border border-border-muted p-3">
      <div className="text-[11px] font-semibold uppercase tracking-wider text-text-muted mb-2">
        VERDICT BOARD
      </div>

      {!hasData ? (
        <div className="text-text-muted text-[13px]">No verdict yet.</div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-[13px]">
            <thead>
              <tr className="text-[11px] font-semibold uppercase tracking-wider text-text-muted border-b border-border-muted pb-1">
                <th className="text-left py-1 px-2">Field</th>
                <th className="text-left py-1 px-2">Agent Claimed</th>
                <th className="text-left py-1 px-2">Found</th>
                <th className="text-left py-1 px-2">Match</th>
                <th className="text-left py-1 px-2">Severity</th>
              </tr>
            </thead>
            <tbody>
              {allClaims.map((claim, idx) => (
                <>
                  <tr
                    key={`claim-${idx}`}
                    className={`border-b border-border-muted/50 ${!claim.match ? 'bg-danger/5' : ''}`}
                  >
                    <td className="py-1.5 px-2 text-text-main">{claim.field}</td>
                    <td className="py-1.5 px-2 text-text-main font-mono text-[12px]">
                      {truncate(claim.agent_claimed)}
                    </td>
                    <td className="py-1.5 px-2 text-text-main font-mono text-[12px]">
                      {truncate(claim.independently_found)}
                    </td>
                    <td className="py-1.5 px-2">
                      {claim.match
                        ? <span className="material-symbols-outlined text-success text-[16px]">check_circle</span>
                        : <span className="material-symbols-outlined text-danger text-[16px]">cancel</span>
                      }
                    </td>
                    <td className="py-1.5 px-2">{renderSeverityBadge(claim.severity)}</td>
                  </tr>
                  {!claim.match && predictionErrors && (() => {
                    const expected = findExpectedValue(claim.field, predictionErrors)
                    return expected ? (
                      <tr key={`pred-${idx}`} className="border-b border-border-muted/30">
                        <td colSpan={5} className="py-1 px-2 pl-6 text-[11px] text-text-muted italic">
                          Expected: {expected}
                        </td>
                      </tr>
                    ) : null
                  })()}
                </>
              ))}
            </tbody>
          </table>

          {/* VB-level summary rows */}
          {verdictBoard && (
            <div className="mt-2 pt-2 border-t border-border-muted/50 space-y-1">
              {verdictBoard.behavioral_flags?.length > 0 && (
                <div className="flex gap-2 text-[12px]">
                  <span className="text-text-muted">Behavioral flags:</span>
                  <span className="text-text-main font-mono">{verdictBoard.behavioral_flags.join(', ')}</span>
                </div>
              )}
              {verdictBoard.confidence_z_score !== null && verdictBoard.confidence_z_score !== undefined && (
                <div className="flex gap-2 text-[12px]">
                  <span className="text-text-muted">Z-score:</span>
                  <span className="text-text-main font-mono">{Number(verdictBoard.confidence_z_score).toFixed(2)}</span>
                </div>
              )}
              {verdictBoard.step_sequence_deviation !== undefined && (
                <div className="flex gap-2 text-[12px]">
                  <span className="text-text-muted">Step deviation:</span>
                  <span className="text-text-main font-mono">{verdictBoard.step_sequence_deviation ? 'Yes' : 'No'}</span>
                </div>
              )}
              {verdictBoard.unable_to_verify?.length > 0 && (
                <div className="flex gap-2 text-[12px]">
                  <span className="text-text-muted">Unable to verify:</span>
                  <span className="text-text-main font-mono">{verdictBoard.unable_to_verify.join(', ')}</span>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
