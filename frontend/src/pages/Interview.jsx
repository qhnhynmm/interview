import { useRef, useState } from 'react'
import { Icon, Spinner } from '../components/icons.jsx'
import { ReasoningStream } from '../components/ReasoningStream.jsx'
import SchedulerModal from '../components/SchedulerModal.jsx'
import { EMPTY } from '../constants/interview.js'

function fmtScheduled(isoStr) {
  const d = new Date(isoStr)
  return d.toLocaleString('en-US', {
    month: 'short',
    day: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).replace(',', ' ·')
}

function isNowSlot(isoStr) {
  const diff = new Date(isoStr) - Date.now()
  // Live only after the scheduled time has arrived (plus 18 min window).
  // A 2-min lead gives the browser time to render before the clock ticks over.
  return diff >= -18 * 60 * 1000 && diff <= 2 * 60 * 1000
}

export default function Interview({ onCreate }) {
  const [form, setForm] = useState(EMPTY)
  const [created, setCreated] = useState(null)
  const [copied, setCopied] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [showScheduler, setShowScheduler] = useState(false)
  const fileRef = useRef(null)
  // The link is revealed only once BOTH the API result is in AND the mock
  // reasoning flow has finished narrating (the API call is usually faster than
  // the animation). Whichever finishes last triggers the reveal. Refs, not
  // state, so the two async completion points coordinate without an effect.
  const recordRef = useRef(null)
  const reasoningDoneRef = useRef(false)

  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }))
  const valid = form.candidateName.trim() && form.email.trim() && form.role.trim() && form.jd.trim() && form.requests.trim() && form.cvFile

  function reveal(record) {
    setCreated(record)
    setCopied(false)
    setForm(EMPTY)
    if (fileRef.current) fileRef.current.value = ''
    setLoading(false)
    recordRef.current = null
    reasoningDoneRef.current = false
  }

  function handleReasoningComplete() {
    reasoningDoneRef.current = true
    if (recordRef.current) reveal(recordRef.current)
  }

  async function submitWithSlot(scheduledAt) {
    setShowScheduler(false)
    setError(null)
    recordRef.current = null
    reasoningDoneRef.current = false
    setLoading(true)
    const resolvedAt = scheduledAt === 'instant' ? new Date().toISOString() : scheduledAt
    try {
      const record = await onCreate({ ...form, scheduledAt: resolvedAt })
      // Park the result; reveal only after the reasoning flow finishes too.
      recordRef.current = record
      if (reasoningDoneRef.current) reveal(record)
    } catch (err) {
      // On failure there's nothing to narrate toward — stop immediately.
      setError(err.message)
      setLoading(false)
    }
  }

  function handleSubmit(e) {
    e.preventDefault()
    if (!valid || loading) return
    setShowScheduler(true)
  }

  function copyLink() {
    if (!created) return
    navigator.clipboard?.writeText(created.meetingLink)
    setCopied(true)
  }

  const linkIsLive = created && isNowSlot(created.scheduledAt || created.scheduledLabel)

  return (
    <div className="page container">
      {showScheduler && (
        <SchedulerModal
          onConfirm={submitWithSlot}
          onCancel={() => setShowScheduler(false)}
        />
      )}

      <div className="section-head">
        <span className="eyebrow">
          <Icon name="video" size={14} /> New interview
        </span>
        <h1>Create a virtual interview</h1>
        <p>
          Provide the candidate details, the job description and any special
          requests. Aurelia will plan the session and generate a meeting link with
          a scheduled time.
        </p>
      </div>

      <div className="layout-2">
        {/* Form */}
        <form className="card form-card" onSubmit={handleSubmit}>
          <div className="grid-2">
            <div className="field">
              <label>
                Candidate name <span className="req">*</span>
              </label>
              <input
                className="input"
                placeholder="e.g. Tran Minh Anh"
                value={form.candidateName}
                onChange={set('candidateName')}
              />
            </div>
            <div className="field">
              <label>Candidate email <span className="req">*</span></label>
              <input
                className="input"
                type="email"
                placeholder="candidate@email.com"
                value={form.email}
                onChange={set('email')}
              />
            </div>
          </div>

          <div className="grid-2">
            <div className="field">
              <label>
                Role / Position <span className="req">*</span>
              </label>
              <input
                className="input"
                placeholder="e.g. Backend Engineer"
                value={form.role}
                onChange={set('role')}
              />
            </div>
            <div className="field">
              <label>Seniority</label>
              <select
                className="select"
                value={form.seniority}
                onChange={set('seniority')}
              >
                <option>Intern</option>
                <option>Junior</option>
                <option>Mid</option>
                <option>Senior</option>
                <option>Lead</option>
              </select>
            </div>
          </div>

          <div className="grid-2">
            <div className="field">
              <label>Interview language</label>
              <select
                className="select"
                value={form.language}
                onChange={set('language')}
              >
                <option value="en">English</option>
                <option value="vi">Tiếng Việt</option>
              </select>
              <span className="hint">
                The interview is conducted in this language.
              </span>
            </div>
          </div>

          <div className="field">
            <label>Candidate CV <span className="req">*</span></label>
            <input
              ref={fileRef}
              className="input"
              type="file"
              accept=".pdf,.docx,.txt"
              onChange={(e) =>
                setForm((f) => ({ ...f, cvFile: e.target.files?.[0] ?? null }))
              }
            />
            <span className="hint">PDF, DOCX or TXT</span>
          </div>

          <div className="field">
            <label>
              Job description (JD) <span className="req">*</span>
            </label>
            <textarea
              className="textarea"
              placeholder="Paste the job description here…"
              value={form.jd}
              onChange={set('jd')}
            />
          </div>

          <div className="field">
            <label>Special requests <span className="req">*</span></label>
            <textarea
              className="textarea"
              style={{ minHeight: 90 }}
              placeholder="Anything Aurelia should focus on — system design depth, culture fit, specific tech…"
              value={form.requests}
              onChange={set('requests')}
            />
          </div>

          {error && (
            <div
              style={{
                padding: '10px 14px',
                borderRadius: 8,
                background: 'rgba(255,80,80,0.08)',
                border: '1px solid rgba(255,80,80,0.3)',
                color: '#ff6b6b',
                fontSize: 13,
              }}
            >
              {error}
            </div>
          )}

          <div className="form-actions">
            <button
              className="btn btn--primary"
              type="submit"
              disabled={!valid || loading}
            >
              {loading ? (
                <>
                  <Spinner size={18} /> Generating…
                </>
              ) : (
                <>
                  <Icon name="calendar" size={18} /> Pick a slot &amp; generate
                </>
              )}
            </button>
            <span className="hint">
              {valid
                ? 'Choose a time slot, then Aurelia builds the plan.'
                : 'All fields marked * are required.'}
            </span>
          </div>
        </form>

        {/* Aside: created link */}
        <aside className="card aside-card">
          <h3>Generated session</h3>
          <p>The candidate-facing meeting link appears here.</p>

          {loading ? (
            <ReasoningStream
              role={form.role}
              seniority={form.seniority}
              candidateName={form.candidateName}
              onComplete={handleReasoningComplete}
            />
          ) : !created ? (
            <div className="empty">
              <div className="empty__icon">
                <Icon name="link" size={30} />
              </div>
              No interview created yet. Fill in the form and generate a link.
            </div>
          ) : (
            <div className="link-box">
              <div className="link-box__top">
                <Icon name="check" size={16} /> Interview ready for{' '}
                {created.candidateName}
              </div>

              <div className="link-row">
                <input className="input" readOnly value={created.meetingLink} />
                <button
                  type="button"
                  className="btn btn--ghost btn--sm"
                  onClick={copyLink}
                >
                  <Icon name={copied ? 'check' : 'copy'} size={15} />
                  {copied ? 'Copied' : 'Copy'}
                </button>
              </div>

              {/* Slot status */}
              {created.scheduledAt ? (
                <div style={{ marginTop: 12 }}>
                  {linkIsLive ? (
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'var(--on-tint)', fontWeight: 600, fontSize: 13 }}>
                      <span className="dot" />
                      Link is live — candidate can join now
                    </div>
                  ) : (
                    <div style={{ fontSize: 13, color: 'var(--muted)' }}>
                      <Icon name="clock" size={13} style={{ verticalAlign: 'middle', marginRight: 5 }} />
                      Link opens{' '}
                      <b style={{ color: 'var(--ink)' }}>
                        {fmtScheduled(created.scheduledAt)}
                      </b>
                      <div style={{ marginTop: 4, fontSize: 12, color: 'var(--muted)' }}>
                        Expires 15 min after start. Share with the candidate — it unlocks at the scheduled time.
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="meta-row">
                  <span>
                    <Icon name="clock" size={13} /> Scheduled
                  </span>
                  <b>{created.scheduledLabel}</b>
                </div>
              )}

              <div className="meta-row" style={{ marginTop: 8 }}>
                <span>Role</span>
                <b>
                  {created.role}
                  {created.seniority ? ` · ${created.seniority}` : ''}
                </b>
              </div>
            </div>
          )}
        </aside>
      </div>
    </div>
  )
}
