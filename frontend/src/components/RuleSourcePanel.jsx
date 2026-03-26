import { useRef, useEffect } from 'react'
import { useStore } from '../store'

function relativeTime(iso) {
  if (!iso) return 'just now'
  const seconds = Math.floor((Date.now() - new Date(iso).getTime()) / 1000)
  if (seconds < 5) return 'just now'
  if (seconds < 60) return `${seconds}s ago`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`
  return `${Math.floor(seconds / 3600)}h ago`
}

function highlightPython(source) {
  if (!source) return ''
  // Order matters -- keywords first, then strings, then numbers, then comments
  return source
    // Multi-line strings/docstrings
    .replace(/("""[\s\S]*?"""|'''[\s\S]*?''')/g, '<span class="text-success">$1</span>')
    // Single-line strings
    .replace(/(["'])(?:(?=(\\?))\2.)*?\1/g, '<span class="text-success">$&</span>')
    // Comments
    .replace(/(#.*$)/gm, '<span class="text-text-muted italic">$1</span>')
    // Keywords
    .replace(/\b(def|return|if|elif|else|for|in|not|and|or|True|False|None|float|dict|int|str|bool|import|from|class|try|except|with|as|lambda|yield)\b/g,
      '<span class="text-primary">$&</span>')
    // Numbers
    .replace(/\b(\d+\.?\d*)\b/g, '<span class="text-warning">$&</span>')
}

function addV2Badge(html) {
  // After def score( line, append [v2] badge
  return html.replace(
    /(<span class="text-primary">def<\/span> score\([^)]*\)[^:]*:)/,
    '$1 <span class="bg-warning/20 text-warning text-[10px] font-mono rounded px-1 inline-block ml-1">[v2]</span>'
  )
}

export function RuleSourcePanel() {
  const ruleSources = useStore((s) => s.ruleSources)
  const ruleStreaming = useStore((s) => s.ruleStreaming)
  const streamingBuffer = useStore((s) => s.streamingBuffer)

  const latestRule = ruleSources.length > 0 ? ruleSources[ruleSources.length - 1] : null

  const codeRef = useRef(null)

  useEffect(() => {
    if (codeRef.current && ruleStreaming) {
      codeRef.current.scrollTop = codeRef.current.scrollHeight
    }
  }, [streamingBuffer, ruleStreaming])

  let highlightedSource = latestRule ? highlightPython(latestRule.source) : ''
  if (latestRule && latestRule.version > 1) {
    highlightedSource = addV2Badge(highlightedSource)
  }

  return (
    <div className="bg-surface rounded-lg border border-border-muted p-3">
      <div className="text-[11px] font-semibold uppercase tracking-wider text-text-muted mb-2">
        Generated Rules
      </div>

      <div
        ref={codeRef}
        className="bg-[#1f2028] rounded border border-border-muted p-3 font-mono text-[12px] leading-relaxed overflow-y-auto max-h-48"
      >
        {ruleStreaming ? (
          <pre className="whitespace-pre-wrap text-text-main">
            {streamingBuffer}<span className="animate-pulse">|</span>
          </pre>
        ) : latestRule ? (
          <pre
            className="whitespace-pre-wrap"
            dangerouslySetInnerHTML={{ __html: highlightedSource }}
          />
        ) : (
          <span className="text-text-muted">No generated rules yet. Run an attack to see Sentinel learn.</span>
        )}
      </div>

      {latestRule && (
        <div className="border-t border-border-muted mt-3 pt-2 text-[11px] text-text-muted font-mono">
          <div className="mb-1">-- Provenance --</div>
          {latestRule.version > 1 ? (
            <div>Evolved from: {latestRule.episode_ids?.join(' + ')} . Deployed: {relativeTime(latestRule.deployedAt)}</div>
          ) : (
            <div>Episode: {latestRule.episode_ids?.[0]} . Deployed: {relativeTime(latestRule.deployedAt)}</div>
          )}
        </div>
      )}
    </div>
  )
}
