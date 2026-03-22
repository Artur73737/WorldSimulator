"""Graph endpoints: nodes, timeline, fork tree."""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.database import get_db
from src.models.graph_node import GraphNode
from src.models.fork import Fork
from src.models.agent import Agent
from src.api.v1.schemas.simulation import GraphNodeResponse, ForkResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/simulation/{simulation_id}/nodes", response_model=list[GraphNodeResponse])
async def get_graph_nodes(
    simulation_id: str,
    fork_id: Optional[str] = Query(default=None),
    decade_from: Optional[int] = Query(default=None),
    decade_to: Optional[int] = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    q = select(GraphNode).where(GraphNode.simulation_id == simulation_id)
    if fork_id: q = q.where(GraphNode.fork_id == fork_id)
    if decade_from is not None: q = q.where(GraphNode.decade >= decade_from)
    if decade_to is not None: q = q.where(GraphNode.decade <= decade_to)
    result = await db.execute(q.order_by(GraphNode.decade.asc()).limit(500))
    return [GraphNodeResponse.model_validate(n) for n in result.scalars().all()]


@router.get("/simulation/{simulation_id}/nodes/{node_id}", response_model=GraphNodeResponse)
async def get_node(simulation_id: str, node_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(GraphNode).where(GraphNode.id == node_id, GraphNode.simulation_id == simulation_id)
    )
    node = result.scalar_one_or_none()
    if not node: raise HTTPException(status_code=404, detail="Node not found")
    return GraphNodeResponse.model_validate(node)


@router.get("/simulation/{simulation_id}/forks", response_model=list[ForkResponse])
async def get_forks(simulation_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Fork).where(Fork.simulation_id == simulation_id))
    return [ForkResponse.model_validate(f) for f in result.scalars().all()]


@router.get("/simulation/{simulation_id}/graph-data")
async def get_graph_data(simulation_id: str, db: AsyncSession = Depends(get_db)):
    """Graph data con agenti_info per sotto-nodi etnia."""
    nodes_r = await db.execute(
        select(GraphNode).where(GraphNode.simulation_id == simulation_id)
        .order_by(GraphNode.decade.asc()).limit(300)
    )
    nodes = nodes_r.scalars().all()

    forks_r = await db.execute(select(Fork).where(Fork.simulation_id == simulation_id))
    forks = forks_r.scalars().all()
    fork_map = {f.id: f for f in forks}

    # Carica tutti gli agenti della simulazione
    agents_r = await db.execute(select(Agent).where(Agent.simulation_id == simulation_id))
    agents = agents_r.scalars().all()

    d3_nodes = []
    d3_links = []
    prev_by_fork: dict = {}

    for node in nodes:
        fork_status = "main"
        if node.fork_id and node.fork_id in fork_map:
            fork_status = fork_map[node.fork_id].status

        eventi = (node.eventi or []) if hasattr(node, 'eventi') else []
        guerre = (node.guerre or []) if hasattr(node, 'guerre') else []
        dialoghi = (node.dialoghi or []) if hasattr(node, 'dialoghi') else []
        decisione = node.decisione or {}

        # Filtra eventi non significativi
        eventi_reali = [e for e in eventi if e.get("tipo") not in ("tendenze_annuali", "tweet", "social")]

        # Costruisci agenti_info: per ogni agente, filtra i dialoghi pertinenti
        agenti_info = []
        for ag in agents:
            # Dialoghi interni di questa società
            interni = [
                d for d in dialoghi
                if d.get("tipo") == "interno" and d.get("societa") == ag.etnia
            ]
            # Dialoghi diplomatici che coinvolgono questa società
            diplomatici = [
                d for d in dialoghi
                if d.get("tipo") == "diplomatico"
                and (ag.etnia in str(d.get("societa", "")) or
                     any(ag.etnia in str(p) for p in d.get("partecipanti", [])))
            ]
            agenti_info.append({
                "etnia": ag.etnia,
                "is_politica": ag.is_politica,
                "prestigio": round(ag.prestigio, 3),
                "economia": round(ag.stato_corrente.get("economia", 0.5), 3),
                "militare": round(ag.stato_corrente.get("militare", 0.5), 3),
                "dialoghi_interni": interni[:4],
                "dialoghi_diplomatici": diplomatici[:4],
            })

        d3_nodes.append({
            "id": node.id,
            "decade": node.decade,
            "etnia_dominante": node.etnia_dominante,
            "fork_id": node.fork_id,
            "fork_status": fork_status,
            "economia": node.metriche_stato.get("economia", 0.5),
            "militare": node.metriche_stato.get("militare", 0.5),
            "popolazione": node.metriche_stato.get("popolazione", 0.5),
            "mini_report": (node.mini_report or "")[:300],
            "eventi": eventi_reali[:8],
            "guerre": guerre[:4],
            "dialoghi": dialoghi[:4],
            "agenti_info": agenti_info,
            "decisione": {
                "proposta": decisione.get("proposta_vincente", ""),
                "proposta_vincente": decisione.get("proposta_vincente", ""),
                "agente": decisione.get("agente_proposta", ""),
                "agente_proposta": decisione.get("agente_proposta", ""),
                "confidence": decisione.get("confidence", 0),
                "rationale": decisione.get("rationale", ""),
                "supporto": decisione.get("supporto", []),
                "opposizione": decisione.get("opposizione", []),
            } if decisione else None,
        })

        key = node.fork_id or "main"
        if key in prev_by_fork:
            d3_links.append({"source": prev_by_fork[key], "target": node.id, "type": "timeline"})
        prev_by_fork[key] = node.id

    for fork in forks:
        origin = next((n for n in nodes if n.fork_id is None and n.decade == fork.created_at_decade), None)
        first_fn = next((n for n in nodes if n.fork_id == fork.id), None)
        if origin and first_fn:
            d3_links.append({"source": origin.id, "target": first_fn.id, "type": "fork_origin"})

    return {"nodes": d3_nodes, "links": d3_links}
