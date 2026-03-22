"""Reports endpoint."""
import logging
import os
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.database import get_db
from src.models.simulation import Simulation
from src.services.report_generator import generate_final_report
from src.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/simulation/{simulation_id}/generate")
async def generate_report(
    simulation_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Simulation).where(Simulation.id == simulation_id))
    sim = result.scalar_one_or_none()
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")
    background_tasks.add_task(generate_final_report, simulation_id, db)
    return {"status": "generating", "simulation_id": simulation_id}


@router.get("/simulation/{simulation_id}", response_class=HTMLResponse)
async def get_report(simulation_id: str):
    """Serve the HTML report."""
    path = os.path.join(settings.reports_dir, f"{simulation_id}.html")
    if not os.path.exists(path):
        # fallback to md
        md_path = os.path.join(settings.reports_dir, f"{simulation_id}.md")
        if os.path.exists(md_path):
            with open(md_path, "r", encoding="utf-8") as f:
                return PlainTextResponse(f.read())
        raise HTTPException(status_code=404, detail="Report not yet generated.")
    with open(path, "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())
