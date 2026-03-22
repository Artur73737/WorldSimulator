import { create } from 'zustand'
import type { SimulationData, AgentData, GraphD3Node, GraphD3Link, ForkData, SSEEvent } from '../types'

interface SimStore {
  simulationId: string | null
  simulation: SimulationData | null
  agents: AgentData[]
  graphNodes: GraphD3Node[]
  graphLinks: GraphD3Link[]
  forks: ForkData[]
  selectedNodeId: string | null
  liveEvents: SSEEvent[]
  sseConnected: boolean
  report: string | null
  showReport: boolean

  setSimulation: (sim: SimulationData) => void
  setSimulationId: (id: string) => void
  setAgents: (agents: AgentData[]) => void
  setGraphData: (nodes: GraphD3Node[], links: GraphD3Link[]) => void
  setForks: (forks: ForkData[]) => void
  selectNode: (id: string | null) => void
  pushEvent: (event: SSEEvent) => void
  setSseConnected: (v: boolean) => void
  setReport: (r: string | null) => void
  setShowReport: (v: boolean) => void
  reset: () => void
}

export const useSimStore = create<SimStore>((set) => ({
  simulationId: null,
  simulation: null,
  agents: [],
  graphNodes: [],
  graphLinks: [],
  forks: [],
  selectedNodeId: null,
  liveEvents: [],
  sseConnected: false,
  report: null,
  showReport: false,

  setSimulation: (sim) => set({ simulation: sim }),
  setSimulationId: (id) => set({ simulationId: id }),
  setAgents: (agents) => set({ agents }),
  setGraphData: (nodes, links) => set({ graphNodes: nodes, graphLinks: links }),
  setForks: (forks) => set({ forks }),
  selectNode: (id) => set({ selectedNodeId: id }),
  pushEvent: (event) => set((s) => ({ liveEvents: [...s.liveEvents.slice(-49), event] })),
  setSseConnected: (v) => set({ sseConnected: v }),
  setReport: (r) => set({ report: r }),
  setShowReport: (v) => set({ showReport: v }),
  reset: () => set({
    simulationId: null, simulation: null, agents: [], graphNodes: [],
    graphLinks: [], forks: [], selectedNodeId: null, liveEvents: [],
    sseConnected: false, report: null, showReport: false,
  }),
}))
