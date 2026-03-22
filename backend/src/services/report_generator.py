"""
Final report generator: produces a styled HTML report for the simulation.
"""
import logging
import os
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.models.simulation import Simulation
from src.models.agent import Agent
from src.models.graph_node import GraphNode
from src.models.fork import Fork
from src.services.llm_client import llm_client
from src.config import settings

logger = logging.getLogger(__name__)

ANALYSIS_SYSTEM = """Sei uno storico accademico specializzato in civilta antiche.
Scrivi in italiano, stile formale e analitico. Usa paragrafi lunghi e articolati.
Niente emoji. Niente elenchi puntati generici. Solo prosa storica densa e precisa."""


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>World Simulation Report</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Helvetica Neue', Arial, sans-serif;
    background: #f5f5f7;
    color: #1d1d1f;
    line-height: 1.75;
    font-size: 15px;
  }}
  .page {{
    max-width: 900px;
    margin: 0 auto;
    padding: 60px 40px;
  }}
  /* Header */
  .report-header {{
    border-bottom: 3px solid #0071e3;
    padding-bottom: 32px;
    margin-bottom: 48px;
  }}
  .report-label {{
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: #6e6e73;
    margin-bottom: 10px;
  }}
  .report-title {{
    font-size: 34px;
    font-weight: 700;
    color: #0071e3;
    letter-spacing: -0.5px;
    margin-bottom: 8px;
    line-height: 1.2;
  }}
  .report-description {{
    font-size: 17px;
    color: #3a3a3c;
    font-style: italic;
    margin-bottom: 20px;
  }}
  .report-meta {{
    display: flex;
    gap: 32px;
    font-size: 13px;
    color: #6e6e73;
    flex-wrap: wrap;
  }}
  .report-meta span strong {{ color: #1d1d1f; }}

  /* Sections */
  .section {{ margin-bottom: 56px; }}
  .section-title {{
    font-size: 22px;
    font-weight: 700;
    color: #0071e3;
    letter-spacing: -0.3px;
    margin-bottom: 6px;
    padding-bottom: 8px;
    border-bottom: 1px solid #d2d2d7;
  }}
  .section-subtitle {{
    font-size: 16px;
    font-weight: 600;
    color: #1d1d1f;
    margin: 28px 0 10px;
  }}
  .subsection-title {{
    font-size: 14px;
    font-weight: 600;
    color: #0071e3;
    margin: 22px 0 8px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }}
  p {{ margin-bottom: 14px; color: #3a3a3c; }}

  /* Stats bar */
  .stats-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 16px;
    margin: 24px 0;
  }}
  .stat-card {{
    background: #fff;
    border-radius: 12px;
    padding: 18px 20px;
    border: 1px solid #e5e5e7;
  }}
  .stat-label {{ font-size: 11px; font-weight: 600; color: #6e6e73; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px; }}
  .stat-value {{ font-size: 26px; font-weight: 300; color: #0071e3; letter-spacing: -0.5px; }}
  .stat-unit {{ font-size: 13px; color: #6e6e73; }}

  /* Tables */
  table {{
    width: 100%;
    border-collapse: collapse;
    margin: 20px 0 28px;
    font-size: 13px;
    background: #fff;
    border-radius: 10px;
    overflow: hidden;
    box-shadow: 0 1px 4px rgba(0,0,0,0.07);
  }}
  thead tr {{ background: #0071e3; color: #fff; }}
  thead th {{ padding: 11px 14px; text-align: left; font-weight: 600; font-size: 12px; letter-spacing: 0.3px; }}
  tbody tr {{ border-bottom: 1px solid #f0f0f0; }}
  tbody tr:last-child {{ border-bottom: none; }}
  tbody td {{ padding: 10px 14px; color: #3a3a3c; }}
  tbody tr:nth-child(even) {{ background: #fafafa; }}

  /* Mini report cards */
  .decade-card {{
    background: #fff;
    border-radius: 14px;
    border: 1px solid #e5e5e7;
    margin-bottom: 24px;
    overflow: hidden;
  }}
  .decade-card-header {{
    background: linear-gradient(135deg, #0071e3, #34aadc);
    padding: 14px 20px;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }}
  .decade-year {{ color: #fff; font-size: 17px; font-weight: 700; }}
  .decade-dominant {{ color: rgba(255,255,255,0.85); font-size: 13px; }}
  .decade-card-body {{ padding: 18px 20px; }}
  .decade-metrics {{
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 12px;
    margin-bottom: 14px;
  }}
  .metric-item {{ text-align: center; }}
  .metric-bar-bg {{ height: 4px; background: #f0f0f0; border-radius: 2px; margin-top: 4px; }}
  .metric-bar {{ height: 4px; border-radius: 2px; transition: width 0.3s; }}
  .metric-name {{ font-size: 10px; color: #6e6e73; text-transform: uppercase; letter-spacing: 0.5px; }}
  .metric-val {{ font-size: 14px; font-weight: 600; color: #1d1d1f; }}
  .decade-report-text {{ font-size: 13px; color: #3a3a3c; line-height: 1.65; border-top: 1px solid #f0f0f0; padding-top: 14px; margin-top: 4px; }}

  /* Agent cards */
  .agent-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 16px; margin: 20px 0; }}
  .agent-card {{
    background: #fff;
    border-radius: 12px;
    padding: 18px;
    border: 1px solid #e5e5e7;
  }}
  .agent-name {{ font-size: 15px; font-weight: 600; color: #1d1d1f; margin-bottom: 4px; }}
  .agent-role {{ font-size: 11px; color: #6e6e73; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 12px; }}
  .agent-bar-row {{ display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }}
  .agent-bar-label {{ font-size: 11px; color: #6e6e73; width: 60px; }}
  .agent-bar-bg {{ flex: 1; height: 3px; background: #f0f0f0; border-radius: 2px; }}
  .agent-bar-fill {{ height: 100%; border-radius: 2px; }}
  .agent-prestige {{ font-size: 12px; color: #6e6e73; margin-top: 10px; }}

  /* Fork section */
  .fork-card {{
    background: #fff;
    border-radius: 12px;
    padding: 18px 20px;
    border-left: 4px solid #ff9500;
    margin-bottom: 16px;
    border-top: 1px solid #e5e5e7;
    border-right: 1px solid #e5e5e7;
    border-bottom: 1px solid #e5e5e7;
  }}
  .fork-card.winning {{ border-left-color: #34c759; }}
  .fork-card.dead {{ border-left-color: #aeaeb2; }}
  .fork-title {{ font-size: 14px; font-weight: 600; color: #1d1d1f; margin-bottom: 4px; }}
  .fork-meta {{ font-size: 12px; color: #6e6e73; margin-bottom: 10px; }}
  .fork-score {{ display: flex; gap: 16px; font-size: 12px; color: #6e6e73; }}
  .fork-score span strong {{ color: #1d1d1f; }}

  /* Analysis prose */
  .analysis-block {{
    background: #fff;
    border-radius: 14px;
    padding: 28px 32px;
    border: 1px solid #e5e5e7;
    margin: 20px 0;
  }}
  .analysis-block p {{ font-size: 15px; line-height: 1.8; }}

  /* Footer */
  .report-footer {{
    margin-top: 60px;
    padding-top: 24px;
    border-top: 1px solid #d2d2d7;
    font-size: 12px;
    color: #aeaeb2;
    text-align: center;
  }}
</style>
</head>
<body>
<div class="page">

  <!-- Header -->
  <div class="report-header">
    <div class="report-label">World Simulation &mdash; Report Finale</div>
    <h1 class="report-title">{title}</h1>
    <p class="report-description">{description}</p>
    <div class="report-meta">
      <span><strong>Generato:</strong> {generated}</span>
      <span><strong>Periodo:</strong> {period}</span>
      <span><strong>Decadi:</strong> {num_decades}</span>
      <span><strong>Fork:</strong> {num_forks}</span>
      <span><strong>Simulazione ID:</strong> {sim_id}</span>
    </div>
  </div>

  <!-- Stats -->
  <div class="section">
    <h2 class="section-title">Panoramica Statistica</h2>
    <div class="stats-grid">
      {stats_cards}
    </div>
  </div>

  <!-- Analysis -->
  <div class="section">
    <h2 class="section-title">Analisi Storica</h2>
    <div class="analysis-block">
      {analysis_html}
    </div>
  </div>

  <!-- Agents -->
  <div class="section">
    <h2 class="section-title">Profili delle Civilta</h2>
    <div class="agent-grid">
      {agent_cards}
    </div>
  </div>

  <!-- Timeline -->
  <div class="section">
    <h2 class="section-title">Cronologia Decennale</h2>
    <table>
      <thead>
        <tr>
          <th>Decade</th>
          <th>Etnia Dominante</th>
          <th>Economia</th>
          <th>Militare</th>
          <th>Popolazione</th>
          <th>Stabilita</th>
          <th>Eventi</th>
          <th>Guerre</th>
        </tr>
      </thead>
      <tbody>
        {timeline_rows}
      </tbody>
    </table>
  </div>

  <!-- Decade cards -->
  <div class="section">
    <h2 class="section-title">Cronache Decennali</h2>
    {decade_cards}
  </div>

  <!-- Forks -->
  {forks_section}

  <!-- Footer -->
  <div class="report-footer">
    World Simulation &mdash; Report generato automaticamente &mdash; {generated}
  </div>

</div>
</body>
</html>"""


def _pct(v: float) -> str:
    return f"{v:.0%}"

def _bar(v: float, color: str) -> str:
    w = int(max(0, min(100, v * 100)))
    return f'<div class="metric-bar-bg"><div class="metric-bar" style="width:{w}%;background:{color}"></div></div>'

def _stat_card(label: str, value: str, unit: str = "") -> str:
    return f'<div class="stat-card"><div class="stat-label">{label}</div><div class="stat-value">{value}<span class="stat-unit"> {unit}</span></div></div>'

def _agent_card(a: Agent) -> str:
    role = "Governo / Istituzione" if a.is_politica else "Popolazione"
    eco = a.stato_corrente.get("economia", 0.5)
    mil = a.stato_corrente.get("militare", 0.5)
    pop = a.stato_corrente.get("popolazione", 0.5)
    return f"""<div class="agent-card">
  <div class="agent-name">{a.etnia}</div>
  <div class="agent-role">{role}</div>
  <div class="agent-bar-row">
    <span class="agent-bar-label">Economia</span>
    <div class="agent-bar-bg"><div class="agent-bar-fill" style="width:{eco*100:.0f}%;background:#0071e3"></div></div>
    <span style="font-size:11px;color:#1d1d1f;width:32px">{eco:.0%}</span>
  </div>
  <div class="agent-bar-row">
    <span class="agent-bar-label">Militare</span>
    <div class="agent-bar-bg"><div class="agent-bar-fill" style="width:{mil*100:.0f}%;background:#ff9500"></div></div>
    <span style="font-size:11px;color:#1d1d1f;width:32px">{mil:.0%}</span>
  </div>
  <div class="agent-bar-row">
    <span class="agent-bar-label">Popol.</span>
    <div class="agent-bar-bg"><div class="agent-bar-fill" style="width:{pop*100:.0f}%;background:#34c759"></div></div>
    <span style="font-size:11px;color:#1d1d1f;width:32px">{pop:.0%}</span>
  </div>
  <div class="agent-prestige">Prestigio: <strong>{a.prestigio:.0%}</strong></div>
</div>"""

def _decade_card(n: GraphNode) -> str:
    eco = n.metriche_stato.get("economia", 0.5)
    mil = n.metriche_stato.get("militare", 0.5)
    pop = n.metriche_stato.get("popolazione", 0.5)
    pol = n.metriche_stato.get("politica", {})
    stab = pol.get("stabilita", 0.5) if isinstance(pol, dict) else 0.5
    eventi_count = len(n.eventi or [])
    guerre_count = len(n.guerre or [])
    dialoghi_count = len(n.dialoghi or [])
    report_text = (n.mini_report or "").strip()[:600]
    if len(n.mini_report or "") > 600:
        report_text += "..."

    dominant = n.etnia_dominante or "N/A"
    decisione = n.decisione or {}
    proposta = str(decisione.get("proposta_vincente", "")).strip()[:120] if decisione else ""

    return f"""<div class="decade-card">
  <div class="decade-card-header">
    <span class="decade-year">{n.decade} d.C.</span>
    <span class="decade-dominant">{dominant}</span>
  </div>
  <div class="decade-card-body">
    <div class="decade-metrics">
      <div class="metric-item">
        <div class="metric-name">Economia</div>
        <div class="metric-val">{eco:.0%}</div>
        {_bar(eco, '#0071e3')}
      </div>
      <div class="metric-item">
        <div class="metric-name">Militare</div>
        <div class="metric-val">{mil:.0%}</div>
        {_bar(mil, '#ff9500')}
      </div>
      <div class="metric-item">
        <div class="metric-name">Stabilita</div>
        <div class="metric-val">{stab:.0%}</div>
        {_bar(stab, '#34c759')}
      </div>
    </div>
    <div style="font-size:12px;color:#6e6e73;margin-bottom:10px">
      {eventi_count} eventi &nbsp;|&nbsp; {guerre_count} conflitti &nbsp;|&nbsp; {dialoghi_count} dialoghi
      {f'&nbsp;|&nbsp; <em>Decisione:</em> {proposta}' if proposta else ''}
    </div>
    {f'<div class="decade-report-text">{report_text}</div>' if report_text else ''}
  </div>
</div>"""

def _fork_card(f: Fork) -> str:
    score = f.score or {}
    css_class = "winning" if f.status == "winning" else ("dead" if f.status == "dead" else "")
    status_label = {"winning": "Vincitrice", "dead": "Estinta", "active": "Attiva"}.get(f.status, f.status)
    return f"""<div class="fork-card {css_class}">
  <div class="fork-title">Fork {f.id[:8]} &mdash; {f.trigger_reason.replace('_', ' ').title()}</div>
  <div class="fork-meta">Generata alla decade {f.created_at_decade} &nbsp;|&nbsp; Stato: <strong>{status_label}</strong></div>
  <div class="fork-score">
    <span>Longevita: <strong>{score.get('longevity', 0):.2f}</strong></span>
    <span>Resilienza: <strong>{score.get('resilience', 0):.2f}</strong></span>
    <span>Innovazione: <strong>{score.get('innovation', 0):.2f}</strong></span>
    <span>Score totale: <strong>{score.get('total', 0):.3f}</strong></span>
  </div>
</div>"""


async def generate_final_report(simulation_id: str, db: AsyncSession) -> str:
    """Generate styled HTML report for completed simulation."""
    os.makedirs(settings.reports_dir, exist_ok=True)
    report_path = os.path.join(settings.reports_dir, f"{simulation_id}.html")

    sim_r = await db.execute(select(Simulation).where(Simulation.id == simulation_id))
    sim = sim_r.scalar_one_or_none()
    if not sim:
        raise ValueError(f"Simulation {simulation_id} not found")

    agents_r = await db.execute(select(Agent).where(Agent.simulation_id == simulation_id))
    agents = agents_r.scalars().all()

    nodes_r = await db.execute(
        select(GraphNode).where(GraphNode.simulation_id == simulation_id).order_by(GraphNode.decade.asc())
    )
    nodes = nodes_r.scalars().all()

    forks_r = await db.execute(select(Fork).where(Fork.simulation_id == simulation_id))
    forks = forks_r.scalars().all()

    winning_fork = next((f for f in forks if f.status == "winning"), None)
    ethnies = [a.etnia for a in agents]
    total_events = sum(len(n.eventi or []) for n in nodes)
    total_wars = sum(len(n.guerre or []) for n in nodes)
    total_dialogs = sum(len(n.dialoghi or []) for n in nodes)
    start_decade = nodes[0].decade if nodes else 0
    end_decade = nodes[-1].decade if nodes else 0
    dominant_final = nodes[-1].etnia_dominante if nodes else "N/A"

    # ── LLM Analysis ────────────────────────────────────────────────────
    analysis_prompt = f"""Scrivi un'analisi storica accademica in prosa di questa simulazione di civilta antiche.

Periodo: {start_decade}-{end_decade} d.C.
Descrizione: {sim.initial_description}
Civilta coinvolte: {', '.join(ethnies)}
Decadi simulate: {len(nodes)}
Civilta dominante finale: {dominant_final}
Conflitti totali: {total_wars}
Fork generate: {len(forks)}

Dati per decade (breve):
{chr(10).join([f"- {n.decade} d.C.: {n.etnia_dominante}, eco={n.metriche_stato.get('economia',0):.0%}, mil={n.metriche_stato.get('militare',0):.0%}, {len(n.guerre or [])} guerre, decisione: {str(n.decisione.get('proposta_vincente','') if n.decisione else '')[:80]}" for n in nodes])}

Scrivi 5 sezioni in prosa (paragrafi completi, niente elenchi puntati):
1. Evoluzione del potere e dinamiche politiche
2. Conflitti militari e alleanze determinanti
3. Economia, demografia e crisi strutturali
4. Dialoghi diplomatici e tensioni sociali
5. Fattori determinanti e conclusione storica

Ogni sezione deve essere almeno 3 paragrafi. Stile accademico, formale, preciso."""

    try:
        analysis_text = await llm_client.call(
            prompt=analysis_prompt,
            system=ANALYSIS_SYSTEM,
            max_tokens=3000,
            temperature=0.65,
        )
        # Converti in HTML: sezioni numerate → titoli + paragrafi
        analysis_html = ""
        for line in analysis_text.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            import re
            if re.match(r"^[1-5]\.", line) or line.startswith("##"):
                clean = re.sub(r"^[#\d\.\s]+", "", line).strip()
                analysis_html += f'<h3 class="subsection-title">{clean}</h3>\n'
            else:
                analysis_html += f"<p>{line}</p>\n"
    except Exception as e:
        logger.error(f"LLM analysis failed: {e}")
        analysis_html = f"<p>Analisi non disponibile ({e}).</p>"

    # ── Build HTML sections ────────────────────────────────────────────
    stats_cards = (
        _stat_card("Decadi simulate", str(len(nodes)), "decadi") +
        _stat_card("Anni di storia", str(len(nodes) * 10), "anni") +
        _stat_card("Civilta", str(len(agents))) +
        _stat_card("Conflitti", str(total_wars)) +
        _stat_card("Dialoghi", str(total_dialogs)) +
        _stat_card("Fork generate", str(len(forks))) +
        _stat_card("Civilta dominante", dominant_final)
    )

    agent_cards = "".join(_agent_card(a) for a in agents)

    timeline_rows = ""
    for n in nodes:
        pol = n.metriche_stato.get("politica", {})
        stab = pol.get("stabilita", 0.5) if isinstance(pol, dict) else 0.5
        timeline_rows += f"""<tr>
          <td><strong>{n.decade}</strong></td>
          <td>{n.etnia_dominante or 'N/A'}</td>
          <td>{n.metriche_stato.get('economia', 0):.0%}</td>
          <td>{n.metriche_stato.get('militare', 0):.0%}</td>
          <td>{n.metriche_stato.get('popolazione', 0):.0%}</td>
          <td>{stab:.0%}</td>
          <td>{len(n.eventi or [])}</td>
          <td>{len(n.guerre or [])}</td>
        </tr>"""

    decade_cards = "".join(_decade_card(n) for n in nodes)

    if forks:
        forks_html = "".join(_fork_card(f) for f in sorted(forks, key=lambda x: x.score.get("total", 0) if x.score else 0, reverse=True))
        forks_section = f'<div class="section"><h2 class="section-title">Universi Paralleli &mdash; Fork</h2>{forks_html}</div>'
    else:
        forks_section = ""

    # ── Assemble HTML ──────────────────────────────────────────────────
    html = HTML_TEMPLATE.format(
        title=f"Simulazione Storica &mdash; {start_decade}&ndash;{end_decade} d.C.",
        description=sim.initial_description or "",
        generated=datetime.utcnow().strftime("%d %B %Y, %H:%M UTC"),
        period=f"{start_decade}&ndash;{end_decade} d.C.",
        num_decades=len(nodes),
        num_forks=len(forks),
        sim_id=simulation_id[:8],
        stats_cards=stats_cards,
        analysis_html=analysis_html,
        agent_cards=agent_cards,
        timeline_rows=timeline_rows,
        decade_cards=decade_cards,
        forks_section=forks_section,
    )

    # Save HTML
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(html)

    # Also save plain text version for API endpoint
    txt_path = os.path.join(settings.reports_dir, f"{simulation_id}.md")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(f"# World Simulation Report\n\n{sim.initial_description}\n\n")
        f.write(f"Periodo: {start_decade}-{end_decade} d.C. | Decadi: {len(nodes)} | Fork: {len(forks)}\n\n")
        f.write(analysis_text if 'analysis_text' in dir() else "")

    sim.status = "completed"
    sim.is_locked = False
    db.add(sim)
    await db.commit()

    logger.info(f"Report HTML generated: {report_path}")
    return html


def _fallback_report(sim, nodes, agents, forks) -> str:
    lines = ["<h2>Sommario</h2>", f"<p>{sim.initial_description}</p>", "<ul>"]
    for n in nodes:
        lines.append(f"<li><strong>{n.decade} d.C.</strong> &mdash; {n.etnia_dominante}: {(n.mini_report or '')[:120]}</li>")
    lines.append("</ul>")
    return "\n".join(lines)
