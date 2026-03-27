import { useState, useEffect } from 'react'
import { useStore } from '../store'

const apiBase = import.meta.env.VITE_API_URL || ''

export function GateDecisionPanel() {
  const gateDecision = useStore((s) => s.gateDecision)
  const currentEpisodeId = useStore((s) => s.currentEpisodeId)
  const trustScore = useStore((s) => s.trustScore)
  const investigationStatus = useStore((s) => s.investigationStatus)

  const [confirming, setConfirming] = useState(false)

  // Reset confirming state when a new investigation starts
  useEffect(() => {
    if (investigationStatus === 'running') {
      setConfirming(false)
    }
  }, [investigationStatus])

  async function handleConfirm() {
    if (!currentEpisodeId || confirming) return
    setConfirming(true)
    try {
      await fetch(`${apiBase}/api/confirm`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          episode_id: currentEpisodeId,
          attack_type: 'confirmed',
        }),
      })
    } catch (err) {
      console.error('confirm request failed', err)
    }
  }

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
        <p className="text-[12px] text-text-main">{attribution}</p>
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

      {/* Confirm button — only visible on NO-GO */}
      {decision === 'NO-GO' && (
        <div className="pt-1">
          <button
            className="bg-accent text-white font-semibold text-sm px-4 py-2 rounded hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed"
            onClick={handleConfirm}
            disabled={confirming}
          >
            {confirming ? (
              <span className="text-text-muted">Generating rule...</span>
            ) : (
              'Confirm Attack \u2014 Learn \u25b6'
            )}
          </button>
        </div>
      )}
    </div>
  )
}
