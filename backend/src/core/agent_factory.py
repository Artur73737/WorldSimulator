"""
AgentFactory: creates initial society from user description via LLM.
"""

import hashlib
import logging
import os
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.agent import Agent
from src.services.llm_client import llm_client
from src.config import settings

logger = logging.getLogger(__name__)


SOCIETY_PROMPT = """Sei un generatore di configurazioni storiche. Descrizione: "{description}"

Rispondi SOLO con questo JSON (niente altro):
{{
  "periodo": "Roma 200 d.C.",
  "agenti": [
    {{
      "etnia": "Roma",
      "ruolo": "impero dominante",
      "bias_militare": 0.7,
      "bias_economia": 0.6,
      "bias_cultura": 0.5,
      "is_politica": false,
      "stato_iniziale": {{"economia": 0.7, "militare": 0.8, "popolazione": 0.7, "territorio": 0.8}}
    }}
  ]
}}

Regole IMPORTANTI:
1. Genera 3-5 agenti storicamente accurati per il contesto
2. UN SOLO agente deve avere is_politica=true - deve essere il GOVERNO/SENATO con nome DISTINTO (es: "Senato", "Corte", "Consiglio", NON usare nomi di popoli come "Roma")
3. Gli altri agenti rappresentano POPOLI/TRIBU (es: "Roma", "Goti", "Germani", ecc.)
4. Ogni etnia deve essere UNICA - non ripetere nomi"""


AGENT_SYSTEM = "Sei {etnia}, {ruolo} nel {periodo}. Rispondi SOLO con JSON."

AGENT_PROMPT = """Decade {decade} d.C. Argomento: {topic}
Stato: economia={eco:.2f} militare={mil:.2f}
Proposte precedenti: {recent}

Rispondi con questo JSON esatto:
{{"proposal": "tua proposta breve", "rationale": "motivazione", "confidence": 0.7, "vote": {{"support": [], "oppose": []}}}}"""


class AgentFactory:
    @staticmethod
    def _compute_seed(simulation_seed: str, etnia: str) -> int:
        raw = f"{simulation_seed}:{etnia}"
        return int(hashlib.sha256(raw.encode()).hexdigest()[:8], 16)

    @staticmethod
    def _write_prompt_file(
        etnia: str, ruolo: str, periodo: str, simulation_id: str
    ) -> str:
        os.makedirs(settings.prompts_dir, exist_ok=True)
        safe_name = etnia.lower().replace(" ", "_")[:40]
        path = os.path.join(
            settings.prompts_dir, f"{simulation_id[:8]}_{safe_name}.txt"
        )
        content = AGENT_SYSTEM.format(etnia=etnia, ruolo=ruolo, periodo=periodo)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path

    @staticmethod
    async def create_initial_society(
        description: str,
        simulation_id: str,
        simulation_seed: str,
        db: AsyncSession,
    ) -> List[Agent]:
        prompt = SOCIETY_PROMPT.format(description=description)
        logger.info(f"Generating society for sim {simulation_id[:8]}")

        try:
            config = await llm_client.call_json(
                prompt=prompt, max_tokens=1500, temperature=0.7
            )
            if not config or "agenti" not in config:
                raise ValueError("No agenti in response")
        except Exception as e:
            logger.warning(f"LLM society generation failed: {e}, using fallback")
            config = AgentFactory._fallback_society(description)

        periodo = config.get("periodo", "Antichita")
        agenti_config = config.get("agenti", [])

        # Remove duplicates by etnia, keeping first occurrence
        seen_etnie = set()
        unique_agenti = []
        for a in agenti_config:
            etnia = a.get("etnia", "Agente")
            if etnia not in seen_etnie:
                seen_etnie.add(etnia)
                unique_agenti.append(a)
        agenti_config = unique_agenti

        # Ensure politica agent
        if not any(a.get("is_politica") for a in agenti_config):
            agenti_config.append(AgentFactory._default_politica_agent())

        agents: List[Agent] = []
        for ac in agenti_config:
            etnia = ac.get("etnia", "Agente")
            ruolo = ac.get("ruolo", "popolo")
            prompt_path = AgentFactory._write_prompt_file(
                etnia, ruolo, periodo, simulation_id
            )

            agent = Agent(
                simulation_id=simulation_id,
                etnia=etnia,
                system_prompt_path=prompt_path,
                memoria={
                    "vittorie": [],
                    "sconfitte": [],
                    "alleanze": {},
                    "tradimenti": [],
                },
                prestigio=0.5,
                personalita_seed=AgentFactory._compute_seed(simulation_seed, etnia),
                bias_vector={
                    "militare_bias": ac.get("bias_militare", 0.5),
                    "economia_bias": ac.get("bias_economia", 0.5),
                    "cultura_bias": ac.get("bias_cultura", 0.5),
                },
                stato_corrente=ac.get(
                    "stato_iniziale",
                    {
                        "economia": 0.5,
                        "militare": 0.5,
                        "popolazione": 0.5,
                        "territorio": 0.5,
                    },
                ),
                is_politica=ac.get("is_politica", False),
            )
            db.add(agent)
            agents.append(agent)

        await db.commit()
        for a in agents:
            await db.refresh(a)

        logger.info(
            f"Created {len(agents)} agents for sim {simulation_id[:8]}: {[a.etnia for a in agents]}"
        )
        return agents

    @staticmethod
    def _default_politica_agent() -> Dict[str, Any]:
        return {
            "etnia": "Senato",
            "ruolo": "governo",
            "bias_militare": 0.4,
            "bias_economia": 0.5,
            "bias_cultura": 0.6,
            "is_politica": True,
            "stato_iniziale": {
                "economia": 0.5,
                "militare": 0.4,
                "popolazione": 0.3,
                "territorio": 0.2,
            },
        }

    @staticmethod
    def _fallback_society(description: str) -> Dict[str, Any]:
        logger.warning("Using fallback society")
        return {
            "periodo": "Antichita",
            "agenti": [
                {
                    "etnia": "Roma",
                    "ruolo": "impero",
                    "bias_militare": 0.7,
                    "bias_economia": 0.6,
                    "bias_cultura": 0.5,
                    "is_politica": False,
                    "stato_iniziale": {
                        "economia": 0.7,
                        "militare": 0.8,
                        "popolazione": 0.7,
                        "territorio": 0.8,
                    },
                },
                {
                    "etnia": "Goti",
                    "ruolo": "tribu guerriera",
                    "bias_militare": 0.8,
                    "bias_economia": 0.3,
                    "bias_cultura": 0.3,
                    "is_politica": False,
                    "stato_iniziale": {
                        "economia": 0.4,
                        "militare": 0.7,
                        "popolazione": 0.5,
                        "territorio": 0.4,
                    },
                },
                {
                    "etnia": "Persia",
                    "ruolo": "impero rivale",
                    "bias_militare": 0.6,
                    "bias_economia": 0.7,
                    "bias_cultura": 0.6,
                    "is_politica": False,
                    "stato_iniziale": {
                        "economia": 0.6,
                        "militare": 0.6,
                        "popolazione": 0.6,
                        "territorio": 0.6,
                    },
                },
                {
                    "etnia": "Senato Romano",
                    "ruolo": "governo",
                    "bias_militare": 0.4,
                    "bias_economia": 0.5,
                    "bias_cultura": 0.7,
                    "is_politica": True,
                    "stato_iniziale": {
                        "economia": 0.5,
                        "militare": 0.4,
                        "popolazione": 0.3,
                        "territorio": 0.2,
                    },
                },
            ],
        }
