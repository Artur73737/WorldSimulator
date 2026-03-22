"""Pydantic schemas for Simulation API."""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


class SimulationStartRequest(BaseModel):
    description: str = Field(..., min_length=10, max_length=5000)  # nessun limite pratico
    user_id: str = Field(default="anonymous")
    max_decades: Optional[int] = Field(default=50, ge=1, le=500)


class SimulationResponse(BaseModel):
    id: str
    user_id: str
    seed: str
    status: str
    current_decade: int
    initial_description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AgentResponse(BaseModel):
    id: str
    etnia: str
    prestigio: float
    is_politica: bool
    stato_corrente: Dict[str, Any] = {}
    memoria: Dict[str, Any] = {}
    bias_vector: Dict[str, float] = {}

    model_config = {"from_attributes": True}


class GraphNodeResponse(BaseModel):
    id: str
    decade: int
    etnia_dominante: Optional[str] = None
    metriche_stato: Dict[str, Any] = {}
    relazioni: List[Dict[str, Any]] = []
    decisione: Optional[Dict[str, Any]] = None
    mini_report: Optional[str] = None
    fork_id: Optional[str] = None
    created_at: Optional[datetime] = None
    eventi: Optional[List[Dict[str, Any]]] = None
    dialoghi: Optional[List[Dict[str, Any]]] = None
    guerre: Optional[List[Dict[str, Any]]] = None
    demografia: Optional[Dict[str, Any]] = None
    economia_dettagliata: Optional[Dict[str, Any]] = None
    politica_dettagliata: Optional[Dict[str, Any]] = None
    tweet_mensili: Optional[List[Dict[str, Any]]] = None
    report_completo: Optional[str] = None

    model_config = {"from_attributes": True}


class ForkResponse(BaseModel):
    id: str
    parent_fork_id: Optional[str] = None
    created_at_decade: int
    trigger_reason: str
    status: str
    score: Optional[Dict[str, float]] = None
    diverged_state: Dict[str, Any] = {}

    model_config = {"from_attributes": True}


class ForkCreateRequest(BaseModel):
    trigger_reason: str = Field(default="manual")


class CheckpointResponse(BaseModel):
    id: str
    decade: int
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class SimulationFullResponse(BaseModel):
    simulation: SimulationResponse
    agents: List[AgentResponse]
    graph_nodes: List[GraphNodeResponse]
    forks: List[ForkResponse]
