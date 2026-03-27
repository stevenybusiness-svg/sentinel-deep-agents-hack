import { useState } from 'react'
import { useStore } from '../store'

export function VoicePanel() {
  const currentEpisodeId = useStore((s) => s.currentEpisodeId)
  const investigationStatus = useStore((s) => s.investigationStatus)
  const gateDecision = useStore((s) => s.gateDecision)
  const voiceCallStatus = useStore((s) => s.voiceCallStatus)
  const setVoiceCallId = useStore((s) => s.setVoiceCallId)
  const setVoiceCallStatus = useStore((s) => s.setVoiceCallStatus)

  const [publicHost, setPublicHost] = useState('')

  const isReady =
    currentEpisodeId !== null &&
    investigationStatus === 'complete' &&
    voiceCallStatus !== 'calling' &&
    publicHost.trim() !== ''

  async function handleStartCall(e) {
    e.preventDefault()
    if (!isReady) return
    setVoiceCallStatus('calling')
    try {
      const res = await fetch('/api/bland-call', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          episode_id: currentEpisodeId,
          public_host: publicHost,
        }),
      })
      if (!res.ok) {
        setVoiceCallStatus('error')
        return
      }
      const data = await res.json()
      setVoiceCallId(data.call_id)
      setVoiceCallStatus('active')
    } catch (err) {
      console.error('bland-call failed', err)
      setVoiceCallStatus('error')
    }
  }

  const inputClass =
    'w-full bg-bg-dark border border-border-muted rounded px-3 py-1.5 text-[13px] text-text-main ' +
    'placeholder:text-text-muted focus:outline-none focus:border-accent transition-colors'

  const labelClass = 'block text-[11px] uppercase text-text-muted mb-1'

  let statusEl = null
  if (voiceCallStatus === 'calling') {
    statusEl = (
      <span className="text-[12px] text-warning font-mono">Connecting...</span>
    )
  } else if (voiceCallStatus === 'active') {
    statusEl = (
      <span className="text-[12px] text-success font-mono">Call active</span>
    )
  } else if (voiceCallStatus === 'error') {
    statusEl = (
      <span className="text-[12px] text-danger font-mono">
        Call failed — use text above
      </span>
    )
  }

  return (
    <div className="bg-surface rounded-lg border border-border-muted p-4 space-y-3">
      {/* Panel header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <span className="material-symbols-outlined text-[16px] text-accent">mic</span>
          <span className="text-[13px] font-semibold text-text-main uppercase tracking-wider">
            Voice Q&amp;A
          </span>
        </div>
        {statusEl}
      </div>

      {/* Text fallback — voice context (VOICE-04) */}
      {gateDecision ? (
        <div className="rounded bg-bg-dark border border-border-muted px-3 py-2 space-y-1">
          <p className="text-[11px] uppercase text-text-muted font-semibold">
            Voice Context (text fallback)
          </p>
          <p className="text-[12px] text-text-main font-mono">
            Decision:{' '}
            <span
              className={
                gateDecision.decision === 'NO-GO'
                  ? 'text-danger'
                  : gateDecision.decision === 'ESCALATE'
                  ? 'text-warning'
                  : 'text-success'
              }
            >
              {gateDecision.decision}
            </span>{' '}
            &middot; Score:{' '}
            <span className="text-text-main">
              {(gateDecision.composite_score ?? 0).toFixed(2)}
            </span>
          </p>
          {gateDecision.attribution && (
            <p className="text-[12px] text-text-muted leading-snug">
              {gateDecision.attribution}
            </p>
          )}
        </div>
      ) : (
        <div className="rounded bg-bg-dark border border-border-muted px-3 py-2">
          <p className="text-[12px] text-text-muted italic">
            Run an investigation to see voice context.
          </p>
        </div>
      )}

      {/* Inline call form */}
      <form onSubmit={handleStartCall} className="space-y-2">
        <div>
          <label className={labelClass}>Public Host URL</label>
          <input
            type="text"
            className={inputClass}
            placeholder="https://your-ngrok-url.ngrok.io"
            value={publicHost}
            onChange={(e) => setPublicHost(e.target.value)}
          />
        </div>
        <button
          type="submit"
          disabled={!isReady}
          className="w-full bg-accent text-white font-semibold text-sm px-4 py-2 rounded hover:opacity-90 transition-opacity disabled:opacity-40 disabled:cursor-not-allowed"
        >
          Start Voice Q&amp;A
        </button>
      </form>
    </div>
  )
}
