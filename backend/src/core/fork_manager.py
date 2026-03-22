"""
ForkManager: creates fork snapshots on crisis events.
ForkEvaluator: ranks active forks every 10 decades.
"""
import hashlib
import logging
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.models.fork import Fork
from src.models.graph_node import GraphNode
from src.models.agent import Agent
from src.config import settings

logger = logging.getLogger(__name__)


class ForkManager:

    @staticmethod
    async def create_fork(
        simulation_id: str,
        parent_fork_id: Optional[str],
        current_decade: int,
        trigger_reason: str,
        diverged_state: Dict[str, Any],
        parent_seed: str,
        db: AsyncSession,
    ) -> Fork:
        """Create a new simulation fork."""
        seed = hashlib.sha256(
            f"{parent_seed}:{current_decade}:{trigger_reason}:{uuid.uuid4()}".encode()
        ).hexdigest()[:16]

        fork = Fork(
            id=str(uuid.uuid4()),
            simulation_id=simulation_id,
            parent_fork_id=parent_fork_id,
            created_at_decade=current_decade,
            trigger_reason=trigger_reason,
            seed=seed,
            diverged_state=diverged_state,
            status="active",
        )
        db.add(fork)
        await db.commit()
        await db.refresh(fork)
        logger.info(f"Fork created: {fork.id[:8]} (trigger: {trigger_reason}, decade: {current_decade})")
        return fork


class ForkEvaluator:

    @staticmethod
    async def evaluate_all_forks(simulation_id: str, current_decade: int, db: AsyncSession) -> Dict[str, Dict]:
        """Evaluate all active forks and mark losers as dead."""
        result = await db.execute(
            select(Fork).where(
                Fork.simulation_id == simulation_id,
                Fork.status == "active",
            )
        )
        forks: List[Fork] = result.scalars().all()
        if not forks:
            return {}

        scores: Dict[str, Dict] = {}

        for fork in forks:
            # Count nodes
            nodes_result = await db.execute(
                select(GraphNode).where(GraphNode.fork_id == fork.id)
            )
            nodes = nodes_result.scalars().all()
            num_nodes = len(nodes)

            # Calculate resilience (min economy metric across nodes)
            if nodes:
                min_eco = min(
                    n.metriche_stato.get("economia", 0.5) for n in nodes
                )
                last_state = nodes[-1].metriche_stato
            else:
                min_eco = diverged_eco = fork.diverged_state.get("economia", 0.5)
                last_state = fork.diverged_state

            # Longevity score
            longevity = (current_decade - fork.created_at_decade) / max(current_decade, 1)
            resilience = 1.0 - min_eco if min_eco < 0.5 else min_eco
            # Count children forks (innovation)
            children_result = await db.execute(
                select(Fork).where(Fork.parent_fork_id == fork.id)
            )
            num_children = len(children_result.scalars().all())
            innovation = min(1.0, num_children * 0.2)

            total = longevity * 0.4 + resilience * 0.4 + innovation * 0.2

            score = {
                "longevity": round(longevity, 3),
                "resilience": round(resilience, 3),
                "innovation": round(innovation, 3),
                "total": round(total, 3),
            }
            fork.score = score
            fork.evaluated_at = datetime.utcnow()

            # Check if fork is in crisis (mark dead if all metrics critical)
            eco = last_state.get("economia", 0.5)
            mil = last_state.get("militare", 0.5)
            if eco < 0.05 and mil < 0.05:
                fork.status = "dead"
                logger.info(f"Fork {fork.id[:8]} marked dead (eco={eco:.2f}, mil={mil:.2f})")

            scores[fork.id] = score
            db.add(fork)

        # Mark best fork as winner
        if scores:
            best_fork_id = max(scores, key=lambda fid: scores[fid]["total"])
            for fork in forks:
                if fork.id == best_fork_id and fork.status == "active":
                    fork.status = "winning"
                    db.add(fork)
                    logger.info(f"Fork {fork.id[:8]} is leading (score={scores[best_fork_id]['total']:.3f})")

        await db.commit()
        return scores
