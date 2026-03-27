import { useState, useEffect } from 'react'

export function AuthenticatingScreen() {
  const [progress, setProgress] = useState(0)
  const [statusText, setStatusText] = useState('Establishing secure connection...')

  useEffect(() => {
    const steps = [
      { at: 300, text: 'Verifying credentials...' },
      { at: 1000, text: 'Initializing threat detection systems...' },
      { at: 1800, text: 'Loading security protocols...' },
      { at: 2400, text: 'Access granted.' },
    ]

    const timers = steps.map((step) =>
      setTimeout(() => setStatusText(step.text), step.at)
    )

    // Smooth progress bar
    const interval = setInterval(() => {
      setProgress((p) => Math.min(p + 1.2, 100))
    }, 30)

    return () => {
      timers.forEach(clearTimeout)
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

      <div className="relative z-10 flex flex-col items-center gap-6">
        {/* Spinning shield icon */}
        <div className="w-16 h-16 rounded-2xl bg-cyber/10 border border-cyber/20 flex items-center justify-center auth-spin">
          <span className="material-symbols-outlined text-cyber text-[32px]">security</span>
        </div>

        <div className="text-center space-y-2">
          <h1 className="text-2xl font-bold text-white tracking-tight">Authenticating</h1>
          <p className="text-sm text-text-muted h-5 transition-all duration-300">{statusText}</p>
        </div>

        {/* Progress bar */}
        <div className="w-64 h-1 rounded-full bg-border-muted overflow-hidden">
          <div
            className="h-full rounded-full bg-cyber transition-all duration-75"
            style={{ width: `${progress}%` }}
          />
        </div>

        <p className="text-text-muted/40 text-[10px]">Sentinel Security Console</p>
      </div>
    </div>
  )
}
