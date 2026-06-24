import { useCallback, useEffect, useRef, useState } from 'react'

const SpeechRecognition =
  window.SpeechRecognition || window.webkitSpeechRecognition

export function useSpeechRecognition({ enabled, onTranscript, onAutoSend, silenceMs = 1500 }) {
  const [listening, setListening] = useState(false)
  const [supported] = useState(() => !!SpeechRecognition)

  const recogRef = useRef(null)
  const silenceTimer = useRef(null)
  const pendingRef = useRef('')
  const enabledRef = useRef(enabled)

  useEffect(() => {
    enabledRef.current = enabled
  }, [enabled])

  const clearSilence = () => {
    if (silenceTimer.current) {
      clearTimeout(silenceTimer.current)
      silenceTimer.current = null
    }
  }

  const armSilence = useCallback(() => {
    clearSilence()
    silenceTimer.current = setTimeout(() => {
      const text = pendingRef.current.trim()
      if (text) {
        pendingRef.current = ''
        onAutoSend?.(text)
      }
    }, silenceMs)
  }, [onAutoSend, silenceMs])

  const stop = useCallback(() => {
    clearSilence()
    recogRef.current?.stop()
    recogRef.current = null
    setListening(false)
  }, [])

  const start = useCallback(() => {
    if (!SpeechRecognition || recogRef.current) return

    const r = new SpeechRecognition()
    r.lang = 'vi-VN'
    r.interimResults = true
    r.continuous = true
    recogRef.current = r

    r.onstart = () => setListening(true)

    r.onresult = (e) => {
      let interim = ''
      let final = ''
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const t = e.results[i][0].transcript
        if (e.results[i].isFinal) final += t
        else interim += t
      }
      if (final) {
        pendingRef.current += (pendingRef.current ? ' ' : '') + final
        onTranscript?.(pendingRef.current, false)
        armSilence()
      } else if (interim) {
        onTranscript?.(pendingRef.current + (pendingRef.current ? ' ' : '') + interim, true)
        clearSilence()
      }
    }

    r.onerror = (e) => {
      if (e.error === 'no-speech') return
      stop()
    }

    r.onend = () => {
      // Auto-restart while enabled so it stays continuous
      if (enabledRef.current && recogRef.current) {
        try { recogRef.current.start() } catch { /* already started */ }
      } else {
        setListening(false)
      }
    }

    r.start()
  }, [armSilence, onTranscript, stop])

  useEffect(() => {
    if (!SpeechRecognition) return
    let cancelled = false
    const timer = window.setTimeout(() => {
      if (cancelled) return
      if (enabled) {
        start()
      } else {
        stop()
        pendingRef.current = ''
      }
    }, 0)
    return () => {
      cancelled = true
      window.clearTimeout(timer)
      stop()
    }
  }, [enabled, start, stop])

  return { listening, supported }
}
