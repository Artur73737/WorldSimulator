"""
Simulation endpoints.
"""
import hashlib
import logging
import uuid
import asyncio
import os
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.database import get_db, async_session_factory
from src.models.simulation import Simulation
from src.models.agent import Agent
from src.models.graph_node import GraphNode
from src.models.fork import Fork
from src.models.checkpoint import Checkpoint
from src.core.agent_factory import AgentFactory
from src.core.simulation_society import SimulationSociety
from src.core.fork_manager import ForkManager
from src.core.checkpoint import save_checkpoint, resume_checkpoint
from src.api.v1.schemas.simulation import (
    SimulationStartRequest, SimulationResponse, SimulationFullResponse,
    AgentResponse, GraphNodeResponse, ForkResponse, ForkCreateRequest, CheckpointResponse,
)
from src.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

MAX_DECADES = 20  # numero massimo decadi per simulazione


def _make_seed(description: str, user_id: str) -> str:
    import time
    raw = f"{description}:{user_id}:{time.time()}:{settings.simulation_seed}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


@router.post("/start", response_model=SimulationResponse, status_code=201)
async def start_simulation(
    req: SimulationStartRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(
        select(Simulation).where(Simulation.user_id == req.user_id, Simulation.is_locked == True)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="User already has an active simulation.")

    seed = _make_seed(req.description, req.user_id)
    simulation = Simulation(
        id=str(uuid.uuid4()), user_id=req.user_id, seed=seed,
        status="running", current_decade=0,
        initial_description=req.description, is_locked=True,
    )
    db.add(simulation)
    await db.commit()
    await db.refresh(simulation)
    background_tasks.add_task(_init_and_run, simulation.id, req.description, seed)
    logger.info(f"Simulation {simulation.id[:8]} started")
    return SimulationResponse.model_validate(simulation)


async def _run_loop(simulation_id: str, db: AsyncSession):
    """Loop principale — itera le decadi e gestisce completamento."""
    from src.api.ws.simulation_stream import broadcast

    for _ in range(MAX_DECADES):
        result = await db.execute(select(Simulation).where(Simulation.id == simulation_id))
        sim = result.scalar_one_or_none()
        if not sim or sim.status != "running":
            logger.info(f"Sim {simulation_id[:8]} stopped: {sim.status if sim else 'gone'}")
            break

        agents_r = await db.execute(select(Agent).where(Agent.simulation_id == simulation_id))
        agents = agents_r.scalars().all()

        try:
            society = SimulationSociety(sim, list(agents))
            node = await society.step_decade(db)
            logger.info(f"[Sim {simulation_id[:8]}] Decade {node.decade} — {node.etnia_dominante}")

            # Broadcast step_complete
            await broadcast(simulation_id, "step_complete", {
                "decade": node.decade,
                "node_id": node.id,
                "metriche": node.metriche_stato,
                "etnia_dominante": node.etnia_dominante,
            })

            # Crisis → fork
            crisis = society.check_crisis(node.metriche_stato)
            if crisis:
                try:
                    await ForkManager.create_fork(
                        simulation_id=simulation_id, parent_fork_id=None,
                        current_decade=node.decade, trigger_reason=crisis,
                        diverged_state=node.metriche_stato, parent_seed=sim.seed, db=db,
                    )
                    await broadcast(simulation_id, "fork_created", {"trigger": crisis, "decade": node.decade})
                except Exception as fe:
                    logger.warning(f"Fork creation failed: {fe}")

        except Exception as e:
            logger.error(f"step_decade failed: {e}", exc_info=True)
            break

        await asyncio.sleep(0.3)

    # ── Simulazione completata ──────────────────────────────────────────────
    result = await db.execute(select(Simulation).where(Simulation.id == simulation_id))
    sim = result.scalar_one_or_none()
    if sim:
        sim.status = "completed"
        sim.is_locked = False
        db.add(sim)
        await db.commit()
        logger.info(f"Sim {simulation_id[:8]} COMPLETED at decade {sim.current_decade}")

        # Genera report finale
        report_text = None
        try:
            from src.services.report_generator import generate_final_report
            report_text = await generate_final_report(simulation_id, db)
            logger.info(f"Report generated for sim {simulation_id[:8]}")
        except Exception as re:
            logger.error(f"Report generation failed: {re}")

        # Broadcast simulation_complete con report inline
        await broadcast(simulation_id, "simulation_complete", {
            "decade": sim.current_decade,
            "simulation_id": simulation_id,
            "report": report_text or "",
        })


async def _init_and_run(simulation_id: str, description: str, seed: str):
    async with async_session_factory() as db:
        try:
            await AgentFactory.create_initial_society(
                description=description, simulation_id=simulation_id,
                simulation_seed=seed, db=db,
            )
            logger.info(f"Agents created for sim {simulation_id[:8]}, starting loop")
            await _run_loop(simulation_id, db)
        except Exception as e:
            logger.error(f"Init failed for sim {simulation_id[:8]}: {e}", exc_info=True)
            try:
                result = await db.execute(select(Simulation).where(Simulation.id == simulation_id))
                sim = result.scalar_one_or_none()
                if sim:
                    sim.status = "failed"; sim.is_locked = False
                    db.add(sim); await db.commit()
            except Exception:
                pass


@router.get("/{simulation_id}", response_model=SimulationFullResponse)
async def get_simulation(simulation_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Simulation).where(Simulation.id == simulation_id))
    sim = result.scalar_one_or_none()
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")
    agents_r = await db.execute(select(Agent).where(Agent.simulation_id == simulation_id))
    nodes_r = await db.execute(
        select(GraphNode).where(GraphNode.simulation_id == simulation_id)
        .order_by(GraphNode.decade.asc()).limit(200)
    )
    forks_r = await db.execute(select(Fork).where(Fork.simulation_id == simulation_id))
    return SimulationFullResponse(
        simulation=SimulationResponse.model_validate(sim),
        agents=[AgentResponse.model_validate(a) for a in agents_r.scalars().all()],
        graph_nodes=[GraphNodeResponse.model_validate(n) for n in nodes_r.scalars().all()],
        forks=[ForkResponse.model_validate(f) for f in forks_r.scalars().all()],
    )


@router.post("/{simulation_id}/pause", response_model=SimulationResponse)
async def pause_simulation(simulation_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Simulation).where(Simulation.id == simulation_id))
    sim = result.scalar_one_or_none()
    if not sim: raise HTTPException(status_code=404)
    sim.status = "paused"; db.add(sim); await db.commit(); await db.refresh(sim)
    return SimulationResponse.model_validate(sim)


@router.post("/{simulation_id}/resume", response_model=SimulationResponse)
async def resume_simulation(simulation_id: str, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Simulation).where(Simulation.id == simulation_id))
    sim = result.scalar_one_or_none()
    if not sim: raise HTTPException(status_code=404)
    sim.status = "running"; db.add(sim); await db.commit(); await db.refresh(sim)
    background_tasks.add_task(_resume_loop, simulation_id)
    return SimulationResponse.model_validate(sim)


async def _resume_loop(simulation_id: str):
    async with async_session_factory() as db:
        await _run_loop(simulation_id, db)


@router.post("/{simulation_id}/fork", response_model=ForkResponse, status_code=201)
async def create_manual_fork(simulation_id: str, req: ForkCreateRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Simulation).where(Simulation.id == simulation_id))
    sim = result.scalar_one_or_none()
    if not sim: raise HTTPException(status_code=404)
    node_r = await db.execute(
        select(GraphNode).where(GraphNode.simulation_id == simulation_id)
        .order_by(GraphNode.decade.desc()).limit(1)
    )
    latest = node_r.scalar_one_or_none()
    fork = await ForkManager.create_fork(
        simulation_id=simulation_id, parent_fork_id=None,
        current_decade=sim.current_decade, trigger_reason=req.trigger_reason,
        diverged_state=latest.metriche_stato if latest else {},
        parent_seed=sim.seed, db=db,
    )
    return ForkResponse.model_validate(fork)


@router.post("/{simulation_id}/step", response_model=GraphNodeResponse)
async def step_one_decade(simulation_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Simulation).where(Simulation.id == simulation_id))
    sim = result.scalar_one_or_none()
    if not sim: raise HTTPException(status_code=404)
    agents_r = await db.execute(select(Agent).where(Agent.simulation_id == simulation_id))
    society = SimulationSociety(sim, list(agents_r.scalars().all()))
    node = await society.step_decade(db)
    return GraphNodeResponse.model_validate(node)


@router.get("/{simulation_id}/checkpoints", response_model=list[CheckpointResponse])
async def list_checkpoints(simulation_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Checkpoint).where(Checkpoint.simulation_id == simulation_id).order_by(Checkpoint.decade.asc())
    )
    return [CheckpointResponse.model_validate(c) for c in result.scalars().all()]


@router.post("/resume-checkpoint")
async def resume_from_checkpoint(checkpoint_id: str = Query(...), background_tasks: BackgroundTasks = None, db: AsyncSession = Depends(get_db)):
    checkpoint = await resume_checkpoint(checkpoint_id, db)
    result = await db.execute(select(Simulation).where(Simulation.id == checkpoint.simulation_id))
    sim = result.scalar_one_or_none()
    if not sim: raise HTTPException(status_code=404)
    sim.status = "running"; sim.current_decade = checkpoint.decade
    db.add(sim); await db.commit()
    background_tasks.add_task(_resume_loop, sim.id)
    return {"status": "resumed", "simulation_id": sim.id, "from_decade": checkpoint.decade}
