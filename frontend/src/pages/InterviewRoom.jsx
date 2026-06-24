import { useCallback, useEffect, useRef, useState } from 'react'
import { Icon, Spinner } from '@/components/icons.jsx'
import RULES from '@/data/interviewRules.json'
import AssignmentPanel from '@/components/AssignmentPanel.jsx'
import { useLiveKit } from '@/hooks/useLiveKit.js'
import { useCameraRecorder } from '@/hooks/useCameraRecorder.js'
import { useProctoring } from '@/hooks/useProctoring.js'
import { fetchInterview, uploadRecording, uploadChunk } from '@/utils/interviews.js'
import '@/App.css'

const INTRO_SECS = 15
const PROCTORING_DELAY_MS = 25000

// ── Mic button — shared between interview mode (large) and code-mode nav (compact) ──

function MicButton({ isLive, micMuted, micLocked, introSecsLeft, speaking, roomPhase, onToggle, audioBlocked, onEnableAudio, compact = false }) {
  const disabled = !isLive || roomPhase === 'final' || micLocked
  const introLocked = micLocked && introSecsLeft !== null && introSecsLeft > 0
  const lockTitle = introLocked ? `Mic unlocks in ${introSecsLeft}s` : 'Mic locked by proctoring warning'
  const lockText = introLocked ? `${introSecsLeft}s` : 'Locked'

  if (compact) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <button
          onClick={micLocked ? undefined : onToggle}
          disabled={disabled}
          title={micLocked ? lockTitle : micMuted ? 'Unmute mic' : 'Mute mic'}
          style={{
            display: 'inline-flex', alignItems: 'center', gap: 5,
            background: micLocked
              ? 'rgba(255,200,0,0.1)'
              : isLive && !micMuted
                ? 'rgba(190,18,60,0.12)'
                : 'rgba(255,255,255,0.06)',
            border: `1px solid ${micLocked
              ? 'rgba(255,200,0,0.4)'
              : isLive && !micMuted
                ? 'rgba(190,18,60,0.5)'
                : 'rgba(255,255,255,0.15)'}`,
            borderRadius: 20, padding: '4px 10px 4px 7px',
            color: micLocked ? '#ffd166' : isLive && !micMuted ? 'var(--color-accent)' : 'var(--color-muted)',
            cursor: disabled ? 'not-allowed' : 'pointer',
            fontSize: 11, fontWeight: 600,
            transition: 'all 0.2s',
            opacity: disabled && !micLocked ? 0.5 : 1,
          }}
        >
          <Icon name={micLocked || micMuted ? 'mute' : 'mic'} size={13} />
          {micLocked ? lockText : micMuted ? 'Muted' : speaking ? 'Speaking' : 'Live'}
        </button>
      </div>
    )
  }

  // Full-size circular mic button with countdown SVG ring
  const radius = 35
  const circumference = 2 * Math.PI * radius
  const progress = introSecsLeft != null ? introSecsLeft / INTRO_SECS : 0
  const dashOffset = circumference * (1 - progress)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12 }}>
      <div style={{ position: 'relative', width: 80, height: 80 }}>
        {introLocked && (
          <svg
            width="80" height="80" viewBox="0 0 80 80"
            style={{ position: 'absolute', inset: 0, transform: 'rotate(-90deg)', pointerEvents: 'none' }}
          >
            <circle cx="40" cy="40" r={radius} fill="none" stroke="rgba(255,200,0,0.12)" strokeWidth="3" />
            <circle
              cx="40" cy="40" r={radius} fill="none"
              stroke="#ffd166" strokeWidth="3" strokeLinecap="round"
              strokeDasharray={circumference}
              strokeDashoffset={dashOffset}
              style={{ transition: 'stroke-dashoffset 0.95s linear' }}
            />
          </svg>
        )}
        <button
          onClick={micLocked ? undefined : onToggle}
          disabled={disabled}
          style={{
            position: 'absolute',
            inset: micLocked ? 6 : 0,
            borderRadius: '50%',
            border: micLocked
              ? '2px solid rgba(255,200,0,0.35)'
              : isLive && !micMuted
                ? '2px solid var(--color-accent)'
                : '2px solid rgba(255,255,255,0.15)',
            background: micLocked
              ? 'rgba(255,200,0,0.07)'
              : isLive && !micMuted
                ? 'rgba(190,18,60,0.12)'
                : 'rgba(255,255,255,0.05)',
            color: micLocked ? '#ffd166' : isLive && !micMuted ? 'var(--color-accent)' : 'var(--color-muted)',
            cursor: disabled ? 'not-allowed' : 'pointer',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            flexDirection: 'column', gap: 2,
            transition: 'all 0.2s',
            boxShadow: !micLocked && speaking
              ? '0 0 0 8px rgba(190,18,60,0.08), 0 0 0 16px rgba(190,18,60,0.04)'
              : 'none',
            animation: !micLocked && speaking ? 'pulse 1.5s ease-in-out infinite' : 'none',
          }}
        >
          {micLocked ? (
            <>
              <Icon name="mute" size={20} />
              <span style={{ fontSize: 13, fontWeight: 800, lineHeight: 1 }}>{introLocked ? introSecsLeft : '!'}</span>
            </>
          ) : (
            <Icon name={isLive && !micMuted ? 'mic' : 'mute'} size={28} />
          )}
        </button>
      </div>

      <span style={{ fontSize: 12, color: 'var(--color-muted)' }}>
        {micLocked
          ? introLocked ? 'Mic opens in…' : 'Mic locked'
          : roomPhase === 'connecting'
            ? 'Connecting…'
            : micMuted
              ? 'Muted'
              : speaking
                ? 'Speaking…'
                : 'Live'}
      </span>

      {audioBlocked && isLive && !micLocked && (
        <button className="btn btn--ghost btn--sm" onClick={onEnableAudio} style={{ fontSize: 12 }}>
          <Icon name="volume" size={14} />
          Enable audio
        </button>
      )}
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

export default function InterviewRoom({ interviewId }) {
  const [phase, setPhase] = useState('loading')
  const [interview, setInterview] = useState(null)
  const [errMsg, setErrMsg] = useState('')
  const [agentReady, setAgentReady] = useState(false)
  const [qNum] = useState(0)
  const [qTotal] = useState(0)
  const [mode, setMode] = useState('interview')
  const [agentProblem, setAgentProblem] = useState(null)
  const [agentAssignment, setAgentAssignment] = useState(null)
  const [assistantEnabled, setAssistantEnabled] = useState(true)
  // Candidate's persisted assignment progress + submit lock. Kept here (above the
  // assignment panel) so a switch_mode('interview') -> switch_mode('code') toggle,
  // which remounts the panel, restores work instead of resetting the editor.
  const [savedCode, setSavedCode] = useState(null)
  const [savedFiles, setSavedFiles] = useState(null)
  const [savedAnswers, setSavedAnswers] = useState(null)
  const [assignmentFinished, setAssignmentFinished] = useState(false)
  const [rulesAccepted, setRulesAccepted] = useState(false)

  // 15-second intro: mic is locked while agent introduces itself
  const [introSecsLeft, setIntroSecsLeft] = useState(null)
  // Cheating detection starts only after 25s
  const [proctoringActive, setProctoringActive] = useState(false)
  const chatStartedRef = useRef(false)

  const onChunk = useCallback(async (blob) => {
    try { await uploadChunk(interviewId, blob) }
    catch (e) { console.warn('[recording] periodic chunk upload failed:', e) }
  }, [interviewId])

  const recorder = useCameraRecorder({ onChunk })
  const recorderRef = useRef(null)
  // Upload the recording exactly once, regardless of which end signal fires
  // first (control:end message, LiveKit disconnect, or unmount).
  const finalizedRef = useRef(false)

  useEffect(() => {
    recorderRef.current = recorder
  }, [recorder])

  // Stop the recorder and upload it. Idempotent via the once-guard, so whichever
  // end signal arrives first wins and the rest are no-ops. This decouples the
  // upload from the single best-effort control:end message — which is missed
  // when the agent auto-ends and the room tears down before the browser handles
  // it, leaving the recording un-uploaded.
  const finalizeRecording = useCallback(async () => {
    if (finalizedRef.current) return
    finalizedRef.current = true
    const rec = recorderRef.current
    if (!rec) return
    try {
      const blob = await rec.stop()
      if (blob) await uploadRecording(interviewId, blob)
    } catch (e) {
      console.error('[recording] finalize/upload failed:', e)
    }
  }, [interviewId])

  const handleDataMessage = useCallback((msg) => {
    if (msg.type === 'ui:switch_mode') {
      setMode(msg.mode)
      if (msg.problem) setAgentProblem(msg.problem)
      if (msg.assignment) setAgentAssignment(msg.assignment)
      if (typeof msg.finished === 'boolean') setAssignmentFinished(msg.finished)
      if (typeof msg.current_code === 'string') setSavedCode(msg.current_code)
      if (msg.sandbox_files) setSavedFiles(msg.sandbox_files)
      if (msg.cognitive_answers) setSavedAnswers(msg.cognitive_answers)
    } else if (msg.type === 'ui:coding_assistant') {
      setAgentAssignment((prev) =>
        prev?.coding
          ? { ...prev, coding: { ...prev.coding, ai_assistant_enabled: msg.enabled } }
          : prev,
      )
    } else if (msg.type === 'ui:agent_message' && msg.message) {
      setAgentReady(true)
    } else if (msg.type === 'ui:assistant_toggle') {
      setAssistantEnabled(!!msg.enabled)
    } else if (msg.type === 'control:end') {
      setPhase('saving')
      finalizeRecording().finally(() => setPhase('ended'))
    }
  }, [finalizeRecording])

  const livekit = useLiveKit(
    interviewId,
    phase === 'connecting' || phase === 'chatting' || phase === 'final',
    handleDataMessage,
    recorder.mixInTrack,
  )

  const roomPhase = phase === 'connecting' && livekit.status === 'connected' && (agentReady || livekit.agentJoined)
    ? 'chatting'
    : phase

  // Safety net: if the room drops after having connected (agent auto-ended, the
  // worker tore the room down, or a network drop), flush the recording before
  // it's lost — the control:end message may never reach the browser.
  const wasConnectedRef = useRef(false)
  useEffect(() => {
    if (livekit.status === 'connected') wasConnectedRef.current = true
    else if (wasConnectedRef.current && livekit.status === 'idle') {
      setPhase('saving')
      finalizeRecording().finally(() => setPhase('ended'))
    }
  }, [livekit.status, finalizeRecording])

  // Last resort: flush on page hide and on unmount (navigation away).
  useEffect(() => {
    const onHide = () => { finalizeRecording() }
    window.addEventListener('pagehide', onHide)
    return () => {
      window.removeEventListener('pagehide', onHide)
      finalizeRecording()
    }
  }, [finalizeRecording])

  // Cheating detection: delayed by 25s from when chatting begins
  useProctoring(
    interviewId,
    proctoringActive,
    recorder.stream,
    { gazeThresholdMs: 5000 },
  )

  // When the agent joins and chatting begins: start the 15s mic lock + 25s proctoring delay
  useEffect(() => {
    if (roomPhase !== 'chatting' || chatStartedRef.current) return
    chatStartedRef.current = true

    let remaining = INTRO_SECS
    setIntroSecsLeft(remaining)

    const countdownId = setInterval(() => {
      remaining -= 1
      setIntroSecsLeft(remaining)
      if (remaining <= 0) clearInterval(countdownId)
    }, 1000)

    const procTimerId = setTimeout(() => setProctoringActive(true), PROCTORING_DELAY_MS)

    return () => {
      clearInterval(countdownId)
      clearTimeout(procTimerId)
    }
  }, [roomPhase])

  useEffect(() => {
    fetchInterview(interviewId)
      .then((data) => {
        setInterview(data)
        if (typeof data.assistant_enabled === 'boolean') setAssistantEnabled(data.assistant_enabled)
        // Restore any persisted assignment progress (survives reload / reconnect).
        if (typeof data.current_code === 'string') setSavedCode(data.current_code)
        if (data.sandbox_files) setSavedFiles(data.sandbox_files)
        if (data.cognitive_answers) setSavedAnswers(data.cognitive_answers)
        if (typeof data.assignment_finished === 'boolean') setAssignmentFinished(data.assignment_finished)
        if (data.status === 'completed') setPhase('ended')
        else if (data.status === 'canceled') setPhase('expired')
        else if (data.status === 'scheduled' && data.scheduled_at && new Date(data.scheduled_at) > new Date()) setPhase('not_yet')
        else setPhase('ready')
      })
      .catch((e) => { setErrMsg(e.message); setPhase('error') })
  }, [interviewId])

  async function startInterview() {
    setErrMsg('')
    setAgentReady(false)
    const started = await recorder.start()
    if (!started) {
      setErrMsg('Camera access is required to join the interview. Please allow your camera and microphone, then try again.')
      return
    }
    setPhase('connecting')
  }

  // Called by any assignment panel when the candidate finishes the task
  function handleAssignmentDone() {
    setMode('interview')
    setAgentAssignment(null)
    setAgentProblem(null)
  }

  // ── Loading ──────────────────────────────────────────────────────────────────

  if (phase === 'loading') {
    return (
      <Shell interview={null}>
        <div style={centeredStyle}>
          <span style={{ color: 'var(--color-muted)', fontSize: 13 }}>Loading interview…</span>
        </div>
      </Shell>
    )
  }

  if (phase === 'not_yet' || (phase === 'connecting' && livekit.status === 'failed' && livekit.errorStatus === 403)) {
    const openAt = interview?.scheduled_at
      ? new Date(interview.scheduled_at).toLocaleString('en-US', { month: 'short', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false })
      : null
    return (
      <Shell interview={null}>
        <div style={{ ...centeredStyle, flexDirection: 'column', gap: 20, padding: '0 24px' }}>
          <div style={{ width: 56, height: 56, borderRadius: '50%', background: 'rgba(251,191,36,0.1)', border: '2px solid rgba(251,191,36,0.4)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fbbf24' }}>
            <Icon name="clock" size={24} />
          </div>
          <div style={{ textAlign: 'center', maxWidth: 360 }}>
            <p style={{ margin: '0 0 8px', fontSize: 15, fontWeight: 600, color: '#fbbf24' }}>It&apos;s not time yet</p>
            <p style={{ margin: 0, fontSize: 13, color: 'var(--color-muted)', lineHeight: 1.6 }}>Please make sure you join the meeting on time.</p>
            {openAt && <p style={{ margin: '8px 0 0', fontSize: 12, color: 'var(--color-muted)' }}>Scheduled for <strong style={{ color: 'var(--color-text)' }}>{openAt}</strong>.</p>}
          </div>
        </div>
      </Shell>
    )
  }

  if (phase === 'expired' || (phase === 'connecting' && livekit.status === 'failed' && livekit.errorStatus === 410)) {
    return (
      <Shell interview={null}>
        <div style={{ ...centeredStyle, flexDirection: 'column', gap: 20, padding: '0 24px' }}>
          <div style={{ width: 56, height: 56, borderRadius: '50%', background: 'rgba(156,163,175,0.08)', border: '2px solid rgba(156,163,175,0.3)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#9ca3af' }}>
            <Icon name="x" size={24} />
          </div>
          <div style={{ textAlign: 'center', maxWidth: 360 }}>
            <p style={{ margin: '0 0 8px', fontSize: 15, fontWeight: 600, color: '#9ca3af' }}>This meeting has expired</p>
            <p style={{ margin: 0, fontSize: 13, color: 'var(--color-muted)', lineHeight: 1.6 }}>The interview session is no longer available. Please contact your HR team to schedule a new interview.</p>
          </div>
        </div>
      </Shell>
    )
  }

  if (phase === 'error' || (phase === 'connecting' && livekit.status === 'failed')) {
    return (
      <Shell interview={null}>
        <div style={{ ...centeredStyle, flexDirection: 'column', gap: 20, padding: '0 24px' }}>
          <div style={{ width: 56, height: 56, borderRadius: '50%', background: 'rgba(255,80,80,0.1)', border: '2px solid rgba(255,80,80,0.4)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#ff6b6b' }}>
            <Icon name="x" size={24} />
          </div>
          <div style={{ textAlign: 'center', maxWidth: 340 }}>
            <p style={{ margin: '0 0 6px', fontSize: 15, fontWeight: 600, color: '#ff6b6b' }}>Unable to load interview</p>
            <p style={{ margin: 0, fontSize: 13, color: 'var(--color-muted)', lineHeight: 1.6 }}>{errMsg || 'Please notify the administrator.'}</p>
          </div>
        </div>
      </Shell>
    )
  }

  if (phase === 'saving') {
    return (
      <Shell interview={interview}>
        <div style={{ ...centeredStyle, flexDirection: 'column', gap: 16, padding: '0 24px' }}>
          <Spinner size={36} />
          <h2 style={{ margin: 0, textAlign: 'center' }}>Saving your session…</h2>
          <p style={{ color: 'var(--color-muted)', textAlign: 'center', margin: 0, fontSize: 14, maxWidth: 300 }}>
            Please keep this page open for a few seconds while we save your recording.
          </p>
        </div>
      </Shell>
    )
  }

  if (phase === 'ended') {
    return (
      <Shell interview={interview}>
        <div style={{ ...centeredStyle, flexDirection: 'column', gap: 16, padding: '0 24px' }}>
          <div style={avatarStyle(68)}><Icon name="check" size={30} /></div>
          <h2 style={{ margin: 0, textAlign: 'center' }}>Interview complete!</h2>
          <p style={{ color: 'var(--color-muted)', textAlign: 'center', margin: 0, fontSize: 14 }}>
            Thank you, <strong>{interview?.candidate_name}</strong>.<br />
            Your responses have been recorded.
          </p>
          <p style={{ color: 'var(--color-muted)', fontSize: 12, textAlign: 'center' }}>
            HR will review the evaluation and get back to you soon.
          </p>
        </div>
      </Shell>
    )
  }

  // ── Derived values ────────────────────────────────────────────────────────────

  const problem = agentProblem ?? interview?.plan?.coding_assignment ?? null
  const assignment = agentAssignment ?? interview?.assignment ?? null
  const waitingForAgent = phase === 'connecting' && roomPhase === 'connecting'
  const isLive = livekit.status === 'connected'
  const micMuted = livekit.muted
  const micLocked = (introSecsLeft !== null && introSecsLeft > 0) || livekit.forcedMicLocked

  // ── Code / assignment mode — mic moves to nav pane ───────────────────────────

  if (mode === 'code') {
    return (
      <Shell
        interview={interview}
        qNum={qNum}
        qTotal={qTotal}
        phase={roomPhase}
        livekit={livekit}
        recording={recorder.recording}
        selfStream={recorder.stream}
        micMuted={micMuted}
        micLocked={micLocked}
        introSecsLeft={introSecsLeft}
        isLive={isLive}
        onToggleMic={livekit.toggleMute}
        mode="code"
      >
        <AssignmentPanel
          key={assignment?.type ?? problem?.title ?? 'fallback'}
          interviewId={interviewId}
          assignment={assignment}
          fallbackProblem={problem}
          assistantEnabled={assistantEnabled}
          savedCode={savedCode}
          savedFiles={savedFiles}
          savedAnswers={savedAnswers}
          finished={assignmentFinished}
          onDone={handleAssignmentDone}
        />
      </Shell>
    )
  }

  // ── Interview voice mode ──────────────────────────────────────────────────────

  return (
    <Shell
      interview={interview}
      qNum={qNum}
      qTotal={qTotal}
      phase={roomPhase}
      livekit={livekit}
      recording={recorder.recording}
      selfStream={recorder.stream}
    >
      <div style={{ ...centeredStyle, flexDirection: 'column', gap: 32, padding: '32px 24px' }}>

        {phase === 'ready' && (
          <>
            <div style={avatarStyle(64)}>T</div>
            <div style={{ textAlign: 'center' }}>
              <h3 style={{ margin: '0 0 6px', fontSize: 18 }}>
                Welcome, {interview?.candidate_name || 'candidate'}
              </h3>
              <p style={{ margin: 0, color: 'var(--color-muted)', fontSize: 13 }}>
                {interview?.position}
              </p>
            </div>
            <button className="btn btn--primary" onClick={startInterview}>
              <Icon name="spark" size={16} />
              Start Interview
            </button>
            <p style={{ margin: 0, fontSize: 12, color: 'var(--color-muted)', display: 'flex', alignItems: 'center', gap: 6 }}>
              <Icon name="video" size={13} />
              Your camera and microphone will be recorded during the interview.
            </p>
            {errMsg && (
              <p style={{ margin: 0, fontSize: 12.5, color: '#ff6b6b', textAlign: 'center', maxWidth: 320 }}>
                {errMsg}
              </p>
            )}
          </>
        )}

        {(roomPhase === 'connecting' || roomPhase === 'chatting' || roomPhase === 'final') && (
          <>
            {waitingForAgent && (
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 14 }}>
                <div style={spinnerStyle} />
                <span style={{ fontSize: 13, color: 'var(--color-muted)' }}>
                  {livekit.status === 'connected' ? 'Waiting for interviewer…' : 'Connecting…'}
                </span>
              </div>
            )}

            {!waitingForAgent && (
              <MicButton
                isLive={isLive}
                micMuted={micMuted}
                micLocked={micLocked}
                introSecsLeft={introSecsLeft}
                speaking={livekit.speaking}
                roomPhase={roomPhase}
                onToggle={livekit.toggleMute}
                audioBlocked={livekit.audioBlocked}
                onEnableAudio={livekit.enableAudio}
              />
            )}
          </>
        )}
      </div>

      {phase === 'ready' && !rulesAccepted && (
        <RulesModal
          lang={interview?.language || 'en'}
          onConfirm={() => setRulesAccepted(true)}
          onExit={() => { window.location.href = '/' }}
        />
      )}

      <style>{`
        @keyframes pulse {
          0%, 100% { box-shadow: 0 0 0 6px rgba(190,18,60,0.08), 0 0 0 12px rgba(190,18,60,0.04); }
          50%        { box-shadow: 0 0 0 10px rgba(190,18,60,0.12), 0 0 0 20px rgba(190,18,60,0.06); }
        }
        @keyframes spin { to { transform: rotate(360deg); } }
      `}</style>
    </Shell>
  )
}

// ── Layout shell ──────────────────────────────────────────────────────────────

function SelfView({ stream }) {
  const ref = useRef(null)
  useEffect(() => {
    if (ref.current) ref.current.srcObject = stream
  }, [stream])
  return (
    <video
      ref={ref} autoPlay muted playsInline
      style={{
        position: 'fixed', bottom: 16, right: 16, width: 180, height: 120,
        borderRadius: 10, border: '1px solid var(--color-border)', objectFit: 'cover',
        background: '#000', zIndex: 50, boxShadow: '0 4px 20px rgba(0,0,0,0.45)',
      }}
    />
  )
}

// Self-view preview + a toggle to hide it. In code mode the fixed bottom-right
// video overlaps the coding-assistant input, so the candidate can collapse it.
// Recording is unaffected — only the on-screen preview is hidden.
function SelfViewDock({ stream }) {
  const [visible, setVisible] = useState(true)
  return (
    <>
      {visible && <SelfView stream={stream} />}
      <button
        onClick={() => setVisible((v) => !v)}
        title={visible ? 'Hide your camera preview' : 'Show your camera preview'}
        style={{
          position: 'fixed', right: 16, bottom: visible ? 142 : 16, zIndex: 51,
          display: 'inline-flex', alignItems: 'center', gap: 5,
          padding: '4px 10px', borderRadius: 20,
          background: 'rgba(0,0,0,0.6)', border: '1px solid var(--color-border)',
          color: 'var(--color-muted)', cursor: 'pointer', fontSize: 11, fontWeight: 600,
          backdropFilter: 'blur(4px)',
        }}
      >
        <Icon name="video" size={13} />
        {visible ? 'Hide camera' : 'Show camera'}
      </button>
    </>
  )
}

function Shell({
  interview, qNum, qTotal, phase, livekit, onSwitchMode, recording, selfStream, children,
  micMuted, micLocked, introSecsLeft, isLive, onToggleMic, mode,
}) {
  return (
    <div style={{ height: '100vh', background: 'var(--color-bg)', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      <header style={{
        borderBottom: '1px solid var(--color-border)',
        padding: '0 20px', height: 52,
        display: 'flex', alignItems: 'center', gap: 14,
        background: 'var(--color-surface)', flexShrink: 0,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
          <div style={{
            width: 26, height: 26, borderRadius: '50%',
            background: 'var(--color-accent)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            color: '#0a0e27', fontSize: 12, fontWeight: 700,
          }}>
            <Icon name="spark" size={13} />
          </div>
          <span style={{ fontWeight: 600, fontSize: 14 }}>Aurelia Interview</span>
        </div>

        {interview && (
          <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 14 }}>
            {recording && (
              <span style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: 11, color: '#ff6b6b' }}>
                <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#ff6b6b', animation: 'pulse 1.5s ease-in-out infinite' }} />
                Recording
              </span>
            )}
            {qTotal > 0 && (phase === 'chatting' || phase === 'final') && (
              <span style={{ fontSize: 11, color: 'var(--color-muted)' }}>Q {qNum} / {qTotal}</span>
            )}
            <span style={{ fontSize: 12, color: 'var(--color-muted)' }}>
              {interview.candidate_name} · {interview.position}
            </span>

            {/* Compact mic toggle — only in code/assignment mode */}
            {mode === 'code' && onToggleMic && (
              <MicButton
                compact
                isLive={isLive}
                micMuted={micMuted}
                micLocked={micLocked}
                introSecsLeft={introSecsLeft}
                speaking={livekit?.speaking}
                roomPhase={phase}
                onToggle={onToggleMic}
              />
            )}

            {onSwitchMode && (phase === 'chatting' || phase === 'final') && (
              <button className="btn btn--ghost btn--sm" onClick={onSwitchMode} style={{ fontSize: 11 }}>
                <Icon name="code" size={13} />
                Code
              </button>
            )}
            {livekit && (
              <span style={{
                display: 'flex', alignItems: 'center', gap: 5, fontSize: 11,
                color: livekit.status === 'connected'
                  ? 'var(--color-accent)'
                  : livekit.status === 'connecting' ? '#ffd166' : 'var(--color-muted)',
              }}>
                <span style={{
                  width: 7, height: 7, borderRadius: '50%',
                  background: livekit.status === 'connected'
                    ? 'var(--color-accent)'
                    : livekit.status === 'connecting' ? '#ffd166' : '#555',
                }} />
                {livekit.status === 'connected' ? 'Live' : livekit.status === 'connecting' ? 'Connecting…' : 'Offline'}
              </span>
            )}
          </div>
        )}
      </header>

      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        {children}
      </div>

      {selfStream && <SelfViewDock stream={selfStream} />}
    </div>
  )
}

// ── Rules modal ───────────────────────────────────────────────────────────────

function RulesModal({ lang = 'en', onConfirm, onExit }) {
  const r = RULES[lang] ?? RULES['en']
  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 200,
      background: 'rgba(0,0,0,0.78)', backdropFilter: 'blur(6px)',
      display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24,
    }}>
      <div style={{
        background: 'var(--color-surface)', border: '1px solid var(--color-border)',
        borderRadius: 16, padding: '28px 28px 24px', maxWidth: 460, width: '100%',
        boxShadow: '0 24px 64px rgba(0,0,0,0.55)',
      }}>
        <div style={{ textAlign: 'center', marginBottom: 22 }}>
          <div style={{
            width: 52, height: 52, borderRadius: '50%',
            background: 'rgba(190,18,60,0.1)', border: '2px solid var(--color-accent)',
            display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 12px',
          }}>
            <Icon name="doc" size={20} />
          </div>
          <h2 style={{ margin: '0 0 5px', fontSize: 17 }}>{r.title}</h2>
          <p style={{ margin: 0, fontSize: 12, color: 'var(--color-muted)' }}>{r.subtitle}</p>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 24 }}>
          {r.items.map((text, i) => (
            <div key={i} style={{
              display: 'flex', gap: 12, alignItems: 'flex-start',
              padding: '10px 14px', borderRadius: 8,
              background: 'rgba(255,255,255,0.03)', border: '1px solid var(--color-border)',
            }}>
              <span style={{
                flexShrink: 0, width: 22, height: 22, borderRadius: '50%',
                background: 'rgba(190,18,60,0.12)', border: '1px solid rgba(190,18,60,0.3)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 11, fontWeight: 700, color: 'var(--color-accent)',
              }}>{i + 1}</span>
              <span style={{ fontSize: 13, lineHeight: 1.55, color: 'var(--color-text)' }}>{text}</span>
            </div>
          ))}
        </div>

        <div style={{ display: 'flex', gap: 10 }}>
          <button className="btn btn--ghost btn--sm" onClick={onExit}>{r.exit}</button>
          <button className="btn btn--primary" onClick={onConfirm} style={{ flex: 1 }}>
            <Icon name="check" size={15} />
            {r.confirm}
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function avatarStyle(size) {
  return {
    width: size, height: size, borderRadius: '50%',
    background: 'rgba(190,18,60,0.1)', border: '2px solid var(--color-accent)',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    fontSize: size * 0.35, fontWeight: 700, color: 'var(--color-accent)',
  }
}

const spinnerStyle = {
  width: 42, height: 42, borderRadius: '50%',
  border: '3px solid rgba(255,255,255,0.14)',
  borderTopColor: 'var(--color-accent)',
  animation: 'spin 0.9s linear infinite',
}

const centeredStyle = {
  flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: 200,
}
