import { useSimStore } from '../store/simStore'

const Label = ({ children }: { children: React.ReactNode }) => (
  <div style={{ fontSize: 11, fontWeight: 600, color: '#aeaeb2', textTransform: 'uppercase' as const, letterSpacing: 0.6, marginBottom: 10 }}>
    {children}
  </div>
)

const ESITO_COLOR: Record<string, string> = {
  accordo: '#34c759', alleanza: '#34c759', pace: '#34c759', vittoria: '#34c759',
  conflitto: '#ff3b30', guerra: '#ff3b30', fallimento: '#ff3b30', sconfitta: '#ff3b30',
  compromesso: '#ff9500', sospeso: '#ff9500', tensione: '#ff9500', stallo: '#ff9500',
}

export default function AgentChat() {
  const { liveEvents, selectedNodeId, graphNodes, agents } = useSimStore()
  const node = graphNodes.find(n => n.id === selectedNodeId)
  const steps = liveEvents.filter(e => e.type === 'step_complete')

  // Estrai decisione dal nodo selezionato
  const dec = node?.decisione as Record<string, unknown> | null | undefined
  const proposta = dec ? (String(dec.proposta_vincente || dec.proposta || '')).trim() : ''
  const agente   = dec ? String(dec.agente_proposta || dec.agente || '') : ''
  const rationale = dec ? String(dec.rationale || '') : ''
  const supporto  = dec ? (dec.supporto as string[] || []) : []
  const opposizione = dec ? (dec.opposizione as string[] || []) : []

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', fontSize: 13 }}>

      {/* Header */}
      <div style={{ padding: '16px 20px', borderBottom: '1px solid #f0f0f0', flexShrink: 0 }}>
        <Label>Dibattito agenti</Label>
      </div>

      {/* Decisione nodo selezionato */}
      {node && (
        <div style={{ padding: '14px 20px', borderBottom: '1px solid #f0f0f0', flexShrink: 0, background: '#fafafa' }}>
          <div style={{ fontSize: 11, fontWeight: 600, color: '#0071e3', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 10 }}>
            Decisione — {node.decade} d.C.
          </div>

          {proposta ? (
            <>
              <div style={{ color: '#1d1d1f', fontWeight: 500, marginBottom: 4, lineHeight: 1.5 }}>
                {proposta}
              </div>
              {agente && (
                <div style={{ fontSize: 11, color: '#6e6e73', marginBottom: 8 }}>
                  Proposto da: <strong style={{ color: '#1d1d1f' }}>{agente}</strong>
                </div>
              )}
              {rationale && (
                <div style={{ fontSize: 12, color: '#6e6e73', lineHeight: 1.5, marginBottom: 10 }}>
                  {rationale.slice(0, 200)}{rationale.length > 200 ? '…' : ''}
                </div>
              )}
              {(supporto.length > 0 || opposizione.length > 0) && (
                <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                  {supporto.map(s => (
                    <span key={s} style={{ fontSize: 11, padding: '3px 8px', borderRadius: 6, background: '#e8f5e9', color: '#1a7f37', fontWeight: 500 }}>{s}</span>
                  ))}
                  {opposizione.map(s => (
                    <span key={s} style={{ fontSize: 11, padding: '3px 8px', borderRadius: 6, background: '#fff0ef', color: '#cc0000', fontWeight: 500 }}>{s}</span>
                  ))}
                </div>
              )}
            </>
          ) : (
            <div style={{ color: '#aeaeb2', fontSize: 12 }}>
              Clicca un nodo nel grafo per vedere la decisione
            </div>
          )}
        </div>
      )}

      {/* Agenti */}
      <div style={{ padding: '14px 20px', borderBottom: '1px solid #f0f0f0', flexShrink: 0 }}>
        <Label>Agenti</Label>
        {agents.length === 0 && <div style={{ color: '#aeaeb2', fontSize: 12 }}>Nessun agente</div>}
        {agents.map(a => (
          <div key={a.id} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 12px', background: '#f5f5f7', borderRadius: 10, marginBottom: 6 }}>
            <div style={{
              width: 28, height: 28, borderRadius: '50%', flexShrink: 0,
              background: a.is_politica ? '#af52de' : '#0071e3',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              color: '#fff', fontSize: 11, fontWeight: 700,
            }}>{a.etnia[0]}</div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: 12, fontWeight: 500, color: '#1d1d1f', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {a.etnia}
              </div>
              <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
                {[['ECO', a.stato_corrente.economia ?? 0.5, '#0071e3'], ['MIL', a.stato_corrente.militare ?? 0.5, '#ff9500']].map(([l, v, col]) => (
                  <div key={l as string} style={{ flex: 1 }}>
                    <div style={{ fontSize: 9, color: '#aeaeb2', fontWeight: 600, marginBottom: 2, textTransform: 'uppercase' }}>{l}</div>
                    <div style={{ height: 2, background: '#e5e5e7', borderRadius: 99 }}>
                      <div style={{ height: '100%', width: `${(v as number) * 100}%`, background: col as string, borderRadius: 99 }} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
            <div style={{ fontSize: 11, color: '#aeaeb2', flexShrink: 0 }}>
              {(a.prestigio * 100).toFixed(0)}
            </div>
          </div>
        ))}
      </div>

      {/* Feed live */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '14px 20px' }}>
        <Label>Feed live</Label>
        {steps.length === 0 && (
          <div style={{ color: '#aeaeb2', fontSize: 12, textAlign: 'center', marginTop: 24 }}>
            In attesa di eventi…
          </div>
        )}
        {[...steps].reverse().map((ev, i) => {
          const d = ev.data as Record<string, unknown>
          return (
            <div key={i} style={{
              marginBottom: 8, padding: '10px 14px', background: '#f5f5f7',
              borderRadius: 10, borderLeft: `3px solid ${d.crisis ? '#ff3b30' : '#0071e3'}`,
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                <span style={{ fontSize: 12, fontWeight: 600, color: '#0071e3' }}>{String(d.decade)} d.C.</span>
                {d.crisis && (
                  <span style={{ fontSize: 10, fontWeight: 600, color: '#ff3b30', textTransform: 'uppercase' }}>
                    ⚡ {String(d.crisis).replace(/_/g, ' ')}
                  </span>
                )}
              </div>
              <div style={{ fontSize: 12, color: '#1d1d1f', marginBottom: 3 }}>
                {String(d.etnia_dominante || '—')}
              </div>
              {d.metriche && (
                <div style={{ fontSize: 11, color: '#aeaeb2' }}>
                  Eco {((d.metriche as Record<string, number>).economia * 100).toFixed(0)}%
                  · Mil {((d.metriche as Record<string, number>).militare * 100).toFixed(0)}%
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
