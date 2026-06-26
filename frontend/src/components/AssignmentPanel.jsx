import dynamic from 'next/dynamic'

const CodePanel = dynamic(() => import('./CodePanel.jsx'), { ssr: false })
const CognitivePanel = dynamic(() => import('./CognitivePanel.jsx'), { ssr: false })
const SandpackPanel = dynamic(() => import('./SandpackPanel.jsx'), { ssr: false })

// Normalize whatever assignment shape we have into { type, coding, cognitive }.
// Accepts the structured Assignment object, or a legacy coding_assignment that
// only carries the coding fields (back-compat with interview.plan).
function normalize(assignment, fallbackProblem) {
  if (assignment?.type === 'cognitive') {
    return { type: 'cognitive', cognitive: assignment.cognitive }
  }
  if (assignment?.type === 'coding') {
    return { type: 'coding', coding: assignment.coding }
  }
  if (fallbackProblem) {
    return { type: 'coding', coding: fallbackProblem }
  }
  return null
}

export default function AssignmentPanel({
  interviewId,
  assignment,
  fallbackProblem,
  assistantEnabled = true,
  savedCode = null,
  savedFiles = null,
  savedAnswers = null,
  finished = false,
  onDone,
}) {
  const norm = normalize(assignment, fallbackProblem)

  if (!norm) {
    return (
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <span style={{ color: 'var(--color-muted)', fontSize: 13 }}>
          No assignment available yet.
        </span>
      </div>
    )
  }

  if (norm.type === 'cognitive') {
    return (
      <CognitivePanel
        interviewId={interviewId}
        test={norm.cognitive}
        savedAnswers={savedAnswers}
        finished={finished}
        onDone={onDone}
      />
    )
  }

  if (norm.coding?.mode === 'project') {
    return (
      <SandpackPanel
        interviewId={interviewId}
        problem={norm.coding}
        aiEnabled={norm.coding?.ai_assistant_enabled}
        assistantEnabled={assistantEnabled}
        savedFiles={savedFiles}
        finished={finished}
        onDone={onDone}
      />
    )
  }

  return (
    <CodePanel
      interviewId={interviewId}
      problem={norm.coding}
      mode={norm.coding?.mode}
      aiEnabled={norm.coding?.ai_assistant_enabled}
      assistantEnabled={assistantEnabled}
      savedCode={savedCode}
      finished={finished}
      onDone={onDone}
    />
  )
}
