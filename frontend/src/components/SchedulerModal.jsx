import { useCallback, useEffect, useRef, useState } from 'react'
import { fetchSlots } from '../utils/interviews.js'
import { Icon, Spinner } from './icons.jsx'

// Only show slots in the working window [06:30, 11:45] local time.
const WORK_START = 6 * 60 + 30
const WORK_END   = 23 * 60 + 45

function inWorkHours(isoStr) {
  const d = new Date(isoStr)
  const m = d.getHours() * 60 + d.getMinutes()
  return m >= WORK_START && m <= WORK_END
}

// Before 04:00 counts as the previous calendar day.
function getEffectiveToday() {
  const now = new Date()
  if (now.getHours() < 4) {
    const prev = new Date(now)
    prev.setDate(now.getDate() - 1)
    prev.setHours(0, 0, 0, 0)
    return prev
  }
  const d = new Date(now)
  d.setHours(0, 0, 0, 0)
  return d
}

function isSameDay(a, b) {
  return a.toDateString() === b.toDateString()
}

function startOfDay(date) {
  const d = new Date(date)
  d.setHours(0, 0, 0, 0)
  return d
}

function fmtTime(isoStr) {
  return new Date(isoStr).toLocaleTimeString('en-US', {
    hour: '2-digit', minute: '2-digit', hour12: false,
  })
}

function slotLabel(slot) {
  if (!slot.available) return 'Full'
  if (slot.active_count === 0) return 'Open'
  return 'Available'
}

function slotColor(slot) {
  if (!slot.available) return 'slot--full'
  if (slot.active_count === 0) return 'slot--open'
  if (slot.active_count === 1) return 'slot--busy1'
  return 'slot--busy2'
}

function isNearNow(isoStr) {
  const diff = new Date(isoStr) - Date.now()
  return diff >= 0 && diff <= 35 * 60 * 1000
}

// ── Mini calendar ─────────────────────────────────────────────────────────────

function MiniCalendar({ selected, onSelect }) {
  const effectiveToday = getEffectiveToday()
  const maxDate = new Date(effectiveToday)
  maxDate.setDate(effectiveToday.getDate() + 13)

  const [viewYear, setViewYear] = useState(effectiveToday.getFullYear())
  const [viewMonth, setViewMonth] = useState(effectiveToday.getMonth())

  const firstDow = new Date(viewYear, viewMonth, 1).getDay()
  const daysInMonth = new Date(viewYear, viewMonth + 1, 0).getDate()

  const cells = []
  for (let i = 0; i < firstDow; i++) cells.push(null)
  for (let d = 1; d <= daysInMonth; d++) cells.push(new Date(viewYear, viewMonth, d))

  const canPrev = viewYear > effectiveToday.getFullYear()
    || (viewYear === effectiveToday.getFullYear() && viewMonth > effectiveToday.getMonth())
  const canNext = viewYear < maxDate.getFullYear()
    || (viewYear === maxDate.getFullYear() && viewMonth < maxDate.getMonth())

  function prevMonth() {
    if (!canPrev) return
    if (viewMonth === 0) { setViewYear(y => y - 1); setViewMonth(11) }
    else setViewMonth(m => m - 1)
  }
  function nextMonth() {
    if (!canNext) return
    if (viewMonth === 11) { setViewYear(y => y + 1); setViewMonth(0) }
    else setViewMonth(m => m + 1)
  }

  const monthLabel = new Date(viewYear, viewMonth, 1)
    .toLocaleDateString('en-US', { month: 'long', year: 'numeric' })

  return (
    <div className="mini-cal">
      <div className="mini-cal-nav">
        <button className="mini-cal-arrow" disabled={!canPrev} onClick={prevMonth}>
          <Icon name="arrow" size={13} style={{ transform: 'scaleX(-1)' }} />
        </button>
        <span className="mini-cal-month">{monthLabel}</span>
        <button className="mini-cal-arrow" disabled={!canNext} onClick={nextMonth}>
          <Icon name="arrow" size={13} />
        </button>
      </div>
      <div className="mini-cal-grid">
        {['Su','Mo','Tu','We','Th','Fr','Sa'].map(d => (
          <div key={d} className="mini-cal-dow">{d}</div>
        ))}
        {cells.map((day, i) => {
          if (!day) return <div key={`e${i}`} className="mini-cal-day mini-cal-day--empty" />
          const isPast    = day < effectiveToday
          const isBeyond  = day > maxDate
          const isDisabled = isPast || isBeyond
          const isToday   = isSameDay(day, effectiveToday)
          const isSel     = isSameDay(day, selected)
          const inRange   = !isPast && !isBeyond && !isSel && !isToday

          return (
            <button
              key={day.toISOString()}
              disabled={isDisabled}
              className={[
                'mini-cal-day',
                isToday    ? 'mini-cal-day--today'    : '',
                isSel      ? 'mini-cal-day--selected' : '',
                inRange    ? 'mini-cal-day--in-range' : '',
                isDisabled ? 'mini-cal-day--disabled' : '',
              ].filter(Boolean).join(' ')}
              onClick={() => !isDisabled && onSelect(startOfDay(day))}
            >
              {day.getDate()}
            </button>
          )
        })}
      </div>
    </div>
  )
}

// ── Main modal ────────────────────────────────────────────────────────────────

export default function SchedulerModal({ onConfirm, onCancel }) {
  const effectiveToday = getEffectiveToday()

  const [selectedDate, setSelectedDate] = useState(effectiveToday)
  const [slots, setSlots] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selected, setSelected] = useState(null)
  const [instantAvailable, setInstantAvailable] = useState(false)
  const overlayRef = useRef(null)

  const loadSlots = useCallback((date) => {
    setLoading(true)
    setError(null)
    setSelected(null)
    const today = getEffectiveToday()
    const fromDate = isSameDay(date, today) ? null : startOfDay(date)
    fetchSlots(8, fromDate)
      .then((data) => {
        const filtered = (data.slots || []).filter(s =>
          inWorkHours(s.start) && isSameDay(new Date(s.start), date)
        )
        setSlots(filtered)
        setInstantAvailable(!!data.instant_available)
        const first = filtered.find(s => s.available)
        if (first) setSelected(first.start)
      })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { loadSlots(selectedDate) }, [selectedDate, loadSlots])

  const selectedSlot = slots.find(s => s.start === selected)

  return (
    <div className="sched-overlay" ref={overlayRef}
      onClick={e => e.target === overlayRef.current && onCancel()}>
      <div className="sched-modal" role="dialog" aria-modal="true">

        <div className="sched-header">
          <div>
            <h3 className="sched-title">
              <Icon name="calendar" size={18} /> Schedule interview
            </h3>
            <p className="sched-sub">Pick a date · working hours 06:30–23:45</p>
          </div>
          <button className="sched-close" onClick={onCancel} aria-label="Close">
            <Icon name="x" size={18} />
          </button>
        </div>

        <div className="sched-content">
          <div className="sched-cal-panel">
            <MiniCalendar selected={selectedDate} onSelect={setSelectedDate} />
          </div>

          <div className="sched-slots-panel">
            {loading && (
              <div className="sched-loading"><Spinner size={22} /> Loading…</div>
            )}
            {error && (
              <div className="sched-error"><Icon name="x" size={14} /> {error}</div>
            )}
            {!loading && !error && slots.length === 0 && (
              <div className="sched-loading" style={{ color: 'var(--color-muted)' }}>
                No slots available for this day.
              </div>
            )}
            {!loading && !error && slots.length > 0 && (
              <div className="sched-slots">
                {slots.map(s => (
                  <button
                    key={s.start}
                    disabled={!s.available}
                    onClick={() => s.available && setSelected(s.start)}
                    className={[
                      'sched-slot',
                      slotColor(s),
                      selected === s.start ? 'sched-slot--selected' : '',
                      isNearNow(s.start) && s.available ? 'sched-slot--now' : '',
                    ].filter(Boolean).join(' ')}
                  >
                    <span className="sched-slot-time">{fmtTime(s.start)}</span>
                    <span className="sched-slot-status">{slotLabel(s)}</span>
                    {isNearNow(s.start) && s.available && (
                      <span className="sched-slot-now-tag">Now</span>
                    )}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="sched-footer">
          <div className="sched-legend">
            <span className="sched-legend-dot sched-legend-dot--open" /> Open
            <span className="sched-legend-dot sched-legend-dot--busy" /> Busy
            <span className="sched-legend-dot sched-legend-dot--full" /> Full
          </div>
          <div className="sched-footer-actions">
            <button
              className="btn btn--primary btn--sm"
              disabled={!selected}
              onClick={() => selected && onConfirm(selected)}
            >
              <Icon name="check" size={15} />
              {selectedSlot ? `Schedule ${fmtTime(selectedSlot.start)}` : 'Select a slot'}
            </button>
            {instantAvailable ? (
              <button
                className="btn btn--ghost btn--sm"
                onClick={() => onConfirm('instant')}
                title="Creates a link that opens immediately and expires in 15 minutes"
              >
                <Icon name="zap" size={14} />
                Instant link
              </button>
            ) : (
              <span className="sched-full-note">Full session. Please wait!</span>
            )}
            <button className="btn btn--danger btn--sm" onClick={onCancel}>
              Cancel
            </button>
          </div>
        </div>

      </div>
    </div>
  )
}
