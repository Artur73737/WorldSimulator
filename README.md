Architettura del Progetto - Versione Completa Espansa (1520 parole)
Panoramica Dettagliata
Il sistema World Simulation è una simulazione evolutiva di società storiche dove agenti LLM rappresentano etnie/popoli che interagiscono attraverso dibattiti persistenti su scala decennale. L'utente definisce l'ambiente iniziale in massimo cinque righe testuali (es: "Mediterraneo 200 d.C., Roma dominante, tribù germaniche ai confini"). Un LLM Kimi genera dinamicamente la configurazione iniziale completa: numero agenti (3-12), identità etniche precise, system prompt individuali, relazioni iniziali, stato mondo baseline e primo nodo grafo. Il motore centrale (SimulationSociety) itera automaticamente attraverso centinaia di decadi, gestendo dibattiti multi-turno, decisioni collettive, outcome probabilistici ed evoluzione dello stato. Crisi sistemiche (soglie configurabili su metriche come economia<20%, militare<15%) triggerano fork parallele sequenziali che competono darwinianamente. Il prodotto finale è triplice: grafo 3D interattivo navigabile (React Three Fiber), pannelli consultabili per stato storico/presente, e REPORT.md esaustivo con analisi completa della simulazione vincitrice.

Vincoli e Regole Tecniche Rispettate
Isolamento utente: Singola simulazione attiva per utente (lock via database row-level)

Rate limit Kimi API: Limite rigido 40 RPM — chiamate LLM solo sequenziali con back-off esponenziale (1s, 2s, 4s...) su 429/errori server

Configurazione agenti: Numero massimo definito dal primo LLM Kimi (fallback: MAX_AGENTS_DEFAULT=8 da settings.py) o override utente

Fork handling: Automatiche su crisi + manuali via API /v1/simulation/{id}/fork

Riproducibilità: Seed univoco per fork (hash descrizione+timestamp+env SIMULATION_SEED), leggibile da FORK_SEED env var

UI philosophy: Minimalismo Apple — pannelli ridimensionabili (React SplitPane), area centrale 100% grafo 3D, zero emoji/decorazioni

Fedeltà storica: Output agenti vincolati a linguaggio antico contestuale — divieto assoluto di anacronismi/tecnologia moderna (enforced via system prompt)

Componenti Principali Espansi
Gestione Agenti LLM (Dettaglio Completo)
Tutti gli agenti nascono dal primo LLM Kimi via AgentFactory.create_initial_society() — output JSON con etnie, ruoli, relazioni baseline.

Proprietà agente (modello Agent in models/agent.py):

text
id: UUID
etnia: str (es: "Goti Orientali")
system_prompt_path: str (core/prompts/goti_orientali.txt)
memoria: JSONB (vittorie=[], sconfitte=[], alleanze={}, tradimenti=[])
prestigio: float (0.0-1.0, accumulato da successi)
personalita_seed: int (hash(env.SIMULATION_SEED + etnia))
bias_vector: JSONB (militare_bias=0.7, economia_bias=-0.2...)
stato_corrente: JSONB (risorse, territorio, popolazione)
System prompt structure (file + injection):

text
[FILE FISSO: core/prompts/{etnia}.txt]
Sei {etnia}, popolo fiero del {periodo}. Parla solo antico. Rispondi JSON.

[INIEZIONE DINAMICA]
Contesto: {stato_mondo}
Ultimi eventi: {lista_5_eventi}
Tua memoria: {memoria_personale}
Proponi: {debate_topic}
Vincoli output rigorosi:

text
{"proposal": str, "rationale": str, "confidence": 0.0-1.0, "vote": {"support": [], "oppose": []}}
AgentFactory workflow:

Primo LLM: generate_society(descrizione_utente) → JSON config

Per ogni etnia: crea file prompt, inizializza memoria, calcola bias da seed

Persistenza: Agent.create() → database

Gestione turni dibattito:

text
config.MAX_TURNS_PER_DEBATE (default=5)
Sequenza: Agent1→Agent2→...→AgentN→convergenza o timeout
Convergenza: 70% confidence media + <20% disagreement
Rate-limit wrapper (services/llm_client.py):

text
async def call_kimi(prompt):
    while True:
        try:
            resp = await kimi_api(prompt)
            return resp
        except RateLimitError:
            await asyncio.sleep(backoff_time)
Simulation Engine Dettagliato
SimulationSociety gestisce ciclo vita completo.

Ciclo decennale espanso (pseudocodice):

text
async def step_decade(self):
    # 1. Carica stato/memorie
    stato = self.load_state()
    
    # 2. Debate loop
    topic = self.generate_debate_topic(stato)
    proposals = await self.run_debate(topic)
    
    # 3. Voto ponderato
    decision = self.weighted_vote(proposals, pesi_prestigio)
    
    # 4. Outcome probabilistico
    nuovo_stato = self.simulate_outcome(decision, stato)
    
    # 5. Salva grafo
    node = GraphNode(decade=self.current_decade, stato=nuovo_stato)
    node.save()
    
    # 6. Check crisi + fork
    if self.is_crisis(nuovo_stato):
        await ForkManager.create_fork(self.id)
    
    # 7. Mini report + update memorie
    await HistoryService.generate_mini_report(node.id)
    await self.update_agent_memories(decision)
Database Schema chiave:

text
GraphNode:
- id: UUID primary_key
- simulation_id: UUID
- parent_fork_id: UUID nullable
- decade: int (200, 210...)
- etnia_dominante: str
- metriche_stato: JSONB {"economia":0.45, "militare":0.60...}
- relazioni: JSONB [{"etnia":"Goti", "tipo":"guerra", "peso":0.8}]

Agent:
- id: UUID
- simulation_id: UUID
- etnia: str unique per sim
- system_prompt_path: str
- memoria: JSONB
- prestigio: float
Fork Management Completo
ForkManager + ForkEvaluator (fork sequenziali per rate limit).

Politica Agent - Dettaglio Completo
Ruolo critico: Il PoliticaAgent è l'arbitro interno della società — gestisce successione imperatori, corruzione, colpi di stato, alleanze interne, fazioni nobiliari e stabilità istituzionale.

Identità e Bias
text
Etnia: "Senato Romano" / "Corte Imperiale" / "Consiglio Tribale"
Bias principali:
- Stabilità istituzionale (+0.8)
- Corruzione personale (-0.6) 
- Centralizzazione potere (+0.7)
- Legittimità dinastica (+0.5)
Personalità seed: influenza ambizione vs lealtà
System Prompt Specifico (core/prompts/politica_romana.txt)
text
Sei il Senato/Corte Imperiale di Roma. Mantieni equilibrio potere.
Parla formale antico. Analizza:
- Legittimità imperatore corrente
- Fazioni interne (optimates/populares)
- Rischio colpi stato
- Corruzione funzionari

Proponi: nomine, esili, riforme costituzionali.
Contributi al Dibattito Decennale
Proposte tipiche del PoliticaAgent:

text
Round Economia: "Aumenta tasse → rischio rivolta plebei (-stabilità)"
Round Militare: "Imperatore debole → generali ribelli (colpo stato 40%)"
Round Crisi: "Convoca comizi → nuova dinastia (legittimità +0.3)"
Metriche Politiche nel Stato Mondo
text
politica: {
  "stabilità": 0.65,           # Rischio collasso istituzionale
  "legittimità": 0.72,         # Supporto dinastia
  "corruzione": 0.45,          # Indebolisce economia/militare
  "fazioni_conflitto": 0.3,    # Interno lotta potere
  "successione_rischio": 0.8   # Morte imperatore → caos
}
Trigger Crisi Politiche (fork automatiche)
text
if stabilità < 0.2: "Colpo di stato militare"
if legittimità < 0.1: "Rivoluzione popolare" 
if corruzione > 0.9: "Anarchia amministrativa"
Evoluzione Memoria Politica
text
Memoria JSONB:
{
  "imperatori": [{"nome": "Valentiniano", "durata": 12a, "causa_fine": "assassinato"}],
  "colpi_stato": 3,
  "riforme_fallite": ["tasse_395", "esercito_408"],
  "alleanze_broken": ["senato_goti"]
}
Interazione con Altri Agenti
text
- Economia: "Senato blocca tasse eccessive"
- Militare: "Imperatore nomina generali leali"
- Clima: "Careste → imperatore delegittimato"
- Cultura: "Nuova religione → scisma senato"
Esempio Output JSON (Debate Turno 3)
json
{
  "proposal": "Esilia generali ribelli, nomina Valentiniano III",
  "rationale": "Dinastia Teodosiana debole, ma legittima. Militari usurpatori rischiano guerra civile.",
  "confidence": 0.82,
  "vote": {
    "support": ["economia", "cultura"],
    "oppose": ["militare"],
    "stabilità_impatto": +0.15,
    "legittimità_impatto": +0.22
  }
}
Impatto sul Grafo 3D
Nodi colorati arancione = crisi politica dominante
Edge "successione" = frecce dinastiche tra imperatori
Hover nodo: "395 d.C.: Onorio esiliato, Stilicone reggente"

Perché è Essenziale
Senza PoliticaAgent, la simulazione sarebbe solo "risorse + eserciti". La politica introduce:

Caos interno più pericoloso di invasioni esterne

Decisioni stupide anche con risorse abbondanti

Fork drammatiche (es: "Imperatore bambino vs generale carismatico")

Esempio fork politica:

text
Main: Imperatore debole → collasso 476
Fork: Colpo stato militare → nuova dinastia germanica → sopravvive +50 anni

Creazione fork:

text
if crisi_score > CRISIS_THRESHOLD (configurabile):
    new_fork = ForkManager.create(
        parent_id=self.id,
        seed=hash(self.seed + decade),
        stato_divergente=generate_alternative_stato()
    )
    await Celery.send_task("simulation_worker.step_fork", new_fork.id)
ForkEvaluator (ogni 10 decadi):

text
scores = {}
for fork in active_forks:
    scores[fork.id] = {
        "longevity": (current_decade - fork.start_decade),
        "resilience": 1 - min_stato[fork],
        "innovation": num_forks_spawned[fork],
        "total": weighted_sum
    }
if max_score_fork.stato_critico < 0.1:
    mark_dead(max_score_fork)
Task Queue + Streaming
Celery + Redis per background processing:

text
@celery.task
def step_fork(fork_id):
    society = SimulationSociety.load(fork_id)
    society.step_decade()
    broadcast_sse(fork_id, "step_complete")
SSE endpoint (api/ws/simulation_stream.py):

text
SSE /v1/simulation/{id}/stream → events: agent_chat, graph_update, fork_created
Agent Lifecycle
text
- Conquista: Agent.kill() → memoria → inglobata in vincitore.system_prompt
- Spawn nuovo: AgentFactory.spawn(context=evento_storico)
Checkpoint System
Auto-save ogni 10 decadi:

text
SimulationCheckpoint.save({
    "fork_states": active_forks,
    "agent_memories": all_memories,
    "graph_nodes": recent_nodes
})
Resume: POST /v1/resume?checkpoint_id=X
Mini Report + Report Finale (invariati)
[Sezione originale mantenuta identica]

Frontend (Espanso)
Layout responsivo con SplitPane:

text
[StatusPanel | Graph3D 70% | AgentChat]
Ridimensionabile + persistenza localStorage
Graph3D.tsx features:

React Three Fiber + D3-force per layout 3D

Click nodo → carica mini_report + chat contestuale

Color coding: etnia_dominante (blu=roma, rosso=goti...)

Zoom timeline (drag decade range)

Flusso Completo Dettagliato
text
1. POST /v1/start → AgentFactory → nodo_0
2. Celery: iterazioni sequenziali (1 fork/step)
3. SSE stream → frontend live updates
4. Crisi → ForkManager → nuova task Celery
5. Fine → ReportGenerator → REPORT.md
Struttura Cartelle Finale Completa
text
world-simulation/
├── CHANGELOG.md                    ├── docker-compose.yml (PostgreSQL+Redis+Celery)
├── backend/
│   ├── migrations/ (Alembic)       ├── workers/simulation_worker.py
│   ├── src/
│   │   ├── api/ws/simulation_stream.py
│   │   ├── core/
│   │   │   ├── fork_manager.py     ├── fork_evaluator.py
│   │   │   ├── checkpoint.py       ├── simulation_society.py
│   │   └── services/llm_client.py
├── frontend/src/components/Graph3D/
└── data/{checkpoints/, reports/}