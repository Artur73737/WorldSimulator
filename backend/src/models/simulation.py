import uuid
from sqlalchemy import String, Integer, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List, Optional
from datetime import datetime

from .base import Base


class Simulation(Base):
    __tablename__ = "simulations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, default="anonymous")
    seed: Mapped[str] = mapped_column(String(255), nullable=False)

    status: Mapped[str] = mapped_column(String(50), default="running")
    current_decade: Mapped[int] = mapped_column(Integer, default=0)
    initial_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    max_turns_per_debate: Mapped[int] = mapped_column(Integer, default=5)
    crisis_threshold_economy: Mapped[float] = mapped_column(default=0.2)
    crisis_threshold_military: Mapped[float] = mapped_column(default=0.15)

    is_locked: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)  # no onupdate per SQLite

    agents: Mapped[List["Agent"]] = relationship("Agent", back_populates="simulation", cascade="all, delete-orphan")
    graph_nodes: Mapped[List["GraphNode"]] = relationship("GraphNode", back_populates="simulation", cascade="all, delete-orphan")
    forks: Mapped[List["Fork"]] = relationship("Fork", back_populates="simulation", cascade="all, delete-orphan")
    checkpoints: Mapped[List["Checkpoint"]] = relationship("Checkpoint", back_populates="simulation", cascade="all, delete-orphan")
