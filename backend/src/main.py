from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import uvicorn

from src.database import init_db, async_session_factory
from src.api.v1.router import api_router
from src.api.ws.simulation_stream import router as ws_router

logger = logging.getLogger(__name__)


async def _unlock_stale_simulations():
    """On startup: unlock any simulations left locked from a previous crashed run."""
    try:
        from sqlalchemy import update
        from src.models.simulation import Simulation
        async with async_session_factory() as db:
            await db.execute(
                update(Simulation)
                .where(Simulation.is_locked == True)
                .values(is_locked=False, status="paused")
            )
            await db.commit()
            logger.info("Stale simulation locks cleared")
    except Exception as e:
        logger.warning(f"Could not clear stale locks: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await _unlock_stale_simulations()
    yield


app = FastAPI(
    title="World Simulation API",
    description="Historical society evolution simulation with LLM agents",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")
app.include_router(ws_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "world-simulation"}


@app.get("/")
async def root():
    return {"name": "World Simulation API", "version": "1.0.0", "docs": "/docs"}


if __name__ == "__main__":
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
