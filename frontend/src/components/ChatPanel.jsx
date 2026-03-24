import { useState, useRef, useEffect } from 'react'
import axios from 'axios'

const STARTERS = [
  'Which products appear in the most billing documents?',
  'Trace the full flow of a billing document',
  'Find sales orders delivered but never billed',
]

function DataTable({ data }) {
  if (!data || data.length === 0) return null
  const keys = Object.keys(data[0])
  return (
    <div>
      <div className="data-table-wrap">
        <table className="data-table">
          <thead>
            <tr>{keys.map(k => <th key={k}>{k}</th>)}</tr>
          </thead>
          <tbody>
            {data.slice(0, 20).map((row, i) => (
              <tr key={i}>{keys.map(k => <td key={k} title={String(row[k] ?? '')}>{String(row[k] ?? '—')}</td>)}</tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="data-row-count">{data.length} row{data.length !== 1 ? 's' : ''} returned</div>
    </div>
  )
}

function AssistantMessage({ msg }) {
  const [showSql, setShowSql] = useState(false)
  const isGuardrail = msg.answer?.includes('only answers questions about')
  return (
    <div className={`msg assistant${isGuardrail ? ' msg-guardrail' : ''}`}>
      <span className="msg-role">Assistant</span>
      <div className="msg-bubble">
        <div>{msg.answer}</div>
        {msg.sql && (
          <div className="sql-toggle">
            <button className="sql-toggle-btn" onClick={() => setShowSql(s => !s)}>
              {showSql ? '▲ Hide SQL' : '▼ View SQL'}
            </button>
            {showSql && <div className="sql-block">{msg.sql}</div>}
          </div>
        )}
        {msg.data && msg.data.length > 0 && !msg.data[0]?.error && (
          <DataTable data={msg.data} />
        )}
      </div>
    </div>
  )
}

export default function ChatPanel({ onHighlight }) {
  const [messages,  setMessages]  = useState([])
  const [input,     setInput]     = useState('')
  const [loading,   setLoading]   = useState(false)
  const bottomRef = useRef(null)

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages, loading])

  const send = async (text) => {
    const q = (text || input).trim()
    if (!q || loading) return
    setInput('')
    const userMsg = { role: 'user', content: q }
    setMessages(prev => [...prev, userMsg])
    setLoading(true)
    try {
      const history = messages.map(m => ({ role: m.role, content: m.content || m.answer || '' }))
      const res = await axios.post('/api/chat', { message: q, history })
      const { answer, data, sql, nodes_referenced } = res.data
      setMessages(prev => [...prev, { role: 'assistant', answer, data, sql }])
      if (nodes_referenced?.length) onHighlight(nodes_referenced)
    } catch (e) {
      setMessages(prev => [...prev, { role: 'assistant', answer: 'Error connecting to server. Is the backend running?', data: [], sql: null }])
    }
    setLoading(false)
  }

  const onKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() }
  }

  return (
    <>
      <div className="chat-header">
        <div className="chat-header-title">Graph Agent</div>
        <div className="chat-header-sub">Ask anything about the O2C dataset</div>
      </div>

      <div className="chat-messages">
        {messages.length === 0 && (
          <div className="welcome-msg">
            <strong>Welcome to O2C Graph Explorer.</strong><br/>
            Ask questions about sales orders, deliveries, billing documents, payments, products, and customers.
            The system generates SQL queries dynamically and returns data-backed answers.
          </div>
        )}
        {messages.map((msg, i) => (
          msg.role === 'user'
            ? <div key={i} className="msg user"><span className="msg-role">You</span><div className="msg-bubble">{msg.content}</div></div>
            : <AssistantMessage key={i} msg={msg} />
        ))}
        {loading && (
          <div className="msg assistant">
            <span className="msg-role">Assistant</span>
            <div className="msg-bubble">
              <div className="typing-indicator">
                <div className="typing-dot"/><div className="typing-dot"/><div className="typing-dot"/>
              </div>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="starter-chips">
        <div className="starter-label">Try asking</div>
        {STARTERS.map(s => (
          <button key={s} className="chip" onClick={() => send(s)}>{s}</button>
        ))}
      </div>

      <div className="chat-input-row">
        <textarea
          className="chat-input"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder="Ask about orders, billing, deliveries…"
          rows={1}
          disabled={loading}
        />
        <button className="send-btn" onClick={() => send()} disabled={loading || !input.trim()}>
          ➤
        </button>
      </div>
    </>
  )
}
