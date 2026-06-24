import { useEffect, useRef, useState } from 'react'

const AGENT_META = {
  Planning: { label: 'plan', color: '#be123c' },
  Assignment: { label: 'assign', color: '#3da5ff' },
}

// Delay before the reasoning starts streaming. The loading shell shows
// immediately on click, then the narration begins after this beat — so it reads
// like the agents actually spin up and think, not a canned animation firing the
// instant you click.
const STREAM_START_DELAY_MS = 1500

// Link creation is driven by the Planning Agent, which grounds the CV+JD, drafts
// the interview/evaluation briefs, then HANDS the assignment directive to the
// Code Assignment Agent and waits for it to design the task. These steps narrate
// that hand-off while the real planning call is in flight.
function buildSteps(role, seniority, name) {
  const r = role || 'the position'
  const s = seniority || 'Mid'
  const n = name || 'the candidate'
  return [
    { agent: 'Planning', text: `Received CV and job description for ${n}.` },
    { agent: 'Planning', text: `Parsing JD — role: ${r} · level: ${s}.` },
    { agent: 'Planning', text: 'Grounding: extracting required skills and primary domain…' },
    { agent: 'Planning', text: `Matching ${n}'s skills against the JD and flagging gaps.` },
    { agent: 'Planning', text: 'Drafting the interview brief — topics & questions tailored to the CV…' },
    { agent: 'Planning', text: 'Drafting the evaluation brief — scoring criteria & red flags…' },
    { agent: 'Planning', text: 'Handing the assignment directive to the Code Assignment Agent…' },
    { agent: 'Assignment', text: `Directive received — designing a ${s}-level task for ${r}.` },
    { agent: 'Assignment', text: 'Searching the problem bank for a difficulty reference…' },
    { agent: 'Assignment', text: 'Calibrating scope, time limit and AI-assistant policy…' },
    { agent: 'Assignment', text: 'Assignment drafted and returned to Planning.' },
    { agent: 'Planning', text: 'Three briefs aligned. Generating meeting link and scheduling…' },
  ]
}

export function ReasoningStream({ role, seniority, candidateName, onComplete }) {
  // Freeze steps on mount so re-renders don't restart the animation.
  const [steps] = useState(() => buildSteps(role, seniority, candidateName))

  const [started, setStarted] = useState(false)
  const [committed, setCommitted] = useState([])
  const [typing, setTyping] = useState({ agent: '', text: '', chars: 0 })
  const [stepIdx, setStepIdx] = useState(0)
  const scrollRef = useRef(null)
  const completedRef = useRef(false)

  // Hold the loading shell for a beat before narrating anything.
  useEffect(() => {
    const t = setTimeout(() => setStarted(true), STREAM_START_DELAY_MS)
    return () => clearTimeout(t)
  }, [])

  useEffect(() => {
    if (!started || stepIdx >= steps.length) return

    const step = steps[stepIdx]

    let char = 0
    let charTimer
    let nextTimer

    const tick = () => {
      char++
      setTyping({ agent: step.agent, text: step.text, chars: char })
      if (char < step.text.length) {
        charTimer = setTimeout(tick, 10)
      } else {
        nextTimer = setTimeout(() => {
          setCommitted((prev) => [...prev, { agent: step.agent, text: step.text }])
          setTyping({ agent: '', text: '', chars: 0 })
          setStepIdx((i) => i + 1)
        }, 140)
      }
    }

    charTimer = setTimeout(tick, 80)
    return () => {
      clearTimeout(charTimer)
      clearTimeout(nextTimer)
    }
  }, [started, stepIdx, steps])

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [committed.length, typing.chars])

  const isTyping = typing.text.length > 0
  const done = started && stepIdx >= steps.length

  // Signal the parent once the full mock flow has narrated, so it can reveal the
  // generated link only after the reasoning finishes (not the instant the API
  // returns, which is usually faster than the animation).
  useEffect(() => {
    if (done && !completedRef.current) {
      completedRef.current = true
      onComplete?.()
    }
  }, [done, onComplete])

  return (
    <div className="reasoning">
      <div className="reasoning__header">
        <span className={`reasoning__dot${done ? ' reasoning__dot--done' : ''}`} />
        <span className="reasoning__title">
          {!started
            ? 'Spinning up Aurelia agents…'
            : done
              ? 'Plan complete — finalising…'
              : 'Aurelia is planning the session…'}
        </span>
      </div>

      <div className="reasoning__log" ref={scrollRef}>
        {committed.map((line, i) => {
          const fromEnd = committed.length - i
          const opacity = fromEnd <= 2 ? 0.55 : Math.max(0.18, 0.55 - (fromEnd - 2) * 0.1)
          return (
            <ReasoningLine key={i} agent={line.agent} text={line.text} opacity={opacity} />
          )
        })}
        {isTyping && (
          <ReasoningLine
            agent={typing.agent}
            text={typing.text.slice(0, typing.chars)}
            opacity={0.9}
            cursor
          />
        )}
      </div>

      <div className="reasoning__preview">
        <div className="skeleton reasoning__skel" style={{ height: 36 }} />
        <div className="skeleton reasoning__skel" style={{ height: 13, width: '62%' }} />
        <div className="skeleton reasoning__skel" style={{ height: 13, width: '44%' }} />
      </div>
    </div>
  )
}

function ReasoningLine({ agent, text, cursor, opacity = 1 }) {
  const meta = AGENT_META[agent] ?? { label: agent, color: '#aaa' }
  return (
    <div className="reasoning__line" style={{ opacity }}>
      <span
        className="reasoning__tag"
        style={{ color: meta.color, borderColor: meta.color + '44' }}
      >
        {meta.label}
      </span>
      <span className="reasoning__text">
        {text}
        {cursor && <span className="reasoning__cursor">▊</span>}
      </span>
    </div>
  )
}
