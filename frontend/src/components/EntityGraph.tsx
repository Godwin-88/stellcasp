// src/components/EntityGraph.tsx
import React, { useMemo } from 'react'
import ForceGraph2D from 'react-force-graph-2d'

type GraphNode = { id: string; type: string; risk: number }
type GraphLink = { source: string; target: string; amount: number; timestamp: number }

type GraphData = {
  nodes: GraphNode[]
  links: GraphLink[]
}

export default function EntityGraph({
  data,
  targetId,
}: {
  data: GraphData
  targetId: string
}) {
  const coloredData = useMemo(() => ({
    nodes: data.nodes.map(n => ({
      ...n,
      color: n.id === targetId ? '#2563eb' : `rgba(239, 68, 68, ${0.3 + n.risk * 0.7})`,
      val: n.id === targetId ? 15 : 6,
    })),
    links: data.links.map(l => ({
      ...l,
      color: `rgba(100, 116, 139, ${Math.min(0.8, l.amount / 10000)})`,
      width: Math.min(3, l.amount / 5000),
    })),
  }), [data, targetId])

  return (
    <div className="h-[500px] rounded-2xl border border-gray-200 bg-white overflow-hidden">
      <ForceGraph2D
        graphData={coloredData}
        nodeLabel="id"
        nodeCanvasObject={(node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
          const label = `${(node.id as string).slice(0, 12)}...`
          const fontSize = 12 / globalScale
          ctx.font = `${fontSize}px Inter, sans-serif`
          ctx.fillStyle = node.id === targetId ? '#fff' : '#64748b'
          ctx.textAlign = 'center'
          ctx.textBaseline = 'top'
          ctx.fillText(label, node.x || 0, (node.y || 0) + 12)
        }}
        linkDirectionalParticles={2}
        linkDirectionalParticleWidth={2}
        backgroundColor="#fff"
        width={800}
        height={500}
      />
    </div>
  )
}