import { useEffect, useRef, useState } from 'react'
import Editor from '@monaco-editor/react'
import { Icon } from '@/components/icons.jsx'
import CodeAssistant from '@/components/CodeAssistant.jsx'
import Markdown from '@/components/Markdown.jsx'
import ToggleChip from '@/components/ToggleChip.jsx'
import { DIFFICULTY_STYLE, FALLBACK_STARTER } from '@/constants/code.js'
import { runCode, submitAssignment, syncCode } from '@/utils/interviews.js'

function TestResultRow({ result }) {
  const ok = result.passed
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'flex-start',
        gap: 8,
        padding: '6px 0',
        borderBottom: '1px solid rgba(255,255,255,0.05)',
        fontSize: 12,
      }}
    >
      <span style={{ color: ok ? 'var(--color-accent)' : '#ff6b6b', flexShrink: 0, marginTop: 1 }}>
        {ok ? '✓' : '✗'}
      </span>
      <div style={{ flex: 1, minWidth: 0 }}>
        <span style={{ color: ok ? 'var(--color-accent)' : '#ff6b6b', fontWeight: 600 }}>
          {result.label}
        </span>
        {!ok && (
          <div style={{ marginTop: 3, fontFamily: 'monospace', color: 'var(--color-muted)' }}>
            <div>expected: <span style={{ color: '#e6edf3' }}>{result.expected}</span></div>
            <div>got:&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style={{ color: '#ff6b6b' }}>{result.got}</span></div>
          </div>
        )}
      </div>
    </div>
  )
}

export default function CodePanel({ interviewId, problem, mode, aiEnabled, assistantEnabled = true, savedCode = null, finished = false, onDone }) {
  const codingMode = mode ?? problem?.mode ?? null
  const ai = aiEnabled ?? problem?.ai_assistant_enabled ?? false
  const starter = problem?.starter_code ?? FALLBACK_STARTER
  const diff = problem?.difficulty ?? 'medium'
  const diffStyle = DIFFICULTY_STYLE[diff] ?? DIFFICULTY_STYLE.medium
  // Seed from the candidate's persisted code (restored on remount / reload) so a
  // mode toggle never resets their work; fall back to the starter on first entry.
  const [code, setCode] = useState(savedCode ?? starter)
  const [running, setRunning] = useState(false)
  const [result, setResult] = useState(null)
  const [showAssistant, setShowAssistant] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [submitted, setSubmitted] = useState(!!finished)
  const syncTimer = useRef(null)
  const editorRef = useRef(null)
  const codeRef = useRef(code)
  useEffect(() => { codeRef.current = code }, [code])

  // Flush the latest code to the backend when the panel unmounts (e.g. the agent
  // toggles back to interview mode), so no edits since the last debounced sync
  // are lost before the editor is restored on the next switch to code mode.
  useEffect(() => {
    return () => {
      if (syncTimer.current) clearTimeout(syncTimer.current)
      syncCode(interviewId, codeRef.current)
    }
  }, [interviewId])

  // Push code to backend on a 5s debounce so the agent can see it live.
  function handleCodeChange(v) {
    if (submitted) return
    const next = v ?? ''
    setCode(next)
    if (syncTimer.current) clearTimeout(syncTimer.current)
    syncTimer.current = setTimeout(() => syncCode(interviewId, next), 5000)
  }

  // Insert an assistant code block at the cursor (replacing any selection),
  // mirroring VS Code's chat "Insert" action. executeEdits fires onChange,
  // which keeps the `code` state and backend sync in lockstep.
  function insertCode(snippet) {
    const editor = editorRef.current
    if (!editor) {
      handleCodeChange(`${code}\n${snippet}`)
      return
    }
    const selection = editor.getSelection()
    editor.executeEdits('assistant-insert', [
      { range: selection, text: snippet, forceMoveMarkers: true },
    ])
    editor.focus()
  }

  async function run() {
    setRunning(true)
    setResult(null)
    // Flush pending sync immediately before running.
    if (syncTimer.current) {
      clearTimeout(syncTimer.current)
      syncTimer.current = null
    }
    await syncCode(interviewId, code)
    try {
      // const res = await fetch(`/api/v1/interviews/${interviewId}/run-code`, { ... })
      setResult(await runCode(interviewId, code))
    } catch (e) {
      setResult({ stdout: '', stderr: e.message, exit_code: 1, timed_out: false, test_results: [], tests_passed: 0, tests_total: 0 })
    } finally {
      setRunning(false)
    }
  }

  async function submit() {
    if (submitted || submitting) return
    setSubmitting(true)
    if (syncTimer.current) { clearTimeout(syncTimer.current); syncTimer.current = null }
    await syncCode(interviewId, code)
    try {
      // await fetch(`/api/v1/interviews/${interviewId}/submit-assignment`, { ... })
      await submitAssignment(interviewId, { type: 'coding', code, mode: codingMode })
    } catch { /* non-critical */ }
    setSubmitted(true)
    setSubmitting(false)
    if (onDone) onDone()
  }

  const hasTests = result && result.tests_total > 0
  const allPassed = hasTests && result.tests_passed === result.tests_total

  return (
    <div style={{ display: 'flex', height: '100%', overflow: 'hidden' }}>
      {/* Problem brief (assignment_brief markdown, rendered as plain pre-wrap text) */}
      {problem && (
        <div
          style={{
            width: 300,
            flexShrink: 0,
            borderRight: '1px solid var(--color-border)',
            overflowY: 'auto',
            padding: '20px 16px',
            fontSize: 13,
            lineHeight: 1.7,
          }}
        >
          <div style={{ fontSize: 10, color: 'var(--color-muted)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 12 }}>
            Coding Assignment
          </div>
          <div style={{ margin: '0 0 10px', color: 'var(--color-text)', fontSize: 15, fontWeight: 700 }}>
            {problem.title ?? 'Assignment'}
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 16 }}>
            <span
              style={{
                display: 'inline-block',
                padding: '2px 8px',
                borderRadius: 4,
                fontSize: 10,
                fontWeight: 700,
                letterSpacing: '0.06em',
                background: diffStyle.bg,
                color: diffStyle.color,
              }}
            >
              {diff.toUpperCase()}
            </span>
            {codingMode && (
              <span
                style={{
                  display: 'inline-block',
                  padding: '2px 8px',
                  borderRadius: 4,
                  fontSize: 10,
                  fontWeight: 700,
                  letterSpacing: '0.06em',
                  background: 'rgba(255,255,255,0.06)',
                  color: 'var(--color-muted)',
                }}
              >
                {codingMode === 'dsa' ? 'DSA' : 'PROJECT'}
              </span>
            )}
            <span
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 4,
                padding: '2px 8px',
                borderRadius: 4,
                fontSize: 10,
                fontWeight: 700,
                letterSpacing: '0.06em',
                background: ai ? 'rgba(190,18,60,0.1)' : 'rgba(255,80,80,0.1)',
                color: ai ? 'var(--color-accent)' : '#ff6b6b',
              }}
            >
              <Icon name="spark" size={10} />
              {ai ? 'AI ASSISTANT ON' : 'AI ASSISTANT OFF'}
            </span>
          </div>
          <Markdown>
            {problem.statement ?? problem.assignment_brief ?? problem.coding_brief ?? ''}
          </Markdown>
        </div>
      )}

      {/* Editor + output */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        {/* Top toolbar — runtime info + run status on the left, actions gathered top-right */}
        <div
          style={{
            borderBottom: '1px solid var(--color-border)',
            padding: '8px 14px',
            display: 'flex',
            alignItems: 'center',
            gap: 12,
            background: 'var(--color-surface)',
            flexShrink: 0,
          }}
        >
          <span
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 6,
              fontSize: 11,
              fontWeight: 600,
              color: 'var(--color-muted)',
            }}
          >
            <Icon name="code" size={13} />
            Python 3 · 10s limit
          </span>

          {result && (
            <span
              style={{
                fontSize: 11,
                fontWeight: 600,
                color: result.timed_out
                  ? '#ffd166'
                  : hasTests
                    ? (allPassed ? 'var(--color-accent)' : '#ff6b6b')
                    : (result.exit_code === 0 ? 'var(--color-accent)' : '#ff6b6b'),
              }}
            >
              {result.timed_out
                ? 'Timed out'
                : hasTests
                  ? `${result.tests_passed} / ${result.tests_total} passed`
                  : result.exit_code === 0 ? '✓ OK' : `✗ Exit ${result.exit_code}`}
            </span>
          )}

          <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 8 }}>
            <button
              className="btn btn--primary"
              onClick={run}
              disabled={running || submitted}
              style={{ height: 30, padding: '0 16px', fontSize: 12, borderRadius: 999 }}
            >
              <Icon name="spark" size={13} />
              {running ? 'Running…' : 'Run'}
            </button>
            <button
              className="btn btn--ghost"
              onClick={submit}
              disabled={submitting || submitted}
              style={{
                height: 30, padding: '0 16px', fontSize: 12, borderRadius: 999,
                borderColor: submitted ? 'rgba(190,18,60,0.4)' : undefined,
                color: submitted ? 'var(--color-accent)' : undefined,
              }}
            >
              <Icon name="check" size={13} />
              {submitting ? 'Submitting…' : submitted ? 'Submitted ✓' : 'Submit'}
            </button>
            <ToggleChip
              active={showAssistant}
              onClick={() => setShowAssistant((v) => !v)}
              icon="chat"
              label="Assistant"
              tone="neutral"
              title={showAssistant ? 'Hide coding assistant' : 'Show coding assistant'}
            />
          </div>
        </div>

        <div style={{ flex: 1, overflow: 'hidden' }}>
          <Editor
            height="100%"
            language="python"
            value={code}
            onChange={handleCodeChange}
            onMount={(editor) => { editorRef.current = editor }}
            theme="vs-dark"
            options={{
              readOnly: submitted,
              fontSize: 13,
              fontFamily: "'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace",
              minimap: { enabled: false },
              scrollBeyondLastLine: false,
              lineNumbers: 'on',
              tabSize: 4,
              renderLineHighlight: 'line',
              automaticLayout: true,
              padding: { top: 12 },
            }}
          />
        </div>

        {/* Output panel */}
        {result && (
          <div
            style={{
              height: 200,
              flexShrink: 0,
              borderTop: '1px solid var(--color-border)',
              background: '#0d1117',
              overflowY: 'auto',
              padding: '10px 14px',
              fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
              fontSize: 12,
              lineHeight: 1.6,
            }}
          >
            {hasTests ? (
              <>
                {/* Test case results */}
                {result.test_results.map((r, i) => (
                  <TestResultRow key={i} result={r} />
                ))}
                {/* Compile / runtime errors */}
                {result.stderr && (
                  <pre style={{ margin: '8px 0 0', color: '#ff6b6b', whiteSpace: 'pre-wrap' }}>
                    {result.stderr}
                  </pre>
                )}
              </>
            ) : (
              <>
                {result.stdout && (
                  <pre style={{ margin: 0, color: '#e6edf3', whiteSpace: 'pre-wrap' }}>
                    {result.stdout}
                  </pre>
                )}
                {result.stderr && (
                  <pre style={{ margin: 0, color: '#ff6b6b', whiteSpace: 'pre-wrap' }}>
                    {result.stderr}
                  </pre>
                )}
                {!result.stdout && !result.stderr && (
                  <span style={{ color: 'var(--color-muted)' }}>No output.</span>
                )}
              </>
            )}
          </div>
        )}
      </div>

      {/* Coding assistant (VS Code chat-style side panel) */}
      {showAssistant && (
        <CodeAssistant
          interviewId={interviewId}
          enabled={ai && assistantEnabled}
          getCode={() => code}
          onInsertCode={insertCode}
        />
      )}
    </div>
  )
}
