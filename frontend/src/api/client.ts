import axios from 'axios'
import type { SimulationData, AgentData, GraphNodeData, ForkData, GraphD3Node, GraphD3Link } from '../types'

const api = axios.create({ baseURL: '/api/v1' })

export const startSimulation = (description: string, userId = 'anonymous') =>
  api.post<SimulationData>('/simulation/start', { description, user_id: userId }).then(r => r.data)

export const getSimulation = (id: string) =>
  api.get<{ simulation: SimulationData; agents: AgentData[]; graph_nodes: GraphNodeData[]; forks: ForkData[] }>(`/simulation/${id}`).then(r => r.data)

export const pauseSimulation = (id: string) =>
  api.post<SimulationData>(`/simulation/${id}/pause`).then(r => r.data)

export const resumeSimulation = (id: string) =>
  api.post<SimulationData>(`/simulation/${id}/resume`).then(r => r.data)

export const stepSimulation = (id: string) =>
  api.post<GraphNodeData>(`/simulation/${id}/step`).then(r => r.data)

export const createFork = (id: string, reason = 'manual') =>
  api.post<ForkData>(`/simulation/${id}/fork`, { trigger_reason: reason }).then(r => r.data)

export const getGraphData = (id: string) =>
  api.get<{ nodes: GraphD3Node[]; links: Array<GraphD3Link> }>(`/graph/simulation/${id}/graph-data`).then(r => r.data)

export const getAgents = (id: string) =>
  api.get<AgentData[]>(`/agents/simulation/${id}`).then(r => r.data)

export const generateReport = (id: string) =>
  api.post(`/reports/simulation/${id}/generate`).then(r => r.data)

export const getReport = (id: string) =>
  api.get<string>(`/reports/simulation/${id}`, { responseType: 'text' }).then(r => r.data)
