import { useStore } from '../store'

export function ForensicScanPanel() {
  const agents = useStore((s) => s.agents)

  // Determine if forensic scan has document-related claims
  // Phase 1 (invoice attack) has document/invoice/hidden fields in claims_checked
  // Phase 2 (identity spoofing) forensics returns empty or non-document claims
  const hasDocuments = agents.forensics?.verdict?.claims_checked?.some(
    (c) =>
      c.field?.toLowerCase().includes('document') ||
      c.field?.toLowerCase().includes('hidden') ||
      c.field?.toLowerCase().includes('invoice')
  )

  return (
    <div className="bg-surface rounded-lg border border-border-muted p-3">
      <div className="text-[11px] font-semibold uppercase tracking-wider text-text-muted mb-2">
        FORENSIC SCAN
      </div>

      <div className="flex gap-3">
        {/* Left pane: Agent view */}
        <div className="flex-1">
          <div className="text-[11px] uppercase text-text-muted mb-1">Invoice (Agent View)</div>
          <div className="bg-surface rounded border border-border-muted h-40 flex items-center justify-center overflow-hidden">
            {hasDocuments
              ? (
                <img
                  src="/invoice_clean.png"
                  alt="Clean invoice"
                  className="object-contain h-full w-full"
                />
              )
              : (
                <span className="text-text-muted text-[13px]">No documents attached.</span>
              )}
          </div>
        </div>

        {/* Right pane: Forensic scan */}
        <div className="flex-1">
          <div className="text-[11px] uppercase text-text-muted mb-1">Forensic Scan</div>
          <div className="bg-surface rounded border border-border-muted h-40 flex items-center justify-center overflow-hidden relative">
            {hasDocuments
              ? (
                <>
                  <img
                    src="/invoice_forensic.png"
                    alt="Forensic scan"
                    className="object-contain h-full w-full"
                  />
                  {/* Red highlight overlay for hidden text region */}
                  <div className="absolute bottom-2 left-2 right-2 h-6 bg-danger/40 rounded border border-danger/60 flex items-center justify-center">
                    <span className="text-[10px] text-white font-semibold">Hidden text detected</span>
                  </div>
                </>
              )
              : (
                <span className="text-text-muted text-[13px]">No documents attached.</span>
              )}
          </div>
        </div>
      </div>
    </div>
  )
}
