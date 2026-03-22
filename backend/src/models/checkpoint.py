import uuid
from sqlalchemy import String, Integer, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Dict, Any, Optional
from datetime import datetime

from .base import Base


class Checkpoint(Base):
    __tablename__ = "checkpoints"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    simulation_id: Mapped[str] = mapped_column(String(36), ForeignKey("simulations.id", ondelete="CASCADE"), nullable=False)

    decade: Mapped[int] = mapped_column(Integer, nullable=False)

    # Serialized states
    fork_states: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    agent_memories: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    graph_nodes: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)

    # Winning fork at this checkpoint
    winning_fork_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    # Relationships
    simulation: Mapped["Simulation"] = relationship("Simulation", back_populates="checkpoints")
