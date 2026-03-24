import { create } from 'zustand'

export const useStore = create((set, get) => ({
  // Connection state
  wsConnected: false,
  setWsConnected: (connected) => set({ wsConnected: connected }),

  // Investigation state (populated in Phase 4)
  currentEpisodeId: null,
  investigationStatus: 'idle', // idle | running | complete
  verdictBoard: null,
  gateDecision: null,

  // Agent states (populated in Phase 4)
  agents: {
    risk: { status: 'pending' },
    compliance: { status: 'pending' },
    forensics: { status: 'pending' },
  },

  // Aerospike latency (displayed on dashboard per DASH-09)
  aerospikeLatencyMs: null,

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
  }),
}))
