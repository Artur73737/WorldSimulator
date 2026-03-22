"""
Celery worker: background simulation processing.
Each task processes one decade for a given fork.
"""
import asyncio
import logging
from celery import Celery
from sqlalchemy import select

from src.config import settings
from src.database import async_session_factory

logger = logging.getLogger(__name__)

celery_app = Celery(
    "world_simulation",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,  # Sequential for rate limiting
)


def run_async(coro):
    """Run async coroutine in sync context."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name="simulation_worker.step_decade", bind=True, max_retries=3)
def step_decade_task(self, simulation_id: str, fork_id: str = None):
    """Process one decade for a simulation/fork."""
    return run_async(_step_decade_async(self, simulation_id, fork_id))


async def _step_decade_async(task, simulation_id: str, fork_id: str = None):
    from src.models.simulation import Simulation
    from src.models.agent import Agent
    from src.core.simulation_society import SimulationSociety
    from src.core.fork_manager import ForkManager, ForkEvaluator
    from src.core.checkpoint import save_checkpoint

    async with async_session_factory() as db:
        # Load simulation
        result = await db.execute(select(Simulation).where(Simulation.id == simulation_id))
        simulation = result.scalar_one_or_none()
        if not simulation or simulation.status not in ("running",):
            logger.warning(f"Simulation {simulation_id[:8]} not found or not running")
            return {"status": "skipped"}

        # Load agents
        agents_result = await db.execute(select(Agent).where(Agent.simulation_id == simulation_id))
        agents = agents_result.scalars().all()

        society = SimulationSociety(simulation, list(agents), fork_id=fork_id)

        # Step decade
        node = await society.step_decade(db)

        current_state = node.metriche_stato
        current_decade = node.decade

        # Check crisis → create fork
        crisis = society.check_crisis(current_state)
        if crisis:
            logger.info(f"Crisis detected: {crisis} at decade {current_decade}")
            try:
                new_fork = await ForkManager.create_fork(
                    simulation_id=simulation_id,
                    parent_fork_id=fork_id,
                    current_decade=current_decade,
                    trigger_reason=crisis,
                    diverged_state=current_state,
                    parent_seed=simulation.seed,
                    db=db,
                )
                # Dispatch new fork task
                step_decade_task.delay(simulation_id, new_fork.id)
            except Exception as e:
                logger.error(f"Fork creation failed: {e}")

        # Checkpoint every N decades
        if current_decade % (settings.checkpoint_interval_decades * 10) == 0:
            try:
                await save_checkpoint(simulation_id, current_decade, db)
            except Exception as e:
                logger.warning(f"Checkpoint failed: {e}")

        # Evaluate forks every 10 decades
        if current_decade % 100 == 0:
            try:
                await ForkEvaluator.evaluate_all_forks(simulation_id, current_decade, db)
            except Exception as e:
                logger.warning(f"Fork evaluation failed: {e}")

        # Broadcast SSE event
        try:
            from src.api.ws.simulation_stream import broadcast_event
            await broadcast_event(simulation_id, "step_complete", {
                "decade": current_decade,
                "node_id": node.id,
                "metriche": current_state,
                "etnia_dominante": node.etnia_dominante,
                "crisis": crisis,
            })
        except Exception as e:
            logger.debug(f"SSE broadcast failed: {e}")

        return {
            "status": "ok",
            "decade": current_decade,
            "node_id": node.id,
            "crisis": crisis,
        }


@celery_app.task(name="simulation_worker.step_fork", bind=True)
def step_fork_task(self, fork_id: str, simulation_id: str):
    """Alias for step_decade on a specific fork."""
    return step_decade_task.delay(simulation_id, fork_id)
