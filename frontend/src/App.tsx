import { useEffect, useRef, useState } from 'react'
import { useSimStore } from './store/simStore'
import { useSimWebSocket } from './api/useWebSocket'
import Graph3D from './components/Graph3D/Graph3D'
import StatusPanel from './components/StatusPanel'
import AgentChat from './components/AgentChat'
import { ControlBar } from './components/ControlBar'
import ReportViewer from './components/ReportViewer'

function Divider({ onDrag }: { onDrag: (dx: number) => void }) {
  const dragging = useRef(false)
  const last = useRef(0)
  useEffect(() => {
    const move = (e: MouseEvent) => { if (dragging.current) { onDrag(e.clientX - last.current); last.current = e.clientX } }
    const up = () => { dragging.current = false }
    window.addEventListener('mousemove', move)
    window.addEventListener('mouseup', up)
    return () => { window.removeEventListener('mousemove', move); window.removeEventListener('mouseup', up) }
  }, [onDrag])
  return (
    <div
      onMouseDown={e => { dragging.current = true; last.current = e.clientX }}
      style={{ width: 1, background: '#e5e5e7', cursor: 'col-resize', flexShrink: 0, transition: 'background 0.15s' }}
      onMouseOver={e => (e.currentTarget.style.background = '#0071e3')}
      onMouseOut={e => (e.currentTarget.style.background = '#e5e5e7')}
    />
  )
}

export default function App() {
  const simulationId  = useSimStore(s => s.simulationId)
  const simulation    = useSimStore(s => s.simulation)
  const report        = useSimStore(s => s.report)
  const setShowReport = useSimStore(s => s.setShowReport)
  useSimWebSocket(simulationId)

  const [leftW, setLeftW]   = useState(260)
  const [rightW, setRightW] = useState(300)

  const isCompleted = simulation?.status === 'completed'

  return (
    <div style={{
      height: '100vh', display: 'flex', flexDirection: 'column', background: '#f5f5f7',
      fontFamily: "-apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Helvetica Neue', sans-serif",
    }}>
      {/* Topbar */}
      <div style={{
        height: 52, display: 'flex', alignItems: 'center', flexShrink: 0,
        background: 'rgba(255,255,255,0.92)',
        backdropFilter: 'blur(20px)', WebkitBackdropFilter: 'blur(20px)',
        borderBottom: '1px solid #e5e5e7',
      }}>
        <div style={{
          padding: '0 24px', fontSize: 13, fontWeight: 600, color: '#1d1d1f',
          letterSpacing: -0.1, borderRight: '1px solid #e5e5e7',
          height: '100%', display: 'flex', alignItems: 'center', minWidth: 180, flexShrink: 0,
        }}>
          World Simulation
        </div>
        <ControlBar />
      </div>

      {/* Completion banner — solo se completata e report disponibile */}
      {isCompleted && (
        <div style={{
          background: 'linear-gradient(90deg, #0071e3, #34aadc)',
          padding: '10px 24px', display: 'flex', alignItems: 'center',
          justifyContent: 'space-between', flexShrink: 0,
        }}>
          <div style={{ color: '#fff', fontSize: 13, fontWeight: 500 }}>
            Simulazione completata — {simulation?.current_decade} d.C. · {report ? 'Report pronto' : 'Generazione report…'}
          </div>
          {report && (
            <button
              onClick={() => setShowReport(true)}
              style={{
                padding: '6px 16px', background: '#fff', border: 'none',
                borderRadius: 8, fontSize: 13, fontWeight: 600, color: '#0071e3', cursor: 'pointer',
              }}
            >
              Leggi Report →
            </button>
          )}
        </div>
      )}

      {/* Main */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden', minHeight: 0 }}>
        <div style={{ width: leftW, flexShrink: 0, background: '#fff', overflowY: 'auto' }}>
          <StatusPanel />
        </div>
        <Divider onDrag={dx => setLeftW(w => Math.max(180, Math.min(480, w + dx)))} />
        <div style={{ flex: 1, minWidth: 0, background: '#f5f5f7' }}>
          <Graph3D />
        </div>
        <Divider onDrag={dx => setRightW(w => Math.max(180, Math.min(480, w - dx)))} />
        <div style={{ width: rightW, flexShrink: 0, background: '#fff', overflowY: 'auto', borderLeft: '1px solid #e5e5e7' }}>
          <AgentChat />
        </div>
      </div>

      <ReportViewer />
    </div>
  )
}
