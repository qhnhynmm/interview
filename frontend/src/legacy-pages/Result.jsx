'use client'

import { useMemo, useState } from 'react'
import { Icon, Spinner } from '@/components/icons.jsx'

// Compute the live display status for a row.
// Scheduled → In Progress once the slot time arrives;
// everything else is taken as-is from the normalized value.
function displayStatus(r) {
  if (r.status === 'Scheduled' && r.scheduledAt && r.scheduledAt <= new Date()) {
    return 'In Progress'
  }
  return r.status
}

function initials(name) {
  return name
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0])
    .join('')
    .toUpperCase()
}

function ReportModal({ report, onClose }) {
  const scores = report.competency_scores ?? []
  const overall = report.overall_score ?? 0
  const max = report.max_score ?? 5

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0,0,0,0.6)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
        padding: 24,
      }}
      onClick={onClose}
    >
      <div
        style={{
          background: 'var(--color-surface)',
          border: '1px solid var(--color-border)',
          borderRadius: 12,
          padding: 28,
          maxWidth: 560,
          width: '100%',
          maxHeight: '80vh',
          overflowY: 'auto',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'flex-start',
            marginBottom: 20,
          }}
        >
          <div>
            <div
              style={{
                fontSize: 11,
                textTransform: 'uppercase',
                letterSpacing: 1,
                color: 'var(--color-muted)',
                marginBottom: 4,
              }}
            >
              Evaluation Report {report.is_mock && '· mock'}
            </div>
            <h2 style={{ margin: 0, fontSize: 18 }}>{report.candidate_name}</h2>
            <div style={{ color: 'var(--color-muted)', fontSize: 13 }}>
              {report.position}
            </div>
          </div>
          <button
            className="btn btn--ghost btn--sm"
            onClick={onClose}
            style={{ marginTop: -4 }}
          >
            ✕
          </button>
        </div>

        <div
          style={{
            display: 'flex',
            alignItems: 'baseline',
            gap: 6,
            marginBottom: 20,
            padding: '12px 16px',
            background: 'rgba(190,18,60,0.06)',
            border: '1px solid rgba(190,18,60,0.2)',
            borderRadius: 8,
          }}
        >
          <span style={{ fontSize: 32, fontWeight: 700, color: 'var(--color-accent)' }}>
            {overall}
          </span>
          <span style={{ color: 'var(--color-muted)' }}>/ {max}</span>
          <span
            style={{
              marginLeft: 'auto',
              fontSize: 12,
              color: 'var(--color-muted)',
              textTransform: 'uppercase',
            }}
          >
            Overall score
          </span>
        </div>

        {scores.length > 0 && (
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--color-border)' }}>
                <th style={{ textAlign: 'left', padding: '6px 0', color: 'var(--color-muted)' }}>
                  Competency
                </th>
                <th style={{ textAlign: 'right', padding: '6px 0', color: 'var(--color-muted)' }}>
                  Weight
                </th>
                <th style={{ textAlign: 'right', padding: '6px 0', color: 'var(--color-muted)' }}>
                  Score
                </th>
              </tr>
            </thead>
            <tbody>
              {scores.map((s, i) => (
                <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                  <td style={{ padding: '8px 0' }}>{s.competency}</td>
                  <td style={{ textAlign: 'right', color: 'var(--color-muted)' }}>
                    {Math.round(s.weight * 100)}%
                  </td>
                  <td
                    style={{
                      textAlign: 'right',
                      color: 'var(--color-accent)',
                      fontWeight: 600,
                    }}
                  >
                    {s.score}/{max}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {report.interview_summary && (
          <p
            style={{
              marginTop: 16,
              fontSize: 12,
              color: 'var(--color-muted)',
              lineHeight: 1.6,
            }}
          >
            {report.interview_summary}
          </p>
        )}
      </div>
    </div>
  )
}

export default function Result({ interviews, loadError, loading, onNew, onRefresh }) {
  const [query, setQuery] = useState('')
  const [activeReport, setActiveReport] = useState(null)

  const rows = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return interviews
    return interviews.filter(
      (r) =>
        r.candidateName.toLowerCase().includes(q) ||
        r.role.toLowerCase().includes(q) ||
        r.id.toLowerCase().includes(q),
    )
  }, [interviews, query])

  const completed = interviews.filter((r) => r.status === 'Completed').length

  return (
    <div className="page container">
      {activeReport && (
        <ReportModal report={activeReport} onClose={() => setActiveReport(null)} />
      )}

      <div className="section-head">
        <span className="eyebrow">
          <Icon name="table" size={14} /> Results
        </span>
        <h2>Interviews & reports</h2>
        <p>
          Every interview link generated by Aurelia, with its scheduled time and
          the matching evaluation report once the session is complete.
        </p>
      </div>

      {loadError && (
        <div
          style={{
            padding: '10px 14px',
            borderRadius: 8,
            background: 'rgba(255,80,80,0.08)',
            border: '1px solid rgba(255,80,80,0.3)',
            color: '#ff6b6b',
            fontSize: 13,
            marginBottom: 16,
          }}
        >
          Could not load interviews: {loadError}
        </div>
      )}

      <div className="toolbar">
        <div className="search">
          <Icon name="search" size={17} />
          <input
            className="input"
            placeholder="Search by candidate, role or ID…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>
        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
          <span className={`hint${loading ? ' is-refreshing' : ''}`}>
            {loading ? 'Refreshing…' : `${completed}/${interviews.length} reports ready`}
          </span>
          <button
            className="btn btn--ghost btn--sm"
            onClick={onRefresh}
            disabled={loading}
          >
            {loading ? <Spinner size={15} /> : <Icon name="refresh" size={15} />} Refresh
          </button>
          <button className="btn btn--primary btn--sm" onClick={onNew}>
            <Icon name="video" size={16} /> New interview
          </button>
        </div>
      </div>

      <div className="card table-wrap">
        <table className="table">
          <thead>
            <tr>
              <th>Candidate</th>
              <th>Scheduled</th>
              <th>Meeting link</th>
              <th>Status</th>
              <th>Report</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td colSpan={5}>
                  <div className="empty" style={{ border: 'none' }}>
                    <div className="empty__icon">
                      {loading ? <Spinner size={28} /> : <Icon name="inbox" size={30} />}
                    </div>
                    {loading
                      ? 'Loading interviews…'
                      : query
                        ? `No interviews match "${query}".`
                        : 'No interviews yet.'}
                  </div>
                </td>
              </tr>
            ) : (
              rows.map((r) => (
                <tr key={r.id}>
                  <td>
                    <a
                      className="cand"
                      href={`/candidate/${r.id}`}
                      style={{ textDecoration: 'none', color: 'inherit', cursor: 'pointer' }}
                    >
                      <div className="avatar">{initials(r.candidateName)}</div>
                      <div>
                        <div className="cand__name">{r.candidateName}</div>
                        <div className="cand__role">
                          {r.role}
                          {r.seniority ? ` · ${r.seniority}` : ''}
                        </div>
                      </div>
                    </a>
                  </td>
                  <td>{r.scheduledLabel}</td>
                  <td>
                    <a
                      className="link-pill"
                      href={r.meetingLink}
                      target="_blank"
                      rel="noreferrer"
                    >
                      <Icon name="link" size={13} />
                      <span>{r.meetingLink.replace(/^https?:\/\//, '')}</span>
                    </a>
                  </td>
                  <td>
                    {(() => {
                      const s = displayStatus(r)
                      return (
                        <span className={`badge badge--${s.toLowerCase().replace(' ', '-')}`}>
                          {s === 'Completed'
                            ? <Icon name="check" size={11} />
                            : <span className="dot" />}
                          {s}
                        </span>
                      )
                    })()}
                  </td>
                  <td>
                    {r.rawReport ? (
                      <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
                        <button
                          className="report-link"
                          style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}
                          onClick={() => setActiveReport(r.rawReport)}
                        >
                          <Icon name="doc" size={15} />
                          Report
                          {r.score != null ? ` · ${r.score}/${r.maxScore}` : ''}
                        </button>
                      </div>
                    ) : (
                      <span className="report-muted">Pending…</span>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
