import { useState, useEffect } from 'react'

export function LandingPage({ onEnter }) {
  // Animated stats that tick up on mount
  const [latency, setLatency] = useState(0)
  const [nodes, setNodes] = useState(0)

  useEffect(() => {
    const t1 = setTimeout(() => setLatency(0.04), 800)
    const t2 = setTimeout(() => setNodes(14892), 1200)
    return () => { clearTimeout(t1); clearTimeout(t2) }
  }, [])

  return (
    <div className="min-h-screen bg-bg-dark text-white font-display overflow-hidden relative">
      {/* Subtle grid background */}
      <div className="absolute inset-0 opacity-[0.03]" style={{
        backgroundImage: 'linear-gradient(rgba(255,255,255,.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.1) 1px, transparent 1px)',
        backgroundSize: '40px 40px',
      }} />

      {/* Radial glow behind hero */}
      <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[900px] h-[600px] rounded-full opacity-20 pointer-events-none"
        style={{ background: 'radial-gradient(circle, rgba(0,212,170,0.12) 0%, transparent 70%)' }} />

      {/* Nav */}
      <nav className="relative z-10 flex items-center justify-between px-8 py-4 border-b border-white/5">
        <div className="flex items-center gap-8">
          <span className="text-lg font-bold tracking-wider text-cyber">SENTINEL</span>
          <div className="hidden md:flex items-center gap-6 text-[10px] text-text-muted uppercase tracking-[0.15em]">
            <span className="hover:text-white transition-colors cursor-default">Missions</span>
            <span className="hover:text-white transition-colors cursor-default">Intelligence</span>
            <span className="hover:text-white transition-colors cursor-default">Network</span>
            <span className="hover:text-white transition-colors cursor-default">Vault</span>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <div className="relative z-10 max-w-7xl mx-auto px-8 pt-16 pb-12">
        <div className="flex items-start justify-between">
          {/* Left content */}
          <div className="max-w-xl">
            {/* Protocol badge */}
            <div className="inline-block px-3 py-1 rounded-full border border-cyber/30 bg-cyber/10 text-cyber text-[10px] uppercase tracking-[0.2em] font-semibold mb-6">
              System Protocol V4.0.2
            </div>

            <h1 className="text-6xl md:text-7xl font-bold tracking-tight mb-4 leading-none">
              Sentinel<span className="text-cyber">.</span>
            </h1>

            {/* AWS badge */}
            <div className="inline-flex items-center gap-2.5 px-3 py-1.5 rounded-md bg-surface border border-border-muted text-xs text-text-muted mb-6">
              <img src="https://upload.wikimedia.org/wikipedia/commons/9/93/Amazon_Web_Services_Logo.svg" alt="AWS" className="h-4 w-auto brightness-0 invert" />
              <span className="text-border-muted">|</span>
              <span className="uppercase tracking-[0.15em] text-[10px]">Powered by AWS</span>
            </div>

            <h2 className="text-3xl md:text-4xl font-semibold leading-tight mb-3 text-white">
              Autonomous Security for<br />Agentic AI
            </h2>

            <p className="text-text-muted text-[11px] uppercase tracking-[0.25em] mb-10">
              Self-Improving. Continuously Learning. Always Adapting.
            </p>

            {/* Single CTA */}
            <button
              onClick={onEnter}
              className="group px-8 py-4 rounded-lg bg-cyber text-bg-dark font-bold text-sm uppercase tracking-wider hover:shadow-lg hover:shadow-cyber/25 transition-all duration-300"
            >
              Enter Sentinel Console
              <span className="inline-block ml-2 group-hover:translate-x-1 transition-transform">&rarr;</span>
            </button>

            {/* Feature grid */}
            <div className="grid grid-cols-2 gap-x-8 gap-y-5 mt-14">
              {[
                { icon: 'shield', title: 'Autonomous Defense', desc: 'Real-time threat neutralizers.' },
                { icon: 'fingerprint', title: 'Full Traceability', desc: 'Immutable agent audit logs.' },
                { icon: 'hub', title: 'Agent Graph Control', desc: 'Mapping interconnected logic.' },
                { icon: 'auto_awesome', title: 'Self-Improving AI', desc: 'Evolving defense protocols.' },
              ].map((f, i) => (
                <div key={i} className="flex items-start gap-3">
                  <div className="w-9 h-9 rounded-lg bg-cyber/10 border border-cyber/20 flex items-center justify-center shrink-0">
                    <span className="material-symbols-outlined text-cyber text-[18px]">{f.icon}</span>
                  </div>
                  <div>
                    <p className="text-[11px] font-bold uppercase tracking-wider text-white">{f.title}</p>
                    <p className="text-[10px] text-text-muted mt-0.5">{f.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Right: Floating UI cards */}
          <div className="hidden lg:block relative w-[480px] h-[480px] mt-8">
            {/* Agent card */}
            <div className="absolute top-0 left-8 float-card" style={{ animationDelay: '0s' }}>
              <div className="bg-surface/80 backdrop-blur border border-border-muted rounded-xl px-4 py-3 flex items-center gap-3 shadow-xl">
                <div className="w-10 h-10 rounded-lg bg-cyber/15 border border-cyber/25 flex items-center justify-center">
                  <span className="material-symbols-outlined text-cyber text-[20px]">smart_toy</span>
                </div>
                <div>
                  <p className="text-[10px] text-text-muted uppercase tracking-wider">Agent</p>
                  <p className="text-xs font-semibold text-white">AGENT_ALPHA</p>
                </div>
              </div>
            </div>

            {/* Activity Log card */}
            <div className="absolute top-4 right-0 float-card" style={{ animationDelay: '0.5s' }}>
              <div className="bg-surface/80 backdrop-blur border border-border-muted rounded-xl p-4 shadow-xl w-52">
                <p className="text-[10px] text-text-muted uppercase tracking-wider mb-3">Activity Log</p>
                <div className="flex items-end gap-1 h-12">
                  {[40, 65, 35, 80, 55, 70, 45, 90, 60, 75].map((h, i) => (
                    <div key={i} className="flex-1 rounded-sm bg-cyber/20 transition-all" style={{ height: `${h}%` }}>
                      <div className="w-full rounded-sm bg-cyber/50" style={{ height: `${Math.min(h + 10, 100)}%` }} />
                    </div>
                  ))}
                </div>
                <div className="flex items-center justify-between mt-2">
                  <span className="text-[8px] text-text-muted font-mono">00:00</span>
                  <span className="text-[8px] text-text-muted font-mono">23:59</span>
                </div>
              </div>
            </div>

            {/* Connection lines (decorative SVG) */}
            <svg className="absolute inset-0 w-full h-full pointer-events-none" style={{ opacity: 0.15 }}>
              <line x1="140" y1="70" x2="280" y2="160" stroke="#00d4aa" strokeWidth="1" strokeDasharray="4,4" />
              <line x1="280" y1="160" x2="350" y2="100" stroke="#00d4aa" strokeWidth="1" strokeDasharray="4,4" />
              <line x1="280" y1="160" x2="200" y2="290" stroke="#00d4aa" strokeWidth="1" strokeDasharray="4,4" />
            </svg>

            {/* Threat indicator */}
            <div className="absolute top-[140px] right-[60px] float-card" style={{ animationDelay: '1s' }}>
              <div className="w-16 h-16 rounded-xl bg-surface/80 backdrop-blur border border-warning/30 flex items-center justify-center shadow-xl">
                <div className="w-10 h-10 rounded-lg bg-warning/15 flex items-center justify-center">
                  <span className="material-symbols-outlined text-warning text-[22px]">warning</span>
                </div>
              </div>
              <p className="text-[8px] text-text-muted text-center mt-1 font-mono uppercase tracking-wider">Threat_D</p>
            </div>

            {/* Scan target circle */}
            <div className="absolute top-[180px] left-[80px] float-card" style={{ animationDelay: '1.5s' }}>
              <div className="w-28 h-28 rounded-2xl bg-cyber/5 border border-cyber/20 flex items-center justify-center relative overflow-hidden">
                <div className="w-16 h-16 rounded-full border-2 border-cyber/40 flex items-center justify-center">
                  <div className="w-8 h-8 rounded-full bg-cyber/20 flex items-center justify-center">
                    <span className="material-symbols-outlined text-cyber text-[18px]">gps_fixed</span>
                  </div>
                </div>
                {/* Scan line */}
                <div className="absolute inset-0 scan-line-overlay" />
              </div>
            </div>

            {/* Real-time intercept card */}
            <div className="absolute bottom-[40px] left-[20px] float-card" style={{ animationDelay: '2s' }}>
              <div className="bg-surface/80 backdrop-blur border border-border-muted rounded-xl p-4 shadow-xl w-64">
                <div className="flex items-center gap-2 mb-3">
                  <span className="material-symbols-outlined text-warning text-[14px]">bolt</span>
                  <p className="text-[10px] font-bold uppercase tracking-wider text-white">Real-Time Intercept</p>
                </div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[9px] text-text-muted font-mono">VECTOR: SQL_INJECT_PT</span>
                  <span className="text-[9px] font-bold text-danger px-1.5 py-0.5 bg-danger/15 rounded">BLOCKED</span>
                </div>
                {/* Fake bars */}
                <div className="flex gap-1 mb-2">
                  {[1,1,1,0,1,1,0,1].map((active, i) => (
                    <div key={i} className={`h-4 flex-1 rounded-sm ${active ? 'bg-warning/40' : 'bg-border-muted/40'}`} />
                  ))}
                </div>
                <p className="text-[8px] text-text-muted font-mono">
                  AUTONOMOUS AGENT RE-ROUTING TRAFFIC THROUGH AWS-US-EAST-1...
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Stats line (bottom-right of hero) */}
        <div className="flex justify-end mt-8">
          <div className="text-right font-mono text-[10px] text-text-muted space-y-0.5">
            <p>LATENCY: <span className="text-cyber">{latency.toFixed(2)}ms</span></p>
            <p>NODES_ACTIVE: <span className="text-cyber">{nodes.toLocaleString()}</span></p>
            <p>THREAT_LEVEL: <span className="text-cyber">STABLE</span></p>
          </div>
        </div>
      </div>

      {/* Bottom info cards */}
      <div className="relative z-10 max-w-7xl mx-auto px-8 pb-12">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-surface/60 border border-border-muted rounded-xl p-5">
            <div className="flex items-center gap-2 mb-2">
              <span className="material-symbols-outlined text-cyber text-[18px]">cloud</span>
              <p className="text-[11px] font-bold uppercase tracking-wider text-white">AWS Infrastructure</p>
            </div>
            <div className="flex items-center gap-2 text-[9px] text-text-muted font-mono uppercase tracking-wider">
              <span className="w-1.5 h-1.5 rounded-full bg-success" />
              US-EAST-1 | OPERATIONAL
            </div>
          </div>

          <div className="bg-surface/60 border border-border-muted rounded-xl p-5">
            <div className="flex items-center gap-2 mb-2">
              <span className="material-symbols-outlined text-cyber text-[18px]">psychology</span>
              <p className="text-[11px] font-bold uppercase tracking-wider text-white">Agentic Intelligence</p>
            </div>
            <div className="flex items-center gap-2 text-[9px] text-text-muted font-mono uppercase tracking-wider">
              <span className="w-1.5 h-1.5 rounded-full bg-cyber" />
              LLM SECURITY ACTIVE
            </div>
          </div>

          <div className="bg-surface/60 border border-border-muted rounded-xl p-5">
            <div className="flex items-center gap-2 mb-3">
              <span className="material-symbols-outlined text-warning text-[18px]">trending_up</span>
              <p className="text-[11px] font-bold uppercase tracking-wider text-white">Learning Loop</p>
            </div>
            <div className="flex items-center gap-3">
              <div className="flex-1 h-1.5 rounded-full bg-border-muted overflow-hidden">
                <div className="h-full rounded-full bg-cyber transition-all duration-1000" style={{ width: '75%' }} />
              </div>
              <span className="text-[10px] font-bold text-cyber shrink-0">75% SYNC</span>
            </div>
          </div>
        </div>
      </div>

      {/* Footer */}
      <footer className="relative z-10 border-t border-white/5 py-6">
        <div className="flex items-center justify-center gap-8 text-[10px] text-text-muted uppercase tracking-[0.15em]">
          <span className="hover:text-white transition-colors cursor-default">Privacy Protocol</span>
          <span className="hover:text-white transition-colors cursor-default">Service Terms</span>
          <span className="hover:text-white transition-colors cursor-default">AWS Node Status</span>
        </div>
      </footer>
    </div>
  )
}
