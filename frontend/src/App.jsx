import { ReactFlow, Background } from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { useStore } from './store'

const initialNodes = []
const initialEdges = []

export default function App() {
  const wsConnected = useStore((s) => s.wsConnected)
  const investigationStatus = useStore((s) => s.investigationStatus)

  return (
    <div className="h-screen bg-bg-dark text-text-main font-display flex flex-col">
      {/* Header */}
      <header className="flex items-center justify-between h-12 px-4 border-b border-border-muted bg-surface/50 backdrop-blur-md sticky top-0 z-10">
        <h1 className="text-sm font-bold tracking-tight text-white">Sentinel Dashboard</h1>
        <div className="flex items-center gap-1.5 px-2 py-0.5 rounded border border-border-muted bg-bg-dark text-[10px] text-text-muted font-mono uppercase tracking-wider">
          <span
            className={`pulse-dot inline-block w-1.5 h-1.5 rounded-full ${wsConnected ? 'bg-success' : 'bg-text-muted'}`}
          />
          {wsConnected ? 'connected' : 'idle'} &middot; {investigationStatus}
        </div>
      </header>

      {/* Main content */}
      <div className="flex flex-1 overflow-hidden">
        {/* ReactFlow panel — proves @xyflow/react import works */}
        <div className="flex-1 bg-bg-dark">
          <ReactFlow
            nodes={initialNodes}
            edges={initialEdges}
            fitView
          >
            <Background color="#30363d" gap={24} />
          </ReactFlow>
        </div>
      </div>
    </div>
  )
}
