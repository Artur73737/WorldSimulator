import { useSimStore } from '../store/simStore'

const Label = ({ children }: { children: React.ReactNode }) => (
  <div style={{ fontSize: 11, fontWeight: 600, color: '#aeaeb2', textTransform: 'uppercase' as const, letterSpacing: 0.6, marginBottom: 10 }}>
    {children}
  </div>
)

const Section = ({ title, children }: { title: string; children: React.ReactNode }) => (
  <div style={{ padding: '20px 20px 0' }}>
    <Label>{title}</Label>
    {children}
  </div>
)

const Bar = ({ value, color }: { value: number; color: string }) => (
  <div style={{ height: 3, background: '#f0f0f0', borderRadius: 99 }}>
    <div style={{ height: '100%', width: `${Math.min(100, Math.max(0, value * 100))}%`, background: color, borderRadius: 99, transition: 'width 0.6s' }} />
  </div>
)

const STATUS_COLOR: Record<string, string> = {
  running: '#34c759', paused: '#ff9500', completed: '#0071e3', failed: '#ff3b30',
}
const STATUS_LABEL: Record<string, string> = {
  running: 'In esecuzione', paused: 'In pausa', completed: 'Completata', failed: 'Errore',
}

export default function StatusPanel() {
  const { simulation, agents, selectedNodeId, graphNodes, forks, liveEvents, sseConnected } = useSimStore()
  const node = graphNodes.find(n => n.id === selectedNodeId)
  const activeForks = forks.filter(f => f.status === 'active').length
  const winFork = forks.find(f => f.status === 'winning')

  if (!simulation) return (
    <div style={{ padding: 24, textAlign: 'center', marginTop: 80, color: '#aeaeb2', fontSize: 13 }}>
      Nessuna simulazione attiva
    </div>
  )

  return (
    <div style={{ fontSize: 13, paddingBottom: 28 }}>

      {/* Header */}
      <div style={{ padding: '20px 20px 16px', borderBottom: '1px solid #f0f0f0' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8 }}>
          <div style={{
            width: 7, height: 7, borderRadius: '50%',
            background: STATUS_COLOR[simulation.status] ?? '#aeaeb2',
            boxShadow: simulation.status === 'running' ? `0 0 0 3px #34c75922` : 'none',
          }} />
          <span style={{ fontSize: 11, fontWeight: 600, color: '#6e6e73', textTransform: 'uppercase', letterSpacing: 0.5 }}>
            {STATUS_LABEL[simulation.status] ?? simulation.status}
          </span>
          {sseConnected && simulation.status === 'running' && (
            <span style={{ marginLeft: 'auto', fontSize: 11, fontWeight: 600, color: '#34c759' }}>● LIVE</span>
          )}
        </div>
        <div style={{ color: '#1d1d1f', lineHeight: 1.5, fontSize: 13 }}>
          {simulation.initial_description}
        </div>
      </div>

      {/* Decade */}
      <div style={{ margin: 16, background: '#f5f5f7', borderRadius: 12, padding: '14px 16px' }}>
        <div style={{ fontSize: 11, fontWeight: 600, color: '#aeaeb2', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 2 }}>
          Decade corrente
        </div>
        <div style={{ fontSize: 30, fontWeight: 300, color: '#1d1d1f', letterSpacing: -1 }}>
          {simulation.current_decade}
          <span style={{ fontSize: 13, fontWeight: 400, color: '#6e6e73', marginLeft: 4 }}>d.C.</span>
        </div>
        <div style={{ fontSize: 11, color: '#aeaeb2', marginTop: 2 }}>
          {activeForks} fork attive · {forks.length} totali · {graphNodes.length} nodi
        </div>
      </div>

      {/* Selected node */}
      {node && (
        <Section title={`Nodo ${node.decade} d.C.`}>
          {node.etnia_dominante && (
            <div style={{ fontWeight: 500, color: '#1d1d1f', marginBottom: 10 }}>{node.etnia_dominante}</div>
          )}
          <div style={{ marginBottom: 8 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: '#6e6e73', marginBottom: 4 }}>
              <span>Economia</span><span>{(node.economia * 100).toFixed(0)}%</span>
            </div>
            <Bar value={node.economia} color="#0071e3" />
          </div>
          <div style={{ marginBottom: 12 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: '#6e6e73', marginBottom: 4 }}>
              <span>Militare</span><span>{(node.militare * 100).toFixed(0)}%</span>
            </div>
            <Bar value={node.militare} color="#ff9500" />
          </div>
          {node.mini_report && (
            <div style={{ fontSize: 12, color: '#6e6e73', lineHeight: 1.6, borderTop: '1px solid #f0f0f0', paddingTop: 10 }}>
              {node.mini_report.slice(0, 300)}{node.mini_report.length > 300 ? '…' : ''}
            </div>
          )}
        </Section>
      )}

      {/* Agents */}
      {agents.length > 0 && (
        <Section title={`Agenti (${agents.length})`}>
          {agents.map(a => (
            <div key={a.id} style={{
              display: 'flex', alignItems: 'center', gap: 10,
              marginBottom: 8, padding: '10px 12px', background: '#f5f5f7', borderRadius: 10,
            }}>
              <div style={{
                width: 30, height: 30, borderRadius: '50%', flexShrink: 0,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 12, fontWeight: 700, color: '#fff',
                background: a.is_politica ? '#af52de' : '#0071e3',
              }}>{a.etnia[0]}</div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 12, fontWeight: 500, color: '#1d1d1f', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {a.etnia}
                </div>
                <div style={{ fontSize: 11, color: '#aeaeb2' }}>
                  Prestigio {(a.prestigio * 100).toFixed(0)}%{a.is_politica ? ' · governo' : ''}
                </div>
              </div>
            </div>
          ))}
        </Section>
      )}

      {/* Winning fork */}
      {winFork && (
        <Section title="Fork vincitrice">
          <div style={{ padding: '10px 12px', background: '#f0fdf4', borderRadius: 10, marginBottom: 0 }}>
            <div style={{ fontSize: 12, color: '#1d1d1f', fontWeight: 500 }}>{winFork.trigger_reason}</div>
            <div style={{ fontSize: 11, color: '#6e6e73', marginTop: 2 }}>
              Decade {winFork.created_at_decade} · score {winFork.score?.total?.toFixed(3) ?? '—'}
            </div>
          </div>
        </Section>
      )}

      {/* Events log */}
      {liveEvents.length > 0 && (
        <Section title="Log">
          <div style={{ maxHeight: 120, overflowY: 'auto' }}>
            {[...liveEvents].reverse().slice(0, 15).map((ev, i) => (
              <div key={i} style={{ fontSize: 11, color: '#6e6e73', padding: '4px 0', borderBottom: '1px solid #f5f5f7' }}>
                <span style={{ fontWeight: 600, color: ev.type === 'step_complete' ? '#0071e3' : '#ff9500' }}>
                  {ev.type}
                </span>
                {' '}{ev.type === 'step_complete' && `decade ${(ev.data as Record<string, unknown>).decade}`}
              </div>
            ))}
          </div>
        </Section>
      )}
    </div>
  )
}
