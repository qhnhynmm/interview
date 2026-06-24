import { useEffect, useRef, useState } from 'react'
import {
  SandpackProvider,
  SandpackLayout,
  SandpackCodeEditor,
  SandpackPreview,
  useSandpack,
} from '@codesandbox/sandpack-react'
import { Icon } from '@/components/icons.jsx'
import CodeAssistant from '@/components/CodeAssistant.jsx'
import Markdown from '@/components/Markdown.jsx'
import ToggleChip from '@/components/ToggleChip.jsx'
import { DIFFICULTY_STYLE } from '@/constants/code.js'
import { submitAssignment, syncSandbox } from '@/utils/interviews.js'

function toFilePayload(files) {
  const payload = {}
  for (const [path, fileObj] of Object.entries(files)) {
    payload[path] = typeof fileObj === 'string' ? fileObj : (fileObj?.code ?? '')
  }
  return payload
}

const DEFAULT_FILES = {
  '/App.js': `import { useState } from 'react'
import './styles.css'

export default function App() {
  return (
    <div className="p-6 font-sans">
      <h1 className="text-2xl font-bold mb-4">Start building here</h1>
      <p className="text-gray-500">Edit App.js to get started.</p>
    </div>
  )
}`,
  '/styles.css': '/* Add custom styles here */',
}

function normalizeFiles(starterFiles, savedFiles) {
  let result = {}
  if (!starterFiles || Object.keys(starterFiles).length === 0) {
    result = { ...DEFAULT_FILES }
  } else {
    for (const [name, code] of Object.entries(starterFiles)) {
      const path = name.startsWith('/') ? name : `/${name}`
      result[path] = code
    }
  }
  // Overlay the candidate's persisted edits so a mode toggle / reload restores
  // their work instead of resetting to the starter files.
  if (savedFiles && Object.keys(savedFiles).length > 0) {
    for (const [name, code] of Object.entries(savedFiles)) {
      const path = name.startsWith('/') ? name : `/${name}`
      result[path] = code
    }
  }
  return result
}

function SandpackContent({ interviewId, ai, assistantEnabled, finished, onDone }) {
  const { sandpack, dispatch } = useSandpack()
  const [showAssistant, setShowAssistant] = useState(true)
  const [showPreview, setShowPreview] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [submitted, setSubmitted] = useState(!!finished)
  const syncTimer = useRef(null)

  function runPreview() {
    setShowPreview(true)
    dispatch({ type: 'refresh' })
  }

  async function submit() {
    if (submitted || submitting) return
    setSubmitting(true)
    if (syncTimer.current) { clearTimeout(syncTimer.current); syncTimer.current = null }
    const payload = toFilePayload(sandpack.files)
    await syncSandbox(interviewId, payload)
    try {
      // await fetch(`/api/v1/interviews/${interviewId}/submit-assignment`, { ... })
      await submitAssignment(interviewId, { type: 'sandbox', files: payload })
    } catch { /* non-critical */ }
    setSubmitted(true)
    setSubmitting(false)
    if (onDone) onDone()
  }

  const filesRef = useRef(sandpack.files)
  useEffect(() => { filesRef.current = sandpack.files }, [sandpack.files])

  useEffect(() => {
    if (!interviewId) return
    if (syncTimer.current) clearTimeout(syncTimer.current)
    syncTimer.current = setTimeout(() => {
      syncSandbox(interviewId, toFilePayload(sandpack.files))
    }, 5000)
    return () => {
      if (syncTimer.current) clearTimeout(syncTimer.current)
    }
  }, [sandpack.files, interviewId])

  // Flush the latest files when the panel unmounts (agent toggles back to
  // interview mode) so edits since the last debounced sync survive the restore.
  useEffect(() => {
    return () => {
      if (!submitted) syncSandbox(interviewId, toFilePayload(filesRef.current))
    }
  }, [interviewId, submitted])

  function getCurrentCode() {
    return sandpack.files[sandpack.activeFile]?.code ?? ''
  }

  function insertCode(snippet) {
    const path = sandpack.activeFile
    const current = sandpack.files[path]?.code ?? ''
    sandpack.updateFile(path, `${current}\n\n${snippet}`)
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0, overflow: 'hidden' }}>
      {/* Top toolbar — stack info on the left, view toggles gathered top-right */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 12,
          padding: '8px 14px',
          borderBottom: '1px solid var(--color-border)',
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
            letterSpacing: '0.02em',
            color: 'var(--color-muted)',
          }}
        >
          <Icon name="code" size={13} />
          React · Tailwind CSS
        </span>
        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 8 }}>
          <button
            className="btn btn--primary"
            onClick={runPreview}
            disabled={submitted}
            style={{ height: 30, padding: '0 16px', fontSize: 12, borderRadius: 999 }}
            title="Reload the live preview"
          >
            <Icon name="refresh" size={13} />
            Run
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
            active={showPreview}
            onClick={() => setShowPreview((v) => !v)}
            icon={showPreview ? 'eye' : 'eye-off'}
            label="Preview"
            title={showPreview ? 'Hide live preview' : 'Show live preview'}
          />
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

      <div style={{ display: 'flex', flex: 1, minHeight: 0, overflow: 'hidden' }}>
        <SandpackLayout
          style={{
            flex: 1,
            height: '100%',
            minWidth: 0,
            borderRadius: 0,
            border: 'none',
            '--sp-layout-height': '100%',
            flexWrap: 'nowrap',
          }}
        >
          <SandpackCodeEditor
            showTabs
            showLineNumbers
            closableTabs
            readOnly={submitted}
            style={{ height: '100%', flex: 1, minWidth: 0 }}
          />
          {showPreview && (
            <SandpackPreview
              showNavigator={false}
              showRefreshButton
              style={{ height: '100%', flex: 1, minWidth: 0 }}
            />
          )}
        </SandpackLayout>

        {showAssistant && (
          <CodeAssistant
            interviewId={interviewId}
            enabled={ai && assistantEnabled}
            getCode={getCurrentCode}
            onInsertCode={insertCode}
          />
        )}
      </div>
    </div>
  )
}

export default function SandpackPanel({ interviewId, problem, aiEnabled, assistantEnabled = true, savedFiles = null, finished = false, onDone }) {
  const ai = aiEnabled ?? problem?.ai_assistant_enabled ?? true
  const diff = problem?.difficulty ?? 'medium'
  const diffStyle = DIFFICULTY_STYLE[diff] ?? DIFFICULTY_STYLE.medium
  const files = normalizeFiles(problem?.starter_files, savedFiles)
  const visibleFiles = Object.keys(files).filter((p) => !p.includes('index.html'))

  return (
    <div style={{ display: 'flex', height: '100%', overflow: 'hidden' }}>
      {problem && (
        <div
          style={{
            width: 280,
            flexShrink: 0,
            borderRight: '1px solid var(--color-border)',
            overflowY: 'auto',
            padding: '20px 16px',
            fontSize: 13,
            lineHeight: 1.7,
          }}
        >
          <div
            style={{
              fontSize: 10,
              color: 'var(--color-muted)',
              textTransform: 'uppercase',
              letterSpacing: '0.1em',
              marginBottom: 12,
            }}
          >
            Project Assignment
          </div>
          <div
            style={{
              margin: '0 0 10px',
              color: 'var(--color-text)',
              fontSize: 15,
              fontWeight: 700,
            }}
          >
            {problem.title ?? 'Project'}
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 16 }}>
            <span
              style={{
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
            <span
              style={{
                padding: '2px 8px',
                borderRadius: 4,
                fontSize: 10,
                fontWeight: 700,
                letterSpacing: '0.06em',
                background: 'rgba(255,255,255,0.06)',
                color: 'var(--color-muted)',
              }}
            >
              PROJECT
            </span>
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
                background: 'rgba(190,18,60,0.1)',
                color: 'var(--color-accent)',
              }}
            >
              <Icon name="spark" size={10} />
              AI ASSISTANT ON
            </span>
          </div>
          <Markdown>{problem.statement ?? ''}</Markdown>
        </div>
      )}

      <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <SandpackProvider
          template="react"
          files={files}
          theme="dark"
          style={{ height: '100%', width: '100%', display: 'flex', flexDirection: 'column' }}
          customSetup={{
            externalResources: ['https://cdn.tailwindcss.com'],
          }}
          options={{
            activeFile: '/App.js',
            visibleFiles,
          }}
        >
          <SandpackContent
            interviewId={interviewId}
            ai={ai}
            assistantEnabled={assistantEnabled}
            finished={finished}
            onDone={onDone}
          />
        </SandpackProvider>
      </div>
    </div>
  )
}
