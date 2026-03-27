import { create } from 'zustand'

export const useStore = create((set, get) => ({
  // Connection state
  wsConnected: false,
  setWsConnected: (connected) => set({ wsConnected: connected }),

  // Investigation state
  currentEpisodeId: null,
  investigationStatus: 'idle', // idle | running | complete
  verdictBoard: null,
  gateDecision: null,

  // Agent states
  agents: {
    risk: { status: 'pending' },
    compliance: { status: 'pending' },
    forensics: { status: 'pending' },
  },

  // Aerospike latency (displayed on dashboard per DASH-09)
  aerospikeLatencyMs: null,

  // --- Phase 4 additions per D-14 ---

  // @xyflow/react state
  nodes: [],
  edges: [],
  setNodes: (nodes) => set({ nodes }),
  setEdges: (edges) => set({ edges }),

  // Prediction data
  predictionData: null,
  setPredictionData: (data) => set({ predictionData: data }),

  // Rule sources
  ruleSources: [],
  addRuleSource: (rule) => set((s) => ({ ruleSources: [...s.ruleSources, rule] })),
  updateRuleSource: (ruleId, update) => set((s) => ({
    ruleSources: s.ruleSources.map((r) =>
      r.rule_id === ruleId ? { ...r, ...update } : r
    ),
  })),

  // Rule streaming
  ruleStreaming: false,
  streamingBuffer: '',
  setRuleStreaming: (streaming) => set({ ruleStreaming: streaming }),
  appendStreamingBuffer: (token) => set((s) => ({ streamingBuffer: s.streamingBuffer + token })),
  clearStreamingBuffer: () => set({ streamingBuffer: '' }),

  // Decision log
  decisionLog: [],
  addDecisionLog: (entry) => set((s) => ({ decisionLog: [entry, ...s.decisionLog] })),

  // Trust score
  trustScore: 0.85,
  setTrustScore: (score) => set({ trustScore: score }),

  // Qualitative panel state (Phase 04.1 / D-04 through D-09)
  narrativeData: {
    attackNarrative: null,
    agentReasoning: null,
    predictionSummary: null,
    selfImprovementArc: null,
  },
  narrativePolishing: {
    attackNarrative: false,
    agentReasoning: false,
    predictionSummary: false,
    // selfImprovementArc intentionally absent -- never polished by LLM
  },
  setNarrativeData: (key, value) => set((s) => ({
    narrativeData: { ...s.narrativeData, [key]: value },
  })),
  setNarrativePolishing: (key, bool) => set((s) => ({
    narrativePolishing: { ...s.narrativePolishing, [key]: bool },
  })),
  resetNarrative: () => set({
    narrativeData: { attackNarrative: null, agentReasoning: null, predictionSummary: null, selfImprovementArc: null },
    narrativePolishing: { attackNarrative: false, agentReasoning: false, predictionSummary: false },
  }),

  // Airbyte report delivery state (DEMO-POLISH-04)
  reportStatus: 'idle', // idle | sending | delivered | failed
  reportChannel: null,
  setReportStatus: (status) => set({ reportStatus: status }),
  setReportChannel: (channel) => set({ reportChannel: channel }),

  // Rule nodes that persist across investigations (PHASE8-03)
  persistedRuleNodes: [],
  persistedRuleEdges: [],

  // Current episode ID setter
  setCurrentEpisodeId: (id) => set({ currentEpisodeId: id }),
  setInvestigationStatus: (status) => set({ investigationStatus: status }),
  setVerdictBoard: (vb) => set({ verdictBoard: vb }),
  setGateDecision: (gd) => set({ gateDecision: gd }),
  setAgentStatus: (agent, status, verdict) => set((s) => ({
    agents: { ...s.agents, [agent]: { status, verdict } },
  })),
  setAerospikeLatencyMs: (ms) => set({ aerospikeLatencyMs: ms }),

  // --- Investigation tree actions (owned by Plan 01, consumed by Plan 02) ---

  initInvestigationTree: () => set((s) => ({
    nodes: [
      { id: 'payment', position: { x: 250, y: 0 }, data: { label: 'Payment Agent (Sonnet)', icon: 'payments', status: 'active' }, type: 'sentinel' },
      { id: 'risk', position: { x: 50, y: 120 }, data: { label: 'Risk Agent', icon: 'shield', status: 'pending' }, type: 'sentinel' },
      { id: 'compliance', position: { x: 250, y: 120 }, data: { label: 'Compliance Agent', icon: 'verified_user', status: 'pending' }, type: 'sentinel' },
      { id: 'forensics', position: { x: 450, y: 120 }, data: { label: 'Forensics Agent', icon: 'search', status: 'pending' }, type: 'sentinel' },
      { id: 'supervisor', position: { x: 250, y: 240 }, data: { label: 'Supervisor (Opus)', icon: 'hub', status: 'pending' }, type: 'sentinel' },
      { id: 'gate', position: { x: 250, y: 340 }, data: { label: 'Safety Gate (Deterministic)', icon: 'security', status: 'pending' }, type: 'sentinel' },
      // Re-add Attack 1's rule nodes as active/pulsing (orange) — they're firing in the gate
      ...s.persistedRuleNodes.map(n => ({
        ...n,
        data: { ...n.data, status: 'rule_node' }
      })),
    ],
    edges: [
      { id: 'e-pay-risk', source: 'payment', target: 'risk', animated: false },
      { id: 'e-pay-comp', source: 'payment', target: 'compliance', animated: false },
      { id: 'e-pay-for', source: 'payment', target: 'forensics', animated: false },
      { id: 'e-risk-sup', source: 'risk', target: 'supervisor', animated: false },
      { id: 'e-comp-sup', source: 'compliance', target: 'supervisor', animated: false },
      { id: 'e-for-sup', source: 'forensics', target: 'supervisor', animated: false },
      { id: 'e-sup-gate', source: 'supervisor', target: 'gate', animated: false },
      ...s.persistedRuleEdges,
    ],
  })),

  updateNodeStatus: (nodeId, status) => set((s) => ({
    nodes: s.nodes.map((n) =>
      n.id === nodeId ? { ...n, data: { ...n.data, status } } : n
    ),
  })),

  setEdgeAnimated: (edgeId, animated) => set((s) => ({
    edges: s.edges.map((e) =>
      e.id === edgeId ? { ...e, animated } : e
    ),
  })),

  setEdgeActive: (edgeId, color = '#3b82f6') => set((s) => ({
    edges: s.edges.map((e) =>
      e.id === edgeId
        ? { ...e, animated: true, style: { stroke: color, strokeWidth: 2 } }
        : e
    ),
  })),

  addRuleNode: (ruleId, label, source) => set((s) => {
    // Check if this rule node already exists (evolution path — same rule_id, new version)
    const existingIdx = s.nodes.findIndex(n => n.id === ruleId)
    if (existingIdx !== -1) {
      // Update existing node: refresh label and ensure it pulses orange
      const updatedNodes = s.nodes.map(n =>
        n.id === ruleId
          ? { ...n, data: { ...n.data, label, status: 'rule_node' } }
          : n
      )
      const updatedPersisted = s.persistedRuleNodes.map(n =>
        n.id === ruleId
          ? { ...n, data: { ...n.data, label, status: 'rule_node' } }
          : n
      )
      return { nodes: updatedNodes, persistedRuleNodes: updatedPersisted }
    }

    const newNode = {
      id: ruleId,
      position: { x: 500, y: 340 },
      data: { label, icon: 'auto_awesome', status: 'rule_node' },
      type: 'sentinel',
    }
    const newEdge = {
      id: `e-gate-${ruleId}`,
      source: 'gate',
      target: ruleId,
      animated: true,
      style: { stroke: '#e3b341' },
    }

    // Build annotation nodes from rule source analysis
    const annotations = []
    const annotationEdges = []
    if (source) {
      const hints = []
      if (source.includes('z_score') || source.includes('z >')) hints.push('Flags z-score > 2\u03C3')
      if (source.includes('verify_counterparty') || source.includes('step_sequence')) hints.push('Detects skipped verification')
      if (source.includes('hidden') || source.includes('injection')) hints.push('Catches hidden injection')
      if (source.includes('mismatch')) hints.push('Penalizes claim mismatches')
      // Limit to 3 annotations
      const displayHints = hints.slice(0, 3)
      displayHints.forEach((hint, i) => {
        const annotId = `${ruleId}-annot-${i}`
        annotations.push({
          id: annotId,
          position: { x: 420 + i * 200, y: 430 },
          data: { label: hint, icon: 'info', status: 'annotation' },
          type: 'sentinel',
        })
        annotationEdges.push({
          id: `e-${ruleId}-annot-${i}`,
          source: ruleId,
          target: annotId,
          animated: false,
          style: { stroke: '#e3b341', strokeWidth: 1, strokeDasharray: '4 4' },
        })
      })
    }

    const allNewNodes = [newNode, ...annotations]
    const allNewEdges = [newEdge, ...annotationEdges]

    return {
      nodes: [...s.nodes, ...allNewNodes],
      edges: [...s.edges, ...allNewEdges],
      persistedRuleNodes: [...s.persistedRuleNodes, ...allNewNodes],
      persistedRuleEdges: [...s.persistedRuleEdges, ...allNewEdges],
    }
  }),

  // Reset for new investigation
  resetInvestigation: () => set({
    currentEpisodeId: null,
    investigationStatus: 'idle',
    verdictBoard: null,
    gateDecision: null,
    agents: {
      risk: { status: 'pending' },
      compliance: { status: 'pending' },
      forensics: { status: 'pending' },
    },
    aerospikeLatencyMs: null,
    nodes: [],
    edges: [],
    predictionData: null,
    ruleStreaming: false,
    streamingBuffer: '',
    trustScore: 0.85,
    narrativeData: { attackNarrative: null, agentReasoning: null, predictionSummary: null, selfImprovementArc: null },
    narrativePolishing: { attackNarrative: false, agentReasoning: false, predictionSummary: false },
    reportStatus: 'idle',
    reportChannel: null,
  }),
}))
