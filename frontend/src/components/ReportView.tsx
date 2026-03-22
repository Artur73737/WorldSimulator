import { useState, useEffect } from 'react'
import { getReport, generateReport } from '../api/client'
import { useSimStore } from '../store/simStore'

const FileTextIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/>
    <polyline points="14 2 14 8 20 8"/>
    <line x1="16" y1="13" x2="8" y2="13"/>
    <line x1="16" y1="17" x2="8" y2="17"/>
    <line x1="10" y1="9" x2="8" y2="9"/>
  </svg>
)

const DownloadIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
    <polyline points="7 10 12 15 17 10"/>
    <line x1="12" y1="15" x2="12" y2="3"/>
  </svg>
)

const RefreshIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <polyline points="23 4 23 10 17 10"/>
    <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
  </svg>
)

const CloseIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <line x1="18" y1="6" x2="6" y2="18"/>
    <line x1="6" y1="6" x2="18" y2="18"/>
  </svg>
)

export default function ReportView({ onClose }: { onClose: () => void }) {
  const { simulationId, simulation } = useSimStore()
  const [report, setReport] = useState<string>('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    if (simulationId) {
      loadReport()
    }
  }, [simulationId])

  const loadReport = async () => {
    if (!simulationId) return
    setLoading(true)
    setError('')
    try {
      const reportData = await getReport(simulationId)
      setReport(reportData)
    } catch (e) {
      setError('Report non ancora disponibile. La simulazione deve completarsi.')
    } finally {
      setLoading(false)
    }
  }

  const handleGenerate = async () => {
    if (!simulationId) return
    setLoading(true)
    try {
      await generateReport(simulationId)
      await loadReport()
    } catch (e) {
      setError('Errore nella generazione del report')
    } finally {
      setLoading(false)
    }
  }

  const handleDownload = () => {
    if (!report) return
    const blob = new Blob([report], { type: 'text/markdown' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `report_${simulation?.seed || 'simulation'}.md`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  const renderReportContent = (content: string) => {
    // Converti markdown base in HTML
    return content
      .split('\n')
      .map((line, i) => {
        if (line.startsWith('# ')) {
          return <h1 key={i} style={styles.h1}>{line.slice(2)}</h1>
        } else if (line.startsWith('## ')) {
          return <h2 key={i} style={styles.h2}>{line.slice(3)}</h2>
        } else if (line.startsWith('### ')) {
          return <h3 key={i} style={styles.h3}>{line.slice(4)}</h3>
        } else if (line.startsWith('- ')) {
          return <li key={i} style={styles.li}>{line.slice(2)}</li>
        } else if (line.trim() === '') {
          return <div key={i} style={{ height: 8 }} />
        } else if (line.startsWith('**') && line.endsWith('**')) {
          return <p key={i} style={styles.strong}>{line.slice(2, -2)}</p>
        } else {
          return <p key={i} style={styles.p}>{line}</p>
        }
      })
  }

  return (
    <div style={styles.overlay} onClick={onClose}>
      <div style={styles.container} onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div style={styles.header}>
          <div style={styles.headerLeft}>
            <div style={styles.iconContainer}>
              <FileTextIcon />
            </div>
            <div>
              <h2 style={styles.title}>Report Storico</h2>
              <p style={styles.subtitle}>
                {simulation?.initial_description || 'Simulazione'}
              </p>
            </div>
          </div>
          <div style={styles.headerActions}>
            <button
              onClick={handleGenerate}
              disabled={loading}
              style={{ ...styles.button, ...styles.buttonSecondary }}
            >
              <RefreshIcon />
              {loading ? 'Generazione...' : 'Rigenera'}
            </button>
            <button
              onClick={handleDownload}
              disabled={!report || loading}
              style={{ ...styles.button, ...styles.buttonPrimary }}
            >
              <DownloadIcon />
              Scarica MD
            </button>
            <button onClick={onClose} style={styles.closeButton}>
              <CloseIcon />
            </button>
          </div>
        </div>

        {/* Content */}
        <div style={styles.content}>
          {loading ? (
            <div style={styles.loading}>
              <div style={styles.spinner} />
              <p style={styles.loadingText}>Generazione report in corso...</p>
            </div>
          ) : error ? (
            <div style={styles.error}>
              <div style={styles.errorIcon}>!</div>
              <p style={styles.errorText}>{error}</p>
              <button onClick={loadReport} style={styles.retryButton}>
                Riprova
              </button>
            </div>
          ) : report ? (
            <div style={styles.report}>
              {renderReportContent(report)}
            </div>
          ) : (
            <div style={styles.empty}>
              <FileTextIcon />
              <p>Nessun report disponibile</p>
              <button onClick={handleGenerate} style={styles.generateButton}>
                Genera Report
              </button>
            </div>
          )}
        </div>

        {/* Footer */}
        <div style={styles.footer}>
          <span style={styles.footerText}>
            {report ? `${report.length} caratteri` : 'Nessun dato'}
          </span>
          <span style={styles.footerStatus}>
            {simulation?.status === 'completed' ? 'Completato' : 'In corso'}
          </span>
        </div>
      </div>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  overlay: {
    position: 'fixed',
    inset: 0,
    background: 'rgba(0, 0, 0, 0.4)',
    backdropFilter: 'blur(4px)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 1000,
    padding: 20,
  },
  container: {
    background: 'rgba(255, 255, 255, 0.95)',
    backdropFilter: 'blur(20px) saturate(180%)',
    borderRadius: 18,
    width: '100%',
    maxWidth: 800,
    maxHeight: '90vh',
    display: 'flex',
    flexDirection: 'column',
    border: '1px solid rgba(255, 255, 255, 0.3)',
    boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '20px 24px',
    borderBottom: '1px solid rgba(0, 0, 0, 0.1)',
  },
  headerLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: 16,
  },
  iconContainer: {
    width: 44,
    height: 44,
    borderRadius: 12,
    background: '#0071e3',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: 'white',
  },
  title: {
    fontSize: 20,
    fontWeight: 600,
    color: '#1d1d1f',
    margin: 0,
  },
  subtitle: {
    fontSize: 13,
    color: '#6e6e73',
    margin: '4px 0 0 0',
  },
  headerActions: {
    display: 'flex',
    alignItems: 'center',
    gap: 10,
  },
  button: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    padding: '8px 16px',
    borderRadius: 8,
    fontSize: 13,
    fontWeight: 500,
    border: 'none',
    cursor: 'pointer',
    transition: 'all 0.2s',
  },
  buttonPrimary: {
    background: '#0071e3',
    color: 'white',
  },
  buttonSecondary: {
    background: 'rgba(0, 0, 0, 0.05)',
    color: '#1d1d1f',
  },
  closeButton: {
    width: 36,
    height: 36,
    borderRadius: '50%',
    border: 'none',
    background: 'transparent',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: '#6e6e73',
    transition: 'all 0.2s',
    marginLeft: 8,
  },
  content: {
    flex: 1,
    overflow: 'auto',
    padding: '24px',
  },
  loading: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '60px 20px',
    gap: 16,
  },
  spinner: {
    width: 40,
    height: 40,
    borderRadius: '50%',
    border: '3px solid rgba(0, 113, 227, 0.2)',
    borderTopColor: '#0071e3',
    animation: 'spin 1s linear infinite',
  },
  loadingText: {
    fontSize: 14,
    color: '#6e6e73',
  },
  error: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '60px 20px',
    gap: 16,
  },
  errorIcon: {
    width: 48,
    height: 48,
    borderRadius: '50%',
    background: '#ff3b30',
    color: 'white',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: 24,
    fontWeight: 600,
  },
  errorText: {
    fontSize: 14,
    color: '#1d1d1f',
    textAlign: 'center',
  },
  retryButton: {
    padding: '10px 20px',
    background: '#0071e3',
    color: 'white',
    border: 'none',
    borderRadius: 8,
    fontSize: 14,
    fontWeight: 500,
    cursor: 'pointer',
  },
  report: {
    fontSize: 14,
    lineHeight: 1.7,
    color: '#1d1d1f',
  },
  h1: {
    fontSize: 28,
    fontWeight: 700,
    color: '#1d1d1f',
    margin: '0 0 16px 0',
    paddingBottom: 8,
    borderBottom: '2px solid #0071e3',
  },
  h2: {
    fontSize: 22,
    fontWeight: 600,
    color: '#1d1d1f',
    margin: '24px 0 12px 0',
  },
  h3: {
    fontSize: 18,
    fontWeight: 600,
    color: '#1d1d1f',
    margin: '16px 0 8px 0',
  },
  p: {
    margin: '0 0 12px 0',
    color: '#3a3a3c',
  },
  strong: {
    fontWeight: 600,
    color: '#0071e3',
    margin: '8px 0',
  },
  li: {
    margin: '4px 0 4px 20px',
    color: '#3a3a3c',
  },
  empty: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '60px 20px',
    gap: 16,
    color: '#6e6e73',
  },
  generateButton: {
    padding: '12px 24px',
    background: '#0071e3',
    color: 'white',
    border: 'none',
    borderRadius: 10,
    fontSize: 15,
    fontWeight: 600,
    cursor: 'pointer',
    marginTop: 8,
  },
  footer: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '16px 24px',
    borderTop: '1px solid rgba(0, 0, 0, 0.1)',
    background: 'rgba(0, 0, 0, 0.02)',
    borderRadius: '0 0 18px 18px',
  },
  footerText: {
    fontSize: 12,
    color: '#6e6e73',
  },
  footerStatus: {
    fontSize: 12,
    color: '#0071e3',
    fontWeight: 500,
  },
}
