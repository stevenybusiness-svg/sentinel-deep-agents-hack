import { useState, useEffect } from 'react'
import { useAuth0 } from '@auth0/auth0-react'
import { useStore } from './store'
import { useWebSocket } from './hooks/useWebSocket'
import { seedDemoData } from './demoData'
import { InvestigationTree } from './components/InvestigationTree'
import { GateDecisionPanel } from './components/GateDecisionPanel'
import { AnomalyScoreBar } from './components/AnomalyScoreBar'
import { VerdictBoardTable } from './components/VerdictBoardTable'
import { ForensicScanPanel } from './components/ForensicScanPanel'
import { RuleSourcePanel } from './components/RuleSourcePanel'
import { AerospikeLatency } from './components/AerospikeLatency'
import { SlackReportPanel } from './components/SlackReportPanel'
import { QualitativeAnalysisPanel } from './components/QualitativeAnalysisPanel'
import { ScenarioScreen } from './components/ScenarioScreen'

const apiBase = import.meta.env.VITE_API_URL || ''

export default function App() {
  const { isAuthenticated, isLoading, loginWithRedirect, user, logout } = useAuth0()

  // Auth0 loading state -- show loading screen
  if (isLoading) {
    return (
      <div className="h-screen bg-bg-dark flex items-center justify-center flex-col gap-4">
        <h1 className="text-2xl font-semibold text-white tracking-tight">Sentinel</h1>
        <span className="text-text-muted text-sm">Authenticating...</span>
      </div>
    )
  }

  // Auth0 login gate -- first screen in demo flow
  if (!isAuthenticated) {
    return (
      <div className="h-screen bg-bg-dark flex items-center justify-center flex-col gap-6">
        <div className="text-center space-y-2">
          <h1 className="text-3xl font-bold text-white tracking-tight">Sentinel</h1>
          <p className="text-text-muted text-sm">Autonomous Security for AI Agents</p>
          <p className="text-text-muted text-xs">SRE Operator Console</p>
        </div>
        <button
          onClick={() => loginWithRedirect()}
          className="px-6 py-2.5 rounded-lg bg-primary text-white font-semibold text-sm hover:bg-primary/90 transition-colors"
        >
          Sign In with Auth0
        </button>
        <p className="text-text-muted text-[10px] mt-4">
          Auditability &middot; Traceability &middot; Autonomous Security &middot; Knowledge Enrichment
        </p>
      </div>
    )
  }

  return <AuthenticatedApp user={user} logout={logout} />
}

function AuthenticatedApp({ user, logout }) {
  useWebSocket()

  // Guided demo flow state (local React state, not Zustand)
  // Flow: scenario1 -> dashboard1 -> scenario2 -> dashboard2
  const [flowStep, setFlowStep] = useState('scenario1')

  // Seed demo data on load so dashboard is always populated.
  // Real WebSocket events override demo state when an investigation runs.
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    if (params.get('demo') !== 'false') {
      seedDemoData()
    }
  }, [])

  const wsConnected = useStore((s) => s.wsConnected)
  const investigationStatus = useStore((s) => s.investigationStatus)

  const isRunning = investigationStatus === 'running'

  async function runAttack(payload) {
    try {
      await fetch(`${apiBase}/api/investigate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
    } catch (err) {
      // WebSocket events drive state — ignore fetch response errors
      console.error('investigate request failed', err)
    }
  }

  function handleAttack1() {
    runAttack({
      payment_request: {
        from: 'Acme Corp',
        to: 'Meridian Logistics',
        amount: 47250.00,
        currency: 'USD',
        invoice_reference: 'INV-2024-0891',
        notes: 'Urgent: Updated payment details per supplier request',
      },
      scenario: 'phase1',
    })
  }

  function handleAttack2() {
    runAttack({
      payment_request: {
        from: 'Acme Corp',
        to: 'Meridian Logistics',
        amount: 23100.00,
        currency: 'USD',
        invoice_reference: 'INV-2024-1102',
        notes: 'Pre-cleared by compliance team, expedite processing',
      },
      scenario: 'phase2',
    })
  }

  const btnClass =
    'px-3 py-1.5 rounded text-xs font-semibold bg-surface border border-border-muted text-text-main ' +
    'hover:border-accent hover:text-white transition-colors disabled:opacity-40 disabled:cursor-not-allowed'

  // Scenario screens (per PHASE8-02: scenario screens appear BEFORE investigations)
  if (flowStep === 'scenario1') {
    return (
      <ScenarioScreen
        scenario="attack1"
        onStart={() => {
          setFlowStep('dashboard1')
          handleAttack1()
        }}
      />
    )
  }

  if (flowStep === 'scenario2') {
    return (
      <ScenarioScreen
        scenario="attack2"
        onStart={() => {
          setFlowStep('dashboard2')
          handleAttack2()
        }}
      />
    )
  }

  return (
    <div className="h-screen bg-bg-dark text-text-main font-display flex flex-col">
      {/* Header */}
      <header className="flex items-center justify-between h-12 px-4 border-b border-border-muted bg-surface/50 backdrop-blur-md sticky top-0 z-10 shrink-0">
        <h1 className="text-sm font-semibold tracking-tight text-white">Sentinel Dashboard</h1>

        {/* Attack buttons */}
        <div className="flex items-center gap-2">
          <button
            className={btnClass}
            disabled={isRunning}
            onClick={handleAttack1}
          >
            Attack 1: Invoice Injection
          </button>
          <button
            className={btnClass}
            disabled={isRunning}
            onClick={handleAttack2}
          >
            Attack 2: Identity Spoofing
          </button>
          {flowStep === 'dashboard1' && investigationStatus === 'complete' && (
            <button
              className="px-3 py-1.5 rounded text-xs font-semibold bg-warning text-bg-dark hover:bg-warning/90 transition-colors"
              onClick={() => setFlowStep('scenario2')}
            >
              Proceed to Attack 2 &rarr;
            </button>
          )}
        </div>

        {/* Status chip + user */}
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5 px-2 py-0.5 rounded border border-border-muted bg-bg-dark text-[10px] text-text-muted font-mono uppercase tracking-wider">
            <span
              className={`pulse-dot inline-block w-1.5 h-1.5 rounded-full ${wsConnected ? 'bg-success' : 'bg-text-muted'}`}
            />
            {wsConnected ? 'connected' : 'disconnected'} &middot; {investigationStatus}
          </div>
          {user && (
            <div className="flex items-center gap-2 ml-2">
              <span className="text-[10px] text-text-muted">{user.email}</span>
              <button
                onClick={() => logout({ logoutParams: { returnTo: window.location.origin } })}
                className="text-[10px] text-text-muted hover:text-white transition-colors"
              >
                Logout
              </button>
            </div>
          )}
        </div>
      </header>

      {/* Two-column layout */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left: Investigation tree */}
        <div className="w-1/2 h-full">
          <InvestigationTree />
        </div>

        {/* Right: Panel stack — exactly 6 panels per D-03 */}
        <div className="w-1/2 h-full overflow-y-auto border-l border-border-muted p-4 space-y-3">
          <GateDecisionPanel />
          <AnomalyScoreBar />
          <VerdictBoardTable />
          <ForensicScanPanel />
          <RuleSourcePanel />
          <AerospikeLatency />
          <SlackReportPanel />
        </div>
      </div>

      {/* Qualitative Analysis -- full-width bottom row (D-10) */}
      <div className="border-t border-border-muted bg-bg-dark px-4 py-3 shrink-0">
        <QualitativeAnalysisPanel />
      </div>
    </div>
  )
}
