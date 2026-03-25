import { ReactFlow, Background, Handle, Position } from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { useStore } from '../store'

// --- Custom node renderer ---

function SentinelNode({ data }) {
  const { status, label, icon } = data

  let borderClass = 'border border-border-muted'
  let iconColorClass = 'text-text-muted'
  let iconName = icon
  let bgStyle = {}

  switch (status) {
    case 'active':
      borderClass = 'border-2 border-accent'
      iconColorClass = 'text-accent'
      iconName = 'sync'
      break
    case 'complete':
      borderClass = 'border border-success'
      iconColorClass = 'text-success'
      iconName = 'check_circle'
      break
    case 'blocked':
      borderClass = 'border-2 border-danger'
      iconColorClass = 'text-danger'
      iconName = 'block'
      bgStyle = { backgroundColor: 'rgba(248,81,73,0.1)' }
      break
    case 'rule_node':
      borderClass = 'border border-warning'
      iconColorClass = 'text-warning'
      iconName = 'auto_awesome'
      bgStyle = { backgroundColor: 'rgba(227,179,65,0.1)' }
      break
    default:
      // pending
      break
  }

  const isSpinning = status === 'active'

  return (
    <div
      className={`bg-surface rounded-lg px-3 py-2 flex items-center gap-2 transition-all duration-150 ${borderClass}`}
      style={bgStyle}
    >
      <Handle type="target" position={Position.Top} style={{ visibility: 'hidden' }} />
      <span
        className={`material-symbols-outlined text-[18px] ${iconColorClass} ${isSpinning ? 'animate-spin' : ''}`}
      >
        {iconName}
      </span>
      <span className="text-[11px] font-display text-text-main whitespace-nowrap">{label}</span>
      <Handle type="source" position={Position.Bottom} style={{ visibility: 'hidden' }} />
    </div>
  )
}

const nodeTypes = { sentinel: SentinelNode }

// --- Investigation Tree component ---

export function InvestigationTree() {
  const nodes = useStore((s) => s.nodes)
  const edges = useStore((s) => s.edges)

  if (nodes.length === 0) {
    return (
      <div className="w-full h-full flex items-center justify-center">
        <span className="text-text-muted text-sm">Waiting for investigation...</span>
      </div>
    )
  }

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      nodeTypes={nodeTypes}
      fitView
      nodesDraggable={false}
      nodesConnectable={false}
      elementsSelectable={false}
    >
      <Background color="#30363d" gap={24} />
    </ReactFlow>
  )
}
