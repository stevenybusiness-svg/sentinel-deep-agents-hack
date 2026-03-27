import { useState, useEffect, useRef, Component } from 'react'
import { useAuth0 } from '@auth0/auth0-react'

// Error boundary to catch and display runtime errors instead of blank screen
class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { error: null }
  }
  static getDerivedStateFromError(error) {
    return { error }
  }
  render() {
    if (this.state.error) {
      return (
        <div style={{ padding: 40, color: '#f85149', fontFamily: 'monospace', background: '#0d1117', minHeight: '100vh' }}>
          <h2>Dashboard Error</h2>
          <pre style={{ whiteSpace: 'pre-wrap', color: '#c9d1d9' }}>{this.state.error.message}</pre>
          <pre style={{ whiteSpace: 'pre-wrap', color: '#8b949e', fontSize: 12 }}>{this.state.error.stack}</pre>
          <button onClick={() => this.setState({ error: null })} style={{ marginTop: 20, padding: '8px 16px', background: '#57abff', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer' }}>
            Retry
          </button>
        </div>
      )
    }
    return this.props.children
  }
}
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
import { LandingPage } from './components/LandingPage'
import { AuthenticatingScreen } from './components/AuthenticatingScreen'
import { SecurityThreatsPage } from './components/SecurityThreatsPage'

const apiBase = import.meta.env.VITE_API_URL || ''

export default function App() {
  const { isAuthenticated, isLoading, user, logout } = useAuth0()
  const [localAuth, setLocalAuth] = useState(false)
  const [authenticating, setAuthenticating] = useState(false)
  const authTimer = useRef(null)

  const handleEnter = () => {
    if (authenticating) return // prevent double-click
    setAuthenticating(true)
    if (authTimer.current) clearTimeout(authTimer.current)
    authTimer.current = setTimeout(() => {
      setLocalAuth(true)
      setAuthenticating(false)
      authTimer.current = null
    }, 4500)
  }

  // Show authenticating screen during transition or Auth0 loading
  if (authenticating || isLoading) {
    return <AuthenticatingScreen />
  }

  // Show landing page if not authenticated
  if (!isAuthenticated && !localAuth) {
    return <LandingPage onEnter={handleEnter} />
  }

  return <AuthenticatedApp user={user} logout={logout} />
}

function AuthenticatedApp({ user, logout }) {
  useWebSocket()

  // View state: which tab is active
  const [activeTab, setActiveTab] = useState('threats') // 'threats' | 'logs'
  // Which attack is currently expanded in the threats view (null = overview)
  const [expandedAttack, setExpandedAttack] = useState(1) // Start with attack 1 expanded
  // Which attack phase we're on (1 or 2)
  const [attackPhase, setAttackPhase] = useState(1)

  // Demo seed removed — investigation animates only when user clicks Launch Investigation

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
      console.error('investigate request failed', err)
    }
  }

  function handleAttack1() {
    useStore.getState().setAttackPhase(1)
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
    useStore.getState().setAttackPhase(2)
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

  function handleLaunchInvestigation(attackId) {
    setAttackPhase(attackId)
    setActiveTab('logs')
    setExpandedAttack(null)
    // Initialize tree and status immediately so user sees animation right away
    const s = useStore.getState()
    s.resetInvestigation()
    s.setAttackPhase(attackId)
    s.initInvestigationTree()
    s.setInvestigationStatus('running')
    // Fire the attack immediately
    if (attackId === 1) handleAttack1()
    else handleAttack2()
  }

  function handleProceedToAttack2() {
    setAttackPhase(2)
    setActiveTab('threats')
    setExpandedAttack(2)
  }

  // Show "Proceed to Attack 2" when attack 1 investigation is complete
  const showProceed = attackPhase === 1 && investigationStatus === 'complete' && activeTab === 'logs'

  return (
    <div className="h-screen bg-bg-dark text-text-main font-display flex flex-col">
      {/* Persistent Header */}
      <header className="flex items-center justify-between h-12 px-5 border-b border-border-muted bg-surface/50 backdrop-blur-md sticky top-0 z-20 shrink-0">
        {/* Left: Branding */}
        <div className="flex items-center gap-6">
          <span className="text-sm font-bold tracking-wider text-cyber">SENTINEL</span>

          {/* Tab navigation */}
          <nav className="flex items-center gap-1">
            <button
              onClick={() => setActiveTab('threats')}
              className={`px-3 py-3 text-[11px] uppercase tracking-wider font-semibold transition-colors ${
                activeTab === 'threats'
                  ? 'tab-active text-cyber'
                  : 'text-text-muted hover:text-white border-b-2 border-transparent'
              }`}
            >
              <span className="material-symbols-outlined text-[14px] align-middle mr-1">warning</span>
              Security Threats
            </button>
            <button
              onClick={() => setActiveTab('logs')}
              className={`px-3 py-3 text-[11px] uppercase tracking-wider font-semibold transition-colors ${
                activeTab === 'logs'
                  ? 'tab-active text-cyber'
                  : 'text-text-muted hover:text-white border-b-2 border-transparent'
              }`}
            >
              <span className="material-symbols-outlined text-[14px] align-middle mr-1">monitoring</span>
              Security Logs
            </button>
          </nav>
        </div>

        {/* Right: Status + actions */}
        <div className="flex items-center gap-3">
          {showProceed && (
            <button
              onClick={handleProceedToAttack2}
              className="px-3 py-1.5 rounded text-[10px] font-bold bg-warning text-bg-dark hover:bg-warning/90 transition-colors uppercase tracking-wider"
            >
              Proceed to Attack 2 &rarr;
            </button>
          )}

          {/* Status chip */}
          <div className="flex items-center gap-1.5 px-2 py-0.5 rounded border border-border-muted bg-bg-dark text-[9px] text-text-muted font-mono uppercase tracking-wider">
            <span className={`pulse-dot inline-block w-1.5 h-1.5 rounded-full ${wsConnected ? 'bg-success' : 'bg-text-muted'}`} />
            {wsConnected ? 'connected' : 'disconnected'} &middot; {investigationStatus}
          </div>

          {user && (
            <div className="flex items-center gap-2">
              <span className="text-[9px] text-text-muted">{user.email}</span>
              <button
                onClick={() => logout({ logoutParams: { returnTo: window.location.origin } })}
                className="text-[9px] text-text-muted hover:text-white transition-colors"
              >
                Logout
              </button>
            </div>
          )}
        </div>
      </header>

      {/* Content area */}
      {activeTab === 'threats' && (
        <SecurityThreatsPage
          expandedAttack={expandedAttack}
          onExpand={setExpandedAttack}
          onCollapse={() => setExpandedAttack(null)}
          onLaunchInvestigation={handleLaunchInvestigation}
          investigationStatus={investigationStatus}
          currentAttack={attackPhase}
        />
      )}
      {activeTab === 'logs' && (
        <ErrorBoundary>
          <DashboardView
            isRunning={isRunning}
            investigationStatus={investigationStatus}
            attackPhase={attackPhase}
          />
        </ErrorBoundary>
      )}
    </div>
  )
}

function DashboardView({ isRunning, investigationStatus, attackPhase }) {
  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Sub-header */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-border-muted bg-bg-dark/50 shrink-0">
        <span className="text-[10px] text-text-muted uppercase tracking-wider font-mono">
          Investigation Log — Attack {attackPhase}
        </span>
      </div>

      {/* Two-column layout */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left: Investigation tree */}
        <div className="w-1/2 h-full">
          <InvestigationTree />
        </div>

        {/* Right: Panel stack */}
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

      {/* Qualitative Analysis -- full-width bottom row */}
      <div className="border-t border-border-muted bg-bg-dark px-4 py-3 shrink-0">
        <QualitativeAnalysisPanel />
      </div>
    </div>
  )
}
