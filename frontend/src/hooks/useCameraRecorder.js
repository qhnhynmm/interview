import { useCallback, useEffect, useRef, useState } from 'react'

// Emit a recorded chunk every this many ms. WITHOUT a timeslice, MediaRecorder
// buffers the entire session in memory and only fires `ondataavailable` once —
// at stop() — so the whole (large) webm has to be finalized and uploaded in a
// single shot at the moment the interview ends. That made stop() slow (visible
// as a long hang before the "complete" screen) and all-or-nothing: a tab close
// or teardown race mid-finalize lost the ENTIRE recording (S3 got nothing).
// A periodic timeslice accumulates chunks during the call, so the final flush
// is tiny and stop() is near-instant.
const CHUNK_MS = 1000

// How often to push accumulated chunks to the backend as a mid-session backup.
// If the browser crashes before stop() is called, the backend already has
// everything up to the last successful flush. The final uploadRecording() call
// combines the temp file with any remaining chunks → one complete file in S3.
const UPLOAD_INTERVAL_MS = 30_000

// Pick a webm codec the browser actually supports.
function pickMimeType() {
  const candidates = [
    'video/webm;codecs=vp9,opus',
    'video/webm;codecs=vp8,opus',
    'video/webm',
  ]
  for (const t of candidates) {
    if (window.MediaRecorder?.isTypeSupported?.(t)) return t
  }
  return ''
}

// Records the candidate from their webcam + microphone, and mixes in any extra
// audio tracks fed via mixInTrack() — used to capture the AI interviewer's
// voice (LiveKit remote audio) so the recording has both sides of the call.
// Audio is mixed through a single Web Audio destination, so tracks that arrive
// later (the agent joins after the candidate) can be added live.
//
// Optional: pass { onChunk } to receive a periodic backup blob every
// UPLOAD_INTERVAL_MS. Fire-and-forget; failures are warned, not retried.
// The final stop() blob still captures any chunks not yet flushed.
export function useCameraRecorder({ onChunk } = {}) {
  const recorderRef = useRef(null)
  const chunksRef = useRef([])
  const streamRef = useRef(null)       // raw camera+mic stream (self-view + cleanup)
  const ctxRef = useRef(null)          // AudioContext doing the mixing
  const destRef = useRef(null)         // mixed-audio destination feeding the recorder
  const extraSourcesRef = useRef([])   // sources connected via mixInTrack
  const mimeRef = useRef('')
  const uploadIntervalRef = useRef(null)
  const onChunkRef = useRef(onChunk)
  const [recording, setRecording] = useState(false)
  const [error, setError] = useState('')
  const [stream, setStream] = useState(null)

  useEffect(() => { onChunkRef.current = onChunk }, [onChunk])

  const cleanup = useCallback(() => {
    extraSourcesRef.current.forEach((s) => {
      try { s.disconnect() } catch { /* noop */ }
    })
    extraSourcesRef.current = []
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => {
        try { t.stop() } catch { /* already stopped */ }
      })
      streamRef.current = null
    }
    if (ctxRef.current) {
      ctxRef.current.close().catch(() => {})
      ctxRef.current = null
    }
    destRef.current = null
    setStream(null)
  }, [])

  const flushChunks = useCallback(() => {
    const pending = chunksRef.current.splice(0)
    if (!pending.length || !onChunkRef.current) return
    const blob = new Blob(pending, { type: mimeRef.current || 'video/webm' })
    Promise.resolve()
      .then(() => onChunkRef.current(blob))
      .catch((e) => console.warn('[recording] periodic chunk upload failed:', e))
  }, [])

  const start = useCallback(async () => {
    setError('')
    try {
      const media = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 1280 }, height: { ideal: 720 }, frameRate: { ideal: 24 } },
        audio: true,
      })
      streamRef.current = media
      setStream(media)

      // Mix all audio (candidate mic + later the agent voice) into one track.
      const AudioCtx = window.AudioContext || window.webkitAudioContext
      const ctx = new AudioCtx()
      ctxRef.current = ctx
      if (ctx.state === 'suspended') ctx.resume().catch(() => {})
      const dest = ctx.createMediaStreamDestination()
      destRef.current = dest
      if (media.getAudioTracks().length) {
        ctx.createMediaStreamSource(new MediaStream(media.getAudioTracks())).connect(dest)
      }

      const mixed = new MediaStream([
        ...media.getVideoTracks(),
        ...dest.stream.getAudioTracks(),
      ])
      const mime = pickMimeType()
      mimeRef.current = mime
      const recorder = new MediaRecorder(mixed, mime ? { mimeType: mime } : undefined)
      chunksRef.current = []
      recorder.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) chunksRef.current.push(e.data)
      }
      recorderRef.current = recorder
      // Timeslice: flush a chunk every CHUNK_MS so the recording is assembled
      // incrementally instead of in one giant blob at stop() — see CHUNK_MS.
      recorder.start(CHUNK_MS)
      setRecording(true)
      if (onChunkRef.current) {
        uploadIntervalRef.current = setInterval(flushChunks, UPLOAD_INTERVAL_MS)
      }
      return true
    } catch (e) {
      setError(e?.message || 'Camera recording not started')
      cleanup()
      return false
    }
  }, [cleanup, flushChunks])

  // Mix an external audio MediaStreamTrack (e.g. the agent's LiveKit voice) into
  // the live recording. Safe to call before/after start — no-ops if not mixing.
  const mixInTrack = useCallback((track) => {
    const ctx = ctxRef.current
    const dest = destRef.current
    if (!ctx || !dest || !track) return
    try {
      const src = ctx.createMediaStreamSource(new MediaStream([track]))
      src.connect(dest)
      extraSourcesRef.current.push(src)
    } catch {
      // Track may be ended/unsupported — skip it.
    }
  }, [])

  // Stop and resolve with the recorded Blob (or null if nothing was recorded).
  // Clears the periodic-flush interval first so we don't race with stop().
  const stop = useCallback(() => {
    if (uploadIntervalRef.current) {
      clearInterval(uploadIntervalRef.current)
      uploadIntervalRef.current = null
    }
    const recorder = recorderRef.current
    if (!recorder || recorder.state === 'inactive') {
      cleanup()
      setRecording(false)
      return Promise.resolve(null)
    }
    return new Promise((resolve) => {
      recorder.onstop = () => {
        const blob = chunksRef.current.length
          ? new Blob(chunksRef.current, { type: mimeRef.current || 'video/webm' })
          : null
        chunksRef.current = []
        recorderRef.current = null
        cleanup()
        setRecording(false)
        resolve(blob)
      }
      try {
        recorder.stop()
      } catch {
        cleanup()
        setRecording(false)
        resolve(null)
      }
    })
  }, [cleanup])

  return { recording, error, stream, start, stop, mixInTrack }
}
