"""
WebSocket endpoint per live updates della simulazione.
Sostituisce SSE + polling.
"""
import asyncio
import json
import logging
from typing import Dict, Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)
router = APIRouter()

# simulation_id -> set di WebSocket connessi
_connections: Dict[str, Set[WebSocket]] = {}


async def broadcast(simulation_id: str, event_type: str, data: dict):
    """Manda un evento a tutti i client connessi per quella simulazione."""
    sockets = _connections.get(simulation_id, set())
    if not sockets:
        return
    payload = json.dumps({"type": event_type, "data": data})
    dead = set()
    for ws in sockets:
        try:
            await ws.send_text(payload)
        except Exception:
            dead.add(ws)
    for ws in dead:
        sockets.discard(ws)


# Alias per compatibilità con simulation_worker
async def broadcast_event(simulation_id: str, event_type: str, data: dict):
    await broadcast(simulation_id, event_type, data)


@router.websocket("/simulation/{simulation_id}/ws")
async def simulation_ws(websocket: WebSocket, simulation_id: str):
    await websocket.accept()
    _connections.setdefault(simulation_id, set()).add(websocket)
    logger.info(f"WS connected: sim={simulation_id[:8]} total={len(_connections[simulation_id])}")

    try:
        await websocket.send_text(json.dumps({"type": "connected", "simulation_id": simulation_id}))
        # Tieni la connessione aperta aspettando messaggi dal client (ping/pong)
        while True:
            try:
                msg = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                if msg == "ping":
                    await websocket.send_text("pong")
            except asyncio.TimeoutError:
                # Manda heartbeat
                await websocket.send_text(json.dumps({"type": "heartbeat"}))
    except WebSocketDisconnect:
        logger.info(f"WS disconnected: sim={simulation_id[:8]}")
    except Exception as e:
        logger.warning(f"WS error: {e}")
    finally:
        _connections.get(simulation_id, set()).discard(websocket)
