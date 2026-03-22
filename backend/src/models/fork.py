import uuid
from sqlalchemy import String, Integer, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, Dict, Any, List
from datetime import datetime

from .base import Base


class Fork(Base):
    __tablename__ = "forks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    simulation_id: Mapped[str] = mapped_column(String(36), ForeignKey("simulations.id", ondelete="CASCADE"), nullable=False)
    parent_fork_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("forks.id"), nullable=True)

    # Fork metadata
    created_at_decade: Mapped[int] = mapped_column(Integer, nullable=False)
    trigger_reason: Mapped[str] = mapped_column(String(255), nullable=False)  # crisis_economy, crisis_politica, manual
    seed: Mapped[str] = mapped_column(String(255), nullable=False)

    # Divergence state snapshot
    diverged_state: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)

    # Evaluation
    status: Mapped[str] = mapped_column(String(50), default="active")  # active, winning, dead
    score: Mapped[Optional[Dict[str, float]]] = mapped_column(JSON, nullable=True)
    # {longevity, resilience, innovation, total}

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    evaluated_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    # Relationships
    simulation: Mapped["Simulation"] = relationship("Simulation", back_populates="forks")
    nodes: Mapped[List["GraphNode"]] = relationship("GraphNode", back_populates="fork")
    parent: Mapped[Optional["Fork"]] = relationship("Fork", remote_side=[id], backref="children")
