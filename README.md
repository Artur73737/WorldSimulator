<div align="center">
  <img src="docs/logo.png" width="450" alt="World Simulation Logo" />

  # World Simulation

  **Simulazione Evolutiva di Società Storiche su Larga Scala**

  ---

  [Concept](#concetto) • [Caratteristiche](#caratteristiche) • [Architettura](#architettura) • [Setup](#setup)

</div>

<br />

## Concetto

Un ecosistema dinamico in cui il passato riprende vita attraverso agenti LLM. **World Simulation** non è solo un software di modellazione, ma un'arena darwiniana dove popoli, etnie e imperi competono, deliberano ed evolvono sotto il peso della storia e della causalità probabilistica.

Gli utenti definiscono un frammento di realtà — cinque righe per delineare un'epoca — e lasciano che il motore generativo orchestrato da Kimi LLM tracci il destino di intere civiltà.

<br />

<details>
<summary><strong>Punti di Forza del Sistema</strong></summary>
<br />
<blockquote>
Il sistema si fonda su tre pilastri fondamentali che garantiscono una profondità simulativa senza precedenti.
</blockquote>

- **Agenti con Memoria Persistente**: Ogni etnia possiede una coscienza storica, ricordando alleanze tradite e vittorie passate.
- **Dinamiche di Crisi e Forking**: Quando la stabilità vacilla, la simulazione si biforca in rami paralleli, testando diverse linee temporali.
- **Navigazione Temporale 3D**: Un grafo interattivo permette di esplorare ogni nodo decade per decade, osservando l'ascesa e la caduta dei regimi.
</details>

<br />

## Caratteristiche

Utilizziamo un approccio modulare per gestire la complessità di una società in evoluzione.

| Modulo | Funzione | Descrizione |
| :--- | :--- | :--- |
| **SimulationSociety** | Core Engine | Gestisce il ciclo decennale, i dibattiti e la risoluzione degli outcome. |
| **AgentFactory** | Genesi | Inizializza le identità etniche, i system prompt e i bias psicologici. |
| **ForkManager** | Evoluzione | Monitora le crisi sistemiche e genera linee temporali alternative. |
| **HistoryService** | Analisi | Produce report dettagliati e analisi sintetiche di ogni epoca. |

<br />

<details>
<summary><strong>Esplora l'Archiettura Tecnica (Deep Dive)</strong></summary>
<br />

Il sistema è suddiviso in un backend Python ad alte prestazioni e un frontend React focalizzato sulla visualizzazione dei dati.

### Backend (Python/FastAPI)
- **Motore di Dibattito**: Gestisce la convergenza del consenso tra 3-12 agenti simultanei.
- **Persistence Layer**: PostgreSQL per lo stato globale e Redis per i flussi in tempo reale.
- **Worker Celery**: Elaborazione distribuita delle fork sequenziali per rispettare i rate limit LLM.

### Frontend (React/ThreeJS)
- **Grafo 3D**: Visualizzazione spaziale dei nodi storici tramite React Three Fiber.
- **SSE Stream**: Aggiornamenti live della chat degli agenti e della creazione di nuove fork.
- **UI Apple-Minimal**: Pannelli modulari e ridimensionabili con integrazione SplitPane.

</details>

<br />

## Setup e Utilizzo

Per avviare l'intero ambiente di simulazione è sufficiente uno script centralizzato.

### Installazione Automatica
```bash
npm run install:all
```

### Avvio Ambiente
```bash
npm run dev
```

> [!NOTE]
> Assicurarsi di configurare il file `.env` nel backend con le chiavi API necessarie (Kimi, PostgreSQL, Redis).

<br />

---

<div align="center">
  <p><strong>World Simulation</strong> • Versione 1.0.0</p>
  <p><em>Progettato per la riproduzione e l'analisi di dinamiche storiche complesse.</em></p>
  <br />
  <code>v1.0.0 - Stabile • 2026</code>
</div>