import { useCallback, useEffect, useRef, useState } from 'react'
import { Room, RoomEvent, Track } from 'livekit-client'
import { USE_MOCK_API } from '@/constants/mock.js'

export function useLiveKit(interviewId, enabled, onMessage, onRemoteAudio) {
  const roomRef = useRef(null)
  const onMessageRef = useRef(onMessage)
  const onRemoteAudioRef = useRef(onRemoteAudio)
  const remoteAudioTracksRef = useRef(new Set())
  const [status, setStatus] = useState('idle') // idle | connecting | connected | failed
  const [errorDetail, setErrorDetail] = useState(null)
  const [errorStatus, setErrorStatus] = useState(null)
  const [muted, setMuted] = useState(false)
  const [speaking, setSpeaking] = useState(false)
  const [audioBlocked, setAudioBlocked] = useState(false)
  const [agentJoined, setAgentJoined] = useState(false)
  const [forcedMicLocked, setForcedMicLocked] = useState(false)
  const forcedMicLockedRef = useRef(false)
  const forcedMicWasEnabledRef = useRef(true)

  useEffect(() => {
    onMessageRef.current = onMessage
  }, [onMessage])

  useEffect(() => {
    onRemoteAudioRef.current = onRemoteAudio
  }, [onRemoteAudio])

  // ── Mock LiveKit (no backend / no real room) ───────────────────────────────
  useEffect(() => {
    if (!USE_MOCK_API || !enabled) return

    let cancelled = false

    const bootTimer = setTimeout(() => {
      if (cancelled) return
      setStatus('connecting')
      setErrorDetail(null)
      setErrorStatus(null)
      setAudioBlocked(false)
      setMuted(false)
    }, 0)

    const connectTimer = setTimeout(() => {
      if (cancelled) return
      setStatus('connected')
    }, 900)

    const agentTimer = setTimeout(() => {
      if (cancelled) return
      setAgentJoined(true)
      onMessageRef.current?.({
        type: 'ui:agent_message',
        message: '[Mock] Hello! I am your AI interviewer. LiveKit is disabled in mock mode.',
      })
    }, 1800)

    return () => {
      cancelled = true
      clearTimeout(bootTimer)
      clearTimeout(connectTimer)
      clearTimeout(agentTimer)
      setStatus('idle')
      setMuted(false)
      setSpeaking(false)
      setAudioBlocked(false)
      setAgentJoined(false)
      setForcedMicLocked(false)
      forcedMicLockedRef.current = false
      forcedMicWasEnabledRef.current = true
    }
  }, [interviewId, enabled])

  // ── Real LiveKit ───────────────────────────────────────────────────────────
  useEffect(() => {
    if (USE_MOCK_API || !enabled) return

    let room = null
    let cancelled = false
    const remoteAudioTracks = remoteAudioTracksRef.current

    function attachAudioTrack(track) {
      if (track.kind !== Track.Kind.Audio || remoteAudioTracks.has(track)) return
      const element = track.attach()
      element.autoplay = true
      element.playsInline = true
      element.style.display = 'none'
      document.body.appendChild(element)
      remoteAudioTracks.add(track)
      const playAttempt = element.play?.()
      playAttempt?.catch(() => setAudioBlocked(true))
      if (track.mediaStreamTrack) onRemoteAudioRef.current?.(track.mediaStreamTrack)
    }

    function detachAudioTrack(track) {
      for (const element of track.detach()) {
        element.remove()
      }
      remoteAudioTracks.delete(track)
    }

    function attachExistingAudioTracks() {
      room.remoteParticipants.forEach((participant) => {
        participant.trackPublications.forEach((publication) => {
          if (publication.isSubscribed && publication.track) {
            attachAudioTrack(publication.track)
          }
        })
      })
    }

    async function sendData(payload) {
      if (!room) return
      const data = new TextEncoder().encode(JSON.stringify(payload))
      await room.localParticipant.publishData(data, { reliable: true })
    }

    async function handleMicControl(msg) {
      const lockId = msg.lock_id || ''
      let ok = true
      try {
        if (msg.action === 'mute') {
          forcedMicWasEnabledRef.current = room.localParticipant.isMicrophoneEnabled
          forcedMicLockedRef.current = true
          setForcedMicLocked(true)
          if (forcedMicWasEnabledRef.current) {
            await room.localParticipant.setMicrophoneEnabled(false)
          }
          setMuted(true)
        } else if (msg.action === 'restore') {
          if (forcedMicWasEnabledRef.current) {
            await room.localParticipant.setMicrophoneEnabled(true)
            setMuted(false)
          } else {
            setMuted(true)
          }
          forcedMicLockedRef.current = false
          setForcedMicLocked(false)
        } else {
          ok = false
        }
      } catch {
        ok = false
      }

      await sendData({
        type: 'control:mic_ack',
        action: msg.action,
        lock_id: lockId,
        ok,
      }).catch(() => {})
    }

    async function unlockAudio() {
      if (!room) return
      try {
        await room.startAudio()
      } catch {
        // ignore
      }
      document.querySelectorAll('audio').forEach((el) => el.play?.().catch(() => {}))
      if (!cancelled) setAudioBlocked(!room.canPlaybackAudio)
    }

    async function connect() {
      try {
        setStatus('connecting')
        setAudioBlocked(false)
        // const res = await fetch(
        //   `/api/v1/interviews/${interviewId}/join-token?role=candidate`,
        // )
        const res = await fetch(
          `/api/v1/interviews/${interviewId}/join-token?role=candidate`,
        )
        if (!res.ok || cancelled) {
          if (!cancelled) {
            setErrorStatus(res.status)
            setStatus('failed')
          }
          return
        }
        setErrorDetail(null)
        const data = await res.json()

        room = new Room({
          audioCaptureDefaults: {
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true,
          },
          adaptiveStream: true,
        })
        if (cancelled) return
        roomRef.current = room

        room.on(RoomEvent.Disconnected, () => {
          if (!cancelled) setStatus('idle')
        })
        room.on(RoomEvent.Reconnecting, () => {
          if (!cancelled) setStatus('connecting')
        })
        room.on(RoomEvent.Reconnected, () => {
          if (!cancelled) setStatus('connected')
        })
        room.on(RoomEvent.ActiveSpeakersChanged, (speakers) => {
          const local = room.localParticipant
          setSpeaking(speakers.some((s) => s.identity === local?.identity))
        })
        room.on(RoomEvent.DataReceived, (payload) => {
          try {
            const msg = JSON.parse(new TextDecoder().decode(payload))
            if (msg.type === 'control:mic') {
              handleMicControl(msg)
              return
            }
            onMessageRef.current?.(msg)
          } catch {
            // ignore malformed messages
          }
        })
        room.on(RoomEvent.TrackSubscribed, (track, _publication, participant) => {
          attachAudioTrack(track)
          if (track.kind === Track.Kind.Audio && !participant.isLocal) {
            setAgentJoined(true)
          }
        })
        room.on(RoomEvent.TrackUnsubscribed, (track, _publication, participant) => {
          detachAudioTrack(track)
          if (track.kind === Track.Kind.Audio && !participant.isLocal) {
            const hasOtherAgentAudio = Array.from(room.remoteParticipants.values()).some(
              (p) => p.identity !== participant.identity &&
                Array.from(p.trackPublications.values()).some(
                  (pub) => pub.isSubscribed && pub.track?.kind === Track.Kind.Audio
                )
            )
            if (!hasOtherAgentAudio) setAgentJoined(false)
          }
        })
        room.on(RoomEvent.AudioPlaybackStatusChanged, () => {
          setAudioBlocked(!room.canPlaybackAudio)
        })

        await room.connect(data.livekit_url, data.token)
        if (cancelled) {
          room.disconnect()
          return
        }

        attachExistingAudioTracks()
        await room.startAudio().catch(() => setAudioBlocked(true))
        await room.localParticipant.setMicrophoneEnabled(true)
        setStatus('connected')
        setMuted(false)
      } catch (err) {
        console.error('[useLiveKit] connection error:', err)
        if (!cancelled) setStatus('failed')
      }
    }

    const onGesture = () => unlockAudio()
    document.addEventListener('pointerdown', onGesture)

    connect()

    return () => {
      cancelled = true
      document.removeEventListener('pointerdown', onGesture)
      Array.from(remoteAudioTracks).forEach((track) => detachAudioTrack(track))
      room?.disconnect()
      roomRef.current = null
      setStatus('idle')
      setErrorDetail(null)
      setErrorStatus(null)
      setMuted(false)
      setSpeaking(false)
      setAudioBlocked(false)
      setAgentJoined(false)
      setForcedMicLocked(false)
      forcedMicLockedRef.current = false
      forcedMicWasEnabledRef.current = true
    }
  }, [interviewId, enabled])

  const toggleMute = useCallback(async () => {
    if (USE_MOCK_API) {
      if (status !== 'connected' || forcedMicLockedRef.current) return
      setMuted((m) => !m)
      return
    }

    const room = roomRef.current
    if (!room || status !== 'connected' || forcedMicLockedRef.current) return
    const isEnabled = room.localParticipant.isMicrophoneEnabled
    await room.localParticipant.setMicrophoneEnabled(!isEnabled)
    setMuted(isEnabled)
  }, [status])

  const enableAudio = useCallback(async () => {
    if (USE_MOCK_API) {
      if (status !== 'connected') return
      setAudioBlocked(false)
      return
    }

    const room = roomRef.current
    if (!room || status !== 'connected') return
    await room.startAudio().catch(() => setAudioBlocked(true))
    document.querySelectorAll('audio').forEach((el) => el.play?.().catch(() => {}))
    setAudioBlocked(!room.canPlaybackAudio)
  }, [status])

  return { status, errorDetail, errorStatus, muted, speaking, audioBlocked, agentJoined, forcedMicLocked, toggleMute, enableAudio }
}