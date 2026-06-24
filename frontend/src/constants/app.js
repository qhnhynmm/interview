// App shell: top navigation tabs and live-refresh cadence.

export const TABS = [
  { id: 'home', label: 'Home', icon: 'home' },
  { id: 'interview', label: 'Interview', icon: 'video' },
  { id: 'result', label: 'Result', icon: 'table' },
]

// Auto-refresh the interview list every 20s while the Result tab is open, so
// status changes (in_progress → completed, new reports) appear without F5.
export const POLL_MS = 20000
