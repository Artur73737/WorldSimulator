"""
AgentDialogSystem: dialoghi autonomi inter-agente via LLM.
"""
import logging
import random
import uuid
import json
from typing import List, Dict, Any, Optional
from src.services.llm_client import llm_client

logger = logging.getLogger(__name__)

INTERNAL_TOPICS = [
    "le tasse opprimono il popolo",
    "la corruzione dei funzionari dilaga",
    "la carestia minaccia le città",
    "la successione al trono è incerta",
    "l'esercito chiede più risorse",
    "il commercio con i barbari porta ricchezza",
    "le opere pubbliche prosciugano il tesoro",
    "una profezia turba il sovrano",
    "i nobili tramano contro il governo",
    "la siccità devasta i campi",
]

INTER_TOPICS = [
    "un trattato di pace dopo anni di guerra",
    "un accordo commerciale su rotte strategiche",
    "una richiesta di alleanza militare urgente",
    "una disputa su territori di confine",
    "uno scambio di ostaggi diplomatici",
    "una minaccia velata di invasione",
    "una proposta di matrimonio tra famiglie regnanti",
    "la divisione del bottino di guerra",
    "un patto segreto di non aggressione",
    "la richiesta di tributi arretrati",
]

ROLES = ["Generale", "Senatore", "Mercante", "Sacerdote", "Consigliere", "Ambasciatore", "Ministro", "Capitano"]


def _extract_dialog_text(raw: str) -> Optional[str]:
    """Estrae il testo del dialogo da qualsiasi formato risponda il modello."""
    if not raw or not raw.strip():
        return None

    # Prova prima JSON pulito
    try:
        cleaned = raw.strip()
        if "```" in cleaned:
            cleaned = "\n".join(l for l in cleaned.split("\n") if not l.strip().startswith("```"))
        start = cleaned.find("{")
        end = cleaned.rfind("}") + 1
        if start >= 0 and end > start:
            obj = json.loads(cleaned[start:end])
            # Cerca il campo contenuto in vari formati
            content = obj.get("contenuto") or obj.get("dialogo") or obj.get("testo")
            if isinstance(content, str) and len(content) > 10:
                return content
            # Se contenuto è dict/list, serializzalo come testo leggibile
            if isinstance(content, dict):
                parts = []
                for k, v in content.items():
                    if isinstance(v, str):
                        parts.append(f"{k}: {v}")
                    elif isinstance(v, list):
                        for item in v:
                            if isinstance(item, dict):
                                speaker = item.get("personaggio") or item.get("nome") or item.get("lato") or k
                                text = item.get("testo") or item.get("dialogo") or item.get("battuta") or str(item)
                                parts.append(f"{speaker}: {text}")
                if parts:
                    return "\n".join(parts)
            if isinstance(content, list):
                parts = []
                for item in content:
                    if isinstance(item, dict):
                        speaker = item.get("personaggio") or item.get("nome") or item.get("lato") or "?"
                        text = item.get("testo") or item.get("battuta") or str(item)
                        parts.append(f"{speaker}: {text}")
                    elif isinstance(item, str):
                        parts.append(item)
                if parts:
                    return "\n".join(parts)
    except Exception:
        pass

    # Fallback: restituisci il testo grezzo se ha senso
    if len(raw.strip()) > 20:
        return raw.strip()[:500]
    return None


def _extract_field(raw: str, field: str, default: str) -> str:
    try:
        cleaned = raw.strip()
        if "```" in cleaned:
            cleaned = "\n".join(l for l in cleaned.split("\n") if not l.strip().startswith("```"))
        start = cleaned.find("{")
        end = cleaned.rfind("}") + 1
        if start >= 0 and end > start:
            obj = json.loads(cleaned[start:end])
            val = obj.get(field)
            if isinstance(val, str):
                return val
    except Exception:
        pass
    return default


class AgentDialogSystem:

    def __init__(self, agents: list, current_decade: int, world_state: Dict[str, Any], rng: random.Random):
        self.agents = agents
        self.decade = current_decade
        self.world_state = world_state
        self.rng = rng

    async def run_autonomous_dialogs(self) -> List[Dict[str, Any]]:
        dialogs = []

        # Dialoghi interni (1 per ogni agente con probabilità 60%)
        for agent in self.agents:
            if self.rng.random() < 0.6:
                d = await self._internal_dialog(agent)
                if d:
                    dialogs.append(d)

        # Dialoghi inter-società (tra coppie casuali)
        candidates = [a for a in self.agents if not a.is_politica]
        if len(candidates) >= 2:
            self.rng.shuffle(candidates)
            for i in range(0, len(candidates) - 1, 2):
                if self.rng.random() < 0.5:
                    d = await self._inter_dialog(candidates[i], candidates[i+1])
                    if d:
                        dialogs.append(d)

        return dialogs

    async def _internal_dialog(self, agent) -> Optional[Dict[str, Any]]:
        topic = self.rng.choice(INTERNAL_TOPICS)
        role_a = self.rng.choice(ROLES)
        role_b = self.rng.choice([r for r in ROLES if r != role_a])
        anno = self.rng.randint(1, 10)
        eco = self.world_state.get("economia", 0.5)

        # Prompt semplice che forza testo dialogo diretto
        prompt = (
            f"Scrivi un dialogo storico realistico tra due personaggi del popolo {agent.etnia}, "
            f"decade {self.decade} d.C., argomento: {topic}.\n"
            f"Personaggio A: {role_a}\n"
            f"Personaggio B: {role_b}\n"
            f"Economia attuale: {eco:.0%}\n\n"
            f"Scrivi esattamente 4-6 battute (2-3 per personaggio) in stile storico antico.\n"
            f"Formato richiesto (solo questo, nient'altro):\n"
            f'{{"contenuto": "{role_a}: [battuta]\\n{role_b}: [battuta]\\n{role_a}: [battuta]\\n{role_b}: [battuta]", '
            f'"esito": "accordo", "impatto": {{"economia": 0.0, "militare": 0.0}}}}'
        )

        try:
            raw = await llm_client.call(prompt=prompt, max_tokens=500, temperature=0.9)
            contenuto = _extract_dialog_text(raw)
            if not contenuto:
                return None
            esito = _extract_field(raw, "esito", self.rng.choice(["accordo", "conflitto", "compromesso", "irrisolto"]))
            return {
                "id": str(uuid.uuid4()),
                "tipo": "interno",
                "societa": agent.etnia,
                "anno": anno,
                "tema": topic,
                "partecipanti": [f"{role_a} ({agent.etnia})", f"{role_b} ({agent.etnia})"],
                "contenuto": contenuto,
                "esito": esito,
                "dettaglio": f"{role_a} e {role_b} di {agent.etnia} discutono: {topic}",
            }
        except Exception as e:
            logger.debug(f"Internal dialog failed for {agent.etnia}: {e}")
            return None

    async def _inter_dialog(self, agent_a, agent_b) -> Optional[Dict[str, Any]]:
        topic = self.rng.choice(INTER_TOPICS)
        role_a = self.rng.choice(ROLES)
        role_b = self.rng.choice(ROLES)
        anno = self.rng.randint(1, 10)

        prompt = (
            f"Scrivi un dialogo diplomatico storico realistico tra due rappresentanti, "
            f"decade {self.decade} d.C., argomento: {topic}.\n"
            f"Diplomatico A: {role_a} di {agent_a.etnia}\n"
            f"Diplomatico B: {role_b} di {agent_b.etnia}\n\n"
            f"Scrivi esattamente 4-6 battute (2-3 per lato) in stile storico antico.\n"
            f"Formato richiesto (solo questo, nient'altro):\n"
            f'{{"contenuto": "{role_a} ({agent_a.etnia}): [battuta]\\n{role_b} ({agent_b.etnia}): [battuta]\\n{role_a} ({agent_a.etnia}): [battuta]\\n{role_b} ({agent_b.etnia}): [battuta]", '
            f'"esito": "accordo", "termini": "breve descrizione termini"}}'
        )

        try:
            raw = await llm_client.call(prompt=prompt, max_tokens=500, temperature=0.9)
            contenuto = _extract_dialog_text(raw)
            if not contenuto:
                return None
            esito = _extract_field(raw, "esito", self.rng.choice(["accordo", "fallimento", "tensione", "sospeso"]))
            termini = _extract_field(raw, "termini", "")
            return {
                "id": str(uuid.uuid4()),
                "tipo": "diplomatico",
                "societa": f"{agent_a.etnia} ↔ {agent_b.etnia}",
                "anno": anno,
                "tema": topic,
                "partecipanti": [f"{role_a} ({agent_a.etnia})", f"{role_b} ({agent_b.etnia})"],
                "contenuto": contenuto,
                "esito": esito,
                "termini": termini,
                "dettaglio": f"Negoziato tra {agent_a.etnia} e {agent_b.etnia}: {topic}",
            }
        except Exception as e:
            logger.debug(f"Inter-society dialog failed: {e}")
            return None
