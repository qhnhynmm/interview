import { API } from '@/constants/api.js'
import { authHeaders } from '@/utils/auth.js'
import { STATUS_MAP } from '@/constants/result.js'
import { USE_MOCK_API } from '@/constants/mock.js'
import { mockDelay } from '@/mocks/delay.js'
import {
  addMockInterview,
  createMockInterviewId,
  generateMockSlots,
  getMockCandidate,
  getMockInterviews,
  getMockInterview,
  mockCodeAssist,
  mockRunCode,
  updateMockInterview,
} from '@/mocks/store.js'

function formatSchedule(date) {
  const label = date.toLocaleString('en-US', {
    month: 'short',
    day: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  })
  return label.replace(',', ' ·')
}

function normalize(r) {
  const scheduledAt = r.scheduled_at ? new Date(r.scheduled_at) : null
  const score = r.report?.overall_score ?? null
  return {
    id: r.id,
    candidateName: r.candidate_name || 'Unknown',
    role: r.position || '—',
    seniority: r.seniority ?? '',
    scheduledAt,
    scheduledLabel: scheduledAt ? formatSchedule(scheduledAt) : '—',
    meetingLink: r.meeting_url || `${window.location.origin}/interview/${r.id}`,
    status: STATUS_MAP[r.status] ?? r.status,
    score: score,
    maxScore: r.report?.max_score ?? 5,
    reportUrl: r.status === 'completed' ? `${API}/interviews/${r.id}/report` : null,
    rawReport: r.report || null,
  }
}

export async function fetchSlots(hoursAhead = 8, fromDate = null) {
  if (USE_MOCK_API) {
    await mockDelay()
    return generateMockSlots(hoursAhead, fromDate)
  }

  let url = `${API}/interviews/slots?hours_ahead=${hoursAhead}`
  if (fromDate) url += `&from_utc=${encodeURIComponent(fromDate.toISOString())}`
  const res = await fetch(url, { headers: authHeaders() })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    if (res.status === 401) throw new Error('Please sign in to view available slots')
    throw new Error(err.detail || 'Failed to load available slots')
  }
  return res.json()
}

export async function loadInterviews() {
  if (USE_MOCK_API) {
    await mockDelay()
    return getMockInterviews().map(normalize)
  }

  const res = await fetch(`${API}/interviews`, { headers: authHeaders() })
  if (!res.ok) throw new Error('Failed to load interviews')
  const list = await res.json()
  return list.map(normalize)
}

function buildInterviewFormData(form) {
  const fd = new FormData()
  fd.append('candidate_name', form.candidateName.trim())
  if (form.email) fd.append('candidate_email', form.email.trim())
  fd.append('position', form.role.trim())
  fd.append('jd_text', form.jd.trim())
  if (form.requests) fd.append('special_requirements', form.requests.trim())
  fd.append('interview_language', form.language || 'en')
  if (form.voice) fd.append('interview_voice', form.voice)
  if (form.seniority) fd.append('seniority', form.seniority)
  if (form.cvFile) fd.append('cv_file', form.cvFile)
  if (form.scheduledAt) fd.append('scheduled_at', form.scheduledAt)
  return fd
}

function parseSseChunk(buffer, onEvent) {
  const parts = buffer.split('\n\n')
  const rest = parts.pop() ?? ''
  for (const block of parts) {
    if (!block.trim()) continue
    let eventType = 'message'
    let dataLine = ''
    for (const line of block.split('\n')) {
      if (line.startsWith('event: ')) eventType = line.slice(7).trim()
      if (line.startsWith('data: ')) dataLine = line.slice(6)
    }
    if (!dataLine) continue
    try {
      const payload = JSON.parse(dataLine)
      onEvent(eventType, payload)
    } catch {
      // ignore malformed chunks
    }
  }
  return rest
}

export async function submitInterviewStream(form, { onProgress } = {}) {
  if (USE_MOCK_API) {
    const record = await submitInterview(form)
    onProgress?.({ agent: 'Planning', text: `[Mock] Session created for ${form.candidateName}.` })
    return record
  }

  const res = await fetch(`${API}/interviews/generate-link/stream`, {
    method: 'POST',
    headers: authHeaders(),
    body: buildInterviewFormData(form),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || 'Failed to create interview')
  }

  const reader = res.body?.getReader()
  if (!reader) throw new Error('Streaming not supported by browser')

  const decoder = new TextDecoder()
  let buffer = ''
  let record = null

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    buffer = parseSseChunk(buffer, (eventType, payload) => {
      if (payload.type === 'progress' || eventType === 'progress') {
        onProgress?.({ agent: payload.agent, text: payload.text })
      } else if (payload.type === 'done' || eventType === 'done') {
        record = normalize(payload.interview)
      } else if (payload.type === 'error' || eventType === 'error') {
        throw new Error(payload.detail || 'Interview generation failed')
      }
    })
  }

  if (buffer.trim()) {
    parseSseChunk(`${buffer}\n\n`, (eventType, payload) => {
      if (payload.type === 'progress' || eventType === 'progress') {
        onProgress?.({ agent: payload.agent, text: payload.text })
      } else if (payload.type === 'done' || eventType === 'done') {
        record = normalize(payload.interview)
      } else if (payload.type === 'error' || eventType === 'error') {
        throw new Error(payload.detail || 'Interview generation failed')
      }
    })
  }

  if (!record) throw new Error('Interview stream ended without a result')
  return record
}

export async function submitInterview(form) {
  if (USE_MOCK_API) {
    await mockDelay(600)
    const id = createMockInterviewId()
    const scheduledAt = form.scheduledAt ? new Date(form.scheduledAt) : null
    const record = {
      id,
      candidate_name: form.candidateName.trim(),
      candidate_email: form.email?.trim() || '',
      position: form.role.trim(),
      scheduled_at: form.scheduledAt || null,
      meeting_url: `${window.location.origin}/interview/${id}`,
      status: 'scheduled',
      report: null,
      language: form.language || 'en',
    }
    addMockInterview(record)
    return {
      id: record.id,
      candidateName: record.candidate_name,
      role: record.position,
      seniority: form.seniority || '',
      scheduledAt: record.scheduled_at,
      scheduledLabel: scheduledAt ? formatSchedule(scheduledAt) : '—',
      meetingLink: record.meeting_url,
      status: 'Scheduled',
      score: null,
      maxScore: 5,
      reportUrl: null,
      rawReport: null,
    }
  }

  const res = await fetch(`${API}/interviews/generate-link`, {
    method: 'POST',
    headers: authHeaders(),
    body: buildInterviewFormData(form),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || 'Failed to create interview')
  }
  const data = await res.json()
  return normalize(data)
}

export async function sendChat(interviewId, message) {
  if (USE_MOCK_API) {
    await mockDelay()
    return {
      reply: `[Mock agent] Received: "${message}". LiveKit chat is disabled in mock mode.`,
    }
  }

  // const res = await fetch(`${API}/interviews/${interviewId}/chat`, {
  //   method: 'POST',
  //   headers: { 'Content-Type': 'application/json' },
  //   body: JSON.stringify({ message }),
  // })
  // if (!res.ok) {
  //   const err = await res.json().catch(() => ({}))
  //   throw new Error(err.detail || 'Chat request failed')
  // }
  // return res.json()
  throw new Error('Backend API is disabled. Set USE_MOCK_API = true in src/constants/mock.js')
}

export async function reportProctorEvent(interviewId, event) {
  if (USE_MOCK_API) {
    console.info('[proctor mock]', interviewId, event)
    return
  }

  try {
    await fetch(`${API}/interviews/${interviewId}/proctor-event`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(event),
      keepalive: true,
    })
  } catch (e) {
    console.warn('[proctor] failed to report event:', e)
  }
}

export async function endInterview(interviewId) {
  if (USE_MOCK_API) {
    await mockDelay()
    updateMockInterview(interviewId, { status: 'completed' })
    return { ok: true }
  }

  // const res = await fetch(`${API}/interviews/${interviewId}/end`, { method: 'POST' })
  // if (!res.ok) {
  //   const err = await res.json().catch(() => ({}))
  //   throw new Error(err.detail || 'Failed to end interview')
  // }
  // return res.json()
  throw new Error('Backend API is disabled. Set USE_MOCK_API = true in src/constants/mock.js')
}

export async function fetchInterview(interviewId) {
  if (USE_MOCK_API) {
    await mockDelay()
    return getMockInterview(interviewId)
  }

  const res = await fetch(`${API}/interviews/${interviewId}`)
  if (!res.ok) throw new Error('Interview not found')
  return res.json()
}

export async function uploadChunk(interviewId, blob) {
  if (USE_MOCK_API) {
    console.info('[recording mock] chunk uploaded', interviewId, blob?.size, 'bytes')
    return { ok: true }
  }

  // const fd = new FormData()
  // fd.append('file', blob, 'chunk.webm')
  // const res = await fetch(`${API}/interviews/${interviewId}/recording/chunk`, {
  //   method: 'POST',
  //   body: fd,
  // })
  // if (!res.ok) {
  //   const err = await res.json().catch(() => ({}))
  //   throw new Error(err.detail || 'Chunk upload failed')
  // }
  // return res.json()
  throw new Error('Backend API is disabled. Set USE_MOCK_API = true in src/constants/mock.js')
}

export async function uploadRecording(interviewId, blob) {
  if (USE_MOCK_API) {
    await mockDelay(500)
    console.info('[recording mock] final upload', interviewId, blob?.size, 'bytes')
    return { ok: true, url: null }
  }

  // const fd = new FormData()
  // fd.append('file', blob, 'recording.webm')
  // const res = await fetch(`${API}/interviews/${interviewId}/recording`, {
  //   method: 'POST',
  //   body: fd,
  // })
  // if (!res.ok) {
  //   const err = await res.json().catch(() => ({}))
  //   throw new Error(err.detail || 'Failed to upload recording')
  // }
  // return res.json()
  throw new Error('Backend API is disabled. Set USE_MOCK_API = true in src/constants/mock.js')
}

export async function downloadReportPdf(interviewId, candidateName) {
  if (USE_MOCK_API) {
    await mockDelay()
    const text = `Mock PDF Report — ${candidateName || interviewId}\nGenerated in mock mode.`
    const blob = new Blob([text], { type: 'application/pdf' })
    const url = URL.createObjectURL(blob)
    const safeName = (candidateName || interviewId).replace(/\s+/g, '_')
    const a = document.createElement('a')
    a.href = url
    a.download = `danh-gia-${safeName}.pdf`
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
    return
  }

  // const res = await fetch(`${API}/interviews/${interviewId}/report.pdf`, {
  //   headers: authHeaders(),
  // })
  // if (!res.ok) {
  //   const err = await res.json().catch(() => ({}))
  //   throw new Error(err.detail || 'PDF report not available')
  // }
  // const blob = await res.blob()
  // ...
  throw new Error('Backend API is disabled. Set USE_MOCK_API = true in src/constants/mock.js')
}

export async function fetchCandidate(candidateId) {
  if (USE_MOCK_API) {
    await mockDelay()
    return getMockCandidate(candidateId)
  }

  // const res = await fetch(`${API}/candidate/${candidateId}`, { headers: authHeaders() })
  // if (!res.ok) throw new Error('Candidate not found')
  // return res.json()
  throw new Error('Backend API is disabled. Set USE_MOCK_API = true in src/constants/mock.js')
}

export function subscribeToEvents(interviewId, onEvent) {
  if (USE_MOCK_API) {
    // No SSE in mock mode — optionally simulate report_ready after delay.
    const timer = setTimeout(() => {
      onEvent({ event: 'report_ready', interview_id: interviewId })
    }, 8000)
    return () => clearTimeout(timer)
  }

  // const es = new EventSource(`${API}/interviews/${interviewId}/events`)
  // es.onmessage = (e) => {
  //   try {
  //     const msg = JSON.parse(e.data)
  //     if (msg.event !== 'connected') onEvent(msg)
  //   } catch { /* ignore malformed SSE payloads */ }
  // }
  // es.onerror = () => es.close()
  // return () => es.close()
  return () => {}
}

export async function codeAssist(interviewId, messages, code) {
  if (USE_MOCK_API) {
    await mockDelay(800)
    return mockCodeAssist(messages, code)
  }

  // const res = await fetch(`${API}/interviews/${interviewId}/code-assist`, {
  //   method: 'POST',
  //   headers: { 'Content-Type': 'application/json' },
  //   body: JSON.stringify({ messages, code, language: 'python' }),
  // })
  // if (!res.ok) {
  //   const err = await res.json().catch(() => ({}))
  //   throw new Error(err.detail || 'Assistant request failed')
  // }
  // return res.json()
  throw new Error('Backend API is disabled. Set USE_MOCK_API = true in src/constants/mock.js')
}

// Assignment endpoints used by CodePanel / SandpackPanel / CognitivePanel.
export async function syncCode(interviewId, code) {
  if (USE_MOCK_API) {
    updateMockInterview(interviewId, { current_code: code })
    return
  }
  // await fetch(`${API}/interviews/${interviewId}/sync-code`, { ... })
}

export async function runCode(interviewId, code) {
  if (USE_MOCK_API) {
    await mockDelay(600)
    return mockRunCode(code)
  }
  // const res = await fetch(`${API}/interviews/${interviewId}/run-code`, { ... })
  throw new Error('Backend API is disabled. Set USE_MOCK_API = true in src/constants/mock.js')
}

export async function submitAssignment(interviewId, body) {
  if (USE_MOCK_API) {
    await mockDelay()
    updateMockInterview(interviewId, { assignment_finished: true, ...body })
    return { ok: true }
  }
  // await fetch(`${API}/interviews/${interviewId}/submit-assignment`, { ... })
  throw new Error('Backend API is disabled. Set USE_MOCK_API = true in src/constants/mock.js')
}

export async function syncSandbox(interviewId, files) {
  if (USE_MOCK_API) {
    updateMockInterview(interviewId, { sandbox_files: files })
    return
  }
  // await fetch(`${API}/interviews/${interviewId}/sync-sandbox`, { ... })
}

export async function syncAnswers(interviewId, answers) {
  if (USE_MOCK_API) {
    updateMockInterview(interviewId, { cognitive_answers: answers })
    return
  }
  // await fetch(`${API}/interviews/${interviewId}/sync-answers`, { ... })
}