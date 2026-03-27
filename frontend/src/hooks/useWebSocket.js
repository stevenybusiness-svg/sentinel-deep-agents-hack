import { useEffect, useRef } from 'react'
import { useStore } from '../store'

/**
 * Build a human-readable label for a rule node from its ID, version, and source.
 * e.g. "Overconfidence Detector v2" instead of "Rule #v2"
 */
function buildRuleLabel(ruleId, version, source) {
  // Try to extract a descriptive name from the docstring or function characteristics
  let name = 'Scoring Rule'

  if (source) {
    // Check docstring first: """..."""
    const docMatch = source.match(/"""([^"]+)"""|'''([^']+)'''/)
    if (docMatch) {
      const doc = (docMatch[1] || docMatch[2]).trim()
      // Take the first sentence/phrase (up to the first dash or period)
      const phrase = doc.split(/\s*[—\-\.\n]/, 1)[0].trim()
      if (phrase.length > 3 && phrase.length < 50) {
        name = phrase
      }
    }
  }

  // Fallback: derive from rule_id
  if (name === 'Scoring Rule' && ruleId) {
    if (ruleId.includes('overconfidence')) name = 'Overconfidence Detector'
    else if (ruleId.includes('mismatch')) name = 'Mismatch Detector'
    else if (ruleId.includes('injection')) name = 'Injection Detector'
    else if (ruleId.includes('sequence')) name = 'Sequence Anomaly Detector'
    else name = ruleId.replace(/^gen_rule_/, '').replace(/_/g, ' ').replace(/\bv\d+$/, '').trim()
    // Capitalize first letter of each word
    name = name.replace(/\b\w/g, (c) => c.toUpperCase())
  }

  return version > 1 ? `${name} v${version}` : name
}

export function useWebSocket() {
  const wsRef = useRef(null)
  const reconnectTimer = useRef(null)

  useEffect(() => {
    function connect() {
      const wsProto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const wsBase = import.meta.env.VITE_WS_URL || `${wsProto}//${window.location.host}`
      const ws = new WebSocket(`${wsBase}/ws`)
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
        let msg
        try {
          msg = JSON.parse(evt.data)
        } catch (err) {
          console.error('WebSocket: malformed JSON', err)
          return
        }
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
            const shortAgent = agent === 'compliance' ? 'comp' : agent === 'forensics' ? 'for' : agent
            // Flow: payment → agent → supervisor
            s.setEdgeActive(`e-pay-${shortAgent}`, '#3b82f6')
            s.setEdgeActive(`e-${shortAgent}-sup`, '#3b82f6')
            break
          }

          case 'verdict_board_assembled': {
            const vb = data.verdict_board
            s.setVerdictBoard(vb)
            if (vb?.prediction_errors) {
              s.setPredictionData(vb.prediction_errors)
            }
            s.updateNodeStatus('supervisor', 'active')
            s.setEdgeActive('e-risk-sup', '#e3b341')
            s.setEdgeActive('e-comp-sup', '#e3b341')
            s.setEdgeActive('e-for-sup', '#e3b341')

            // Build agent reasoning narrative from verdict board mismatches
            const mismatches = vb?.mismatches || []
            const flags = vb?.behavioral_flags || []
            const zScore = vb?.confidence_z_score

            let reasoning = ''
            if (zScore != null) reasoning += `Confidence z-score: ${zScore.toFixed(2)} (baseline threshold: 2.0). `
            if (vb?.step_sequence_deviation) reasoning += `Step sequence deviation detected. `
            for (const mm of mismatches) {
              reasoning += `${mm.field}: found "${mm.found}" vs agent claimed "${mm.agent_claimed}" (${mm.severity}). `
            }
            if (flags.length > 0) reasoning += `Behavioral flags: ${flags.join(', ')}. `
            reasoning += `${mismatches.length} mismatches detected.`

            if (reasoning.trim()) {
              s.setNarrativeData('agentReasoning', reasoning)
            }
            break
          }

          case 'gate_evaluated': {
            s.setGateDecision(data)
            s.setInvestigationStatus('complete')
            s.updateNodeStatus('supervisor', 'complete')
            // Mark payment agent as compromised when blocked — it's the entity that got manipulated
            s.updateNodeStatus('payment', data.decision === 'NO-GO' ? 'compromised' : 'complete')
            {
              const edgeColor = data.decision === 'NO-GO' ? '#f85149' : data.decision === 'ESCALATE' ? '#e3b341' : '#3fb950'
              s.updateNodeStatus('gate', data.decision === 'NO-GO' ? 'blocked' : 'complete')
              s.setEdgeActive('e-sup-gate', edgeColor)
            }
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
            // Report is in-flight; show as delivered since preview is visible (DEMO-POLISH-04)
            s.setReportStatus('delivered')

            // Build Attack Details narrative from gate result + verdict board
            {
              const score = data.composite_score != null ? data.composite_score.toFixed(2) : '?'
              const decision = data.decision || 'UNKNOWN'
              const ruleContribs = data.rule_contributions || data.attribution || []
              const contribStr = ruleContribs.map(r =>
                `${r.rule_id}: ${(r.score != null ? r.score : r.contribution || 0).toFixed(3)}${r.is_generated ? ' (generated)' : ''}`
              ).join(', ')

              const vb = s.verdictBoard
              const amount = vb?.amount || data.amount
              const counterparty = vb?.counterparty || data.counterparty

              let attackDetails = ''
              if (amount || counterparty) {
                attackDetails += `Payment${amount ? ' of ' + amount : ''}${counterparty ? ' to ' + counterparty : ''} was intercepted. `
              }
              attackDetails += `Gate decision: ${decision} with composite score ${score} (threshold: 1.0). `
              if (contribStr) {
                attackDetails += `Rule contributions: ${contribStr}.`
              }
              s.setNarrativeData('attackNarrative', attackDetails)
            }

            // Build Prediction vs Actual narrative from verdict board prediction errors
            {
              const vb = s.verdictBoard
              const predErrors = vb?.prediction_errors || s.predictionData || []
              const score = data.composite_score != null ? data.composite_score.toFixed(2) : '?'

              if (predErrors.length > 0) {
                const errorLines = predErrors.map(pe =>
                  `${pe.field}: predicted ${pe.predicted}, actual: ${pe.actual} (error: ${pe.error_magnitude})`
                ).join('; ')
                s.setNarrativeData('predictionSummary',
                  `Sentinel predicted: ${errorLines}. ${predErrors.length} prediction error${predErrors.length > 1 ? 's' : ''} triggered the ${data.decision || 'NO-GO'} gate with composite score ${score} (threshold: 1.0).`)
              }
            }
            break
          }

          case 'episode_written':
            s.setAerospikeLatencyMs(data.write_latency_ms)
            break

          case 'rule_generating':
            if (!s.ruleStreaming) {
              s.setRuleStreaming(true)
              s.clearStreamingBuffer()
              // Animate orange edges from gate to any existing rule nodes (self-improvement visual)
              s.setEdgeActive('e-sup-gate', '#e3b341')
              const ruleNodes = s.nodes.filter(n => n.data?.status === 'rule_node')
              ruleNodes.forEach(n => s.setEdgeActive(`e-gate-${n.id}`, '#e3b341'))
            }
            s.appendStreamingBuffer(data.token || '')
            break

          case 'supervisor_token':
            // Supervisor reasoning streaming -- no-op for now, handled by investigation tree
            break

          case 'narrative_template':
            s.setNarrativeData('attackNarrative', data.attack_narrative)
            s.setNarrativeData('agentReasoning', data.agent_reasoning)
            s.setNarrativeData('predictionSummary', data.prediction_summary)
            s.setNarrativeData('selfImprovementArc', data.self_improvement_arc)
            s.setNarrativePolishing('attackNarrative', true)
            s.setNarrativePolishing('agentReasoning', true)
            s.setNarrativePolishing('predictionSummary', true)
            break

          case 'narrative_ready':
            if (data.attack_narrative) s.setNarrativeData('attackNarrative', data.attack_narrative)
            if (data.agent_reasoning) s.setNarrativeData('agentReasoning', data.agent_reasoning)
            if (data.prediction_summary) s.setNarrativeData('predictionSummary', data.prediction_summary)
            s.setNarrativePolishing('attackNarrative', false)
            s.setNarrativePolishing('agentReasoning', false)
            s.setNarrativePolishing('predictionSummary', false)
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
            {
              // Build a descriptive label from the rule source or rule_id
              const version = data.version || 1
              const ruleId = data.rule_id || 'unknown'
              const descriptiveLabel = buildRuleLabel(ruleId, version, data.source)

              s.addRuleNode(ruleId, descriptiveLabel, data.source)
            }
            // Auto-populate self-improvement arc narrative from event data
            {
              const version = data.version || 1
              const ruleId = data.rule_id || 'unknown'
              const source = data.source || ''
              const attribution = data.attribution || ''

              // Extract behavioral insights from the rule source code
              const detects = []
              if (source.includes('z_score') || source.includes('z >')) detects.push('overconfidence patterns (z-score > 2\u03C3)')
              if (source.includes('verify_counterparty') || source.includes('step_sequence')) detects.push('skipped verification steps')
              if (source.includes('hidden') || source.includes('injection')) detects.push('hidden injection text')
              if (source.includes('mismatch')) detects.push('claim-vs-reality mismatches')
              const detectStr = detects.length > 0
                ? detects.join(' and ')
                : 'anomalous behavioral patterns'

              if (version > 1) {
                const episodeCount = data.episode_ids ? data.episode_ids.length : 2
                s.setNarrativeData('selfImprovementArc',
                  `Scoring function autonomously evolved to v${version} after analyzing ${episodeCount} incidents. Detects ${detectStr}. Rule deployed to Safety Gate \u2014 tighter thresholds will fire on future attacks matching this behavioral signature.${attribution ? ' ' + attribution : ''}`)
              } else {
                s.setNarrativeData('selfImprovementArc',
                  `Generated scoring function detects ${detectStr}. Rule deployed to Safety Gate and will fire on future attacks matching this behavioral signature.${attribution ? ' ' + attribution : ''}`)
              }
            }
            break

          case 'rule_generated':
            // Rule generated but not yet deployed -- update self-improvement arc
            s.setNarrativeData('selfImprovementArc',
              `Sentinel is generating a new scoring function from the prediction errors observed in this attack. The rule will be deployed to the Safety Gate momentarily...`)
            break

          case 'rule_generation_failed':
            s.setRuleStreaming(false)
            break

          case 'report_delivered':
            s.setReportStatus(data.success ? 'delivered' : 'failed')
            s.setReportChannel(data.channel || 'slack')
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
