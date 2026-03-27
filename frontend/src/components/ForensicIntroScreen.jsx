export function ForensicIntroScreen({ onAttack1, onAttack2 }) {
  return (
    <div className="h-screen bg-bg-dark text-text-main font-display flex flex-col items-center justify-center p-8">
      {/* Title */}
      <h1 className="text-2xl font-bold text-white mb-2 tracking-tight">Sentinel</h1>
      <p className="text-sm text-text-muted mb-8 max-w-xl text-center">
        Runtime security for autonomous AI agents. The payment agent below was given an invoice
        with hidden injection text — invisible to humans, but it manipulates the AI into approving
        a fraudulent payment. Sentinel catches it.
      </p>

      {/* Side-by-side forensic comparison */}
      <div className="flex gap-6 mb-8 max-w-4xl w-full">
        {/* Clean invoice */}
        <div className="flex-1">
          <div className="text-[11px] uppercase text-text-muted mb-2 font-semibold tracking-wider">
            What the Agent Sees
          </div>
          <div className="bg-surface rounded-lg border border-border-muted overflow-hidden">
            <img
              src="/invoice_clean.png"
              alt="Clean invoice — what the AI agent sees"
              className="w-full h-auto"
            />
          </div>
          <p className="text-[11px] text-text-muted mt-2 text-center">
            A normal-looking invoice. Nothing suspicious.
          </p>
        </div>

        {/* Forensic scan */}
        <div className="flex-1">
          <div className="text-[11px] uppercase text-danger mb-2 font-semibold tracking-wider">
            What Sentinel Finds
          </div>
          <div className="bg-surface rounded-lg border border-danger/40 overflow-hidden">
            <img
              src="/invoice_forensic.png"
              alt="Forensic scan — hidden injection text revealed"
              className="w-full h-auto"
            />
          </div>
          <div className="mt-2 flex items-center justify-center gap-1.5">
            <span className="text-danger text-[12px]">&#9888;</span>
            <span className="text-[11px] text-danger font-semibold">
              Hidden injection text detected at bottom of invoice
            </span>
          </div>
        </div>
      </div>

      {/* Attack buttons */}
      <div className="flex gap-3">
        <button
          onClick={onAttack1}
          className="bg-accent text-white font-semibold text-sm px-6 py-2.5 rounded hover:opacity-90 transition-opacity"
        >
          Attack 1: Invoice Injection
        </button>
        <button
          onClick={onAttack2}
          className="bg-surface text-text-main font-semibold text-sm px-6 py-2.5 rounded border border-border-muted hover:border-accent hover:text-white transition-colors"
        >
          Attack 2: Identity Spoofing
        </button>
      </div>

      <p className="text-[10px] text-text-muted mt-4">
        Click an attack to launch the investigation dashboard
      </p>
    </div>
  )
}
