import { useStore } from '../store'

function NarrativeCard({ label, contentKey, polishingKey, emptyState }) {
  const content = useStore((s) => s.narrativeData[contentKey])
  const polishing = useStore((s) => polishingKey ? s.narrativePolishing[polishingKey] : false)

  return (
    <div className="bg-surface rounded-lg border border-border-muted p-4 flex flex-col gap-2 h-36">
      {/* Card label */}
      <div className="text-[11px] font-semibold uppercase tracking-wider text-text-muted shrink-0 flex items-center justify-between">
        <span>{label}</span>
        {polishing && (
          <span className="flex items-center gap-1 text-[11px] text-text-muted font-normal normal-case tracking-normal">
            <span className="pulse-dot inline-block w-1.5 h-1.5 rounded-full bg-primary" />
            Polishing...
          </span>
        )}
      </div>
      {/* Card body */}
      <div className="text-[13px] text-text-main leading-relaxed overflow-y-auto flex-1">
        {content || <span className="text-text-muted">{emptyState}</span>}
      </div>
    </div>
  )
}

export function QualitativeAnalysisPanel() {
  return (
    <div className="grid grid-cols-4 gap-3">
      <NarrativeCard
        label="Attack Narrative"
        contentKey="attackNarrative"
        polishingKey="attackNarrative"
        emptyState="Run an attack to see the narrative."
      />
      <NarrativeCard
        label="Agent Reasoning"
        contentKey="agentReasoning"
        polishingKey="agentReasoning"
        emptyState="Awaiting investigation results."
      />
      <NarrativeCard
        label="Prediction vs. Actual"
        contentKey="predictionSummary"
        polishingKey="predictionSummary"
        emptyState="Prediction data will appear after investigation."
      />
      <NarrativeCard
        label="Self-Improvement Arc"
        contentKey="selfImprovementArc"
        polishingKey={null}
        emptyState="No rules generated yet. Confirm an attack to trigger learning."
      />
    </div>
  )
}
