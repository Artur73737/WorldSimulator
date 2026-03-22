"""
Checkpoint system: auto-save every N decades.
"""
import json
import logging
import os
import uuid
from typing import List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.models.checkpoint import Checkpoint
from src.models.agent import Agent
from src.models.graph_node import GraphNode
from src.models.fork import Fork
from src.config import settings

logger = logging.getLogger(__name__)


async def save_checkpoint(simulation_id: str, current_decade: int, db: AsyncSession) -> Checkpoint:
    """Save current simulation state as checkpoint."""
    os.makedirs(settings.checkpoints_dir, exist_ok=True)

    # Load agents
    agents_r = await db.execute(select(Agent).where(Agent.simulation_id == simulation_id))
    agents = agents_r.scalars().all()
    agent_memories = {a.etnia: {"memoria": a.memoria, "prestigio": a.prestigio, "stato": a.stato_corrente} for a in agents}

    # Load recent nodes
    nodes_r = await db.execute(
        select(GraphNode)
        .where(GraphNode.simulation_id == simulation_id)
        .order_by(GraphNode.decade.desc())
        .limit(20)
    )
    nodes = nodes_r.scalars().all()
    graph_nodes_snap = [{"id": n.id, "decade": n.decade, "metriche": n.metriche_stato, "dominante": n.etnia_dominante} for n in nodes]

    # Load active forks
    forks_r = await db.execute(select(Fork).where(Fork.simulation_id == simulation_id, Fork.status == "active"))
    forks = forks_r.scalars().all()
    fork_states = [{"id": f.id, "trigger": f.trigger_reason, "decade": f.created_at_decade, "score": f.score} for f in forks]

    checkpoint = Checkpoint(
        id=str(uuid.uuid4()),
        simulation_id=simulation_id,
        decade=current_decade,
        fork_states=fork_states,
        agent_memories=agent_memories,
        graph_nodes=graph_nodes_snap,
    )
    db.add(checkpoint)
    await db.commit()
    await db.refresh(checkpoint)
    logger.info(f"Checkpoint saved: decade {current_decade}, sim {simulation_id[:8]}")
    return checkpoint


async def resume_checkpoint(checkpoint_id: str, db: AsyncSession) -> Checkpoint:
    """Load a checkpoint by ID."""
    result = await db.execute(select(Checkpoint).where(Checkpoint.id == checkpoint_id))
    checkpoint = result.scalar_one_or_none()
    if not checkpoint:
        raise ValueError(f"Checkpoint {checkpoint_id} not found")
    return checkpoint
