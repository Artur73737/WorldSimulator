import uuid
from sqlalchemy import String, Float, ForeignKey, Integer, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, Dict, Any

from .base import Base


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    simulation_id: Mapped[str] = mapped_column(String(36), ForeignKey("simulations.id", ondelete="CASCADE"), nullable=False)

    # Identity
    etnia: Mapped[str] = mapped_column(String(255), nullable=False)
    system_prompt_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # State
    memoria: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    prestigio: Mapped[float] = mapped_column(Float, default=0.5)
    personalita_seed: Mapped[int] = mapped_column(Integer, nullable=False)
    bias_vector: Mapped[Dict[str, float]] = mapped_column(JSON, default=dict)
    stato_corrente: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)

    # Is this a special PoliticaAgent?
    is_politica: Mapped[bool] = mapped_column(default=False)
    politica_metrics: Mapped[Optional[Dict[str, float]]] = mapped_column(JSON, nullable=True)

    # Relationships
    simulation: Mapped["Simulation"] = relationship("Simulation", back_populates="agents")

    __table_args__ = (
        UniqueConstraint("simulation_id", "etnia", name="uq_simulation_etnia"),
    )

    def __repr__(self) -> str:
        return f"<Agent {self.etnia} (sim {self.simulation_id[:8]})>"
