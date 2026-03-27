import { useState, useEffect, useCallback } from 'react'
import { useStore } from '../store'

function NarrativeCard({ label, contentKey, polishingKey, emptyState, onExpand }) {
  const content = useStore((s) => s.narrativeData[contentKey])
  const polishing = useStore((s) => polishingKey ? s.narrativePolishing[polishingKey] : false)

  return (
    <div
      className={`bg-surface rounded-lg border border-border-muted p-4 flex flex-col gap-2 h-36 transition-all duration-150 ${content ? 'cursor-pointer hover:border-accent/60 hover:bg-surface/80' : ''}`}
      onClick={() => content && onExpand(contentKey, label)}
    >
      {/* Card label */}
      <div className="text-[11px] font-semibold uppercase tracking-wider text-text-muted shrink-0 flex items-center justify-between">
        <span>{label}</span>
        <div className="flex items-center gap-2">
          {polishing && (
            <span className="flex items-center gap-1 text-[11px] text-text-muted font-normal normal-case tracking-normal">
              <span className="pulse-dot inline-block w-1.5 h-1.5 rounded-full bg-primary" />
              Polishing...
            </span>
          )}
          {content && (
            <span className="material-symbols-outlined text-[14px] text-text-muted">open_in_full</span>
          )}
        </div>
      </div>
      {/* Card body */}
      <div className="text-[13px] text-text-main leading-relaxed overflow-y-auto flex-1">
        {content || <span className="text-text-muted">{emptyState}</span>}
      </div>
    </div>
  )
}

function ExpandedOverlay({ label, contentKey, onClose }) {
  const content = useStore((s) => s.narrativeData[contentKey])

  const handleKeyDown = useCallback((e) => {
    if (e.key === 'Escape') onClose()
  }, [onClose])

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [handleKeyDown])

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="bg-surface border border-border-muted rounded-xl p-6 max-w-2xl w-full mx-4 max-h-[80vh] flex flex-col shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between mb-4 shrink-0">
          <span className="text-[12px] font-semibold uppercase tracking-wider text-text-muted">{label}</span>
          <button
            onClick={onClose}
            className="text-text-muted hover:text-white transition-colors"
          >
            <span className="material-symbols-outlined text-[20px]">close</span>
          </button>
        </div>
        {/* Content */}
        <div className="text-[15px] text-text-main leading-relaxed overflow-y-auto flex-1">
          {content || <span className="text-text-muted">No content available.</span>}
        </div>
      </div>
    </div>
  )
}

export function QualitativeAnalysisPanel() {
  const [expanded, setExpanded] = useState(null) // { key, label } or null

  const handleExpand = (key, label) => setExpanded({ key, label })
  const handleClose = () => setExpanded(null)

  return (
    <>
      <div className="grid grid-cols-4 gap-3">
        <NarrativeCard
          label="Attack Details"
          contentKey="attackNarrative"
          polishingKey="attackNarrative"
          emptyState="Run an attack to see the narrative."
          onExpand={handleExpand}
        />
        <NarrativeCard
          label="Agent Reasoning"
          contentKey="agentReasoning"
          polishingKey="agentReasoning"
          emptyState="Awaiting investigation results."
          onExpand={handleExpand}
        />
        <NarrativeCard
          label="Prediction vs. Actual"
          contentKey="predictionSummary"
          polishingKey="predictionSummary"
          emptyState="Prediction data will appear after investigation."
          onExpand={handleExpand}
        />
        <NarrativeCard
          label="Self-Improvement Arc"
          contentKey="selfImprovementArc"
          emptyState="Rule generation data will appear after gate evaluation."
          onExpand={handleExpand}
        />
      </div>

      {expanded && (
        <ExpandedOverlay
          label={expanded.label}
          contentKey={expanded.key}
          onClose={handleClose}
        />
      )}
    </>
  )
}
