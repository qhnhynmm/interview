import { useEffect, useState } from 'react'
import { Icon, Spinner } from '@/components/icons.jsx'
import { fetchCandidate, subscribeToEvents } from '@/utils/interviews.js'
import { STATUS_LABEL } from '@/constants/candidate.js'
import '@/App.css'

function Section({ icon, title, action, children }) {
  return (
    <div className="card" style={{ padding: 20, marginBottom: 16 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 14 }}>
        <Icon name={icon} size={15} />
        <h3 style={{ margin: 0, fontSize: 14 }}>{title}</h3>
        {action && <div style={{ marginLeft: 'auto' }}>{action}</div>}
      </div>
      {children}
    </div>
  )
}

function Field({ label, value }) {
  return (
    <div style={{ marginBottom: 10 }}>
      <div style={{ fontSize: 10.5, textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--color-muted)', marginBottom: 2 }}>
        {label}
      </div>
      <div style={{ fontSize: 13.5, color: 'var(--color-text)' }}>{value ?? '—'}</div>
    </div>
  )
}

function ReportBlock({ report }) {
  const scores = report.competency_scores ?? []
  const overall = report.overall_score ?? 0
  const max = report.max_score ?? 5
  return (
    <>
      <div style={{
        display: 'flex', alignItems: 'baseline', gap: 6, marginBottom: 16,
        padding: '12px 16px', background: 'rgba(190,18,60,0.06)',
        border: '1px solid rgba(190,18,60,0.2)', borderRadius: 8,
      }}>
        <span style={{ fontSize: 30, fontWeight: 700, color: 'var(--color-accent)' }}>{overall}</span>
        <span style={{ color: 'var(--color-muted)' }}>/ {max}</span>
        <span style={{ marginLeft: 'auto', fontSize: 11, color: 'var(--color-muted)', textTransform: 'uppercase' }}>
          Overall score {report.is_mock && '· mock'}
        </span>
      </div>
      {scores.length > 0 && (
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--color-border)' }}>
              <th style={{ textAlign: 'left', padding: '6px 0', color: 'var(--color-muted)' }}>Competency</th>
              <th style={{ textAlign: 'right', padding: '6px 0', color: 'var(--color-muted)' }}>Weight</th>
              <th style={{ textAlign: 'right', padding: '6px 0', color: 'var(--color-muted)' }}>Score</th>
            </tr>
          </thead>
          <tbody>
            {scores.map((s, i) => (
              <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                <td style={{ padding: '8px 0' }}>{s.competency}</td>
                <td style={{ textAlign: 'right', color: 'var(--color-muted)' }}>{Math.round((s.weight ?? 0) * 100)}%</td>
                <td style={{ textAlign: 'right', color: 'var(--color-accent)', fontWeight: 600 }}>{s.score}/{max}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {report.interview_summary && (
        <p style={{ marginTop: 16, fontSize: 12.5, color: 'var(--color-muted)', lineHeight: 1.6 }}>
          {report.interview_summary}
        </p>
      )}
    </>
  )
}

const VIOLATION_KW = [
  'warning', 'cheat', 'violation', 'detected', 'suspicious', 'looking away',
  'please refrain', 'reminder', 'vi phạm', 'gian lận', 'nhắc nhở', 'cảnh báo', 'phát hiện',
]

function isWarning(content) {
  const lower = (content || '').toLowerCase()
  return VIOLATION_KW.some((kw) => lower.includes(kw))
}

export default function CandidateProfile({ candidateId }) {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    fetchCandidate(candidateId)
      .then(setData)
      .catch((e) => setError(e.message))
  }, [candidateId])

  // Subscribe to SSE while the report is being generated; auto-refresh on ready.
  useEffect(() => {
    if (!data || data.status !== 'evaluating') return
    return subscribeToEvents(candidateId, (msg) => {
      if (msg.event === 'report_ready') {
        fetchCandidate(candidateId).then(setData).catch(() => {})
      }
    })
  }, [data?.status, candidateId])

  if (error) {
    return (
      <div className="page container" style={{ paddingTop: 40 }}>
        <a className="btn btn--ghost btn--sm" href="/">← Back</a>
        <p style={{ color: '#ff6b6b', marginTop: 20 }}>Could not load candidate: {error}</p>
      </div>
    )
  }

  if (!data) {
    return (
      <div className="page container" style={{ paddingTop: 40, color: 'var(--color-muted)' }}>
        Loading candidate…
      </div>
    )
  }

  const cv = data.cv_fields ?? {}
  const skills = Array.isArray(cv.skills) ? cv.skills : []
  const statusLabel = STATUS_LABEL[data.status] ?? data.status
  const scheduled = data.scheduled_at ? new Date(data.scheduled_at).toLocaleString('en-US', {
    month: 'short', day: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit', hour12: false,
  }) : '—'
  const transcript = Array.isArray(data.conversation_history) ? data.conversation_history : []

  return (
    <div className="page container" style={{ paddingTop: 28, paddingBottom: 48 }}>
      <a className="btn btn--ghost btn--sm" href="/?tab=result" style={{ marginBottom: 18 }}>← Back to results</a>

      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 24 }}>
        <div style={{
          width: 56, height: 56, borderRadius: '50%',
          background: 'rgba(190,18,60,0.1)', border: '2px solid var(--color-accent)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 20, fontWeight: 700, color: 'var(--color-accent)',
        }}>
          {(data.candidate_name || '?').slice(0, 1).toUpperCase()}
        </div>
        <div>
          <h1 style={{ margin: 0, fontSize: 22 }}>{data.candidate_name || 'Unknown candidate'}</h1>
          <div style={{ color: 'var(--color-muted)', fontSize: 14 }}>{data.position || '—'}</div>
        </div>
        <span className={`badge badge--${statusLabel.toLowerCase().replace(' ', '-')}`} style={{ marginLeft: 'auto' }}>
          <span className="dot" />{statusLabel}
        </span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) minmax(0, 1fr)', gap: 16 }}>
        {/* Left column */}
        <div>
          <Section icon="inbox" title="Candidate info">
            <Field label="Email" value={data.candidate_email} />
            <Field label="Language" value={data.language === 'vi' ? 'Tiếng Việt' : 'English'} />
            <Field label="Scheduled" value={scheduled} />
          </Section>

          <Section icon="doc" title="CV">
            <Field label="File" value={data.cv_filename} />
            {skills.length > 0 && (
              <div style={{ marginBottom: 12 }}>
                <div style={{ fontSize: 10.5, textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--color-muted)', marginBottom: 6 }}>
                  Skills
                </div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                  {skills.map((s, i) => (
                    <span key={i} style={{
                      fontSize: 11.5, padding: '3px 9px', borderRadius: 999,
                      background: 'rgba(190,18,60,0.08)', border: '1px solid rgba(190,18,60,0.2)',
                      color: 'var(--color-accent)',
                    }}>{s}</span>
                  ))}
                </div>
              </div>
            )}
            {data.cv_text && (
              <details style={{ marginTop: 8 }}>
                <summary style={{ cursor: 'pointer', fontSize: 12.5, color: 'var(--color-muted)' }}>
                  View extracted CV text
                </summary>
                <pre style={{
                  marginTop: 10, padding: 12, background: 'var(--color-bg)', borderRadius: 8,
                  border: '1px solid var(--color-border)', fontSize: 12, lineHeight: 1.6,
                  color: 'var(--color-text)', whiteSpace: 'pre-wrap', maxHeight: 320, overflowY: 'auto',
                }}>{data.cv_text}</pre>
              </details>
            )}
          </Section>

          <Section icon="video" title="Interview recording">
            {data.recording_url ? (
              <>
                <video
                  src={data.recording_url}
                  controls
                  playsInline
                  preload="metadata"
                  style={{
                    width: '100%', borderRadius: 8, background: '#000',
                    border: '1px solid var(--color-border)', maxHeight: 380,
                  }}
                />
                <a
                  className="btn btn--ghost btn--sm"
                  href={data.recording_url}
                  target="_blank"
                  rel="noreferrer"
                  style={{ marginTop: 10 }}
                >
                  <Icon name="link" size={13} /> Open in new tab
                </a>
              </>
            ) : (
              <p style={{ margin: 0, fontSize: 12.5, color: 'var(--color-muted)' }}>
                No recording available yet.
              </p>
            )}
          </Section>
        </div>

        {/* Right column */}
        <div>
          <Section
            icon="doc"
            title="Evaluation report"
            action={data.report_pdf_url ? (
              <a
                className="btn btn--ghost btn--sm"
                href={data.report_pdf_url}
                target="_blank"
                rel="noreferrer"
                download
              >
                <Icon name="doc" size={13} /> Tải PDF
              </a>
            ) : null}
          >
            {data.status === 'evaluating' ? (
              <div style={{ textAlign: 'center', padding: '32px 0', color: 'var(--color-muted)' }}>
                <Spinner size={26} />
                <p style={{ marginTop: 12, fontSize: 13 }}>Generating evaluation report…</p>
              </div>
            ) : data.report ? (
              <ReportBlock report={data.report} />
            ) : (
              <p style={{ margin: 0, fontSize: 12.5, color: 'var(--color-muted)' }}>
                Report not generated yet.
              </p>
            )}
          </Section>

          <Section icon="chat" title={`Transcript${transcript.length ? ` · ${transcript.length} turns` : ''}`}>
            {transcript.length === 0 ? (
              <p style={{ margin: 0, fontSize: 12.5, color: 'var(--color-muted)' }}>No transcript recorded.</p>
            ) : (
              <div style={{ maxHeight: 420, overflowY: 'auto' }}>
                {transcript.map((t, i) => {
                  const isViolationWarning = t.role === 'agent' && isWarning(t.content)
                  return (
                    <div key={i} style={{ marginBottom: 12 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 3 }}>
                        <span style={{
                          fontSize: 11, fontWeight: 600,
                          color: t.role === 'agent' ? 'var(--color-accent)' : 'var(--color-muted)',
                        }}>
                          {t.role === 'agent' ? 'Interviewer' : 'Candidate'}
                        </span>
                        {t.timestamp && (
                          <span style={{ fontSize: 10, color: 'var(--color-muted)' }}>
                            · {new Date(t.timestamp).toLocaleTimeString('en-US', { hour12: false })}
                          </span>
                        )}
                        {isViolationWarning && (
                          <span style={{
                            fontSize: 10, fontWeight: 600,
                            color: 'var(--color-accent)', opacity: 0.7,
                          }}>
                            ⚠ Violation notice
                          </span>
                        )}
                      </div>
                      <div style={{
                        fontSize: 13, lineHeight: 1.6, whiteSpace: 'pre-wrap',
                        background: isViolationWarning ? 'rgba(190,18,60,0.09)' : 'transparent',
                        borderRadius: isViolationWarning ? 4 : 0,
                        padding: isViolationWarning ? '2px 4px' : 0,
                      }}>
                        {t.content}
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </Section>
        </div>
      </div>
    </div>
  )
}
