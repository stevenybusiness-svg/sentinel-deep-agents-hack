import { useState, useCallback } from 'react'
import { useStore } from '../store'

function Lightbox({ src, alt, isForensic, onClose }) {
  const [scale, setScale] = useState(1)

  const zoom = useCallback((delta) => {
    setScale((s) => Math.min(4, Math.max(0.5, s + delta)))
  }, [])

  const handleWheel = useCallback((e) => {
    e.preventDefault()
    zoom(e.deltaY < 0 ? 0.2 : -0.2)
  }, [zoom])

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
            <button
              onClick={() => zoom(-0.25)}
              className="text-text-muted hover:text-text-primary text-lg leading-none px-2 py-0.5 border border-border-muted rounded"
            >−</button>
            <span className="text-[11px] text-text-muted w-10 text-center">
              {Math.round(scale * 100)}%
            </span>
            <button
              onClick={() => zoom(0.25)}
              className="text-text-muted hover:text-text-primary text-lg leading-none px-2 py-0.5 border border-border-muted rounded"
            >+</button>
            <button
              onClick={() => setScale(1)}
              className="text-[11px] text-text-muted hover:text-text-primary px-2 py-0.5 border border-border-muted rounded ml-1"
            >Reset</button>
            <button
              onClick={onClose}
              className="text-text-muted hover:text-danger text-lg leading-none px-2 py-0.5 border border-border-muted rounded ml-2"
            >✕</button>
          </div>
        </div>

        {/* Image container */}
        <div
          className="overflow-auto bg-black border-x border-b border-border-muted rounded-b-lg"
          style={{ maxHeight: 'calc(90vh - 48px)' }}
          onWheel={handleWheel}
        >
          <div
            className="relative inline-block transition-transform duration-100 origin-top-left"
            style={{ transform: `scale(${scale})`, transformOrigin: 'top left' }}
          >
            <img
              src={src}
              alt={alt}
              className="block max-w-none"
              style={{ width: `${Math.round(100 / scale)}%`, minWidth: '600px' }}
              draggable={false}
            />
            {isForensic && (
              <div
                className="absolute left-0 right-0 bg-danger/50 border-2 border-danger rounded-t flex items-center justify-center"
                style={{ top: 0, height: '8%' }}
              >
                <span className="text-white font-bold text-sm drop-shadow">
                  [FORENSIC SCAN] ⚠ Hidden prompt injection — white text on white background
                </span>
              </div>
            )}
          </div>
        </div>

        <p className="text-[10px] text-text-muted mt-2 text-center">
          Scroll to zoom · Click outside to close
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
              className={`bg-surface rounded border border-border-muted h-40 flex items-center justify-center overflow-hidden relative ${hasDocuments ? 'cursor-zoom-in hover:border-danger/60 transition-colors' : ''}`}
              onClick={() => hasDocuments && setLightbox({ src: '/invoice_forensic.png', alt: 'Forensic Scan', isForensic: true })}
              title={hasDocuments ? 'Click to expand' : undefined}
            >
              {hasDocuments
                ? (
                  <>
                    <img
                      src="/invoice_forensic.png"
                      alt="Forensic scan"
                      className="object-contain h-full w-full"
                    />
                    <div className="absolute top-2 left-2 right-2 h-6 bg-danger/40 rounded border border-danger/60 flex items-center justify-center">
                      <span className="text-[10px] text-white font-semibold">Hidden text detected</span>
                    </div>
                  </>
                )
                : (
                  <span className="text-text-muted text-[13px]">No documents attached.</span>
                )}
            </div>
            {hasDocuments && (
              <p className="text-[10px] text-text-muted mt-1 text-center">Click to expand</p>
            )}
          </div>
        </div>
      </div>
    </>
  )
}
