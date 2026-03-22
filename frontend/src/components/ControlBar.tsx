import { createPortal } from 'react-dom'
import { useState } from 'react'
import axios from 'axios'
import { startSimulation, pauseSimulation, resumeSimulation, getSimulation, getGraphData, getAgents } from '../api/client'
import { useSimStore } from '../store/simStore'

/* ─── Button ───────────────────────────────────────────────────────── */
const Btn = ({ children, onClick, primary, danger, disabled, style = {} }: {
  children: React.ReactNode; onClick?: () => void; primary?: boolean
  danger?: boolean; disabled?: boolean; style?: React.CSSProperties
}) => (
  <button onClick={onClick} disabled={disabled} style={{
    padding: '8px 18px', fontSize: 13, fontWeight: 500, fontFamily: 'inherit',
    borderRadius: 8, border: 'none', cursor: disabled ? 'not-allowed' : 'pointer',
    opacity: disabled ? 0.5 : 1, transition: 'opacity 0.15s',
    background: primary ? '#0071e3' : danger ? '#ff3b30' : '#f0f0f0',
    color: primary || danger ? '#fff' : '#1d1d1f',
    ...style,
  }}>{children}</button>
)

/* ─── Portal Modal ─────────────────────────────────────────────────── */
function Modal({ children, onClose }: { children: React.ReactNode; onClose: () => void }) {
  return createPortal(
    <div
      onClick={onClose}
      style={{
        position: 'fixed', inset: 0, zIndex: 99999,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        background: 'rgba(0,0,0,0.28)',
        backdropFilter: 'blur(6px)',
        WebkitBackdropFilter: 'blur(6px)',
        padding: '20px',
      }}
    >
      <div
        onClick={e => e.stopPropagation()}
        style={{
          background: '#fff',
          borderRadius: 18,
          padding: '32px',
          width: '100%',
          maxWidth: 460,
          boxShadow: '0 30px 80px rgba(0,0,0,0.18)',
        }}
      >
        {children}
      </div>
    </div>,
    document.body
  )
}

/* ─── Start Modal ──────────────────────────────────────────────────── */
function StartModal({ onClose }: { onClose: () => void }) {
  const [desc, setDesc] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const { setSimulation, setSimulationId, setAgents, setGraphData, setForks } = useSimStore()

  const submit = async () => {
    if (desc.trim().length < 10) { setError('Almeno 10 caratteri'); return }
    setLoading(true); setError('')
    try {
      const sim = await startSimulation(desc.trim())
      setSimulation(sim); setSimulationId(sim.id)
      await new Promise(r => setTimeout(r, 2000))
      const full = await getSimulation(sim.id)
      setSimulation(full.simulation); setAgents(full.agents); setForks(full.forks)
      const g = await getGraphData(sim.id)
      setGraphData(g.nodes, g.links)
      onClose()
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Errore')
    } finally { setLoading(false) }
  }

  return (
    <Modal onClose={onClose}>
      <div style={{ fontSize: 19, fontWeight: 600, color: '#1d1d1f', marginBottom: 6, letterSpacing: -0.3 }}>
        Nuova simulazione
      </div>
      <div style={{ fontSize: 13, color: '#6e6e73', marginBottom: 20, lineHeight: 1.5 }}>
        Descrivi l'ambiente storico iniziale in poche righe.
      </div>
      <textarea
        autoFocus
        value={desc}
        onChange={e => setDesc(e.target.value)}
        placeholder="Mediterraneo 200 d.C., Roma dominante, tribù germaniche ai confini…"
        rows={4}
        style={{
          width: '100%', background: '#f5f5f7', border: '1.5px solid transparent',
          borderRadius: 10, padding: '12px 14px', fontSize: 14, color: '#1d1d1f',
          fontFamily: 'inherit', lineHeight: 1.6, resize: 'vertical', outline: 'none',
          transition: 'border-color 0.15s', boxSizing: 'border-box',
        }}
        onFocus={e => (e.currentTarget.style.borderColor = '#0071e3')}
        onBlur={e => (e.currentTarget.style.borderColor = 'transparent')}
      />
      {error && <div style={{ color: '#ff3b30', fontSize: 12, marginTop: 8 }}>{error}</div>}
      <div style={{ display: 'flex', gap: 10, marginTop: 22, justifyContent: 'flex-end' }}>
        <Btn onClick={onClose}>Annulla</Btn>
        <Btn primary onClick={submit} disabled={loading}>{loading ? 'Avvio…' : 'Avvia'}</Btn>
      </div>
    </Modal>
  )
}

/* ─── Reset Modal ──────────────────────────────────────────────────── */
function ResetModal({ onConfirm, onClose }: { onConfirm: () => void; onClose: () => void }) {
  return (
    <Modal onClose={onClose}>
      <div style={{ fontSize: 19, fontWeight: 600, color: '#1d1d1f', marginBottom: 6, letterSpacing: -0.3 }}>
        Reset database
      </div>
      <div style={{ fontSize: 13, color: '#6e6e73', lineHeight: 1.6, marginBottom: 24 }}>
        Cancella tutte le simulazioni, agenti e dati.<br />
        <strong style={{ color: '#1d1d1f' }}>Operazione irreversibile.</strong>
      </div>
      <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
        <Btn onClick={onClose}>Annulla</Btn>
        <Btn danger onClick={onConfirm}>Resetta tutto</Btn>
      </div>
    </Modal>
  )
}

/* ─── ControlBar ───────────────────────────────────────────────────── */
export function ControlBar() {
  const { simulation, simulationId, setSimulation, setGraphData, setForks, setAgents, reset } = useSimStore()
  const [showStart, setShowStart] = useState(false)
  const [showReset, setShowReset] = useState(false)
  const [busy, setBusy] = useState(false)

  const refresh = async () => {
    if (!simulationId) return
    const [full, g] = await Promise.all([getSimulation(simulationId), getGraphData(simulationId)])
    setSimulation(full.simulation); setAgents(full.agents); setForks(full.forks); setGraphData(g.nodes, g.links)
  }

  const togglePause = async () => {
    if (!simulationId) return
    const u = simulation?.status === 'running'
      ? await pauseSimulation(simulationId)
      : await resumeSimulation(simulationId)
    setSimulation(u)
  }

  const doReset = async () => {
    setBusy(true); setShowReset(false)
    try { await axios.post('/api/v1/admin/reset-db'); reset() }
    finally { setBusy(false) }
  }

  return (
    <>
      {showStart && <StartModal onClose={() => { setShowStart(false); refresh() }} />}
      {showReset && <ResetModal onConfirm={doReset} onClose={() => setShowReset(false)} />}

      <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '0 20px', height: '100%', flex: 1 }}>
        <Btn primary onClick={() => setShowStart(true)}>+ Nuova</Btn>
        {simulation && (
          <>
            <Btn onClick={togglePause}>{simulation.status === 'running' ? 'Pausa' : 'Riprendi'}</Btn>
            <Btn onClick={refresh} style={{ padding: '8px 12px' }}>↻</Btn>
          </>
        )}
        <div style={{ flex: 1 }} />
        <Btn danger onClick={() => setShowReset(true)} disabled={busy}>
          {busy ? '…' : 'Reset DB'}
        </Btn>
      </div>
    </>
  )
}
