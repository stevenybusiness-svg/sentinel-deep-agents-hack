import { useState, useEffect } from 'react'

export function AuthenticatingScreen() {
  const [progress, setProgress] = useState(0)
  const [statusText, setStatusText] = useState('Establishing secure connection...')
  const [checks, setChecks] = useState([])

  useEffect(() => {
    const steps = [
      { at: 400, text: 'Verifying credentials via Auth0...' },
      { at: 1200, text: 'Validating IAM role permissions...' },
      { at: 2200, text: 'Checking security clearance level...' },
      { at: 3200, text: 'Initializing threat detection systems...' },
      { at: 4200, text: 'Loading security protocols...' },
      { at: 5200, text: 'Access granted.' },
    ]

    const checkItems = [
      { at: 800, label: 'Auth0 token verified', icon: 'verified_user' },
      { at: 1600, label: 'IAM role: SecurityOperator', icon: 'admin_panel_settings' },
      { at: 2600, label: 'MFA status: Confirmed', icon: 'security' },
      { at: 3600, label: 'Session scope: read/execute/escalate', icon: 'policy' },
      { at: 4600, label: 'Sentinel pipeline: Online', icon: 'hub' },
    ]

    const timers = steps.map((step) =>
      setTimeout(() => setStatusText(step.text), step.at)
    )

    const checkTimers = checkItems.map((item) =>
      setTimeout(() => setChecks((prev) => [...prev, item]), item.at)
    )

    // Smooth progress bar
    const interval = setInterval(() => {
      setProgress((p) => Math.min(p + 0.55, 100))
    }, 30)

    return () => {
      timers.forEach(clearTimeout)
      checkTimers.forEach(clearTimeout)
      clearInterval(interval)
    }
  }, [])

  return (
    <div className="h-screen bg-bg-dark flex items-center justify-center relative overflow-hidden">
      {/* Grid background */}
      <div className="absolute inset-0 opacity-[0.03]" style={{
        backgroundImage: 'linear-gradient(rgba(255,255,255,.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.1) 1px, transparent 1px)',
        backgroundSize: '40px 40px',
      }} />

      {/* Radial glow */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] rounded-full opacity-25 pointer-events-none"
        style={{ background: 'radial-gradient(circle, rgba(0,212,170,0.15) 0%, transparent 70%)' }} />

      <div className="relative z-10 flex flex-col items-center gap-5">
        {/* Spinning shield icon */}
        <div className="w-16 h-16 rounded-2xl bg-cyber/10 border border-cyber/20 flex items-center justify-center auth-spin">
          <span className="material-symbols-outlined text-cyber text-[32px]">security</span>
        </div>

        <div className="text-center space-y-2">
          <h1 className="text-2xl font-bold text-white tracking-tight">Authenticating</h1>
          {/* Auth0 badge */}
          <div className="flex items-center justify-center gap-2 mt-1">
            <svg width="20" height="20" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M44.08 7.03L32 0 19.92 7.03 27.9 30.53l-19.84 6.44 7.88 24.27L32 47.92l16.06 13.32 7.88-24.27-19.84-6.44L44.08 7.03z" fill="#8b949e"/>
            </svg>
            <span className="text-[11px] text-text-muted font-semibold tracking-wide">Powered by Auth0</span>
          </div>
          <p className="text-sm text-text-muted h-5 transition-all duration-300">{statusText}</p>
        </div>

        {/* Progress bar */}
        <div className="w-72 h-1.5 rounded-full bg-border-muted overflow-hidden">
          <div
            className="h-full rounded-full bg-cyber transition-all duration-75"
            style={{ width: `${progress}%` }}
          />
        </div>

        {/* Security check items — appear one by one */}
        <div className="w-80 space-y-1.5 mt-2">
          {checks.map((check, i) => (
            <div
              key={i}
              className="flex items-center gap-2.5 px-3 py-1.5 rounded-lg bg-surface/60 border border-border-muted/50 card-enter"
            >
              <span className="material-symbols-outlined text-cyber text-[16px]">{check.icon}</span>
              <span className="text-[11px] text-text-main font-mono">{check.label}</span>
              <span className="material-symbols-outlined text-success text-[14px] ml-auto">check_circle</span>
            </div>
          ))}
        </div>

        <p className="text-text-muted/40 text-[10px] mt-2">Sentinel Security Console</p>
      </div>
    </div>
  )
}
