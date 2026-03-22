import { useRef, useState, useEffect, useCallback, useMemo } from 'react'
import { createPortal } from 'react-dom'
import { useSimStore } from '../../store/simStore'
import type { GraphD3Node, GraphD3Link } from '../../types'

const C = {
  bg: '#f5f5f7',
  decade:      '#0071e3',
  winning:     '#34c759',
  fork:        '#ff9500',
  dead:        '#aeaeb2',
  etnia:       '#5856d6',
  gov:         '#af52de',
  interno:     '#bf5af2',
  diplomatico: '#0a84ff',
  guerra:      '#ff453a',
  evento:      '#30d158',
  decisione:   '#ffd60a',
  edge:        '#d1d1d6',
  edgeFork:    '#ff9500',
}

interface PopupData { kind: string; title: string; subtitle?: string; detail: string; extra?: string }
interface AgentInfo {
  etnia: string; is_politica: boolean; prestigio: number
  economia: number; militare: number
  dialoghi_interni: Record<string,unknown>[]
  dialoghi_diplomatici: Record<string,unknown>[]
}
interface HitRecord {
  kind: 'decade'|'etnia'|'child'
  nodeId: string
  etniaKey?: string
  popup?: PopupData
}

const R_DECADE = 20
const R_ETNIA  = 11
const R_CHILD  = 7
const ORBT_E   = 140
const ORBT_C   = 80

function decadeColor(n: GraphD3Node) {
  if (n.fork_status === 'dead')    return C.dead
  if (n.fork_status === 'winning') return C.winning
  if (n.fork_id)                   return C.fork
  return C.decade
}

function buildLayout(nodes: GraphD3Node[]): Map<string,{x:number,y:number}> {
  const pos = new Map<string,{x:number,y:number}>()
  if (!nodes.length) return pos
  const groups = new Map<string, GraphD3Node[]>()
  for (const n of nodes) {
    const k = n.fork_id ?? 'main'
    if (!groups.has(k)) groups.set(k,[])
    groups.get(k)!.push(n)
  }
  const keys = Array.from(groups.keys())
  const maxD = Math.max(...nodes.map(n=>n.decade),1)
  const W = 3200, H = 500
  keys.forEach((k,fi) => {
    const grp = groups.get(k)!.sort((a,b)=>a.decade-b.decade)
    const yBase = H/2 + (fi===0 ? 0 : (fi%2===0?1:-1)*Math.ceil(fi/2)*260)
    grp.forEach(n => {
      pos.set(n.id, { x: 100+(n.decade/maxD)*(W-200), y: yBase })
    })
  })
  return pos
}

function Popup({ data, onClose }: { data: PopupData|null; onClose: ()=>void }) {
  if (!data) return null
  const colorMap: Record<string,string> = {
    decade:C.decade, etnia:C.etnia, gov:C.gov, interno:C.interno,
    diplomatico:C.diplomatico, guerra:C.guerra, evento:C.evento, decisione:C.decisione,
  }
  const col = colorMap[data.kind] ?? C.decade
  return createPortal(
    <div onClick={onClose} style={{
      position:'fixed',inset:0,zIndex:99999,
      display:'flex',alignItems:'center',justifyContent:'center',
      background:'rgba(0,0,0,0.22)',backdropFilter:'blur(6px)',
      WebkitBackdropFilter:'blur(6px)',padding:20,
    }}>
      <div onClick={e=>e.stopPropagation()} style={{
        background:'#fff',borderRadius:16,padding:28,
        width:'100%',maxWidth:440,
        boxShadow:'0 24px 60px rgba(0,0,0,0.14)',
      }}>
        <div style={{display:'inline-flex',alignItems:'center',gap:6,
          background:`${col}15`,borderRadius:8,padding:'4px 10px',marginBottom:14}}>
          <div style={{width:8,height:8,borderRadius:'50%',background:col}}/>
          <span style={{fontSize:11,fontWeight:600,color:col,textTransform:'uppercase',letterSpacing:0.5}}>
            {data.kind}
          </span>
        </div>
        <div style={{fontSize:17,fontWeight:700,color:'#1d1d1f',marginBottom:4,letterSpacing:-0.3}}>
          {data.title}
        </div>
        {data.subtitle && <div style={{fontSize:12,color:'#6e6e73',marginBottom:12}}>{data.subtitle}</div>}
        <div style={{fontSize:14,color:'#3a3a3c',lineHeight:1.7}}>{data.detail||'Nessun dettaglio.'}</div>
        {data.extra && (
          <div style={{marginTop:12,padding:'10px 14px',background:'#f5f5f7',
            borderRadius:10,fontSize:13,color:'#6e6e73'}}>{data.extra}</div>
        )}
        <button onClick={onClose} style={{marginTop:20,width:'100%',padding:'10px 0',
          background:'#f5f5f7',border:'none',borderRadius:10,
          fontSize:14,fontWeight:500,color:'#1d1d1f',cursor:'pointer'}}>Chiudi</button>
      </div>
    </div>,
    document.body
  )
}

export default function Graph2D() {
  const { graphNodes, graphLinks, selectedNodeId, selectNode } = useSimStore()
  const canvasRef    = useRef<HTMLCanvasElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const camRef       = useRef({ px: 0, py: 0, zoom: 1 })
  const dragging     = useRef(false)
  const dragStart    = useRef({ mx:0, my:0, px:0, py:0 })
  const didDrag      = useRef(false)

  const [selNode,  setSelNode]  = useState<string|null>(null)
  const [selEtnia, setSelEtnia] = useState<string|null>(null)
  const [popup,    setPopup]    = useState<PopupData|null>(null)
  const [, setTick] = useState(0)
  const redraw = () => setTick(t=>t+1)

  const layout = useMemo(() => buildLayout(graphNodes), [graphNodes])

  const w2s = (wx:number, wy:number) => {
    const {px,py,zoom} = camRef.current
    return { x: wx*zoom+px, y: wy*zoom+py }
  }

  const etniasAngle = (i:number, total:number) => {
    const spread = Math.min(Math.PI*0.85, total*0.38)
    return (Math.PI/2) + (total>1 ? -spread/2 + (i/(total-1))*spread : 0)
  }

  const draw = useCallback(() => {
    const canvas = canvasRef.current; if (!canvas) return
    const ctx = canvas.getContext('2d')!
    const {zoom} = camRef.current

    ctx.clearRect(0,0,canvas.width,canvas.height)
    ctx.fillStyle = C.bg
    ctx.fillRect(0,0,canvas.width,canvas.height)

    // Edges
    graphLinks.forEach(lnk => {
      const a=layout.get(lnk.source), b=layout.get(lnk.target); if(!a||!b) return
      const sa=w2s(a.x,a.y), sb=w2s(b.x,b.y)
      ctx.beginPath()
      if (lnk.type==='fork_origin') {
        const mx=(sa.x+sb.x)/2, my=Math.min(sa.y,sb.y)-70*zoom
        ctx.moveTo(sa.x,sa.y); ctx.quadraticCurveTo(mx,my,sb.x,sb.y)
        ctx.strokeStyle=C.edgeFork; ctx.lineWidth=1.8*zoom; ctx.setLineDash([7*zoom,4*zoom])
      } else {
        ctx.moveTo(sa.x,sa.y); ctx.lineTo(sb.x,sb.y)
        ctx.strokeStyle=C.edge; ctx.lineWidth=1.4*zoom; ctx.setLineDash([])
      }
      ctx.globalAlpha=0.5; ctx.stroke(); ctx.setLineDash([]); ctx.globalAlpha=1
    })

    // Nodes
    graphNodes.forEach(node => {
      const wp=layout.get(node.id); if(!wp) return
      const sp=w2s(wp.x,wp.y)
      const isSel=selNode===node.id
      const col=decadeColor(node)
      const r=R_DECADE*zoom
      const agenti: AgentInfo[] = ((node as unknown as Record<string,unknown>).agenti_info as AgentInfo[])||[]

      if (isSel) {
        agenti.forEach((ag,i) => {
          const angle=etniasAngle(i,agenti.length)
          const ex=sp.x+Math.cos(angle)*ORBT_E*zoom
          const ey=sp.y+Math.sin(angle)*ORBT_E*zoom
          const er=R_ETNIA*zoom
          const eCol=ag.is_politica ? C.gov : C.etnia
          const etniaKey=`${node.id}::${ag.etnia}`
          const isEtniaSel=selEtnia===etniaKey

          // Line decade -> etnia
          ctx.beginPath(); ctx.moveTo(sp.x,sp.y); ctx.lineTo(ex,ey)
          ctx.strokeStyle=eCol; ctx.lineWidth=1*zoom; ctx.globalAlpha=0.22; ctx.stroke(); ctx.globalAlpha=1

          if (isEtniaSel) {
            // Glow
            ctx.beginPath(); ctx.arc(ex,ey,er+5*zoom,0,Math.PI*2)
            ctx.strokeStyle=eCol; ctx.lineWidth=2*zoom; ctx.globalAlpha=0.3; ctx.stroke(); ctx.globalAlpha=1

            // Build children for this etnia
            type Child = {label:string,col:string,shape:'circle'|'square'|'diamond',popup:PopupData}
            const children: Child[] = []

            ag.dialoghi_interni.slice(0,4).forEach(d => {
              const dl=d as Record<string,unknown>
              children.push({
                label: String(dl.tema||'Dialogo').slice(0,10),
                col: C.interno, shape:'diamond',
                popup:{ kind:'interno', title:'Dialogo interno - '+ag.etnia,
                  subtitle:'Tema: '+String(dl.tema||'?'),
                  detail: String(dl.contenuto||'Nessun contenuto.'),
                  extra: dl.esito ? 'Esito: '+String(dl.esito) : undefined },
              })
            })

            ag.dialoghi_diplomatici.slice(0,3).forEach(d => {
              const dl=d as Record<string,unknown>
              children.push({
                label: String(dl.tema||'Diplomazia').slice(0,10),
                col: C.diplomatico, shape:'square',
                popup:{ kind:'diplomatico', title:'Diplomazia - '+ag.etnia,
                  subtitle: String(dl.societa||''),
                  detail: String(dl.contenuto||'Nessun contenuto.'),
                  extra: dl.esito ? 'Esito: '+String(dl.esito)+(dl.termini?' - '+String(dl.termini).slice(0,80):'') : undefined },
              })
            })

            children.push({
              label:'Stato',
              col: C.decisione, shape:'circle',
              popup:{ kind:'etnia', title:'Stato - '+ag.etnia,
                subtitle: ag.is_politica ? 'Governo / Istituzione' : 'Popolazione',
                detail: 'Prestigio: '+(ag.prestigio*100).toFixed(0)+'%\nEconomia: '+(ag.economia*100).toFixed(0)+'%\nMilitare: '+(ag.militare*100).toFixed(0)+'%' },
            })

            children.forEach((ch,ci) => {
              const ca=angle+(ci-(children.length-1)/2)*0.65
              const cr=R_CHILD*zoom
              const cex=ex+Math.cos(ca)*ORBT_C*zoom
              const cey=ey+Math.sin(ca)*ORBT_C*zoom

              ctx.beginPath(); ctx.moveTo(ex,ey); ctx.lineTo(cex,cey)
              ctx.strokeStyle=ch.col; ctx.lineWidth=0.8*zoom; ctx.globalAlpha=0.22; ctx.stroke(); ctx.globalAlpha=1

              ctx.fillStyle=ch.col; ctx.globalAlpha=0.92
              if (ch.shape==='circle') {
                ctx.beginPath(); ctx.arc(cex,cey,cr,0,Math.PI*2); ctx.fill()
              } else if (ch.shape==='square') {
                ctx.fillRect(cex-cr,cey-cr,cr*2,cr*2)
              } else {
                ctx.save(); ctx.translate(cex,cey); ctx.rotate(Math.PI/4)
                ctx.fillRect(-cr*0.85,-cr*0.85,cr*1.7,cr*1.7); ctx.restore()
              }
              ctx.globalAlpha=1

              ctx.fillStyle=ch.col
              ctx.font=Math.max(7,8*zoom)+'px -apple-system,sans-serif'
              ctx.textAlign='center'; ctx.textBaseline='bottom'
              ctx.fillText(ch.label, cex, cey-cr-2*zoom)
            })
          }

          // Etnia circle (drawn after children so it's on top)
          ctx.beginPath(); ctx.arc(ex,ey,er,0,Math.PI*2)
          ctx.fillStyle=eCol; ctx.globalAlpha=isEtniaSel?1:0.82; ctx.fill()
          if (isEtniaSel) { ctx.strokeStyle='#fff'; ctx.lineWidth=2*zoom; ctx.stroke() }
          ctx.globalAlpha=1

          ctx.fillStyle=eCol
          ctx.font=Math.max(8,9*zoom)+'px -apple-system,sans-serif'
          ctx.textAlign='center'; ctx.textBaseline='top'
          ctx.fillText(ag.etnia.slice(0,14), ex, ey+er+3*zoom)
        })
      }

      // Main decade circle
      if (isSel) { ctx.save(); ctx.shadowBlur=18*zoom; ctx.shadowColor=col }
      ctx.beginPath(); ctx.arc(sp.x,sp.y,r,0,Math.PI*2)
      ctx.fillStyle=col; ctx.globalAlpha=isSel?1:0.88; ctx.fill()
      if (isSel) { ctx.restore(); ctx.strokeStyle='#fff'; ctx.lineWidth=2.5*zoom; ctx.stroke() }
      ctx.globalAlpha=1

      ctx.fillStyle=isSel?'#1d1d1f':'#6e6e73'
      ctx.font=Math.max(9,11*zoom)+'px -apple-system,sans-serif'
      ctx.textAlign='center'; ctx.textBaseline='bottom'
      ctx.fillText(node.decade+' d.C.', sp.x, sp.y-r-4*zoom)

      if (isSel && node.etnia_dominante) {
        ctx.fillStyle=col
        ctx.font='600 '+Math.max(8,10*zoom)+'px -apple-system,sans-serif'
        ctx.fillText(node.etnia_dominante, sp.x, sp.y-r-16*zoom)
      }

      // Badge count
      if (!isSel && agenti.length>0) {
        const bx=sp.x+r*0.72, by=sp.y-r*0.72, br=7*zoom
        ctx.beginPath(); ctx.arc(bx,by,br,0,Math.PI*2)
        ctx.fillStyle='#fff'; ctx.fill()
        ctx.strokeStyle=col; ctx.lineWidth=1*zoom; ctx.stroke()
        ctx.fillStyle=col
        ctx.font='600 '+Math.max(7,9*zoom)+'px -apple-system,sans-serif'
        ctx.textAlign='center'; ctx.textBaseline='middle'
        ctx.fillText(String(agenti.length), bx, by)
      }
    })
  }, [graphNodes, graphLinks, layout, selNode, selEtnia])

  useEffect(() => {
    const resize = () => {
      const c=canvasRef.current, d=containerRef.current; if(!c||!d) return
      c.width=d.clientWidth; c.height=d.clientHeight; draw()
    }
    resize()
    window.addEventListener('resize',resize)
    return ()=>window.removeEventListener('resize',resize)
  },[draw])

  useEffect(()=>{ draw() },[draw])

  const hitTest = useCallback((sx:number,sy:number): HitRecord|null => {
    const {px,py,zoom}=camRef.current
    const s2=(wx:number,wy:number)=>({x:wx*zoom+px,y:wy*zoom+py})
    const d=(ax:number,ay:number,bx:number,by:number)=>Math.hypot(ax-bx,ay-by)

    for (const node of graphNodes) {
      const wp=layout.get(node.id); if(!wp) continue
      const sp=s2(wp.x,wp.y)
      const r=R_DECADE*zoom
      const agenti: AgentInfo[] = ((node as unknown as Record<string,unknown>).agenti_info as AgentInfo[])||[]

      if (selNode===node.id) {
        for (let i=0;i<agenti.length;i++) {
          const ag=agenti[i]
          const angle=etniasAngle(i,agenti.length)
          const ex=sp.x+Math.cos(angle)*ORBT_E*zoom
          const ey=sp.y+Math.sin(angle)*ORBT_E*zoom
          const etniaKey=`${node.id}::${ag.etnia}`

          if (selEtnia===etniaKey) {
            const children: {popup:PopupData}[] = []
            ag.dialoghi_interni.slice(0,4).forEach(dl2 => {
              const dl=dl2 as Record<string,unknown>
              children.push({popup:{kind:'interno',title:'Dialogo interno - '+ag.etnia,subtitle:'Tema: '+String(dl.tema||'?'),detail:String(dl.contenuto||''),extra:dl.esito?'Esito: '+String(dl.esito):undefined}})
            })
            ag.dialoghi_diplomatici.slice(0,3).forEach(dl2 => {
              const dl=dl2 as Record<string,unknown>
              children.push({popup:{kind:'diplomatico',title:'Diplomazia - '+ag.etnia,subtitle:String(dl.societa||''),detail:String(dl.contenuto||''),extra:dl.esito?'Esito: '+String(dl.esito):undefined}})
            })
            children.push({popup:{kind:'etnia',title:'Stato - '+ag.etnia,subtitle:ag.is_politica?'Governo':'Popolazione',detail:'Prestigio: '+(ag.prestigio*100).toFixed(0)+'%\nEconomia: '+(ag.economia*100).toFixed(0)+'%\nMilitare: '+(ag.militare*100).toFixed(0)+'%'}})

            for (let ci=0;ci<children.length;ci++) {
              const ca=angle+(ci-(children.length-1)/2)*0.65
              const cex=ex+Math.cos(ca)*ORBT_C*zoom
              const cey=ey+Math.sin(ca)*ORBT_C*zoom
              if (d(sx,sy,cex,cey)<R_CHILD*zoom+6) return {kind:'child',nodeId:node.id,etniaKey,popup:children[ci].popup}
            }
          }

          if (d(sx,sy,ex,ey)<R_ETNIA*zoom+4) return {kind:'etnia',nodeId:node.id,etniaKey}
        }
      }

      if (d(sx,sy,sp.x,sp.y)<r+4) return {kind:'decade',nodeId:node.id}
    }
    return null
  },[graphNodes,layout,selNode,selEtnia])

  const onMouseDown = useCallback((e: React.MouseEvent) => {
    if (e.button!==0) return
    dragging.current=true; didDrag.current=false
    dragStart.current={mx:e.clientX,my:e.clientY,px:camRef.current.px,py:camRef.current.py}
  },[])

  const onMouseMove = useCallback((e: React.MouseEvent) => {
    if (!dragging.current) return
    const dx=e.clientX-dragStart.current.mx, dy=e.clientY-dragStart.current.my
    if (Math.abs(dx)>3||Math.abs(dy)>3) didDrag.current=true
    camRef.current.px=dragStart.current.px+dx
    camRef.current.py=dragStart.current.py+dy
    draw()
  },[draw])

  const onMouseUp = useCallback((e: React.MouseEvent) => {
    dragging.current=false
    if (didDrag.current) return
    const rect=canvasRef.current!.getBoundingClientRect()
    const hit=hitTest(e.clientX-rect.left,e.clientY-rect.top)
    if (!hit) { setSelNode(null); setSelEtnia(null); selectNode(null); redraw(); return }
    if (hit.kind==='decade') {
      const n=hit.nodeId===selNode?null:hit.nodeId
      setSelNode(n); setSelEtnia(null); selectNode(n); redraw()
    } else if (hit.kind==='etnia') {
      setSelEtnia(prev=>prev===hit.etniaKey?null:hit.etniaKey!); redraw()
    } else if (hit.kind==='child') {
      if (hit.popup) setPopup(hit.popup)
    }
  },[hitTest,selNode,selEtnia,selectNode])

  const onMouseLeave = useCallback(()=>{ dragging.current=false },[])

  const onWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault()
    const rect=canvasRef.current!.getBoundingClientRect()
    const mx=e.clientX-rect.left, my=e.clientY-rect.top
    const f=e.deltaY<0?1.13:0.88
    const {px,py,zoom}=camRef.current
    const nz=Math.max(0.12,Math.min(6,zoom*f))
    camRef.current={px:mx-(mx-px)*(nz/zoom),py:my-(my-py)*(nz/zoom),zoom:nz}
    draw()
  },[draw])

  const onMouseMoveCanvas = useCallback((e: React.MouseEvent) => {
    onMouseMove(e)
    if (!dragging.current) {
      const rect=canvasRef.current!.getBoundingClientRect()
      const hit=hitTest(e.clientX-rect.left,e.clientY-rect.top)
      if (canvasRef.current) canvasRef.current.style.cursor=hit?'pointer':'grab'
    } else {
      if (canvasRef.current) canvasRef.current.style.cursor='grabbing'
    }
  },[onMouseMove,hitTest])

  const zoomBtns = [
    {t:'+', fn:()=>{camRef.current.zoom=Math.min(6,camRef.current.zoom*1.2);draw()}},
    {t:'-', fn:()=>{camRef.current.zoom=Math.max(0.12,camRef.current.zoom*0.8);draw()}},
    {t:'R', fn:()=>{camRef.current={px:0,py:0,zoom:1};draw()}},
  ]

  return (
    <div ref={containerRef} style={{width:'100%',height:'100%',position:'relative',overflow:'hidden'}}>
      {graphNodes.length===0 && (
        <div style={{position:'absolute',inset:0,display:'flex',flexDirection:'column',
          alignItems:'center',justifyContent:'center',pointerEvents:'none'}}>
          <div style={{fontSize:36,opacity:0.1,marginBottom:10}}>o</div>
          <div style={{fontSize:12,color:'#aeaeb2',letterSpacing:2,textTransform:'uppercase'}}>
            Avvia una simulazione
          </div>
        </div>
      )}

      {graphNodes.length>0 && (
        <div style={{position:'absolute',top:14,left:'50%',transform:'translateX(-50%)',
          fontSize:11,color:'#aeaeb2',pointerEvents:'none',
          background:'rgba(255,255,255,0.82)',padding:'4px 14px',
          borderRadius:20,backdropFilter:'blur(4px)',whiteSpace:'nowrap',zIndex:10}}>
          Trascina per muovere &nbsp;|&nbsp; Scroll per zoom &nbsp;|&nbsp; Clicca nodo &gt; etnie &gt; dialoghi
        </div>
      )}

      <canvas ref={canvasRef} style={{display:'block'}}
        onMouseDown={onMouseDown} onMouseMove={onMouseMoveCanvas}
        onMouseUp={onMouseUp} onMouseLeave={onMouseLeave} onWheel={onWheel}
      />

      <div style={{position:'absolute',bottom:14,left:14,display:'flex',gap:12,
        fontSize:11,color:'#6e6e73',flexWrap:'wrap',
        background:'rgba(255,255,255,0.85)',padding:'7px 14px',
        borderRadius:12,backdropFilter:'blur(4px)'}}>
        {([
          {l:'nodo',c:C.decade},{l:'fork',c:C.fork},{l:'vincente',c:C.winning},
          {l:'etnia',c:C.etnia},{l:'governo',c:C.gov},
          {l:'dialogo',c:C.interno},{l:'diplomazia',c:C.diplomatico},
          {l:'guerra',c:C.guerra},{l:'evento',c:C.evento},{l:'decisione',c:C.decisione},
        ] as {l:string,c:string}[]).map(({l,c})=>(
          <div key={l} style={{display:'flex',alignItems:'center',gap:4}}>
            <div style={{width:7,height:7,borderRadius:'50%',background:c}}/>{l}
          </div>
        ))}
      </div>

      <div style={{position:'absolute',bottom:14,right:14,display:'flex',flexDirection:'column',gap:4}}>
        {zoomBtns.map(({t,fn})=>(
          <button key={t} onClick={fn} style={{width:32,height:32,borderRadius:8,
            border:'1px solid #e5e5e7',background:'#fff',cursor:'pointer',
            fontSize:15,fontWeight:600,color:'#1d1d1f',
            display:'flex',alignItems:'center',justifyContent:'center',
            boxShadow:'0 1px 4px rgba(0,0,0,0.08)',fontFamily:'monospace'}}>
            {t}
          </button>
        ))}
      </div>

      <Popup data={popup} onClose={()=>setPopup(null)}/>
    </div>
  )
}
