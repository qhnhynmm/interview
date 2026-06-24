import { useEffect, useRef, useState } from 'react'
import { Icon } from '@/components/icons.jsx'
import { codeAssist } from '@/utils/interviews.js'

// Split an assistant message into plain-text and fenced-code segments so code
// blocks can be rendered with Copy / Insert actions, like VS Code's chat.
function parseSegments(text) {
  const segments = []
  const fence = /```(\w+)?\n?([\s\S]*?)```/g
  let last = 0
  let m
  while ((m = fence.exec(text)) !== null) {
    if (m.index > last) {
      segments.push({ type: 'text', value: text.slice(last, m.index) })
    }
    segments.push({ type: 'code', lang: m[1] || 'python', value: m[2].replace(/\n$/, '') })
    last = fence.lastIndex
  }
  if (last < text.length) {
    segments.push({ type: 'text', value: text.slice(last) })
  }
  return segments
}

function CodeBlock({ value, lang, onInsert }) {
  const [copied, setCopied] = useState(false)
  function copy() {
    navigator.clipboard?.writeText(value).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 1200)
    })
  }
  return (
    <div style={{ border: '1px solid var(--color-border)', borderRadius: 6, overflow: 'hidden', margin: '8px 0' }}>
      <div style={{
        display: 'flex', alignItems: 'center', gap: 6,
        padding: '4px 8px', background: 'var(--color-surface)',
        borderBottom: '1px solid var(--color-border)',
        fontSize: 10, color: 'var(--color-muted)', textTransform: 'uppercase', letterSpacing: '0.06em',
      }}>
        <span>{lang}</span>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 4 }}>
          <button className="btn btn--ghost btn--sm" onClick={copy} style={btnTiny}>
            <Icon name={copied ? 'check' : 'copy'} size={11} />
            {copied ? 'Copied' : 'Copy'}
          </button>
          {onInsert && (
            <button className="btn btn--ghost btn--sm" onClick={() => onInsert(value)} style={btnTiny}>
              <Icon name="arrow" size={11} />
              Insert
            </button>
          )}
        </div>
      </div>
      <pre style={{
        margin: 0, padding: '10px 12px', background: '#0d1117',
        fontFamily: "'JetBrains Mono', 'Fira Code', monospace", fontSize: 12,
        lineHeight: 1.5, color: '#e6edf3', overflowX: 'auto', whiteSpace: 'pre',
      }}>
        {value}
      </pre>
    </div>
  )
}

function Message({ msg, onInsert }) {
  const isUser = msg.role === 'user'
  return (
    <div style={{ marginBottom: 14 }}>
      <div style={{
        display: 'flex', alignItems: 'center', gap: 6, marginBottom: 5,
        fontSize: 11, fontWeight: 600,
        color: isUser ? 'var(--color-muted)' : 'var(--color-accent)',
      }}>
        <Icon name={isUser ? 'mic' : 'spark'} size={12} />
        {isUser ? 'You' : 'Assistant'}
      </div>
      <div style={{ fontSize: 13, lineHeight: 1.6, color: 'var(--color-text)' }}>
        {parseSegments(msg.content).map((seg, i) =>
          seg.type === 'code'
            ? <CodeBlock key={i} value={seg.value} lang={seg.lang} onInsert={isUser ? null : onInsert} />
            : <span key={i} style={{ whiteSpace: 'pre-wrap' }}>{seg.value}</span>
        )}
      </div>
    </div>
  )
}

export default function CodeAssistant({ interviewId, enabled, getCode, onInsertCode }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [attachCode, setAttachCode] = useState(true)
  const scrollRef = useRef(null)

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, loading])

  async function send() {
    const text = input.trim()
    if (!text || loading || !enabled) return
    setError('')
    const next = [...messages, { role: 'user', content: text }]
    setMessages(next)
    setInput('')
    setLoading(true)
    try {
      const code = attachCode ? getCode?.() : null
      const { reply } = await codeAssist(interviewId, next, code)
      setMessages([...next, { role: 'assistant', content: reply || '(no response)' }])
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  function onKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      send()
    }
  }

  return (
    <div style={{
      width: 360, flexShrink: 0, display: 'flex', flexDirection: 'column',
      borderLeft: '1px solid var(--color-border)', background: 'var(--color-bg)',
      height: '100%', overflow: 'hidden', position: 'relative',
    }}>
      {/* Header */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 8,
        padding: '10px 14px', borderBottom: '1px solid var(--color-border)',
        background: 'var(--color-surface)', flexShrink: 0,
      }}>
        <Icon name="spark" size={15} />
        <span style={{ fontWeight: 600, fontSize: 13 }}>Coding Assistant</span>
        {messages.length > 0 && (
          <button
            className="btn btn--ghost btn--sm"
            onClick={() => { setMessages([]); setError('') }}
            style={{ ...btnTiny, marginLeft: 'auto' }}
          >
            Clear
          </button>
        )}
      </div>

      {/* Messages */}
      <div ref={scrollRef} style={{ flex: 1, overflowY: 'auto', padding: '14px' }}>
        {messages.length === 0 && (
          <div style={{ color: 'var(--color-muted)', fontSize: 12.5, lineHeight: 1.7, marginTop: 8 }}>
            <p style={{ margin: '0 0 8px', fontWeight: 600, color: 'var(--color-text)' }}>
              Ask me about your code.
            </p>
            <p style={{ margin: 0 }}>
              Paste a snippet and I'll explain, debug, or complete it. Use{' '}
              <strong>Insert</strong> on a code block to drop it straight into the editor,
              then <strong>Run</strong>.
            </p>
          </div>
        )}
        {messages.map((m, i) => (
          <Message key={i} msg={m} onInsert={onInsertCode} />
        ))}
        {loading && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'var(--color-muted)', fontSize: 12 }}>
            <span style={dotSpinner} />
            Thinking…
          </div>
        )}
        {error && (
          <div style={{ color: '#ff6b6b', fontSize: 12, marginTop: 8 }}>{error}</div>
        )}
      </div>

      {/* Composer */}
      <div style={{ borderTop: '1px solid var(--color-border)', padding: 10, flexShrink: 0, background: 'var(--color-surface)' }}>
        <button
          onClick={() => setAttachCode((v) => !v)}
          className="btn btn--ghost btn--sm"
          style={{
            ...btnTiny, marginBottom: 8,
            color: attachCode ? 'var(--color-accent)' : 'var(--color-muted)',
          }}
        >
          <Icon name="code" size={11} />
          {attachCode ? 'Editor code attached' : 'Attach editor code'}
        </button>
        <div style={{ display: 'flex', gap: 8, alignItems: 'flex-end' }}>
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={onKeyDown}
            disabled={!enabled || loading}
            placeholder={enabled ? 'Ask a question…  (Enter to send)' : 'Assistant disabled'}
            rows={2}
            style={{
              flex: 1, resize: 'none', borderRadius: 6,
              border: '1px solid var(--color-border)', background: 'var(--color-bg)',
              color: 'var(--color-text)', padding: '8px 10px', fontSize: 13,
              fontFamily: 'inherit', lineHeight: 1.5, outline: 'none',
            }}
          />
          <button
            className="btn btn--primary btn--sm"
            onClick={send}
            disabled={!enabled || loading || !input.trim()}
            style={{ height: 36, minWidth: 44 }}
          >
            <Icon name="arrow" size={14} />
          </button>
        </div>
      </div>

      {/* Disabled overlay */}
      {!enabled && (
        <div style={{
          position: 'absolute', inset: 0, background: 'rgba(10,14,39,0.82)',
          display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
          gap: 10, padding: 24, textAlign: 'center', backdropFilter: 'blur(2px)',
        }}>
          <Icon name="shield" size={28} />
          <p style={{ margin: 0, fontSize: 13, fontWeight: 600 }}>Assistant disabled</p>
          <p style={{ margin: 0, fontSize: 12, color: 'var(--color-muted)' }}>
            The interviewer has turned off AI assistance for this section.
          </p>
        </div>
      )}

      <style>{`
        @keyframes dot-spin { to { transform: rotate(360deg); } }
      `}</style>
    </div>
  )
}

const btnTiny = {
  fontSize: 10.5,
  padding: '3px 7px',
  display: 'inline-flex',
  alignItems: 'center',
  gap: 4,
}

const dotSpinner = {
  width: 12, height: 12, borderRadius: '50%',
  border: '2px solid rgba(255,255,255,0.18)',
  borderTopColor: 'var(--color-accent)',
  display: 'inline-block',
  animation: 'dot-spin 0.8s linear infinite',
}
