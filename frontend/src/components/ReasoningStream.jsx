import { useEffect, useRef } from 'react'

const AGENT_META = {
  Planning: { label: 'plan', color: '#be123c' },
  Assignment: { label: 'assign', color: '#3da5ff' },
  System: { label: 'sys', color: '#64748b' },
}

export function ReasoningStream({ lines = [], done = false, error = null }) {
  const scrollRef = useRef(null)

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [lines.length])

  const title = error
    ? 'Session generation failed'
    : !lines.length
      ? 'Spinning up Aurelia agents…'
      : done
        ? 'Plan complete — finalising…'
        : 'Aurelia is planning the session…'

  return (
    <div className="reasoning">
      <div className="reasoning__header">
        <span className={`reasoning__dot${done ? ' reasoning__dot--done' : ''}`} />
        <span className="reasoning__title">{title}</span>
      </div>

      {error && <div className="reasoning__error">{error}</div>}

      <div className="reasoning__log" ref={scrollRef}>
        {lines.map((line, i) => {
          const fromEnd = lines.length - i
          const opacity = fromEnd <= 2 ? 0.55 : Math.max(0.18, 0.55 - (fromEnd - 2) * 0.1)
          return (
            <ReasoningLine
              key={`${line.agent}-${i}-${line.text.slice(0, 24)}`}
              agent={line.agent}
              text={line.text}
              opacity={opacity}
            />
          )
        })}
      </div>

      {!done && (
        <div className="reasoning__preview">
          <div className="skeleton reasoning__skel" style={{ height: 36 }} />
          <div className="skeleton reasoning__skel" style={{ height: 13, width: '62%' }} />
          <div className="skeleton reasoning__skel" style={{ height: 13, width: '44%' }} />
        </div>
      )}
    </div>
  )
}

function ReasoningLine({ agent, text, opacity = 1 }) {
  const meta = AGENT_META[agent] ?? { label: agent, color: '#aaa' }
  return (
    <div className="reasoning__line" style={{ opacity }}>
      <span
        className="reasoning__tag"
        style={{ color: meta.color, borderColor: meta.color + '44' }}
      >
        {meta.label}
      </span>
      <span className="reasoning__text">{text}</span>
    </div>
  )
}