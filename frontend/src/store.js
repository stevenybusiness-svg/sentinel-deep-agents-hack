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

  initInvestigationTree: () => set({
    nodes: [
      { id: 'supervisor', position: { x: 250, y: 0 }, data: { label: 'Supervisor', icon: 'hub', status: 'active' }, type: 'sentinel' },
      { id: 'payment', position: { x: 250, y: 100 }, data: { label: 'Payment Agent', icon: 'payments', status: 'active' }, type: 'sentinel' },
      { id: 'risk', position: { x: 50, y: 220 }, data: { label: 'Risk Agent', icon: 'shield', status: 'pending' }, type: 'sentinel' },
      { id: 'compliance', position: { x: 250, y: 220 }, data: { label: 'Compliance Agent', icon: 'verified_user', status: 'pending' }, type: 'sentinel' },
      { id: 'forensics', position: { x: 450, y: 220 }, data: { label: 'Forensics Agent', icon: 'search', status: 'pending' }, type: 'sentinel' },
      { id: 'gate', position: { x: 250, y: 340 }, data: { label: 'Safety Gate', icon: 'security', status: 'pending' }, type: 'sentinel' },
    ],
    edges: [
      { id: 'e-sup-pay', source: 'supervisor', target: 'payment', animated: true },
      { id: 'e-sup-risk', source: 'supervisor', target: 'risk', animated: false },
      { id: 'e-sup-comp', source: 'supervisor', target: 'compliance', animated: false },
      { id: 'e-sup-for', source: 'supervisor', target: 'forensics', animated: false },
      { id: 'e-risk-gate', source: 'risk', target: 'gate', animated: false },
      { id: 'e-comp-gate', source: 'compliance', target: 'gate', animated: false },
      { id: 'e-for-gate', source: 'forensics', target: 'gate', animated: false },
    ],
  }),

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

  addRuleNode: (ruleId, label) => set((s) => ({
    nodes: [...s.nodes, {
      id: ruleId,
      position: { x: 450, y: 340 + (s.nodes.length - 6) * 80 },
      data: { label, icon: 'auto_awesome', status: 'rule_node' },
      type: 'sentinel',
    }],
    edges: [...s.edges, {
      id: `e-gate-${ruleId}`,
      source: 'gate',
      target: ruleId,
      animated: true,
      style: { stroke: '#e3b341' },
    }],
  })),

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
  }),
}))
