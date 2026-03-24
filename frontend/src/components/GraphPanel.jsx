import { useEffect, useState, useCallback } from 'react'
import {
  ReactFlow, Background, Controls,
  useNodesState, useEdgesState, MarkerType,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import axios from 'axios'

const TYPE_COLORS = {
  Customer:        { bg: '#D85A30', text: '#fff', border: '#ff7043' },
  SalesOrder:      { bg: '#378ADD', text: '#fff', border: '#64b5f6' },
  Delivery:        { bg: '#1D9E75', text: '#fff', border: '#4db6ac' },
  BillingDocument: { bg: '#534AB7', text: '#fff', border: '#9575cd' },
  JournalEntry:    { bg: '#BA7517', text: '#fff', border: '#ffb74d' },
  Payment:         { bg: '#639922', text: '#fff', border: '#aed581' },
  Plant:           { bg: '#607D8B', text: '#fff', border: '#90a4ae' },
  Cancellation:    { bg: '#E24B4A', text: '#fff', border: '#ef9a9a' },
  Product:         { bg: '#D4537E', text: '#fff', border: '#f48fb1' },
}

const FLOW_LAYOUT = {
  Customer:        { x: 60,  y: 340 },
  SalesOrder:      { x: 280, y: 340 },
  Delivery:        { x: 500, y: 240 },
  BillingDocument: { x: 720, y: 340 },
  JournalEntry:    { x: 940, y: 240 },
  Payment:         { x: 940, y: 440 },
  Product:         { x: 280, y: 120 },
  Plant:           { x: 500, y: 480 },
  Cancellation:    { x: 720, y: 120 },
}

const FLOW_EDGES = [
  { source: 'Customer',        target: 'SalesOrder',      label: 'PLACED' },
  { source: 'Product',         target: 'SalesOrder',      label: 'ORDERED IN' },
  { source: 'SalesOrder',      target: 'Delivery',        label: 'FULFILLS' },
  { source: 'SalesOrder',      target: 'BillingDocument', label: 'BILLS' },
  { source: 'Delivery',        target: 'Plant',           label: 'SHIPS FROM' },
  { source: 'Delivery',        target: 'BillingDocument', label: 'INVOICED' },
  { source: 'BillingDocument', target: 'JournalEntry',    label: 'HAS JOURNAL' },
  { source: 'BillingDocument', target: 'Payment',         label: 'PAID BY' },
  { source: 'Cancellation',    target: 'BillingDocument', label: 'CANCELS' },
]

export default function GraphPanel({ highlightedNodes }) {
  const [nodes, setNodes, onNodesChange] = useNodesState([])
  const [edges, setEdges, onEdgesChange] = useEdgesState([])
  const [selectedNode, setSelectedNode]  = useState(null)
  const [counts, setCounts]              = useState({})
  const [loading, setLoading]            = useState(true)

  useEffect(() => {
    axios.get('/api/counts').then((countsRes) => {
      const c = countsRes.data
      setCounts(c)

      const overviewNodes = Object.entries(FLOW_LAYOUT).map(([type, pos]) => {
        const col   = TYPE_COLORS[type] || { bg: '#888', text: '#fff', border: '#aaa' }
        const count = c[type] || 0
        return {
          id:       `overview-${type}`,
          type:     'default',
          position: pos,
          data:     { label: `${type}\n${count} records`, nodeType: type, count },
          style: {
            background:   col.bg,
            border:       `2px solid ${col.border}`,
            borderRadius: '12px',
            color:        col.text,
            fontSize:     '12px',
            fontWeight:   '600',
            padding:      '14px 20px',
            minWidth:     '140px',
            textAlign:    'center',
            cursor:       'pointer',
            boxShadow:    `0 4px 16px ${col.bg}66`,
            lineHeight:   '1.6',
          },
        }
      })

      const overviewEdges = FLOW_EDGES.map((e, i) => ({
        id:           `oe-${i}`,
        source:       `overview-${e.source}`,
        target:       `overview-${e.target}`,
        label:        e.label,
        labelStyle:   { fontSize: '10px', fill: '#8b93a8', fontWeight: '500' },
        labelBgStyle: { fill: '#161b27', fillOpacity: 0.8 },
        style:        { stroke: '#4f7ef8', strokeWidth: 2 },
        markerEnd:    { type: MarkerType.ArrowClosed, color: '#4f7ef8' },
      }))

      setNodes(overviewNodes)
      setEdges(overviewEdges)
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [])

  const onNodeClick = useCallback((_, node) => {
    const type = node.data.nodeType
    setSelectedNode({
      type,
      count: node.data.count,
      neighbors: FLOW_EDGES
        .filter(e => e.source === type || e.target === type)
        .map(e => ({
          label:     e.source === type ? e.target : e.source,
          relation:  e.label,
          direction: e.source === type ? '→' : '←',
        })),
    })
  }, [])

  if (loading) {
    return (
      <div style={{
        display: 'flex', alignItems: 'center',
        justifyContent: 'center', height: '100%',
        color: '#5a6278', flexDirection: 'column', gap: 12,
      }}>
        <div style={{
          width: 28, height: 28,
          border: '3px solid #2e3a52',
          borderTopColor: '#4f7ef8',
          borderRadius: '50%',
          animation: 'spin 0.7s linear infinite',
        }} />
        <span style={{ fontSize: 13 }}>Building graph…</span>
        <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      </div>
    )
  }

  return (
    <div className="graph-wrapper">

      {/* Hint bar top center */}
      <div style={{
        position: 'absolute', top: 14, left: '50%',
        transform: 'translateX(-50%)',
        background: 'rgba(22,27,39,0.92)',
        border: '1px solid #2e3a52',
        borderRadius: 20, padding: '5px 16px',
        fontSize: 11, color: '#8b93a8',
        zIndex: 10, whiteSpace: 'nowrap',
        pointerEvents: 'none',
      }}>
        Scroll to zoom &nbsp;•&nbsp; Drag to pan &nbsp;•&nbsp; Click a node to explore
      </div>

      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={onNodeClick}
        fitView
        fitViewOptions={{ padding: 0.3 }}
        minZoom={0.3}
        maxZoom={2}
        style={{ background: '#0f1117' }}
      >
        <Background color="#1e2535" gap={24} size={1} />
        <Controls
          position="bottom-right"
          showInteractive={false}
          style={{
            background: '#1e2535',
            border: '1px solid #4f7ef8',
            borderRadius: 8,
            marginBottom: 60,
            marginRight: 20,
          }}
        />
      </ReactFlow>

      {/* Graph Zoom label */}
      <div style={{
        position: 'absolute', bottom: 32, right: 20,
        fontSize: 10, color: '#5a6278',
        zIndex: 10, textAlign: 'center',
        letterSpacing: '0.06em', fontWeight: 600,
        textTransform: 'uppercase',
        pointerEvents: 'none',
      }}>
        Graph Zoom
      </div>

      {/* Legend bottom left */}
      <div style={{
        position: 'absolute', bottom: 20, left: 14,
        background: 'rgba(22,27,39,0.92)',
        border: '1px solid #2e3a52',
        borderRadius: 10, padding: '10px 14px',
        zIndex: 10,
      }}>
        <div style={{
          fontSize: 10, fontWeight: 600, color: '#5a6278',
          textTransform: 'uppercase', letterSpacing: '0.08em',
          marginBottom: 8,
        }}>
          Entity Types
        </div>
        {Object.entries(TYPE_COLORS).map(([type, col]) => (
          <div key={type} style={{
            display: 'flex', alignItems: 'center',
            gap: 7, marginBottom: 5,
            fontSize: 11, color: '#8b93a8',
          }}>
            <span style={{
              width: 10, height: 10, borderRadius: '50%',
              background: col.bg, flexShrink: 0,
            }} />
            {type}
            {counts[type] ? (
              <span style={{ color: '#5a6278', fontSize: 10 }}>
                ({counts[type]})
              </span>
            ) : null}
          </div>
        ))}
      </div>

      {/* Node detail side panel */}
      {selectedNode && (
        <div style={{
          position: 'absolute', top: 50, right: 14,
          width: 260,
          background: 'rgba(22,27,39,0.97)',
          border: `2px solid ${TYPE_COLORS[selectedNode.type]?.bg || '#2e3a52'}`,
          borderRadius: 12, padding: 16,
          zIndex: 10,
        }}>
          <button onClick={() => setSelectedNode(null)} style={{
            position: 'absolute', top: 10, right: 10,
            background: 'none', border: 'none',
            color: '#5a6278', cursor: 'pointer',
            fontSize: 18, lineHeight: 1,
          }}>×</button>

          <div style={{
            display: 'inline-block',
            background: TYPE_COLORS[selectedNode.type]?.bg || '#888',
            color: '#fff', fontSize: 10, fontWeight: 600,
            padding: '3px 10px', borderRadius: 20, marginBottom: 10,
          }}>
            {selectedNode.type}
          </div>

          <div style={{
            fontSize: 22, fontWeight: 700,
            color: '#e8eaf0', marginBottom: 2,
          }}>
            {selectedNode.count}
          </div>
          <div style={{ fontSize: 11, color: '#5a6278', marginBottom: 14 }}>
            total records in dataset
          </div>

          <div style={{
            borderTop: '1px solid #2e3a52',
            paddingTop: 10, marginBottom: 10,
          }}>
            <div style={{
              fontSize: 10, fontWeight: 600, color: '#5a6278',
              textTransform: 'uppercase', letterSpacing: '0.08em',
              marginBottom: 8,
            }}>
              Relationships
            </div>
            {selectedNode.neighbors?.map((nb, i) => (
              <div key={i} style={{
                display: 'flex', alignItems: 'center',
                gap: 6, marginBottom: 8, fontSize: 11,
                background: '#1e2535', borderRadius: 6,
                padding: '5px 8px',
              }}>
                <span style={{
                  width: 8, height: 8, borderRadius: '50%',
                  background: TYPE_COLORS[nb.label]?.bg || '#888',
                  flexShrink: 0,
                }} />
                <span style={{ color: '#4f7ef8', fontWeight: 600 }}>
                  {nb.direction}
                </span>
                <span style={{ color: '#5a6278', fontSize: 10 }}>
                  {nb.relation}
                </span>
                <span style={{ color: '#e8eaf0', marginLeft: 'auto' }}>
                  {nb.label}
                </span>
              </div>
            ))}
          </div>

          <div style={{
            background: '#1e2535', borderRadius: 8,
            padding: '8px 10px', fontSize: 11,
            color: '#8b93a8', lineHeight: 1.5,
          }}>
            💬 Use the chat to query {selectedNode.type} data in detail
          </div>
        </div>
      )}

      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
        .react-flow__controls-button {
          background: #1e2535 !important;
          border-bottom: 1px solid #2e3a52 !important;
          fill: #e8eaf0 !important;
        }
        .react-flow__controls-button:hover {
          background: #2e3a52 !important;
        }
        .react-flow__controls-button svg {
          fill: #e8eaf0 !important;
        }
      `}</style>
    </div>
  )
}