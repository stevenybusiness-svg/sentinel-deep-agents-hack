import { useStore } from '../store'

export function AerospikeLatency() {
  const latency = useStore((s) => s.aerospikeLatencyMs)
  const decisionLog = useStore((s) => s.decisionLog)

  const dotColor = latency === null ? 'bg-text-muted' :
    latency < 5 ? 'bg-success' :
    latency < 20 ? 'bg-warning' : 'bg-danger'

  return (
    <div className="bg-surface rounded-lg border border-border-muted p-3">
      {/* Aerospike latency metric */}
      <div className="flex items-center gap-2 text-[12px] font-mono text-text-muted">
        <span className={`inline-block w-1.5 h-1.5 rounded-full ${dotColor}`} />
        <span>Aerospike: {latency !== null ? `${latency.toFixed(1)}ms` : '--'}</span>
      </div>

      {/* Decision log sub-section (DASH-08) */}
      {decisionLog.length > 0 && (
        <div className="mt-2 pt-2 border-t border-border-muted/50">
          <div className="text-[11px] font-semibold uppercase tracking-wider text-text-muted mb-1">Decision Log</div>
          <div className="max-h-[80px] overflow-y-auto space-y-1">
            {decisionLog.map((entry, i) => (
              <div key={i} className="card-enter flex items-start gap-2 text-[11px]">
                <span className="font-mono text-text-muted whitespace-nowrap">
                  {new Date(entry.timestamp).toLocaleTimeString()}
                </span>
                <span className={`font-semibold ${
                  entry.gate_decision === 'NO-GO' ? 'text-danger' :
                  entry.gate_decision === 'GO' ? 'text-success' : 'text-warning'
                }`}>
                  {entry.gate_decision}
                </span>
                <span className="text-text-main truncate">{entry.attribution}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
