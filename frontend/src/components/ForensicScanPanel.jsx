import { useState, useRef, useEffect, useCallback } from 'react'
import { useStore } from '../store'

const BASE_WIDTH = 800

function Lightbox({ src, alt, isForensic, onClose }) {
  // Forensic scans open at 2× so the hidden text at the bottom is immediately readable
  const [scale, setScale] = useState(isForensic ? 2 : 1)
  const containerRef = useRef(null)

  // Auto-scroll to bottom for forensic scans so hidden text is immediately visible
  useEffect(() => {
    if (isForensic && containerRef.current) {
      const el = containerRef.current
      setTimeout(() => { el.scrollTop = el.scrollHeight }, 150)
    }
  }, [isForensic])

  const handleWheel = useCallback((e) => {
    e.preventDefault()
    // ctrlKey = trackpad pinch; plain scroll = mouse wheel — both zoom
    const delta = e.deltaY < 0 ? 0.12 : -0.12
    setScale((s) => Math.min(5, Math.max(0.5, s + delta)))
  }, [])

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/85"
      onClick={onClose}
    >
      <div
        className="relative max-w-5xl max-h-[90vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Toolbar */}
        <div className="flex items-center justify-between bg-surface border border-border-muted rounded-t-lg px-3 py-2 gap-4">
          <span className="text-[11px] uppercase tracking-wider text-text-muted font-semibold">
            {alt}
          </span>
          <div className="flex items-center gap-2">
            <span className="text-[11px] text-text-muted w-10 text-center">
              {Math.round(scale * 100)}%
            </span>
            <button
              onClick={() => setScale(isForensic ? 2 : 1)}
              className="text-[11px] text-text-muted hover:text-text-primary px-2 py-0.5 border border-border-muted rounded"
            >Reset</button>
            <button
              onClick={onClose}
              className="text-text-muted hover:text-danger text-lg leading-none px-2 py-0.5 border border-border-muted rounded ml-2"
            >✕</button>
          </div>
        </div>

        {/* Image container — scroll/pinch to zoom */}
        <div
          ref={containerRef}
          className="overflow-auto bg-black border-x border-b border-border-muted rounded-b-lg"
          style={{ maxHeight: 'calc(90vh - 48px)' }}
          onWheel={handleWheel}
        >
          <img
            src={src}
            alt={alt}
            className="block"
            style={{ width: `${BASE_WIDTH * scale}px`, maxWidth: 'none' }}
            draggable={false}
          />
        </div>

        <p className="text-[10px] text-text-muted mt-2 text-center">
          Scroll or pinch to zoom · Click outside to close
        </p>
      </div>
    </div>
  )
}

export function ForensicScanPanel() {
  const agents = useStore((s) => s.agents)
  const [lightbox, setLightbox] = useState(null) // { src, alt, isForensic }

  const hasDocuments = agents.forensics?.verdict?.claims_checked?.some(
    (c) =>
      c.field?.toLowerCase().includes('document') ||
      c.field?.toLowerCase().includes('hidden') ||
      c.field?.toLowerCase().includes('invoice')
  )

  return (
    <>
      {lightbox && (
        <Lightbox
          src={lightbox.src}
          alt={lightbox.alt}
          isForensic={lightbox.isForensic}
          onClose={() => setLightbox(null)}
        />
      )}

      <div className="bg-surface rounded-lg border border-border-muted p-3">
        <div className="text-[11px] font-semibold uppercase tracking-wider text-text-muted mb-2">
          FORENSIC SCAN
        </div>

        <div className="flex gap-3">
          {/* Left pane: Agent view */}
          <div className="flex-1">
            <div className="text-[11px] uppercase text-text-muted mb-1">Invoice (Agent View)</div>
            <div
              className={`bg-surface rounded border border-border-muted h-40 flex items-center justify-center overflow-hidden ${hasDocuments ? 'cursor-zoom-in hover:border-border-primary transition-colors' : ''}`}
              onClick={() => hasDocuments && setLightbox({ src: '/invoice_clean.png', alt: 'Invoice (Agent View)', isForensic: false })}
              title={hasDocuments ? 'Click to expand' : undefined}
            >
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
            {hasDocuments && (
              <p className="text-[10px] text-text-muted mt-1 text-center">Click to expand</p>
            )}
          </div>

          {/* Right pane: Forensic scan */}
          <div className="flex-1">
            <div className="text-[11px] uppercase text-text-muted mb-1">Forensic Scan</div>
            <div
              className={`bg-surface rounded border border-danger/40 h-40 flex items-center justify-center overflow-hidden ${hasDocuments ? 'cursor-zoom-in hover:border-danger/70 transition-colors' : ''}`}
              onClick={() => hasDocuments && setLightbox({ src: '/invoice_forensic.png', alt: 'Forensic Scan', isForensic: true })}
              title={hasDocuments ? 'Click to expand' : undefined}
            >
              {hasDocuments
                ? (
                  <img
                    src="/invoice_forensic.png"
                    alt="Forensic scan"
                    className="object-contain h-full w-full"
                  />
                )
                : (
                  <span className="text-text-muted text-[13px]">No documents attached.</span>
                )}
            </div>
            {hasDocuments && (
              <>
                <div className="mt-1.5 flex items-center gap-1.5 bg-danger/10 border border-danger/30 rounded px-2 py-1">
                  <span className="text-danger text-[12px]">⚠</span>
                  <span className="text-[10px] text-danger font-semibold">
                    Hidden injection text detected — click to expand &amp; hover to magnify
                  </span>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </>
  )
}
