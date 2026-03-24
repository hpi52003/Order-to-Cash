import { useState } from 'react'
import GraphPanel from './components/GraphPanel'
import ChatPanel from './components/ChatPanel'
import './App.css'

export default function App() {
  const [highlightedNodes, setHighlightedNodes] = useState([])

  return (
    <div className="app-root">
      <header className="topbar">
        <div className="topbar-left">
          <span className="topbar-logo">◈</span>
          <div>
            <div className="topbar-title">O2C Graph Explorer</div>
            <div className="topbar-sub">Order-to-Cash Intelligence</div>
          </div>
        </div>
        <div className="topbar-right">
          <span className="topbar-badge">SAP Dataset</span>
        </div>
      </header>
      <div className="main-panels">
        <div className="panel-graph">
          <GraphPanel highlightedNodes={highlightedNodes} />
        </div>
        <div className="panel-chat">
          <ChatPanel onHighlight={setHighlightedNodes} />
        </div>
      </div>
    </div>
  )
}
