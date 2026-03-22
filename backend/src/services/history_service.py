"""
History service: generates detailed reports after each decade.
"""

import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.models.graph_node import GraphNode
from src.services.llm_client import llm_client

logger = logging.getLogger(__name__)


MINI_REPORT_SYSTEM = """Sei uno storico romano che scrive analisi dettagliate di decadi imperiali.
Stile narrativo, drammatico, in italiano antico/formale.
Includi dettagli su battaglie, intrighi politici, decisioni del senato.
Massimo 10 paragrafi. Nessun anacronismo moderno."""


async def generate_mini_report(
    node_id: str,
    db: AsyncSession,
    periodo: str = "epoca antica",
) -> str:
    """Generate a detailed historical report for a GraphNode."""
    result = await db.execute(select(GraphNode).where(GraphNode.id == node_id))
    node = result.scalar_one_or_none()
    if not node:
        return ""

    # Costruisci prompt dettagliato con tutti i dati
    eventi = node.eventi or []
    guerre = node.guerre or []
    dialoghi = node.dialoghi or []
    politica = node.politica_dettagliata or {}
    demografia = node.demografia or {}
    economia = node.economia_dettagliata or {}
    decisione = node.decisione or {}

    # Conta eventi per tipo
    eventi_count = {}
    for e in eventi:
        t = e.get("tipo", "altro")
        eventi_count[t] = eventi_count.get(t, 0) + 1

    prompt = f"""Scrivi un rapporto storico dettagliato per la decade {node.decade} d.C.

CONTESTO:
- Periodo: {node.decade - 10}-{node.decade} d.C.
- Etnia dominante: {node.etnia_dominante or "sconosciuta"}
- Sovrano: {politica.get("imperatore", "Sconosciuto")}
- Stabilita: {int(politica.get("stabilita", 0.5) * 100)}%

STATO DELLA CIVILTA:
- Economia: {int(node.metriche_stato.get("economia", 0.5) * 100)}%
- Militare: {int(node.metriche_stato.get("militare", 0.5) * 100)}%
- Popolazione: {demografia.get("popolazione_totale", "sconosciuta")}
- Legittimita: {int(politica.get("legittimita", 0.5) * 100)}%
- Corruzione: {int(politica.get("corruzione", 0.3) * 100)}%

EVENTI DEL DECENNIO ({len(eventi)} eventi totali):
{chr(10).join([f"- Anno {e.get('anno', '?')}: {e.get('descrizione', 'evento')} [{e.get('tipo', '?')}]" for e in eventi[:10]])}

CONFLITTI MILITARI ({len(guerre)} guerre):
{chr(10).join([f"- {g.get('nome', 'guerra')}: durata {g.get('durata', '?')} anni, esito {g.get('esito_finale', '?')}" for g in guerre])}

DIALOGHI E CONSULTAZIONI ({len(dialoghi)} dialoghi):
{chr(10).join([f"- Anno {d.get('anno', '?')}: {d.get('tipo', '?')} - {d.get('contenuto', 'discussione')[:100]}" for d in dialoghi[:5]])}

DECISIONE COLLETTIVA:
- Proposta: {decisione.get("proposta_vincente", "nessuna")}
- Proposto da: {decisione.get("agente_proposta", "sconosciuto")}
- Supporto: {", ".join(decisione.get("supporto", [])[:5])}

Scrivi un report narrativo lungo e dettagliato. Descrivi:
1. Il contesto politico all'inizio della decade
2. I principali conflitti e le loro fasi
3. I dialoghi interni e le decisioni importanti
4. Eventi demografici ed economici
5. La decisione finale e il suo impatto

Stile: narrativo, drammatico, in prima persona o terza persona storica."""

    try:
        report = await llm_client.call(
            prompt=prompt,
            system=MINI_REPORT_SYSTEM,
            max_tokens=2000,  # Aumentato per report piu lunghi
            temperature=0.7,
        )

        if report and len(report) > 100:
            node.mini_report = report[:3000]  # Salva versione lunga
            await db.commit()
            logger.info(f"Report generated for node {node_id[:8]}: {len(report)} chars")
            return report
        else:
            logger.warning(f"Report too short for node {node_id[:8]}")
            return (
                node.report_completo[:500]
                if node.report_completo
                else "Report non disponibile"
            )

    except Exception as e:
        logger.error(f"Failed to generate report: {e}")
        # Fallback: usa il report completo gia generato
        if node.report_completo:
            return node.report_completo[:1000]
        return f"[Report non disponibile: {str(e)[:50]}]"
