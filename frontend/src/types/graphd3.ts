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

  // Dati estesi per child nodes 3D
  eventi: Record<string, unknown>[]
  guerre: Record<string, unknown>[]
  dialoghi: Record<string, unknown>[]

  // Agenti/popolazioni per sotto-nodi etnia
  agenti_info: AgentInfo[]
}

export interface AgentInfo {
  etnia: string
  is_politica: boolean
  prestigio: number
  economia: number
  militare: number
  // Dialoghi interni filtrati per questa etnia
  dialoghi_interni: Record<string, unknown>[]
  // Dialoghi diplomatici con altre etnie
  dialoghi_diplomatici: Record<string, unknown>[]
}
