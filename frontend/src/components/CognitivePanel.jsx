import { useEffect, useMemo, useRef, useState } from 'react'
import { Icon } from '@/components/icons.jsx'
import { LETTERS } from '@/constants/cognitive.js'
import { submitAssignment, syncAnswers } from '@/utils/interviews.js'

export default function CognitivePanel({ interviewId, test, savedAnswers = null, finished = false, onDone }) {
  const questions = useMemo(() => test?.questions ?? [], [test])
  // Seed from any persisted answers (restored on remount) so toggling back into
  // the test never wipes what the candidate already selected.
  const [answers, setAnswers] = useState(() => {
    const base = Array(questions.length).fill(null)
    if (Array.isArray(savedAnswers)) {
      savedAnswers.forEach((a, i) => { if (i < base.length) base[i] = a ?? null })
    }
    return base
  })
  const [submitting, setSubmitting] = useState(false)
  const [submitted, setSubmitted] = useState(!!finished)
  const syncTimer = useRef(null)
  const answersRef = useRef(answers)
  useEffect(() => { answersRef.current = answers }, [answers])

  // Flush the latest answers when the panel unmounts (agent toggles back to
  // interview mode) so nothing since the last debounced sync is lost.
  useEffect(() => {
    return () => {
      if (syncTimer.current) clearTimeout(syncTimer.current)
      if (!submitted) syncAnswers(interviewId, answersRef.current)
    }
  }, [interviewId, submitted])

  const answeredCount = answers.filter((a) => a !== null).length
  const allAnswered = questions.length > 0 && answeredCount === questions.length

  // Local score using the embedded answer keys, so the candidate sees a result
  // even before the backend grader endpoint exists.
  const score = useMemo(() => {
    if (!submitted) return null
    let correct = 0
    questions.forEach((q, i) => {
      if (answers[i] && answers[i] === q.answer) correct += 1
    })
    return correct
  }, [submitted, answers, questions])

  function choose(qi, letter) {
    if (submitted) return
    setAnswers((prev) => {
      const next = [...prev]
      next[qi] = letter
      if (syncTimer.current) clearTimeout(syncTimer.current)
      syncTimer.current = setTimeout(() => syncAnswers(interviewId, next), 1500)
      return next
    })
  }

  async function handleSubmit() {
    if (!allAnswered || submitting) return
    setSubmitting(true)
    // await fetch(`/api/v1/interviews/${interviewId}/submit-assignment`, { ... })
    await submitAssignment(interviewId, { type: 'cognitive', answers })
    setSubmitted(true)
    setSubmitting(false)
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      {/* Header */}
      <div
        style={{
          flexShrink: 0,
          borderBottom: '1px solid var(--color-border)',
          padding: '16px 24px',
          display: 'flex',
          alignItems: 'center',
          gap: 14,
          background: 'var(--color-surface)',
        }}
      >
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 10, color: 'var(--color-muted)', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
            Cognitive Test
          </div>
          <div style={{ fontWeight: 600, fontSize: 15, marginTop: 2 }}>
            {test?.topic ?? 'Aptitude assessment'}
          </div>
        </div>
        <span style={{ fontSize: 12, color: 'var(--color-muted)' }}>
          {answeredCount} / {questions.length} answered
        </span>
        {submitted && score !== null && (
          <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--color-accent)' }}>
            Score: {score} / {questions.length}
          </span>
        )}
      </div>

      {/* Questions */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '20px 24px' }}>
        {questions.map((q, qi) => (
          <div
            key={qi}
            style={{
              marginBottom: 22,
              paddingBottom: 18,
              borderBottom: '1px solid rgba(255,255,255,0.05)',
            }}
          >
            <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 12, lineHeight: 1.5 }}>
              <span style={{ color: 'var(--color-muted)', marginRight: 8 }}>{qi + 1}.</span>
              {q.prompt}
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {q.options.map((opt, oi) => {
                const letter = LETTERS[oi]
                const selected = answers[qi] === letter
                const isCorrect = submitted && letter === q.answer
                const isWrongPick = submitted && selected && letter !== q.answer
                let borderColor = 'var(--color-border)'
                let bg = 'transparent'
                if (isCorrect) {
                  borderColor = 'var(--color-accent)'
                  bg = 'rgba(190,18,60,0.1)'
                } else if (isWrongPick) {
                  borderColor = '#ff6b6b'
                  bg = 'rgba(255,80,80,0.1)'
                } else if (selected) {
                  borderColor = 'var(--color-accent)'
                  bg = 'rgba(190,18,60,0.06)'
                }
                return (
                  <button
                    key={oi}
                    onClick={() => choose(qi, letter)}
                    disabled={submitted}
                    style={{
                      display: 'flex',
                      alignItems: 'flex-start',
                      gap: 10,
                      textAlign: 'left',
                      padding: '10px 12px',
                      borderRadius: 8,
                      border: `1px solid ${borderColor}`,
                      background: bg,
                      color: 'var(--color-text)',
                      fontSize: 13,
                      cursor: submitted ? 'default' : 'pointer',
                      transition: 'all 0.15s',
                    }}
                  >
                    <span
                      style={{
                        flexShrink: 0,
                        width: 22,
                        height: 22,
                        borderRadius: '50%',
                        border: `1px solid ${selected || isCorrect ? 'var(--color-accent)' : 'var(--color-border)'}`,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontSize: 11,
                        fontWeight: 700,
                        color: selected || isCorrect ? 'var(--color-accent)' : 'var(--color-muted)',
                      }}
                    >
                      {letter}
                    </span>
                    <span style={{ flex: 1, lineHeight: 1.5 }}>{opt}</span>
                  </button>
                )
              })}
            </div>
            {submitted && q.explanation && (
              <div style={{ marginTop: 10, fontSize: 12, color: 'var(--color-muted)', lineHeight: 1.5 }}>
                {q.explanation}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Submit bar */}
      <div
        style={{
          flexShrink: 0,
          borderTop: '1px solid var(--color-border)',
          padding: '10px 24px',
          display: 'flex',
          alignItems: 'center',
          gap: 12,
          background: 'var(--color-surface)',
        }}
      >
        {!submitted ? (
          <>
            <button
              className="btn btn--primary btn--sm"
              onClick={handleSubmit}
              disabled={!allAnswered || submitting}
            >
              <Icon name="check" size={13} />
              {submitting ? 'Submitting…' : 'Submit Answers'}
            </button>
            {!allAnswered && (
              <span style={{ fontSize: 11, color: 'var(--color-muted)' }}>
                Answer all {questions.length} questions to submit.
              </span>
            )}
          </>
        ) : (
          <>
            <span style={{ fontSize: 12, color: 'var(--color-accent)', fontWeight: 600 }}>
              ✓ Score: {score} / {questions.length} — answers recorded.
            </span>
            {onDone && (
              <button
                className="btn btn--primary btn--sm"
                onClick={onDone}
                style={{ marginLeft: 'auto' }}
              >
                <Icon name="mic" size={13} />
                Back to Interview
              </button>
            )}
          </>
        )}
      </div>
    </div>
  )
}
