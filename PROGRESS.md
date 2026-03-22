# World Simulation - Log Progressi

## Data: 2024-03-21 (aggiornato)

---

## Fase 1: Fondamenti Backend — COMPLETATA ✓

[vedere versione precedente]

---

## Fase 2: Core Engine + API + Frontend — COMPLETATA ✓

### Backend — Nuovi file creati

#### Services
- **services/llm_client.py** — Client Kimi API con:
  - Rate limiting 40 RPM via asyncio.Lock
  - Backoff esponenziale (1s→2s→4s…→64s) su 429/5xx
  - `call()` base e `call_json()` con parsing JSON + retry
  - Stripping automatico markdown fence

- **services/history_service.py** — Generazione mini report decennali:
  - Prompt storico contestuale per ogni GraphNode
  - Persistenza report nel campo `mini_report`

- **services/report_generator.py** — Report finale REPORT.md:
  - Aggrega timeline, agenti, fork
  - Prompt LLM per analisi storiografica completa
  - Fallback senza LLM
  - Salva su `data/reports/{simulation_id}.md`
  - Segna simulazione come `completed` al termine

#### Core
- **core/agent_factory.py** — Generazione società iniziale:
  - Prompt LLM → JSON config con 3-12 agenti storici
  - Garantisce presenza agente `is_politica`
  - Scrive system prompt su file per ogni agente
  - Calcola `personalita_seed` deterministico (hash)
  - Fallback society se LLM fallisce

- **core/simulation_society.py** — Engine centrale:
  - `step_decade()`: loop completo decennale
  - `_run_debate()`: multi-turno con convergenza
  - `_weighted_vote()`: voto ponderato per prestigio
  - `_simulate_outcome()`: effetti stocastici basati su keyword proposta
  - `_update_agents()`: memoria + prestigio post-dibattito
  - `check_crisis()`: verifica soglie su 5 metriche

- **core/fork_manager.py** — Gestione fork:
  - `ForkManager.create_fork()`: snapshot + seed deterministico
  - `ForkEvaluator.evaluate_all_forks()`: scoring darwiniano ogni 10 decadi
  - Marcatura automatica fork dead/winning

- **core/checkpoint.py**:
  - `save_checkpoint()`: snapshot agenti + nodi + fork
  - `resume_checkpoint()`: carica da checkpoint_id

#### Workers
- **workers/simulation_worker.py** — Celery tasks:
  - `step_decade_task`: step decade + crisis detection + fork spawn
  - Fallback inline senza Celery (dev mode)
  - Broadcast SSE post-step
  - Auto-checkpoint ogni N decadi
  - Fork evaluation ogni 100 decadi

#### API Endpoints
- **api/v1/schemas/simulation.py** — Pydantic schemas:
  - `SimulationStartRequest`, `SimulationResponse`
  - `AgentResponse`, `GraphNodeResponse`, `ForkResponse`
  - `SimulationFullResponse`, `CheckpointResponse`

- **api/v1/endpoints/simulation.py**:
  - `POST /simulation/start` — avvio + lock utente
  - `GET /simulation/{id}` — stato completo
  - `POST /simulation/{id}/pause|resume`
  - `POST /simulation/{id}/fork` — fork manuale
  - `POST /simulation/{id}/step` — step singolo (dev)
  - `GET /simulation/{id}/checkpoints`
  - `POST /resume-checkpoint?checkpoint_id=X`

- **api/v1/endpoints/agents.py**:
  - `GET /agents/simulation/{id}` — lista agenti
  - `GET /agents/{agent_id}` — agente singolo

- **api/v1/endpoints/graph.py**:
  - `GET /graph/simulation/{id}/nodes` — nodi filtrabili per fork/decade
  - `GET /graph/simulation/{id}/nodes/{node_id}` — nodo singolo
  - `GET /graph/simulation/{id}/forks` — lista fork
  - `GET /graph/simulation/{id}/graph-data` — formato D3 {nodes, links}

- **api/v1/endpoints/reports.py**:
  - `POST /reports/simulation/{id}/generate`
  - `GET /reports/simulation/{id}` → PlainText REPORT.md

- **api/ws/simulation_stream.py** — SSE endpoint:
  - `GET /simulation/{id}/stream`
  - Event queue per subscriber con asyncio.Queue
  - Heartbeat ogni 25s
  - `broadcast_event()` chiamabile da worker/Celery

---

### Frontend — Creato da zero

#### Setup
- `package.json` — React 18, Three.js, R3F, Drei, Zustand, Axios, Vite
- `vite.config.ts` — proxy `/api` → `localhost:8000`
- `tsconfig.json` — TypeScript strict
- `index.html` — dark base, no scroll

#### Struttura src/
```
src/
├── main.tsx              — ReactDOM.createRoot
├── App.tsx               — Layout con SplitPane manuale (draggable)
├── types/index.ts        — Tutti i tipi TypeScript
├── api/
│   ├── client.ts         — Axios wrapper per tutti gli endpoint
│   └── useSSE.ts         — Hook EventSource con auto-refresh grafo
├── store/
│   └── simStore.ts       — Zustand store globale
└── components/
    ├── Graph3D/
    │   └── Graph3D.tsx   — Canvas R3F con nodi 3D animati
    ├── StatusPanel.tsx   — Pannello sinistro: stato, agenti, fork, log
    ├── AgentChat.tsx     — Pannello destro: dibattiti, decisioni, feed live
    └── ControlBar.tsx    — Top bar: avvio, pausa, step, report
```

#### Graph3D.tsx features:
- React Three Fiber + Three.js
- Nodi icosaedro animati (rotazione + scala su hover/select)
- Colori per fork_status: main/winning/active/dead
- Dimensione nodo proporzionale a economia+militare
- Layout 3D: asse X = tempo, fork su archi circolari
- Edges timeline (blu scuro) + fork_origin (arancio tratteggiato)
- Labels decade + etnia su hover
- OrbitControls con damping
- Legenda colori

#### StatusPanel.tsx:
- Indicatore stato simulazione (live dot)
- Decade corrente grande
- Dettaglio nodo selezionato (metriche + mini report)
- Lista agenti con barre economia/militare + prestigio
- Badge fork vincitrice
- Log eventi SSE

#### AgentChat.tsx:
- Dettaglio decisione nodo selezionato (proposta + supporto/opposizione badge)
- Schede agenti con mini-barre metriche
- Feed live eventi step_complete cronologico

#### ControlBar.tsx:
- Modal "Nuova simulazione" con textarea descrizione
- Bottoni Pausa/Riprendi, Step singolo, Aggiorna, Genera Report

---

## Come avviare

### Backend
```bash
cd backend
pip install -r requirements.txt
# Configurare .env con KIMI_API_KEY
docker-compose up -d db redis
uvicorn src.main:app --reload --port 8000

# (opzionale) Celery worker
celery -A src.workers.simulation_worker.celery_app worker --loglevel=info
```

### Frontend
```bash
cd frontend
npm install
npm run dev   # → http://localhost:3000
```

---

## Stato Corrente
**PROGETTO COMPLETO** — Backend + Frontend implementati integralmente.

Pendente: test end-to-end con API key reale e database running.
