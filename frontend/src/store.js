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

  // Track which attack phase we're on (1 or 2)
  attackPhase: 1,
  setAttackPhase: (phase) => set({ attackPhase: phase }),

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

  initInvestigationTree: () => set((s) => {
    // Separate persisted rules (pulsing boxes) from annotations
    const isRuleStatus = (st) => st === 'rule_node' || st === 'rule_new' || st === 'rule_evolving'
    const persistedRules = s.persistedRuleNodes.filter(n => isRuleStatus(n.data?.status))
    const hasPersistedRules = persistedRules.length > 0

    // For Attack 2: position rule nodes at TOP, feeding into Payment Agent
    const topRuleNodes = hasPersistedRules
      ? persistedRules.map((n, i) => ({
          ...n,
          position: { x: 250 + i * 180, y: -80 },
          data: { ...n.data, status: 'rule_node' },
        }))
      : []

    // Edges from top rules → Payment Agent (yellow pulsing, shows rules monitoring the agent)
    const topRuleEdges = topRuleNodes.map(n => ({
      id: `e-rule-${n.id}-to-payment`,
      source: n.id,
      target: 'payment',
      animated: true,
      style: { stroke: '#e3b341', strokeWidth: 2 },
    }))

    return {
      nodes: [
        ...topRuleNodes,
        { id: 'payment', position: { x: 250, y: hasPersistedRules ? 40 : 0 }, data: { label: 'Payment Agent (Sonnet)', icon: 'payments', status: 'active' }, type: 'sentinel' },
        { id: 'risk', position: { x: 50, y: hasPersistedRules ? 160 : 120 }, data: { label: 'Risk Agent', icon: 'shield', status: 'pending' }, type: 'sentinel' },
        { id: 'compliance', position: { x: 250, y: hasPersistedRules ? 160 : 120 }, data: { label: 'Compliance Agent', icon: 'verified_user', status: 'pending' }, type: 'sentinel' },
        { id: 'forensics', position: { x: 450, y: hasPersistedRules ? 160 : 120 }, data: { label: 'Forensics Agent', icon: 'search', status: 'pending' }, type: 'sentinel' },
        { id: 'supervisor', position: { x: 250, y: hasPersistedRules ? 280 : 240 }, data: { label: 'Supervisor (Opus)', icon: 'hub', status: 'pending' }, type: 'sentinel' },
        { id: 'gate', position: { x: 250, y: hasPersistedRules ? 380 : 340 }, data: { label: 'Safety Gate (Deterministic)', icon: 'security', status: 'pending' }, type: 'sentinel' },
      ],
      edges: [
        ...topRuleEdges,
        { id: 'e-pay-risk', source: 'payment', target: 'risk', animated: false },
        { id: 'e-pay-comp', source: 'payment', target: 'compliance', animated: false },
        { id: 'e-pay-for', source: 'payment', target: 'forensics', animated: false },
        { id: 'e-risk-sup', source: 'risk', target: 'supervisor', animated: false },
        { id: 'e-comp-sup', source: 'compliance', target: 'supervisor', animated: false },
        { id: 'e-for-sup', source: 'forensics', target: 'supervisor', animated: false },
        { id: 'e-sup-gate', source: 'supervisor', target: 'gate', animated: false },
      ],
    }
  }),

  addNodes: (newNodes) => set((s) => ({ nodes: [...s.nodes, ...newNodes] })),
  addEdges: (newEdges) => set((s) => ({ edges: [...s.edges, ...newEdges] })),
  removeNode: (nodeId) => set((s) => ({
    nodes: s.nodes.filter(n => n.id !== nodeId),
    edges: s.edges.filter(e => e.source !== nodeId && e.target !== nodeId),
  })),

  updateNodeStatus: (nodeId, status) => set((s) => ({
    nodes: s.nodes.map((n) =>
      n.id === nodeId ? { ...n, data: { ...n.data, status } } : n
    ),
  })),

  updateNodeLabel: (nodeId, label) => set((s) => ({
    nodes: s.nodes.map((n) =>
      n.id === nodeId ? { ...n, data: { ...n.data, label } } : n
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
    const isRuleStatus = (st) => st === 'rule_node' || st === 'rule_new' || st === 'rule_evolving' || st === 'rule_generating'

    // Remove the "Learning..." placeholder and its annotation branches
    const genIds = new Set(['__generating__', '__gen_annot_0__', '__gen_annot_1__'])
    const filteredNodes = s.nodes.filter(n => !genIds.has(n.id))
    const filteredEdges = s.edges.filter(e => !genIds.has(e.source) && !genIds.has(e.target))

    // Check if this rule node already exists in CURRENT nodes (evolution path — same rule_id)
    const existingIdx = filteredNodes.findIndex(n => n.id === ruleId && isRuleStatus(n.data?.status))
    if (existingIdx !== -1) {
      // Update existing node: refresh label, entrance glow burst then settle
      const updatedNodes = filteredNodes.map(n =>
        n.id === ruleId
          ? { ...n, data: { ...n.data, label, status: 'rule_new' } }
          : n
      )
      const updatedPersisted = s.persistedRuleNodes.map(n =>
        n.id === ruleId
          ? { ...n, data: { ...n.data, label, status: 'rule_new' } }
          : n
      )
      return { nodes: updatedNodes, edges: filteredEdges, persistedRuleNodes: updatedPersisted }
    }

    // Find persisted rules from previous attacks (these are at the top of the graph in Attack 2)
    const previousRules = s.persistedRuleNodes.filter(n => isRuleStatus(n.data?.status))
    const hasPersistedRules = previousRules.length > 0

    // Position the new rule below and right of the gate
    const gateNode = filteredNodes.find(n => n.id === 'gate')
    const gateY = gateNode?.position?.y || 340
    const ruleY = gateY + 120

    const newNode = {
      id: ruleId,
      position: { x: 350, y: ruleY },
      data: { label, icon: 'auto_awesome', status: 'rule_new' },
      type: 'sentinel',
    }
    const newEdges = [
      {
        id: `e-gate-${ruleId}`,
        source: 'gate',
        target: ruleId,
        animated: true,
        style: { stroke: '#e3b341' },
      },
    ]

    // If there are persisted rules from Attack 1, add evolution edges (branch from old rule → new rule)
    if (hasPersistedRules) {
      previousRules.forEach(oldRule => {
        newEdges.push({
          id: `e-evolve-${oldRule.id}-${ruleId}`,
          source: oldRule.id,
          target: ruleId,
          animated: true,
          style: { stroke: '#e3b341', strokeWidth: 2, strokeDasharray: '6 3' },
        })
      })
    }

    // Build annotation nodes from rule source analysis — wider spacing to prevent overlap
    const annotations = []
    const annotationEdges = []
    if (source) {
      const hints = []
      if (source.includes('z_score') || source.includes('z >')) hints.push('Flags z-score > 2\u03C3')
      if (source.includes('hidden') || source.includes('injection')) hints.push('Catches hidden injection')
      if (source.includes('mismatch')) hints.push('Penalizes claim mismatches')
      if (source.includes('verify_counterparty') || source.includes('step_sequence')) hints.push('Detects skipped verification')
      // Limit to 2 annotations to keep tree clean
      const displayHints = hints.slice(0, 2)
      const annotY = ruleY + 100
      const totalWidth = (displayHints.length - 1) * 300
      const startX = 350 - totalWidth / 2
      displayHints.forEach((hint, i) => {
        const annotId = `${ruleId}-annot-${i}`
        annotations.push({
          id: annotId,
          position: { x: startX + i * 300, y: annotY },
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
    const allNewEdges = [...newEdges, ...annotationEdges]

    return {
      nodes: [...filteredNodes, ...allNewNodes],
      edges: [...filteredEdges, ...allNewEdges],
      persistedRuleNodes: [...s.persistedRuleNodes, newNode],
      persistedRuleEdges: [...s.persistedRuleEdges, ...newEdges],
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
