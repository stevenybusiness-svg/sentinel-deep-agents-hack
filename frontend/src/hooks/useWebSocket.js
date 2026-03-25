import { useEffect, useRef } from 'react'
import { useStore } from '../store'

export function useWebSocket() {
  const wsRef = useRef(null)
  const reconnectTimer = useRef(null)

  useEffect(() => {
    function connect() {
      const ws = new WebSocket(`ws://${window.location.host}/ws`)
      wsRef.current = ws

      ws.onopen = () => {
        useStore.getState().setWsConnected(true)
        if (reconnectTimer.current) {
          clearTimeout(reconnectTimer.current)
          reconnectTimer.current = null
        }
      }

      ws.onclose = () => {
        useStore.getState().setWsConnected(false)
        reconnectTimer.current = setTimeout(connect, 2000)
      }

      ws.onerror = () => {
        ws.close()
      }

      ws.onmessage = (evt) => {
        const msg = JSON.parse(evt.data)
        const { event, episode_id, data } = msg
        const s = useStore.getState()

        switch (event) {
          case 'investigation_started':
            s.resetInvestigation()
            s.setCurrentEpisodeId(episode_id)
            s.setInvestigationStatus('running')
            s.initInvestigationTree()
            break

          case 'agent_completed': {
            const agent = data.agent // "risk" | "compliance" | "forensics"
            s.setAgentStatus(agent, 'complete', data.verdict)
            s.updateNodeStatus(agent, 'complete')
            s.setEdgeAnimated(`e-sup-${agent === 'compliance' ? 'comp' : agent === 'forensics' ? 'for' : agent}`, true)
            break
          }

          case 'verdict_board_assembled':
            s.setVerdictBoard(data.verdict_board)
            if (data.verdict_board?.prediction_errors) {
              s.setPredictionData(data.verdict_board.prediction_errors)
            }
            break

          case 'gate_evaluated':
            s.setGateDecision(data)
            s.setInvestigationStatus('complete')
            s.updateNodeStatus('gate', data.decision === 'NO-GO' ? 'blocked' : 'complete')
            // Add to decision log
            s.addDecisionLog({
              timestamp: msg.timestamp,
              gate_decision: data.decision,
              attribution: data.attribution,
              score: data.composite_score,
              episode_id,
            })
            // Compute trust score: inverse of composite_score, clamped 0-1
            {
              const trust = Math.max(0, Math.min(1, 1.0 - (data.composite_score || 0)))
              s.setTrustScore(trust)
            }
            break

          case 'episode_written':
            s.setAerospikeLatencyMs(data.write_latency_ms)
            break

          case 'rule_generating':
            if (!s.ruleStreaming) {
              s.setRuleStreaming(true)
              s.clearStreamingBuffer()
            }
            s.appendStreamingBuffer(data.token || '')
            break

          case 'rule_deployed':
            s.setRuleStreaming(false)
            s.addRuleSource({
              rule_id: data.rule_id,
              version: data.version,
              source: data.source,
              episode_ids: data.episode_ids,
              deployedAt: new Date().toISOString(),
              attribution: data.attribution,
            })
            s.addRuleNode(data.rule_id, `Rule #${data.version || data.rule_id}`)
            break

          case 'rule_generation_failed':
            s.setRuleStreaming(false)
            break

          default:
            break
        }
      }
    }

    connect()

    return () => {
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current)
      if (wsRef.current) wsRef.current.close()
    }
  }, [])
}
