import { createPortal } from 'react-dom'
import { useSimStore } from '../store/simStore'

export default function ReportViewer() {
  const { report, showReport, setShowReport, simulation } = useSimStore()

  if (!showReport || !report) return null

  const isHtml = report.trimStart().startsWith('<!DOCTYPE') || report.trimStart().startsWith('<html')

  return createPortal(
    <div
      onClick={() => setShowReport(false)}
      style={{
        position: 'fixed', inset: 0, zIndex: 99999,
        background: 'rgba(0,0,0,0.45)',
        backdropFilter: 'blur(8px)',
        WebkitBackdropFilter: 'blur(8px)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        padding: 32,
      }}
    >
      <div
        onClick={e => e.stopPropagation()}
        style={{
          background: '#fff',
          borderRadius: 20,
          width: '100%',
          maxWidth: 860,
          height: '88vh',
          display: 'flex',
          flexDirection: 'column',
          boxShadow: '0 40px 100px rgba(0,0,0,0.25)',
          overflow: 'hidden',
        }}
      >
        {/* Toolbar */}
        <div style={{
          padding: '14px 20px',
          borderBottom: '1px solid #e5e5e7',
          display: 'flex', alignItems: 'center',
          justifyContent: 'space-between',
          background: '#fafafa', flexShrink: 0,
        }}>
          <div>
            <div style={{ fontSize: 14, fontWeight: 600, color: '#1d1d1f' }}>Report Finale</div>
            <div style={{ fontSize: 11, color: '#6e6e73', marginTop: 1 }}>
              {simulation?.initial_description?.slice(0, 70)}
            </div>
          </div>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <button
              onClick={() => {
                const ext = isHtml ? 'html' : 'md'
                const mime = isHtml ? 'text/html' : 'text/markdown'
                const blob = new Blob([report], { type: mime })
                const url = URL.createObjectURL(blob)
                const a = document.createElement('a')
                a.href = url; a.download = `REPORT.${ext}`; a.click()
                URL.revokeObjectURL(url)
              }}
              style={{
                padding: '6px 14px', fontSize: 12, fontWeight: 500,
                background: '#f0f0f0', border: 'none', borderRadius: 8,
                cursor: 'pointer', color: '#1d1d1f',
              }}
            >
              Scarica
            </button>
            <button
              onClick={() => setShowReport(false)}
              style={{
                width: 28, height: 28, borderRadius: '50%',
                border: 'none', background: '#e5e5e7',
                cursor: 'pointer', fontSize: 18, color: '#6e6e73',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                lineHeight: 1,
              }}
            >
              x
            </button>
          </div>
        </div>

        {/* Content */}
        {isHtml ? (
          <iframe
            srcDoc={report}
            style={{ flex: 1, border: 'none', width: '100%' }}
            title="Report Finale"
          />
        ) : (
          <div style={{
            flex: 1, overflowY: 'auto', padding: '28px 36px',
            fontFamily: "-apple-system, BlinkMacSystemFont, 'SF Pro Text', sans-serif",
            fontSize: 14, lineHeight: 1.75, color: '#3a3a3c',
            whiteSpace: 'pre-wrap',
          }}>
            {report}
          </div>
        )}
      </div>
    </div>,
    document.body
  )
}
