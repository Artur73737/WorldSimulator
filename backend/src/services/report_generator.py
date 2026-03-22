"""
Final report generator: produces REPORT.md for the winning simulation.
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

REPORT_SYSTEM = """Sei uno storico che scrive report accademici dettagliati sulle simulazioni di civiltà antiche.
Stile formale, analitico, ricco di dettagli storici. Scrivi in italiano."""


async def generate_final_report(simulation_id: str, db: AsyncSession) -> str:
    """Generate REPORT.md for a completed simulation."""
    os.makedirs(settings.reports_dir, exist_ok=True)
    report_path = os.path.join(settings.reports_dir, f"{simulation_id}.md")

    # Load data
    sim_r = await db.execute(select(Simulation).where(Simulation.id == simulation_id))
    sim = sim_r.scalar_one_or_none()
    if not sim:
        raise ValueError(f"Simulation {simulation_id} not found")

    agents_r = await db.execute(select(Agent).where(Agent.simulation_id == simulation_id))
    agents = agents_r.scalars().all()

    nodes_r = await db.execute(
        select(GraphNode)
        .where(GraphNode.simulation_id == simulation_id)
        .order_by(GraphNode.decade.asc())
    )
    nodes = nodes_r.scalars().all()

    forks_r = await db.execute(select(Fork).where(Fork.simulation_id == simulation_id))
    forks = forks_r.scalars().all()

    # Winning fork
    winning_fork = next((f for f in forks if f.status == "winning"), None)

    # Build summary for LLM
    ethnies = [a.etnia for a in agents]
    node_summaries = [
        f"- Decade {n.decade}: {n.etnia_dominante} domina. Eco={n.metriche_stato.get('economia', '?'):.2f}, Mil={n.metriche_stato.get('militare', '?'):.2f}. {(n.mini_report or '')[:150]}"
        for n in nodes[:30]
    ]
    fork_summaries = [
        f"- Fork {f.id[:8]}: triggered da '{f.trigger_reason}' alla decade {f.created_at_decade}, status={f.status}, score={f.score}"
        for f in forks
    ]

    prompt = f"""Simulazione: {sim.initial_description}
Periodo simulato: decadi {nodes[0].decade if nodes else 0} - {nodes[-1].decade if nodes else 0} d.C.
Etnie coinvolte: {', '.join(ethnies)}
Fork create: {len(forks)} (vincitrice: {winning_fork.id[:8] if winning_fork else 'nessuna'})

Timeline eventi:
{chr(10).join(node_summaries)}

Fork history:
{chr(10).join(fork_summaries)}

Scrivi un REPORT.md completo con:
1. Sommario esecutivo (cosa è successo, chi ha vinto)
2. Analisi per etnia (punto di forza, momento di gloria, declino)
3. Crisi principali e come sono state gestite
4. Fork più significative e cosa hanno rivelato
5. Conclusioni storiche: cosa avrebbe potuto cambiare il destino
6. Statistiche finali (tabella markdown)

Usa markdown. Sii drammatico ma rigoroso."""

    try:
        report_content = await llm_client.call(
            prompt=prompt,
            system=REPORT_SYSTEM,
            max_tokens=4096,
            temperature=0.7,
        )
    except Exception as e:
        logger.error(f"LLM report generation failed: {e}")
        report_content = _fallback_report(sim, nodes, agents, forks)

    # Prepend header
    header = f"""# World Simulation — Report Finale
**Simulazione:** {simulation_id}
**Descrizione:** {sim.initial_description}
**Generato:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}
**Decadi simulate:** {len(nodes)} | **Fork totali:** {len(forks)}

---

"""
    full_report = header + report_content

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(full_report)

    # Mark simulation as completed
    sim.status = "completed"
    sim.is_locked = False
    db.add(sim)
    await db.commit()

    logger.info(f"Report generated: {report_path}")
    return full_report


def _fallback_report(sim, nodes, agents, forks) -> str:
    """Minimal report without LLM."""
    lines = [
        "## Sommario",
        f"Simulazione basata su: {sim.initial_description}",
        f"Decadi totali: {len(nodes)}",
        f"Agenti: {', '.join(a.etnia for a in agents)}",
        "",
        "## Timeline",
    ]
    for n in nodes:
        lines.append(f"- **{n.decade} d.C.** — {n.etnia_dominante}: {n.mini_report or 'nessun report'}")
    lines.append("")
    lines.append("## Fork")
    for f in forks:
        lines.append(f"- Fork `{f.id[:8]}`: {f.trigger_reason} (decade {f.created_at_decade}), status: {f.status}")
    return "\n".join(lines)
