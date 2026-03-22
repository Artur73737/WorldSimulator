from fastapi import APIRouter

from src.api.v1.endpoints import simulation, agents, graph, reports, admin

api_router = APIRouter()

api_router.include_router(simulation.router, prefix="/simulation", tags=["simulation"])
api_router.include_router(agents.router, prefix="/agents", tags=["agents"])
api_router.include_router(graph.router, prefix="/graph", tags=["graph"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
