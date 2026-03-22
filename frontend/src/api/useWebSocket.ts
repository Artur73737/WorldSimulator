import { useEffect, useRef } from 'react'
import { useSimStore } from '../store/simStore'
import { getGraphData, getSimulation } from '../api/client'
import type { SSEEvent } from '../types'

export function useSimWebSocket(simulationId: string | null) {
  const pushEvent       = useSimStore(s => s.pushEvent)
  const setSseConnected = useSimStore(s => s.setSseConnected)
  const setGraphData    = useSimStore(s => s.setGraphData)
  const setSimulation   = useSimStore(s => s.setSimulation)
  const setAgents       = useSimStore(s => s.setAgents)
  const setForks        = useSimStore(s => s.setForks)
  const setReport       = useSimStore(s => s.setReport)
  const setShowReport   = useSimStore(s => s.setShowReport)
  const wsRef           = useRef<WebSocket | null>(null)
  const retryRef        = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    if (!simulationId) return
    let active = true

    const connect = () => {
      if (!active) return
      const ws = new WebSocket(`ws://localhost:8000/api/v1/simulation/${simulationId}/ws`)
      wsRef.current = ws

      ws.onopen  = () => { setSseConnected(true); console.log('[WS] connected') }
      ws.onclose = () => {
        setSseConnected(false)
        if (active) retryRef.current = setTimeout(connect, 3000)
      }

      ws.onmessage = async (e) => {
        // Skip non-JSON (pong)
        if (typeof e.data !== 'string' || !e.data.startsWith('{')) return
        try {
          const event = JSON.parse(e.data) as SSEEvent & { type: string }
          if (event.type === 'heartbeat' || event.type === 'connected') return

          pushEvent(event as SSEEvent)

          if (event.type === 'step_complete') {
            const [full, graphData] = await Promise.all([
              getSimulation(simulationId),
              getGraphData(simulationId),
            ])
            setSimulation(full.simulation)
            setAgents(full.agents)
            setForks(full.forks)
            setGraphData(graphData.nodes, graphData.links)
          }

          if (event.type === 'simulation_complete') {
            // Aggiorna stato finale
            const [full, graphData] = await Promise.all([
              getSimulation(simulationId),
              getGraphData(simulationId),
            ])
            setSimulation(full.simulation)
            setAgents(full.agents)
            setForks(full.forks)
            setGraphData(graphData.nodes, graphData.links)

            // Mostra report inline dall'evento (niente polling)
            const report = (event.data as Record<string, unknown>).report as string
            if (report && report.length > 50) {
              setReport(report)
              setShowReport(true)
            }
          }

        } catch (err) {
          console.warn('[WS] parse error', err)
        }
      }

      const pingInterval = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) ws.send('ping')
      }, 20000)
      ws.addEventListener('close', () => clearInterval(pingInterval))
    }

    connect()
    return () => {
      active = false
      if (retryRef.current) clearTimeout(retryRef.current)
      wsRef.current?.close()
      setSseConnected(false)
    }
  }, [simulationId])
}
