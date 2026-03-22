import uuid
from sqlalchemy import String, Integer, ForeignKey, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, Dict, Any, List
from datetime import datetime

from .base import Base


class GraphNode(Base):
    __tablename__ = "graph_nodes"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    simulation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("simulations.id", ondelete="CASCADE"), nullable=False
    )
    fork_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("forks.id", ondelete="SET NULL"), nullable=True
    )

    # Timeline
    decade: Mapped[int] = mapped_column(Integer, nullable=False)
    etnia_dominante: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # State metrics
    metriche_stato: Mapped[Dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )

    # Relations between ethnic groups
    relazioni: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)

    # Complex events within this decade
    eventi: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)

    # Internal dialogs and citizen interactions
    dialoghi: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)

    # Wars and conflicts
    guerre: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)

    # Population and demographics
    demografia: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)

    # Economic activities
    economia_dettagliata: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)

    # Political events
    politica_dettagliata: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)

    # Monthly social events (tweets/news from factions)
    tweet_mensili: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)

    # Debate outcome
    decisione: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Full historical report (not truncated)
    mini_report: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Extended full report
    report_completo: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    # Relationships
    simulation: Mapped["Simulation"] = relationship(
        "Simulation", back_populates="graph_nodes"
    )
    fork: Mapped[Optional["Fork"]] = relationship("Fork", back_populates="nodes")

    def __repr__(self) -> str:
        return f"<GraphNode decade={self.decade} etnia={self.etnia_dominante}>"
