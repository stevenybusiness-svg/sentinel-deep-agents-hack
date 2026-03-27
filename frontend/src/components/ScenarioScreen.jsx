export function ScenarioScreen({ scenario, onStart }) {
  // scenario = 'attack1' | 'attack2'
  const scenarios = {
    attack1: {
      title: 'Attack 1: Invoice Injection',
      subtitle: 'Hidden Text Manipulation',
      description: 'A payment agent processes an invoice containing hidden text — invisible to humans but readable by AI. The hidden text manipulates the agent into approving a fraudulent payment with inflated confidence.',
      details: [
        'The invoice contains rgb(254,254,254) text on white background',
        'The Payment Agent (Sonnet 4.6) genuinely reads and is manipulated by hidden instructions',
        "Sentinel's Forensics Agent independently scans the document to detect hidden content",
      ],
      buttonText: 'Launch Investigation',
      icon: 'description',
    },
    attack2: {
      title: 'Attack 2: Identity Spoofing',
      subtitle: 'KYC Pre-Clearance Forgery',
      description: 'A payment request claims pre-clearance by compliance — but the counterparty has no KYC record. The generated rule from Attack 1 now fires on this new attack type, proving the system learned.',
      details: [
        'Meridian Logistics is absent from the KYC ledger — an intentional gap',
        'The generated scoring function from Attack 1 detects shared behavioral patterns',
        "Rule evolution: the system autonomously refines the rule using both attacks' prediction errors",
      ],
      buttonText: 'Launch Investigation',
      icon: 'person_off',
      hasLearnedRule: true,
    },
  }

  const s = scenarios[scenario]

  return (
    <div className="h-screen bg-bg-dark flex items-center justify-center p-8">
      <div className="max-w-xl w-full space-y-6">
        <div className="text-center space-y-2">
          <span className="material-symbols-outlined text-[48px] text-warning">{s.icon}</span>
          <h1 className="text-2xl font-bold text-white">{s.title}</h1>
          <p className="text-warning text-sm font-semibold">{s.subtitle}</p>
        </div>

        <p className="text-text-main text-sm leading-relaxed text-center">{s.description}</p>

        <div className="bg-surface rounded-lg border border-border-muted p-4 space-y-2">
          <p className="text-[11px] uppercase text-text-muted font-semibold tracking-wider">What to Watch</p>
          <ul className="space-y-1.5">
            {s.details.map((d, i) => (
              <li key={i} className="text-[12px] text-text-main flex items-start gap-2">
                <span className="material-symbols-outlined text-[14px] text-accent mt-0.5">arrow_right</span>
                <span>{d}</span>
              </li>
            ))}
          </ul>
        </div>

        {s.hasLearnedRule && (
          <div className="bg-warning/10 border border-warning/30 rounded-lg px-4 py-3 text-center">
            <p className="text-[12px] text-warning font-semibold">
              <span className="material-symbols-outlined text-[14px] align-middle mr-1">auto_awesome</span>
              Generated Rule from Attack 1 is now active in the Safety Gate
            </p>
          </div>
        )}

        <div className="text-center">
          <button
            onClick={onStart}
            className="px-6 py-2.5 rounded-lg bg-danger text-white font-semibold text-sm hover:bg-danger/90 transition-colors"
          >
            {s.buttonText}
          </button>
        </div>
      </div>
    </div>
  )
}
