"""Agents endpoints."""
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.database import get_db
from src.models.agent import Agent
from src.api.v1.schemas.simulation import AgentResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/simulation/{simulation_id}", response_model=list[AgentResponse])
async def get_agents(simulation_id: str, db: AsyncSession = Depends(get_db)):
    """List all agents for a simulation."""
    result = await db.execute(select(Agent).where(Agent.simulation_id == simulation_id))
    agents = result.scalars().all()
    if not agents:
        raise HTTPException(status_code=404, detail="No agents found for this simulation")
    return [AgentResponse.model_validate(a) for a in agents]


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: str, db: AsyncSession = Depends(get_db)):
    """Get a single agent by ID."""
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return AgentResponse.model_validate(agent)
