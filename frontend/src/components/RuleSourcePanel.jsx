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

  // Single-pass tokenizer to avoid regex passes clobbering each other's HTML spans.
  // Each token type is captured in a single combined regex with named groups.
  const keywords = new Set([
    'def', 'return', 'if', 'elif', 'else', 'for', 'in', 'not', 'and', 'or',
    'True', 'False', 'None', 'float', 'dict', 'int', 'str', 'bool',
    'import', 'from', 'class', 'try', 'except', 'with', 'as', 'lambda', 'yield',
  ])

  // Combined regex: order matters -- earlier alternatives are tried first.
  // 1. Triple-quoted strings (docstrings)
  // 2. Single-line strings (double or single quoted)
  // 3. Comments
  // 4. Words (potential keywords or identifiers)
  // 5. Numbers
  // 6. Any other character (passed through)
  const tokenRegex = /("""[\s\S]*?"""|'''[\s\S]*?''')|(["'])(?:(?=(\\?))\3.)*?\2|(#.*$)|(\b[a-zA-Z_]\w*\b)|(\b\d+\.?\d*\b)/gm

  let result = ''
  let lastIndex = 0

  for (const match of source.matchAll(tokenRegex)) {
    // Append any text between the previous match and this one (whitespace, operators, etc.)
    if (match.index > lastIndex) {
      result += escapeHtml(source.slice(lastIndex, match.index))
    }

    const [full, tripleStr, , , comment, word, num] = match

    if (tripleStr !== undefined) {
      result += '<span style="color:#3fb950">' + escapeHtml(tripleStr) + '</span>'
    } else if (comment !== undefined) {
      result += '<span style="color:#8b949e;font-style:italic">' + escapeHtml(comment) + '</span>'
    } else if (word !== undefined) {
      if (keywords.has(word)) {
        result += '<span style="color:#57abff">' + escapeHtml(word) + '</span>'
      } else {
        result += escapeHtml(word)
      }
    } else if (num !== undefined) {
      result += '<span style="color:#e3b341">' + escapeHtml(num) + '</span>'
    } else {
      // Single-line string match (group 2 matched the quote char)
      result += '<span style="color:#3fb950">' + escapeHtml(full) + '</span>'
    }

    lastIndex = match.index + full.length
  }

  // Append any remaining text after last match
  if (lastIndex < source.length) {
    result += escapeHtml(source.slice(lastIndex))
  }

  return result
}

function escapeHtml(text) {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}

function addV2Badge(html) {
  // After def score( line, append [v2] badge
  return html.replace(
    /(<span style="color:#57abff">def<\/span> score\([^)]*\)[^:]*:)/,
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
