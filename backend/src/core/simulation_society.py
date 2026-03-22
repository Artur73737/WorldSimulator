"""
SimulationSociety: core engine per simulazione decennale con eventi complessi.

Ogni decade contiene:
- Eventi annuali (guerre, dialoghi, rivolte, carestie, epidemie)
- Guerre multi-fase con perdite e strategie
- Dialoghi interni (senato, plebe, esercito, fazioni)
- Cambiamenti demografici ed economici
- Politica dinamica (imperatori, congiure, riforme)
"""

import logging
import random
import uuid
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.models.agent import Agent
from src.models.simulation import Simulation
from src.models.graph_node import GraphNode
from src.services.llm_client import llm_client
from src.core.agent_dialog import AgentDialogSystem
from src.config import settings

logger = logging.getLogger(__name__)

# Topics per le discussioni principali
DEBATE_TOPICS = [
    "Espansione territoriale vs consolidamento interno",
    "Alleanza militare con popoli vicini",
    "Riforma fiscale per finanziare l'esercito",
    "Politica commerciale: apertura vs protezionismo",
    "Gestione della crisi agricola",
    "Diplomazia con nemici storici",
    "Successione alla leadership",
    "Investimento in infrastrutture",
    "Risposta all'invasione barbarica",
    "Riforme religiose e culturali",
]

# Tipi di eventi annuali
EVENT_TYPES = [
    "guerra",
    "dialogo_interno",
    "rivolta",
    "commercio",
    "successione",
    "carestia",
    "epidemia",
    "conquista",
    "trattato",
    "ribellione",
    "fame",
    "prosperita",
]

# Tipi di dialoghi interni
DIALOG_TYPES = [
    "senato",
    "plebe",
    "esercito",
    "fazioni",
    "mercanti",
    "sacerdoti",
    "nobilta",
    "contadini",
    "generali",
]

# Template per tweet/eventi social interni
TWEET_TEMPLATES = {
    "senato": [
        "Il Senato discute nuove tasse. I mercanti protestano.",
        "Riforma fiscale approvata. Discontento nella plebe.",
        "Senatori in disaccordo sulla politica estera.",
        "Debate acceso sulla successione imperiale.",
        "Nuova legge sulla proprieta' terriera approvata.",
    ],
    "mercanti": [
        "La Via del Commercio bloccata dai barbari! Perdite ingenti.",
        "Ottimo anno per il commercio di seta. Profitti record.",
        "Inflazione galoppante. I prezzi salgono ogni settimana.",
        "Nuova rotta commerciale aperta verso Oriente.",
        "Crisi economica: i mercati chiudono in anticipo.",
    ],
    "plebe": [
        "La fame ci ucc! Dove sono le riforme promesse?",
        "Manifestazione contro le tasse eccessive.",
        "Grano caro: le famiglie non possono piu' mangiare.",
        "I lavoratori richiedono piu' diritti e salari.",
        "Rivolta della plebe sedata dalle guardie.",
    ],
    "esercito": [
        "Le legioni reclutano nuovi soldati. Bonus di reclutamento.",
        "Vittoria contro i barbari! Spoglie e gloria.",
        "Carencia di armamenti. Richiesta urgente di fondi.",
        "Il generale Marsus richiede rinforzi al fronte.",
        "Scontro di confine. Perdite moderate.",
    ],
    "fazioni": [
        "La fazione dei Populares guadagna influenza.",
        "Congiura scoperta! I congiurati arrestati.",
        "Guerra civile? I generali si schierano.",
        "La vecchia aristocrazia perde potere.",
        "Alleanza improbabile tra due fazioni rivali.",
    ],
    "sacerdoti": [
        "I sacerdoti predicono sventure. Panico in citta'.",
        "Festa religiosa con sacrifici al tempio di Giove.",
        "Nuova setta religiosa si diffonde nelle province.",
        "I dotti discutono la nuova filosofia greca.",
        "Miracolo al tempio? La folla si raduna.",
    ],
    "nobilta": [
        "Banchetto di nozze tra due famiglie potenti.",
        "Scandalo alla corte! Un nobile in disgrazia.",
        "Patrimonio ereditato. La famiglia cresce.",
        "Duello tra nobili per questione d'onore.",
        "La matrona Claudia dona fondi all'esercito.",
    ],
    "contadini": [
        "Raccolto abbondante! I campi sono d'oro.",
        "Caretta colpisce le messi. Fame in vista.",
        "Grande inondazione. I campi sono distrutti.",
        "Nuove tecniche agricole aumentano la resa.",
        "Terremoto nelle province. Molti senza casa.",
    ],
    "generali": [
        "Il generale Aulo richiede truppe per campagna estiva.",
        "Scontro vittorioso. Il morale e' alto.",
        "Problemi di rifornimento. Le strade sono insicure.",
        "Nuova fortificazione completata al confine.",
        "Spionaggio: i nemici conoscono i nostri piani.",
    ],
}

# Frequenza eventi mensili
MONTHLY_EVENT_TYPES = [
    "economia",
    "politica",
    "militare",
    "sociale",
    "religione",
    "commercio",
]


# ============== NUOVE FUNZIONI PER GRANULARITA MENSILE ==============


def generate_tweet(dialog_type: str, rng: random.Random) -> Dict[str, Any]:
    """Genera un tweet/evento social dalla fazione specificata."""
    if dialog_type in TWEET_TEMPLATES:
        return {
            "tipo": "tweet",
            "fazione": dialog_type,
            "contenuto": rng.choice(TWEET_TEMPLATES[dialog_type]),
            "timestamp": "",  # Sara popolato con mese/anno
            "viralita": round(rng.uniform(0.1, 1.0), 2),
            "reazioni": {
                "accordi": rng.randint(0, 50),
                "opposizioni": rng.randint(0, 30),
                "condivisioni": rng.randint(0, 20),
            },
        }
    return {"tipo": "tweet", "fazione": dialog_type, "contenuto": "Rumors..."}


class SimulationSociety:
    def __init__(
        self, simulation: Simulation, agents: List[Agent], fork_id: Optional[str] = None
    ):
        self.simulation = simulation
        self.agents = agents
        self.fork_id = fork_id
        self.rng = random.Random(simulation.seed)
        self.current_decade = simulation.current_decade

    async def step_decade(self, db: AsyncSession) -> GraphNode:
        """Esegue una decade completa con eventi annuali dettagliati."""
        decade = self.simulation.current_decade + 10
        self.current_decade = decade
        logger.info(f"[Sim {self.simulation.id[:8]}] Stepping decade {decade}")

        # 1. Esegui eventi MENSILI (120 mesi = 10 anni)
        # Ogni mese ha eventi granulari: tweet social, economia, politica
        eventi_mensili = await self._run_monthly_events()

        # 2. Aggrega in eventi annuali
        eventi_annuali = self._aggregate_monthly_to_annual(eventi_mensili)

        # 3. Gestisci guerre e conflitti (da eventi annuali)
        guerre = await self._simulate_wars(eventi_annuali)

        # 4. Stato mondo corrente (serve per dialoghi e outcome)
        previous_state = self._get_current_world_state()

        # 5. Dialoghi autonomi inter-agente via LLM
        dialog_system = AgentDialogSystem(
            self.agents, decade, previous_state, self.rng
        )
        dialoghi = await dialog_system.run_autonomous_dialogs()

        # 6. Calcola impatto demografico ed economico
        demografia, economia = self._calculate_demographic_economic_impact(
            eventi_annuali, eventi_mensili, guerre
        )

        # 7. Eventi politici
        politica = await self._simulate_political_events(eventi_annuali, eventi_mensili)

        # 8. Discussione decennale tra agenti
        topic = DEBATE_TOPICS[(decade // 10) % len(DEBATE_TOPICS)]
        proposals = await self._run_debate(topic)
        decision = self._weighted_vote(proposals)

        # 9. Calcola stato finale
        new_state = self._simulate_outcome(
            decision, previous_state, eventi_annuali, guerre
        )
        etnia_dom = self._get_dominant_etnia()
        relations = self._compute_relations(proposals, decision)

        # 8. Genera report completo
        report = await self._generate_full_report(
            decade, eventi_annuali, guerre, dialoghi, politica, decision
        )

        # 9. Crea nodo grafo con dati completi (inclusi tweet mensili)
        node = GraphNode(
            id=str(uuid.uuid4()),
            simulation_id=self.simulation.id,
            fork_id=self.fork_id,
            decade=decade,
            etnia_dominante=etnia_dom,
            metriche_stato=new_state,
            relazioni=relations,
            decisione=decision,
            eventi=eventi_annuali,
            dialoghi=dialoghi,
            guerre=guerre,
            demografia=demografia,
            economia_dettagliata=economia,
            politica_dettagliata=politica,
            tweet_mensili=eventi_mensili,
            report_completo=report,
            mini_report=report[:2000] if report else None,
        )
        db.add(node)

        self.simulation.current_decade = decade
        db.add(self.simulation)

        await self._update_agents(decision, new_state, db)
        await db.commit()

        logger.info(
            f"[Sim {self.simulation.id[:8]}] Decade {decade} completed with {len(eventi_annuali)} events, {len(guerre)} wars"
        )
        return node

    async def _run_annual_events(self) -> List[Dict[str, Any]]:
        """Genera eventi per ogni anno della decade."""
        eventi = []

        for year in range(1, 11):
            # Determina se c'Ã¨ un evento (70% probabilitÃ )
            if self.rng.random() < 0.7:
                event_type = self.rng.choice(EVENT_TYPES)
                event = await self._generate_annual_event(year, event_type)
                eventi.append(event)

        return eventi

    async def _run_monthly_events(self) -> List[Dict[str, Any]]:
        """Genera eventi mensili con tweet social per tutti i 120 mesi."""
        eventi_mensili = []

        for month in range(1, 121):  # 120 mesi = 10 anni
            year = (month - 1) // 12 + 1

            # Ogni mese ha 1-3 tweet da fazioni diverse
            num_tweets = self.rng.randint(1, 3)
            for _ in range(num_tweets):
                fazione = self.rng.choice(list(TWEET_TEMPLATES.keys()))
                tweet = {
                    "mese": month,
                    "anno": year,
                    "fazione": fazione,
                    "contenuto": self.rng.choice(TWEET_TEMPLATES[fazione]),
                    "viralita": round(self.rng.uniform(0.2, 0.95), 2),
                    "reazioni": {
                        "accordi": self.rng.randint(5, 100),
                        "opposizioni": self.rng.randint(0, 50),
                        "condivisioni": self.rng.randint(0, 30),
                        "commenti": self.rng.randint(0, 40),
                    },
                    "impatto": {
                        "stabilita": round(self.rng.uniform(-0.02, 0.03), 3),
                        "legittimita": round(self.rng.uniform(-0.01, 0.02), 3),
                    },
                }
                eventi_mensili.append(tweet)

            # Eventi speciali mensili (economia, crisi, etc)
            if self.rng.random() < 0.15:  # 15% chance per evento speciale
                evento_tipo = self.rng.choice(
                    [
                        "crisi_economica",
                        "boom_commerciale",
                        "rivolta_minore",
                        "influenza_culturale",
                        "tensioni_diplomatiche",
                    ]
                )
                evento = {
                    "mese": month,
                    "anno": year,
                    "fazione": "sistema",
                    "tipo_evento": evento_tipo,
                    "contenuto": f"{evento_tipo.replace('_', ' ').title()} nel mese {month}",
                    "viralita": round(self.rng.uniform(0.5, 1.0), 2),
                    "reazioni": {
                        "accordi": 0,
                        "opposizioni": 0,
                        "condivisioni": 0,
                        "commenti": 0,
                    },
                    "impatto": self._calcola_impatto_evento(evento_tipo),
                }
                eventi_mensili.append(evento)

        return eventi_mensili

    def _calcola_impatto_evento(self, tipo: str) -> Dict[str, float]:
        """Calcola l'impatto di un evento mensile."""
        impatti = {
            "crisi_economica": {"economia": -0.05, "stabilita": -0.03},
            "boom_commerciale": {"economia": 0.04, "legittimita": 0.02},
            "rivolta_minore": {"stabilita": -0.04, "legittimita": -0.02},
            "influenza_culturale": {"cultura": 0.03, "legittimita": 0.01},
            "tensioni_diplomatiche": {"stabilita": -0.02, "economia": -0.01},
        }
        return impatti.get(tipo, {})

    def _aggregate_monthly_to_annual(
        self, eventi_mensili: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Aggrega eventi mensili in eventi annuali."""
        eventi_annuali = []

        for year in range(1, 11):
            # Filtra tweet di questo anno
            tweet_anno = [
                e for e in eventi_mensili if e.get("anno") == year and "fazione" in e
            ]

            # Crea riassunto annuale basato sui tweet
            fazioni_attive = {}
            for t in tweet_anno:
                fazione = t.get("fazione", "sistema")
                if fazione not in fazioni_attive:
                    fazioni_attive[fazione] = {"count": 0, "viralita": 0, "tweet": []}
                fazioni_attive[fazione]["count"] += 1
                fazioni_attive[fazione]["viralita"] += t.get("viralita", 0)
                fazioni_attive[fazione]["tweet"].append(t.get("contenuto", ""))

            # Se ci sono abbastanza tweet, crea evento annuale
            if len(tweet_anno) >= 3:
                fazione_piu_attiva = max(
                    fazioni_attive.items(), key=lambda x: x[1]["count"]
                )[0]
                viralita_media = sum(t.get("viralita", 0) for t in tweet_anno) / len(
                    tweet_anno
                )

                evento_annuale = {
                    "tipo": "tendenze_annuali",
                    "anno": year,
                    "descrizione": f"Tendenze sociali dell'anno {year}",
                    "partecipanti": list(fazioni_attive.keys()),
                    "fazione_dominante": fazione_piu_attiva,
                    "num_tweet": len(tweet_anno),
                    "viralita_media": round(viralita_media, 2),
                    "outcome": "completato",
                    "impatto": {
                        "stabilita": round(self.rng.uniform(-0.05, 0.05), 3),
                        "legittimita": round(self.rng.uniform(-0.03, 0.03), 3),
                    },
                }
                eventi_annuali.append(evento_annuale)

        return eventi_annuali

    async def _generate_annual_event(
        self, year: int, event_type: str
    ) -> Dict[str, Any]:
        """Genera un evento specifico per l'anno."""
        non_politica = [a for a in self.agents if not a.is_politica]

        if event_type == "guerra":
            if len(non_politica) >= 2:
                a1, a2 = self.rng.sample(non_politica, 2)
                return {
                    "tipo": "guerra",
                    "anno": year,
                    "descrizione": f"Conflitto militare tra {a1.etnia} e {a2.etnia}",
                    "partecipanti": [a1.etnia, a2.etnia],
                    "outcome": self.rng.choice(
                        ["vittoria", "sconfitta", "stallo", "continua"]
                    ),
                    "impatto": {
                        "economia": round(self.rng.uniform(-0.15, 0.05), 3),
                        "militare": round(self.rng.uniform(-0.1, 0.2), 3),
                        "popolazione": round(self.rng.uniform(-0.1, -0.02), 3),
                    },
                }

        elif event_type == "dialogo_interno":
            agent = self.rng.choice(self.agents)
            dialog_type = self.rng.choice(DIALOG_TYPES)
            return {
                "tipo": "dialogo_interno",
                "anno": year,
                "descrizione": f"Consultazione {dialog_type} nel territorio {agent.etnia}",
                "partecipanti": [agent.etnia],
                "tema": self.rng.choice(
                    ["tasse", "guerra", "pace", "carestia", "religione"]
                ),
                "outcome": self.rng.choice(["accordo", "disaccordo", "rimandato"]),
                "impatto": {
                    "stabilita": round(self.rng.uniform(-0.05, 0.1), 3),
                    "legittimita": round(self.rng.uniform(-0.05, 0.05), 3),
                },
            }

        elif event_type == "rivolta":
            agent = self.rng.choice(non_politica if non_politica else self.agents)
            return {
                "tipo": "rivolta",
                "anno": year,
                "descrizione": f"Sollevazione popolare in {agent.etnia}",
                "partecipanti": [agent.etnia],
                "causa": self.rng.choice(
                    ["tasse", "carestia", "oppressione", "corruzione"]
                ),
                "outcome": self.rng.choice(["repressa", "concessioni", "continua"]),
                "impatto": {
                    "stabilita": round(self.rng.uniform(-0.15, -0.05), 3),
                    "economia": round(self.rng.uniform(-0.1, 0), 3),
                },
            }

        elif event_type in ["carestia", "epidemia", "fame"]:
            agent = self.rng.choice(non_politica if non_politica else self.agents)
            return {
                "tipo": event_type,
                "anno": year,
                "descrizione": f"{event_type.capitalize()} colpisce {agent.etnia}",
                "partecipanti": [agent.etnia],
                "gravita": self.rng.choice(["lieve", "moderata", "grave"]),
                "outcome": "in_corso",
                "impatto": {
                    "popolazione": round(self.rng.uniform(-0.15, -0.05), 3),
                    "economia": round(self.rng.uniform(-0.1, -0.02), 3),
                },
            }

        elif event_type == "commercio":
            if len(non_politica) >= 2:
                a1, a2 = self.rng.sample(non_politica, 2)
                return {
                    "tipo": "commercio",
                    "anno": year,
                    "descrizione": f"Accordo commerciale tra {a1.etnia} e {a2.etnia}",
                    "partecipanti": [a1.etnia, a2.etnia],
                    "volume": round(self.rng.uniform(0.05, 0.2), 3),
                    "outcome": "successo",
                    "impatto": {"economia": round(self.rng.uniform(0.02, 0.1), 3)},
                }

        elif event_type == "conquista":
            if len(non_politica) >= 2:
                a1, a2 = self.rng.sample(non_politica, 2)
                return {
                    "tipo": "conquista",
                    "anno": year,
                    "descrizione": f"{a1.etnia} conquista territori di {a2.etnia}",
                    "partecipanti": [a1.etnia, a2.etnia],
                    "territorio_conquistato": round(self.rng.uniform(0.05, 0.2), 3),
                    "outcome": "vittoria",
                    "impatto": {
                        "territorio": round(self.rng.uniform(0.05, 0.15), 3),
                        "militare": round(self.rng.uniform(0.02, 0.08), 3),
                        "prestigio": 0.1,
                    },
                }

        # Default fallback
        return {
            "tipo": "evento",
            "anno": year,
            "descrizione": f"Evento storico nell'anno {year}",
            "partecipanti": [a.etnia for a in self.agents[:2]],
            "outcome": self.rng.choice(["positivo", "negativo", "neutrale"]),
            "impatto": {},
        }

    async def _simulate_wars(
        self, eventi: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Raggruppa eventi di guerra in guerre complete."""
        guerre = []
        war_events = [e for e in eventi if e["tipo"] in ["guerra", "conquista"]]

        if not war_events:
            return guerre

        # Raggruppa per partecipanti
        conflicts = {}
        for event in war_events:
            key = tuple(sorted(event["partecipanti"]))
            if key not in conflicts:
                conflicts[key] = []
            conflicts[key].append(event)

        for (a1, a2), events in conflicts.items():
            if len(events) >= 1:
                inizio = min(e["anno"] for e in events)
                fine = max(e["anno"] for e in events)

                # Calcola perdite
                perdite_a1 = round(self.rng.uniform(0.02, 0.15), 3)
                perdite_a2 = round(self.rng.uniform(0.02, 0.15), 3)

                # Determina esito finale
                outcomes = [e.get("outcome", "stallo") for e in events]
                esito = self._determine_war_outcome(outcomes)

                guerra = {
                    "nome": f"Guerra {a1}-{a2}",
                    "inizio_anno": inizio,
                    "fine_anno": fine,
                    "durata": fine - inizio + 1,
                    "belligeranti": {"attaccante": a1, "difensore": a2},
                    "fasi": [
                        {
                            "anno": e["anno"],
                            "evento": e["descrizione"],
                            "esito": e.get("outcome", "inconcluso"),
                        }
                        for e in sorted(events, key=lambda x: x["anno"])
                    ],
                    "esito_finale": esito,
                    "perdite": {a1: perdite_a1, a2: perdite_a2},
                    "descrizione_dettagliata": f"Conflitto di {fine - inizio + 1} anni tra {a1} e {a2}. Esito: {esito}.",
                }
                guerre.append(guerra)

        return guerre

    def _determine_war_outcome(self, outcomes: List[str]) -> str:
        """Determina l'esito finale di una guerra da una serie di esiti."""
        vittorie = outcomes.count("vittoria")
        sconfitte = outcomes.count("sconfitta")
        if vittorie > sconfitte:
            return "vittoria_attaccante"
        elif sconfitte > vittorie:
            return "vittoria_difensore"
        else:
            return "stallo"

    async def _simulate_internal_dialogs(self, eventi: List[Dict[str, Any]], eventi_mensili: List[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Genera dialoghi interni basati sugli eventi."""
        dialoghi = []

        # Crea dialoghi per eventi di rivolta e successione
        for event in eventi:
            if event["tipo"] in ["rivolta", "successione", "dialogo_interno"]:
                dialogo = {
                    "tipo": event.get("tipo", "senato"),
                    "anno": event["anno"],
                    "contenuto": self._generate_dialog_content(event),
                    "partecipanti": self._generate_dialog_participants(event),
                    "tema": event.get("tema", "politica"),
                    "esito": event.get("outcome", "discusso"),
                    "dettaglio": event["descrizione"],
                }
                dialoghi.append(dialogo)

        # Aggiungi dialoghi casuali
        num_extra_dialogs = self.rng.randint(2, 5)
        for _ in range(num_extra_dialogs):
            dialogo = {
                "tipo": self.rng.choice(DIALOG_TYPES),
                "anno": self.rng.randint(1, 10),
                "contenuto": self._generate_random_dialog(),
                "partecipanti": [
                    a.etnia
                    for a in self.rng.sample(self.agents, min(2, len(self.agents)))
                ],
                "tema": self.rng.choice(
                    ["tasse", "guerra", "pace", "religione", "commercio"]
                ),
                "esito": self.rng.choice(["accordo", "compromesso", "conflitto"]),
                "dettaglio": "Discussione interna sulla gestione dello stato",
            }
            dialoghi.append(dialogo)

        return sorted(dialoghi, key=lambda x: x["anno"])

    def _generate_dialog_content(self, event: Dict[str, Any]) -> str:
        """Genera contenuto dettagliato per un dialogo."""
        templates = {
            "rivolta": [
                "La plebe si solleva contro le tasse eccessive. Richiede riforme immediate.",
                "I contadini protestano per la carestia. Chiedono aiuto dalle autoritÃ .",
                "Fazioni rivali si scontrano nel senato per il controllo del potere.",
            ],
            "successione": [
                "Il senato discute la successione imperiale. Diverse fazioni sostengono candidati diversi.",
                "Crisi di successione: l'imperatore Ã¨ malato. I generali si preparano.",
                "Il popolo chiede un nuovo leader dopo la crisi politica.",
            ],
            "dialogo_interno": [
                "Debate sul bilancio dello stato: aumentare le tasse o ridurre le spese militari?",
                "Discussione commerciale: aprire nuove rotte con i barbari o chiudersi?",
                "Il clero richiede maggiore influenza nelle decisioni politiche.",
            ],
        }

        template_list = templates.get(event["tipo"], ["Discussione interna importante"])
        return self.rng.choice(template_list)

    def _generate_dialog_participants(self, event: Dict[str, Any]) -> List[str]:
        """Genera partecipanti al dialogo."""
        base_participants = event.get("partecipanti", [])
        roles = [
            "Senatore",
            "Console",
            "Generale",
            "Sacerdote",
            "Mercante",
            "Contadino",
        ]

        participants = base_participants.copy()
        num_extra = self.rng.randint(1, 3)
        for _ in range(num_extra):
            role = self.rng.choice(roles)
            name = f"{role} {self.rng.choice(['A', 'B', 'C', 'D', 'E'])}"
            participants.append(name)

        return participants

    def _generate_random_dialog(self) -> str:
        """Genera un dialogo casuale."""
        dialogs = [
            "Discussione sulla gestione delle frontiere settentrionali.",
            "Debate sulle riforme fiscali proposte dal senato.",
            "Consultazione con i generali sulla strategia militare.",
            "Il popolo chiede miglioramenti nelle infrastrutture.",
            "Mercanti richiedono protezione dalle razzie barbariche.",
            "Sacerdoti richiedono fondi per nuovi templi.",
        ]
        return self.rng.choice(dialogs)

    def _calculate_demographic_economic_impact(
        self, eventi: List[Dict[str, Any]], guerre: List[Dict[str, Any]], eventi_mensili: List[Dict[str, Any]] = None
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Calcola impatto demografico ed economico completo."""

        # Calcola popolazione totale
        popolazione_base = sum(
            a.stato_corrente.get("popolazione", 0.5) * 1000000
            for a in self.agents
            if not a.is_politica
        )

        cambiamento_pop = 0.02  # Crescita naturale 2%

        # Applica impatti degli eventi
        for event in eventi:
            impatto = event.get("impatto", {})
            if "popolazione" in impatto:
                cambiamento_pop += impatto["popolazione"]

        # Applica perdite di guerra
        for guerra in guerre:
            perdite = sum(guerra.get("perdite", {}).values()) if isinstance(guerra.get("perdite"), dict) else float(guerra.get("perdite", 0))
            cambiamento_pop -= perdite * 0.5

        popolazione_finale = int(popolazione_base * (1 + cambiamento_pop))

        demografia = {
            "popolazione_totale": popolazione_finale,
            "cambiamento_percentuale": round(cambiamento_pop * 100, 2),
            "distribuzione": self._calculate_population_distribution(),
            "fattori": self._extract_factors(eventi),
        }

        # Economia
        pil_base = popolazione_base * 0.1
        cambiamento_eco = sum(e.get("impatto", {}).get("economia", 0) for e in eventi)

        economia = {
            "pil": round(pil_base * (1 + cambiamento_eco), 2),
            "crescita": round(cambiamento_eco * 100, 2),
            "settori": {
                "agricoltura": round(self.rng.uniform(0.3, 0.5), 2),
                "artigianato": round(self.rng.uniform(0.2, 0.3), 2),
                "commercio": round(self.rng.uniform(0.2, 0.4), 2),
            },
            "commercio_internazionale": self._generate_trade_routes(),
            "crisi": [
                e["tipo"]
                for e in eventi
                if e["tipo"] in ["carestia", "epidemia", "fame"]
            ],
        }

        return demografia, economia

    def _calculate_population_distribution(self) -> Dict[str, float]:
        """Calcola distribuzione popolazione tra etnie."""
        non_politica = [a for a in self.agents if not a.is_politica]
        if not non_politica:
            return {}

        total = len(non_politica)
        return {a.etnia: round(1.0 / total, 3) for a in non_politica}

    def _extract_factors(self, eventi: List[Dict[str, Any]]) -> List[str]:
        """Estrae fattori demografici dagli eventi."""
        factors = []
        for event in eventi:
            if event["tipo"] in ["guerra", "carestia", "epidemia"]:
                factors.append(f"{event['tipo']}_anno{event['anno']}")
        return factors if factors else ["crescita_naturale"]

    def _generate_trade_routes(self) -> List[Dict[str, Any]]:
        """Genera rotte commerciali."""
        routes = []
        non_politica = [a for a in self.agents if not a.is_politica]

        if len(non_politica) >= 2:
            for i in range(min(3, len(non_politica))):
                partner = non_politica[i]
                routes.append(
                    {
                        "partner": partner.etnia,
                        "volume": round(self.rng.uniform(0.05, 0.2), 3),
                        "merci": self.rng.choice(
                            ["grano", "vino", "metalli", "stoffe", "spezie"]
                        ),
                    }
                )

        return routes

    async def _simulate_political_events(
        self, eventi: List[Dict[str, Any]], eventi_mensili: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Simula eventi politici complessi."""
        politica_agent = next((a for a in self.agents if a.is_politica), None)

        # Determina imperatore
        imperatore = "Sconosciuto"
        if politica_agent:
            imperatore = f"Imperatore di {politica_agent.etnia}"

        anni_regno = self.rng.randint(1, 10)

        # Genera fazioni
        fazioni = []
        if politica_agent:
            fazioni = [
                {
                    "nome": "Optimates",
                    "potere": round(self.rng.uniform(0.4, 0.7), 2),
                    "fedelta": round(self.rng.uniform(0.6, 0.9), 2),
                },
                {
                    "nome": "Populares",
                    "potere": round(self.rng.uniform(0.3, 0.6), 2),
                    "fedelta": round(self.rng.uniform(0.4, 0.8), 2),
                },
            ]

        # Genera congiure
        congiure = []
        if self.rng.random() < 0.3:  # 30% probabilitÃ  di congiura
            congiure.append(
                {
                    "anno": self.rng.randint(1, 10),
                    "congiurati": [f"Generale {self.rng.choice(['A', 'B', 'C'])}"],
                    "esito": self.rng.choice(["scoperta", "successo", "fallita"]),
                    "motivo": self.rng.choice(
                        ["ambizione", "corruzione", "tradimento"]
                    ),
                }
            )

        # Genera riforme
        riforme = []
        if self.rng.random() < 0.4:  # 40% probabilitÃ  di riforma
            riforme.append(
                {
                    "anno": self.rng.randint(1, 10),
                    "tipo": self.rng.choice(
                        ["fiscale", "militare", "agraria", "religiosa"]
                    ),
                    "successo": self.rng.choice([True, False]),
                    "descrizione": "Riforma importante del decennio",
                }
            )

        return {
            "imperatore": imperatore,
            "anni_regno": anni_regno,
            "stabilita": round(self.rng.uniform(0.3, 0.8), 2),
            "corruzione": round(self.rng.uniform(0.2, 0.6), 2),
            "fazioni": fazioni,
            "congiure": congiure,
            "riforme": riforme,
            "legittimita": round(self.rng.uniform(0.4, 0.9), 2),
        }

    async def _generate_full_report(
        self,
        decade: int,
        eventi: List[Dict[str, Any]],
        guerre: List[Dict[str, Any]],
        dialoghi: List[Dict[str, Any]],
        politica: Dict[str, Any],
        decision: Dict[str, Any],
    ) -> str:
        """Genera un report storico completo e dettagliato."""

        # Costruisci il report strutturato
        report_parts = []

        # Intro
        report_parts.append(f"# Rapporto Storico: Decade {decade} d.C.")
        report_parts.append(f"\n## Contesto Generale")
        report_parts.append(f"Etnia dominante: {self._get_dominant_etnia()}")
        report_parts.append(f"Periodo: {decade - 10}-{decade} d.C.")

        # Politica
        report_parts.append(f"\n## Situazione Politica")
        report_parts.append(f"Sovrano: {politica.get('imperatore', 'Sconosciuto')}")
        report_parts.append(f"Anni di regno: {politica.get('anni_regno', 0)}")
        report_parts.append(f"Stabilita: {int(politica.get('stabilita', 0.5) * 100)}%")
        report_parts.append(
            f"Corruzione: {int(politica.get('corruzione', 0.3) * 100)}%"
        )

        if politica.get("fazioni"):
            report_parts.append(f"\n### Fazioni Politiche")
            for f in politica["fazioni"]:
                report_parts.append(
                    f"- {f['nome']}: potere {int(f['potere'] * 100)}%, fedelta {int(f['fedelta'] * 100)}%"
                )

        if politica.get("congiure"):
            report_parts.append(f"\n### Congiure")
            for c in politica["congiure"]:
                report_parts.append(
                    f"- Anno {c['anno']}: {c['esito'].upper()} - Motivo: {c['motivo']}"
                )

        if politica.get("riforme"):
            report_parts.append(f"\n### Riforme")
            for r in politica["riforme"]:
                status = "SUCCESSO" if r["successo"] else "FALLIMENTO"
                report_parts.append(
                    f"- Anno {r['anno']}: Riforma {r['tipo']} - {status}"
                )

        # Guerre
        if guerre:
            report_parts.append(f"\n## Conflitti Militari")
            for guerra in guerre:
                nome = guerra.get("nome", "Conflitto sconosciuto")
                report_parts.append(f"\n### {nome}")
                belligeranti = guerra.get("belligeranti", {})
                att = belligeranti.get("attaccante", "?") if isinstance(belligeranti, dict) else "?"
                dif = belligeranti.get("difensore", "?") if isinstance(belligeranti, dict) else "?"
                report_parts.append(f"Durata: {guerra.get('durata','?')} anni ({guerra.get('inizio_anno','?')}-{guerra.get('fine_anno','?')})")
                report_parts.append(f"Belligeranti: {att} vs {dif}")
                report_parts.append(f"Esito: {guerra.get('esito_finale','sconosciuto')}")
                report_parts.append(f"Perdite: {guerra.get('perdite','N/A')}")
                for fase in guerra.get("fasi", []):
                    if isinstance(fase, dict):
                        report_parts.append(f"- Anno {fase.get('anno','?')}: {fase.get('evento','?')} [{fase.get('esito','?')}]")

        # Dialoghi
        if dialoghi:
            report_parts.append(f"\n## Dialoghi e Consultazioni Interne")
            for d in dialoghi[:5]:  # Limita a 5 dialoghi nel report
                report_parts.append(f"\n### {d['tipo'].upper()} - Anno {d['anno']}")
                report_parts.append(f"Tema: {d['tema']}")
                report_parts.append(f"Partecipanti: {', '.join(d['partecipanti'][:3])}")
                report_parts.append(f"Contenuto: {d['contenuto']}")
                report_parts.append(f"Esito: {d['esito']}")

        # Eventi
        report_parts.append(f"\n## Eventi del Decennio")
        eventi_by_type = {}
        for e in eventi:
            t = e["tipo"]
            if t not in eventi_by_type:
                eventi_by_type[t] = []
            eventi_by_type[t].append(e)

        for tipo, events in eventi_by_type.items():
            report_parts.append(f"\n### {tipo.upper()}: {len(events)} eventi")
            for e in events[:3]:  # Mostra max 3 per tipo
                report_parts.append(f"- Anno {e['anno']}: {e['descrizione']}")
                if "impatto" in e:
                    impatto = ", ".join(
                        [f"{k}: {v:+.0%}" for k, v in e["impatto"].items()]
                    )
                    report_parts.append(f"  Impatto: {impatto}")

        # Decisione finale
        report_parts.append(f"\n## Decisione Collettiva")
        report_parts.append(
            f"Proposta vincente: {decision.get('proposta_vincente', 'Nessuna')}"
        )
        report_parts.append(
            f"Proposto da: {decision.get('agente_proposta', 'Sconosciuto')}"
        )
        report_parts.append(f"Supporto: {', '.join(decision.get('supporto', []))}")
        report_parts.append(
            f"Opposizione: {', '.join(decision.get('opposizione', []))}"
        )

        return "\n".join(report_parts)

    async def _run_debate(self, topic: str) -> List[Dict[str, Any]]:
        """Esegue dibattito multi-turno tra agenti."""
        proposals = []
        world_state = self._get_current_world_state()

        for turn in range(settings.max_turns_per_debate):
            for agent in self.agents:
                proposal = await self._get_agent_proposal(
                    agent, topic, world_state, proposals
                )
                proposals.append(proposal)
                if self._check_convergence(proposals):
                    return proposals

        return proposals

    async def _get_agent_proposal(
        self,
        agent: Agent,
        topic: str,
        world_state: Dict[str, Any],
        previous_proposals: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Ottiene proposta da un agente."""
        FALLBACK = {
            "agente": agent.etnia,
            "proposal": "Manteniamo lo status quo",
            "rationale": "Prudenza",
            "confidence": 0.5,
            "vote": {"support": [], "oppose": []},
            "prestigio": agent.prestigio,
            "is_politica": agent.is_politica,
        }

        try:
            recent = previous_proposals[-2:] if previous_proposals else []
            recent_text = (
                "; ".join(
                    f"{p.get('agente', '?')}: {p.get('proposal', '')[:50]}"
                    for p in recent
                )
                or "nessuna"
            )

            prompt = f"""Sei {agent.etnia}. Decade {self.current_decade} d.C.

Stato attuale:
- Economia: {world_state.get("economia", 0.5):.0%}
- Militare: {world_state.get("militare", 0.5):.0%}
- Popolazione: {world_state.get("popolazione", 0.5):.0%}
- Stabilita politica: {world_state.get("politica", {}).get("stabilita", 0.5):.0%}

Argomento: {topic}
Proposte recenti: {recent_text}

Sei {agent.etnia} nel {self.current_decade - 10}-{self.current_decade} d.C. Pensa come un leader storico.
Proponi una strategia appropriata all'epoca.

Rispondi SOLO con questo JSON:
{{"proposal":"la tua proposta strategica","rationale":"motivazione storica dettagliata","confidence":0.7,"vote":{{"support":[],"oppose":[]}}}}"""

            resp = await llm_client.call_json(
                prompt=prompt,
                system=f"Sei {agent.etnia}, leader nel {self.current_decade} d.C. Rispondi SOLO con JSON valido.",
                max_tokens=400,
                temperature=0.8,
            )

            if not resp or not isinstance(resp, dict) or not resp.get("proposal"):
                return FALLBACK

            return {
                "agente": agent.etnia,
                "proposal": str(resp.get("proposal", "status quo")),
                "rationale": str(resp.get("rationale", "")),
                "confidence": float(resp.get("confidence", 0.5)),
                "vote": resp.get("vote", {"support": [], "oppose": []}),
                "prestigio": agent.prestigio,
                "is_politica": agent.is_politica,
            }

        except Exception as e:
            logger.warning(f"Agent {agent.etnia} fallback: {type(e).__name__}")
            return FALLBACK

    def _check_convergence(self, proposals: List[Dict[str, Any]]) -> bool:
        """Controlla se il dibattito e' convergente."""
        if len(proposals) < 2:
            return False
        confs = [p.get("confidence", 0.5) for p in proposals]
        avg = sum(confs) / len(confs)
        variance = sum((c - avg) ** 2 for c in confs) / len(confs)
        return (
            avg >= settings.convergence_confidence_threshold
            and variance < settings.convergence_disagreement_threshold
        )

    def _weighted_vote(self, proposals: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Voto ponderato per prestigio."""
        if not proposals:
            return {
                "proposta_vincente": "status quo",
                "rationale": "",
                "confidence": 0.5,
                "supporto": [],
                "opposizione": [],
            }

        best = max(
            proposals, key=lambda p: p.get("prestigio", 0.5) * p.get("confidence", 0.5)
        )
        supporters = [p["agente"] for p in proposals if p.get("confidence", 0) >= 0.6]
        opposers = [p["agente"] for p in proposals if p.get("confidence", 0) < 0.4]

        return {
            "proposta_vincente": best.get("proposal", "status quo"),
            "agente_proposta": best.get("agente", "unknown"),
            "rationale": best.get("rationale", ""),
            "confidence": best.get("confidence", 0.5),
            "supporto": supporters,
            "opposizione": opposers,
        }

    def _get_current_world_state(self) -> Dict[str, Any]:
        """Ottiene stato attuale del mondo."""
        if not self.agents:
            return {
                "economia": 0.5,
                "militare": 0.5,
                "popolazione": 0.5,
                "politica": {"stabilita": 0.5, "legittimita": 0.5, "corruzione": 0.3},
            }

        non_politica = [a for a in self.agents if not a.is_politica]
        if not non_politica:
            non_politica = self.agents

        eco = sum(a.stato_corrente.get("economia", 0.5) for a in non_politica) / len(
            non_politica
        )
        mil = sum(a.stato_corrente.get("militare", 0.5) for a in non_politica) / len(
            non_politica
        )
        pop = sum(a.stato_corrente.get("popolazione", 0.5) for a in non_politica) / len(
            non_politica
        )

        politica_agent = next((a for a in self.agents if a.is_politica), None)
        politica = (politica_agent.politica_metrics or {}) if politica_agent else {}

        return {
            "economia": eco,
            "militare": mil,
            "popolazione": pop,
            "politica": politica,
        }

    def _simulate_outcome(
        self,
        decision: Dict[str, Any],
        state: Dict[str, Any],
        eventi: List[Dict[str, Any]],
        guerre: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Simula outcome della decisione con impatti eventi."""
        confidence = decision.get("confidence", 0.5)
        noise = self.rng.uniform(-0.08, 0.08)

        eco = state.get("economia", 0.5)
        mil = state.get("militare", 0.5)
        pop = state.get("popolazione", 0.5)
        politica = dict(state.get("politica", {}))

        # Applica impatti eventi
        for event in eventi:
            impatto = event.get("impatto", {})
            if "economia" in impatto:
                eco += impatto["economia"]
            if "militare" in impatto:
                mil += impatto["militare"]
            if "popolazione" in impatto:
                pop += impatto["popolazione"]

        # Applica decisione
        proposal = decision.get("proposta_vincente", "").lower()

        if any(w in proposal for w in ["espansione", "conquista", "guerra"]):
            mil = min(1.0, mil + 0.05 * confidence + noise)
            eco = max(0.0, eco - 0.03 + noise)
        elif any(w in proposal for w in ["commerci", "fiscale", "economia"]):
            eco = min(1.0, eco + 0.07 * confidence + noise)
        elif any(w in proposal for w in ["alleanza", "diplomazi", "pace"]):
            politica["legittimita"] = min(1.0, politica.get("legittimita", 0.5) + 0.05)

        # Impatti guerra
        for guerra in guerre:
            perdite = sum(guerra.get("perdite", {}).values()) if isinstance(guerra.get("perdite"), dict) else float(guerra.get("perdite", 0))
            mil -= perdite * 0.3
            eco -= perdite * 0.2

        return {
            "economia": round(max(0.0, min(1.0, eco)), 3),
            "militare": round(max(0.0, min(1.0, mil)), 3),
            "popolazione": round(max(0.0, min(1.0, pop)), 3),
            "politica": {
                k: round(max(0.0, min(1.0, v)), 3) for k, v in politica.items()
            },
        }

    def _get_dominant_etnia(self) -> str:
        """Determina etnia dominante."""
        non_politica = [a for a in self.agents if not a.is_politica]
        if not non_politica:
            return self.agents[0].etnia if self.agents else "Sconosciuto"

        scores = {}
        for a in non_politica:
            s = a.stato_corrente
            score = (
                s.get("economia", 0.5) * 0.3
                + s.get("militare", 0.5) * 0.4
                + s.get("territorio", 0.5) * 0.3
                + a.prestigio * 0.1
            )
            scores[a.etnia] = score

        return max(scores, key=scores.get)

    def _compute_relations(
        self, proposals: List[Dict[str, Any]], decision: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Calcola relazioni tra agenti."""
        supporters = set(decision.get("supporto", []))
        opposers = set(decision.get("opposizione", []))
        relations = []

        for i, a1 in enumerate(self.agents):
            for a2 in self.agents[i + 1 :]:
                if a1.etnia in supporters and a2.etnia in supporters:
                    tipo, peso = "alleanza", 0.7
                elif (a1.etnia in supporters) != (a2.etnia in supporters):
                    tipo, peso = "tensione", 0.4
                else:
                    tipo, peso = "neutrale", 0.5

                relations.append(
                    {"da": a1.etnia, "a": a2.etnia, "tipo": tipo, "peso": peso}
                )

        return relations

    async def _update_agents(
        self, decision: Dict[str, Any], new_state: Dict[str, Any], db: AsyncSession
    ) -> None:
        """Aggiorna stato agenti."""
        winner = decision.get("agente_proposta")

        for agent in self.agents:
            memoria = dict(agent.memoria or {})

            if agent.etnia == winner:
                agent.prestigio = min(1.0, agent.prestigio + 0.05)
                memoria.setdefault("vittorie", []).append(
                    f"Decade {self.current_decade}"
                )
            elif agent.etnia in decision.get("opposizione", []):
                agent.prestigio = max(0.0, agent.prestigio - 0.02)

            agent.memoria = memoria
            if agent.is_politica:
                agent.politica_metrics = new_state.get("politica", {})

            db.add(agent)

    def check_crisis(self, state: Dict[str, Any]) -> Optional[str]:
        """Controlla se c'Ã¨ crisi."""
        eco = state.get("economia", 1.0)
        mil = state.get("militare", 1.0)
        pol = state.get("politica", {})

        if eco < settings.crisis_economy_threshold:
            return "crisi_economia"
        if mil < settings.crisis_military_threshold:
            return "crisi_militare"
        if pol.get("stabilita", 1.0) < settings.crisis_political_stability:
            return "crisi_politica"

        return None






