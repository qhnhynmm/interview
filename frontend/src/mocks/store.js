// In-memory mock store — persists for the browser session.

function daysAgo(n, hour = 10, minute = 0) {
  const d = new Date()
  d.setDate(d.getDate() - n)
  d.setHours(hour, minute, 0, 0)
  return d.toISOString()
}

function daysAhead(n, hour = 10, minute = 0) {
  const d = new Date()
  d.setDate(d.getDate() + n)
  d.setHours(hour, minute, 0, 0)
  return d.toISOString()
}

function minutesAgo(n) {
  return new Date(Date.now() - n * 60 * 1000).toISOString()
}

function meetingUrl(id) {
  const origin = typeof window !== 'undefined' ? window.location.origin : 'http://localhost:3000'
  return `${origin}/interview/${id}`
}

function buildReport(candidateName, position, overall) {
  return {
    overall_score: overall,
    max_score: 5,
    is_mock: true,
    candidate_name: candidateName,
    position,
    competency_scores: [
      { competency: 'Technical depth', weight: 0.3, score: Math.min(5, overall + 0.2) },
      { competency: 'Problem solving', weight: 0.25, score: overall },
      { competency: 'Communication', weight: 0.25, score: Math.max(1, overall - 0.3) },
      { competency: 'Culture fit', weight: 0.2, score: Math.min(5, overall + 0.1) },
    ],
    interview_summary:
      'Mock evaluation report. Candidate demonstrated solid fundamentals and clear communication. '
      + 'Recommend proceeding to the next round pending backend integration.',
  }
}

const MOCK_TRANSCRIPT = [
  { role: 'agent', content: 'Hello! Welcome to your technical interview. Could you briefly introduce yourself?', timestamp: daysAgo(1, 14, 0) },
  { role: 'candidate', content: 'Hi, I am a software engineer with 4 years of experience in backend systems.', timestamp: daysAgo(1, 14, 1) },
  { role: 'agent', content: 'Great. Let us start with a coding exercise — implement a function to find two numbers that sum to a target.', timestamp: daysAgo(1, 14, 3) },
  { role: 'candidate', content: 'I would use a hash map to store complements while iterating through the array.', timestamp: daysAgo(1, 14, 8) },
  { role: 'agent', content: 'Good approach. Please walk me through the time and space complexity.', timestamp: daysAgo(1, 14, 12) },
]

const MOCK_CODING_PROBLEM = {
  title: 'Two Sum',
  difficulty: 'medium',
  mode: 'dsa',
  ai_assistant_enabled: true,
  description:
    'Given an array of integers `nums` and an integer `target`, return indices of the two numbers such that they add up to `target`.\n\n'
    + 'You may assume each input has exactly one solution.',
  starter_code: '# Write your solution here\n\ndef two_sum(nums, target):\n    """Return indices of two numbers that add up to target."""\n    pass\n',
}

/** @type {{ id: number, username: string, email: string } | null} */
let currentUser = null

/** @type {Record<string, object>} */
const interviewDetails = {}

let nextInterviewNum = 2060

function seedInterviewDetail(id, overrides = {}) {
  const base = {
    id,
    candidate_name: overrides.candidate_name ?? 'Demo Candidate',
    candidate_email: overrides.candidate_email ?? 'candidate@demo.com',
    position: overrides.position ?? 'Software Engineer',
    language: overrides.language ?? 'en',
    status: overrides.status ?? 'scheduled',
    scheduled_at: overrides.scheduled_at ?? minutesAgo(5),
    meeting_url: meetingUrl(id),
    assistant_enabled: true,
    assignment_finished: false,
    current_code: null,
    sandbox_files: null,
    cognitive_answers: null,
    plan: { coding_assignment: MOCK_CODING_PROBLEM },
    assignment: null,
    ...overrides,
  }
  interviewDetails[id] = base
  return base
}

/** Backend-shaped interview list */
let interviews = [
  {
    id: 'itv-2041',
    candidate_name: 'Tran Minh Anh',
    candidate_email: 'minhanh.tran@email.com',
    position: 'Senior Backend Engineer',
    scheduled_at: daysAgo(3, 9, 30),
    meeting_url: meetingUrl('itv-2041'),
    status: 'completed',
    report: buildReport('Tran Minh Anh', 'Senior Backend Engineer', 4.3),
  },
  {
    id: 'itv-2038',
    candidate_name: 'Nguyen Hoang Long',
    candidate_email: 'long.nh@email.com',
    position: 'Data Scientist',
    scheduled_at: daysAgo(2, 14, 0),
    meeting_url: meetingUrl('itv-2038'),
    status: 'completed',
    report: buildReport('Nguyen Hoang Long', 'Data Scientist', 3.9),
  },
  {
    id: 'itv-2052',
    candidate_name: 'Le Thu Ha',
    candidate_email: 'ha.le@email.com',
    position: 'Frontend Engineer',
    scheduled_at: daysAhead(2, 10, 15),
    meeting_url: meetingUrl('itv-2052'),
    status: 'scheduled',
    report: null,
  },
  {
    id: 'itv-2047',
    candidate_name: 'Pham Quoc Bao',
    candidate_email: 'bao.pq@email.com',
    position: 'DevOps Engineer',
    scheduled_at: daysAgo(1, 16, 30),
    meeting_url: meetingUrl('itv-2047'),
    status: 'completed',
    report: buildReport('Pham Quoc Bao', 'DevOps Engineer', 4.6),
  },
  {
    id: 'itv-2055',
    candidate_name: 'Vo Thi Kim Ngan',
    candidate_email: 'ngan.vtk@email.com',
    position: 'Product Manager',
    scheduled_at: minutesAgo(20),
    meeting_url: meetingUrl('itv-2055'),
    status: 'scheduled',
    report: null,
  },
]

interviews.forEach((r) => {
  seedInterviewDetail(r.id, {
    candidate_name: r.candidate_name,
    candidate_email: r.candidate_email,
    position: r.position,
    scheduled_at: r.scheduled_at,
    status: r.status === 'completed' ? 'completed' : 'scheduled',
    meeting_url: r.meeting_url,
  })
})

// Default live interview room — joinable now.
seedInterviewDetail('demo', {
  candidate_name: 'Demo Candidate',
  candidate_email: 'demo@candidate.com',
  position: 'Full Stack Engineer',
  scheduled_at: minutesAgo(1),
  status: 'scheduled',
})

export function getMockUser() {
  return currentUser
}

export function setMockUser(user) {
  currentUser = user
}

export function clearMockUser() {
  currentUser = null
}

export function getMockInterviews() {
  return [...interviews]
}

export function addMockInterview(record) {
  interviews = [record, ...interviews]
  seedInterviewDetail(record.id, {
    candidate_name: record.candidate_name,
    candidate_email: record.candidate_email,
    position: record.position,
    scheduled_at: record.scheduled_at,
    status: 'scheduled',
    meeting_url: record.meeting_url,
    language: record.language,
  })
  return record
}

export function getMockInterview(id) {
  if (interviewDetails[id]) return { ...interviewDetails[id] }
  // Unknown id — return a joinable demo room so any link works.
  return seedInterviewDetail(id, {
    candidate_name: 'Guest Candidate',
    scheduled_at: minutesAgo(1),
    status: 'scheduled',
  })
}

export function updateMockInterview(id, patch) {
  if (!interviewDetails[id]) seedInterviewDetail(id)
  interviewDetails[id] = { ...interviewDetails[id], ...patch }
  return interviewDetails[id]
}

export function getMockCandidate(id) {
  const row = interviews.find((r) => r.id === id)
  const detail = getMockInterview(id)
  const report = row?.report ?? null

  return {
    id,
    candidate_name: detail.candidate_name,
    candidate_email: detail.candidate_email,
    position: detail.position,
    language: detail.language ?? 'en',
    status: row?.status === 'completed' ? 'completed' : row?.status === 'scheduled' && new Date(detail.scheduled_at) <= new Date() ? 'in_progress' : row?.status ?? 'scheduled',
    scheduled_at: detail.scheduled_at,
    cv_filename: 'cv_demo.pdf',
    cv_text: 'Mock CV text — 4 years experience in software engineering.\nSkills: Python, React, PostgreSQL, Docker.',
    cv_fields: {
      skills: ['Python', 'React', 'PostgreSQL', 'Docker', 'LiveKit'],
      experience_years: 4,
    },
    recording_url: row?.status === 'completed' ? null : null,
    report,
    report_pdf_url: row?.status === 'completed' ? '#' : null,
    conversation_history: row?.status === 'completed' ? MOCK_TRANSCRIPT : [],
  }
}

export function createMockInterviewId() {
  const id = `itv-${nextInterviewNum++}`
  return id
}

export function generateMockSlots(hoursAhead = 8, fromDate = null) {
  const base = fromDate ? new Date(fromDate) : new Date()
  base.setSeconds(0, 0)

  const slots = []
  const startHour = 7
  const endHour = 22

  for (let h = startHour; h <= endHour; h++) {
    for (const m of [0, 30]) {
      if (h === endHour && m > 0) break
      const slot = new Date(base)
      slot.setHours(h, m, 0, 0)
      if (slot <= new Date()) continue
      const diffH = (slot - Date.now()) / (1000 * 60 * 60)
      if (diffH > hoursAhead + 24) continue
      slots.push({
        start: slot.toISOString(),
        available: m !== 30 || h % 3 !== 0,
        active_count: m === 30 && h % 3 === 0 ? 2 : h % 5 === 0 ? 1 : 0,
      })
    }
  }

  return {
    slots,
    instant_available: true,
  }
}

export function mockRunCode(code) {
  const hasReturn = /return\s+/.test(code)
  const passed = hasReturn ? 3 : 1
  return {
    stdout: hasReturn ? 'All tests completed.\n' : 'Tests ran with failures.\n',
    stderr: '',
    exit_code: hasReturn ? 0 : 1,
    timed_out: false,
    test_results: [
      { label: 'test_empty', passed: true, expected: '[]', got: '[]' },
      { label: 'test_basic', passed: hasReturn, expected: '[0, 1]', got: hasReturn ? '[0, 1]' : 'None' },
      { label: 'test_no_solution', passed: hasReturn, expected: '[]', got: hasReturn ? '[]' : 'None' },
    ],
    tests_passed: passed,
    tests_total: 3,
  }
}

export function mockCodeAssist(messages, code = '') {
  const last = messages?.filter((m) => m.role === 'user').pop()?.content ?? ''
  const codeLines = code ? code.split('\n').length : 0
  return {
    reply:
      'Here is a hint for your approach:\n\n'
      + '```python\n'
      + 'def two_sum(nums, target):\n'
      + '    seen = {}\n'
      + '    for i, n in enumerate(nums):\n'
      + '        if target - n in seen:\n'
      + '            return [seen[target - n], i]\n'
      + '        seen[n] = i\n'
      + '    return []\n'
      + '```\n\n'
      + `(Mock assistant · ${codeLines} lines in editor · question: "${last.slice(0, 80)}${last.length > 80 ? '…' : ''}")`,
  }
}