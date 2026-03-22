"""Admin endpoints: reset DB, clear locks."""
import logging
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, update

from src.database import get_db, init_db
from src.models.simulation import Simulation

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/reset-db")
async def reset_db(db: AsyncSession = Depends(get_db)):
    """Drop and recreate all tables. Wipes everything."""
    try:
        from src.database import engine
        from src.models.base import Base
        from src.models import simulation, agent, graph_node, fork, checkpoint

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

        logger.info("DB reset: all tables dropped and recreated")
        return {"status": "ok", "message": "Database resettato con successo"}
    except Exception as e:
        logger.error(f"DB reset failed: {e}")
        return {"status": "error", "message": str(e)}


@router.post("/unlock")
async def unlock_simulations(db: AsyncSession = Depends(get_db)):
    """Unlock all stale locked simulations."""
    await db.execute(
        update(Simulation)
        .where(Simulation.is_locked == True)
        .values(is_locked=False, status="paused")
    )
    await db.commit()
    return {"status": "ok", "message": "Simulazioni sbloccate"}
