import { createPortal } from 'react-dom'
import { useSimStore } from '../store/simStore'

// Renderer markdown minimale senza dipendenze
function renderMarkdown(md: string): string {
  return md
    // H1
    .replace(/^# (.+)$/gm, '<h1 style="font-size:22px;font-weight:700;color:#1d1d1f;margin:28px 0 10px;letter-spacing:-0.4px;border-bottom:2px solid #e5e5e7;padding-bottom:8px">$1</h1>')
    // H2
    .replace(/^## (.+)$/gm, '<h2 style="font-size:17px;font-weight:600;color:#1d1d1f;margin:22px 0 8px;letter-spacing:-0.2px">$1</h2>')
    // H3
    .replace(/^### (.+)$/gm, '<h3 style="font-size:14px;font-weight:600;color:#1d1d1f;margin:16px 0 6px">$1</h3>')
    // Bold
    .replace(/\*\*(.+?)\*\*/g, '<strong style="font-weight:600;color:#1d1d1f">$1</strong>')
    // Italic
    .replace(/\*(.+?)\*/g, '<em style="color:#6e6e73">$1</em>')
    // Horizontal rule
    .replace(/^---$/gm, '<hr style="border:none;border-top:1px solid #e5e5e7;margin:20px 0">')
    // Table rows (basic)
    .replace(/^\|(.+)\|$/gm, (_, row) => {
      const cells = row.split('|').map((c: string) => c.trim())
      const isHeader = false
      return `<tr>${cells.map((c: string) => `<td style="padding:8px 12px;border-bottom:1px solid #f0f0f0;font-size:13px;color:#1d1d1f">${c}</td>`).join('')}</tr>`
    })
    // Table separator rows (skip)
    .replace(/<tr><td[^>]*>[-: ]+<\/td>(<td[^>]*>[-: ]+<\/td>)*<\/tr>/g, '')
    // Bullet list
    .replace(/^- (.+)$/gm, '<li style="padding:3px 0;color:#3a3a3c;font-size:14px;line-height:1.6">$1</li>')
    // Wrap consecutive <li> in <ul>
    .replace(/(<li[^>]*>.*<\/li>\n?)+/g, (match) => `<ul style="margin:8px 0 8px 20px;padding:0">${match}</ul>`)
    // Wrap consecutive <tr> in <table>
    .replace(/(<tr>.*<\/tr>\n?)+/g, (match) => `<table style="width:100%;border-collapse:collapse;margin:12px 0;background:#f5f5f7;border-radius:8px;overflow:hidden">${match}</table>`)
    // Paragraphs (lines not already wrapped)
    .replace(/^(?!<[a-z]|$)(.+)$/gm, '<p style="margin:6px 0;color:#3a3a3c;font-size:14px;line-height:1.7">$1</p>')
}

export default function ReportViewer() {
  const { report, showReport, setShowReport, simulation } = useSimStore()

  if (!showReport || !report) return null

  return createPortal(
    <div
      onClick={() => setShowReport(false)}
      style={{
        position: 'fixed', inset: 0, zIndex: 99999,
        background: 'rgba(0,0,0,0.4)',
        backdropFilter: 'blur(8px)',
        WebkitBackdropFilter: 'blur(8px)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        padding: 40,
      }}
    >
      <div
        onClick={e => e.stopPropagation()}
        style={{
          background: '#fff',
          borderRadius: 20,
          width: '100%',
          maxWidth: 780,
          maxHeight: '85vh',
          display: 'flex',
          flexDirection: 'column',
          boxShadow: '0 40px 100px rgba(0,0,0,0.2)',
          overflow: 'hidden',
        }}
      >
        {/* Header */}
        <div style={{
          padding: '20px 28px',
          borderBottom: '1px solid #f0f0f0',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexShrink: 0,
          background: '#fafafa',
        }}>
          <div>
            <div style={{ fontSize: 16, fontWeight: 700, color: '#1d1d1f', letterSpacing: -0.3 }}>
              Report Finale
            </div>
            <div style={{ fontSize: 12, color: '#6e6e73', marginTop: 2 }}>
              {simulation?.initial_description?.slice(0, 60)}…
            </div>
          </div>
          <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
            <button
              onClick={() => {
                const blob = new Blob([report], { type: 'text/markdown' })
                const url = URL.createObjectURL(blob)
                const a = document.createElement('a')
                a.href = url; a.download = 'REPORT.md'; a.click()
                URL.revokeObjectURL(url)
              }}
              style={{
                padding: '6px 14px', fontSize: 12, fontWeight: 500,
                background: '#f0f0f0', border: 'none', borderRadius: 8,
                cursor: 'pointer', color: '#1d1d1f',
              }}
            >
              ↓ Scarica .md
            </button>
            <button
              onClick={() => setShowReport(false)}
              style={{
                width: 28, height: 28, borderRadius: '50%', border: 'none',
                background: '#e5e5e7', cursor: 'pointer', fontSize: 16,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                color: '#6e6e73', fontWeight: 300,
              }}
            >×</button>
          </div>
        </div>

        {/* Content */}
        <div
          style={{
            flex: 1,
            overflowY: 'auto',
            padding: '24px 32px 36px',
            fontFamily: "-apple-system, BlinkMacSystemFont, 'SF Pro Text', sans-serif",
          }}
          dangerouslySetInnerHTML={{ __html: renderMarkdown(report) }}
        />
      </div>
    </div>,
    document.body
  )
}
