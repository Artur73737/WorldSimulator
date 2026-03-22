export interface SimulationData {
  id: string
  user_id: string
  seed: string
  status: string
  current_decade: number
  initial_description: string
  created_at: string
  updated_at: string
}

export interface AgentData {
  id: string
  etnia: string
  prestigio: number
  is_politica: boolean
  stato_corrente: Record<string, number>
  memoria: Record<string, unknown>
  bias_vector: Record<string, number>
}

// Eventi complessi all'interno di una decade
export interface AnnualEvent {
  tipo: string
  anno: number
  descrizione: string
  partecipanti: string[]
  outcome: string
  impatto?: Record<string, number>
  causa?: string
  gravita?: string
  volume?: number
  merci?: string
  territorio_conquistato?: number
}

// Guerre complete con fasi
export interface WarPhase {
  anno: number
  evento: string
  esito: string
}

export interface WarData {
  nome: string
  inizio_anno: number
  fine_anno: number
  durata: number
  belligeranti: { attaccante: string; difensore: string }
  fasi: WarPhase[]
  esito_finale: string
  perdite: Record<string, number>
  descrizione_dettagliata: string
}

// Dialoghi interni
export interface DialogData {
  tipo: string
  anno: number
  contenuto: string
  partecipanti: string[]
  tema: string
  esito: string
  dettaglio: string
}

// Politica dettagliata
export interface FactionData {
  nome: string
  potere: number
  fedelta: number
}

export interface ConspiracyData {
  anno: number
  congiurati: string[]
  esito: string
  motivo: string
}

export interface ReformData {
  anno: number
  tipo: string
  successo: boolean
  descrizione: string
}

export interface PoliticaData {
  imperatore: string
  anni_regno: number
  stabilita: number
  corruzione: number
  legittimita: number
  fazioni: FactionData[]
  congiure: ConspiracyData[]
  riforme: ReformData[]
}

// Demografia
export interface DemografiaData {
  popolazione_totale: number
  cambiamento_percentuale: number
  distribuzione: Record<string, number>
  fattori: string[]
}

// Economia dettagliata
export interface TradeRoute {
  partner: string
  volume: number
  merci: string
}

export interface EconomiaData {
  pil: number
  crescita: number
  settori: {
    agricoltura: number
    artigianato: number
    commercio: number
  }
  commercio_internazionale: TradeRoute[]
  crisi: string[]
}

// Relazioni inter-etniche
export interface RelationData {
  da: string
  a: string
  tipo: string
  peso: number
}

// Decisione collettiva
export interface DecisionData {
  proposta_vincente: string
  agente_proposta: string
  rationale: string
  confidence: number
  supporto: string[]
  opposizione: string[]
}

// Stato metriche
export interface MetricheStato {
  economia: number
  militare: number
  popolazione: number
  politica?: {
    stabilita: number
    legittimita: number
    corruzione: number
    fazioni_conflitto: number
    successione_rischio: number
  }
}

// GraphNode completo
export interface GraphNodeData {
  id: string
  decade: number
  etnia_dominante: string | null
  metriche_stato: MetricheStato
  relazioni: RelationData[]
  decisione: DecisionData | null
  mini_report: string | null
  report_completo: string | null
  fork_id: string | null
  created_at: string

  // Dati complessi
  eventi: AnnualEvent[]
  dialoghi: DialogData[]
  guerre: WarData[]
  demografia: DemografiaData
  economia_dettagliata: EconomiaData
  politica_dettagliata: PoliticaData
}

export interface ForkData {
  id: string
  parent_fork_id: string | null
  created_at_decade: number
  trigger_reason: string
  status: string
  score: { longevity: number; resilience: number; innovation: number; total: number } | null
  diverged_state: Record<string, unknown>
}

export interface AgentInfo {
  etnia: string
  is_politica: boolean
  prestigio: number
  economia: number
  militare: number
  dialoghi_interni: Record<string, unknown>[]
  dialoghi_diplomatici: Record<string, unknown>[]
}

export interface GraphD3Node {
  id: string
  decade: number
  etnia_dominante: string | null
  fork_id: string | null
  fork_status: string
  economia: number
  militare: number
  popolazione: number
  mini_report: string
  decisione: Record<string, unknown> | null
  agenti_info: AgentInfo[]

  // Dati estesi per 3D
  eventi: Record<string, unknown>[]
  guerre: Record<string, unknown>[]
  dialoghi: Record<string, unknown>[]
}

export interface GraphD3Link {
  source: string
  target: string
  type: string
}

export interface SSEEvent {
  type: 'connected' | 'step_complete' | 'fork_created' | 'agent_chat'
  data: Record<string, unknown>
}

