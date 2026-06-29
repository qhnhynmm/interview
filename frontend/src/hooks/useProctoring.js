import { useEffect, useRef } from 'react'
import { getProctoring } from '@/lib/proctoring-config.js'
import { reportProctorEvent } from '@/utils/interviews.js'

// Anti-cheat proctoring for the live interview. Detects several things from the
// candidate's browser and reports each to the backend (which logs it and
// forwards it to the interview agent):
//   1. secondary_monitor   — an external/extended display is connected
//   2. tab_switch          — the candidate left the interview tab/window
//   3. gaze_away           — the candidate looked away from the screen too long
//   4. multiple_faces      — a second person is visible in the camera frame
//   5. phone_detected      — a phone is visible in the camera frame
//
// Detection that the browser cannot perform (e.g. no Window Management API on
// Firefox/Safari/non-HTTPS) is reported once as `detection_unsupported` so the
// Inspector knows it could not be checked, rather than silently passing.
//
// All reporting is fire-and-forget: proctoring never disrupts the interview.

const PROCTORING = getProctoring()

const FLICKER_MS = PROCTORING.flicker_ms
const BLUR_GRACE_MS = PROCTORING.blur_grace_ms
const MONITOR_REPEAT_MS = PROCTORING.monitor_repeat_ms
const GAZE_REPEAT_MS = PROCTORING.gaze_repeat_ms
const TAB_REPEAT_MS = PROCTORING.tab_repeat_ms
const FACE_REPEAT_MS = PROCTORING.face_repeat_ms
const PHONE_REPEAT_MS = PROCTORING.phone_repeat_ms
const MULTI_GRACE_MS = PROCTORING.multi_grace_ms
const PHONE_GRACE_MS = PROCTORING.phone_grace_ms
const MEDIAPIPE_VERSION = PROCTORING.medipipe_version
const WASM_BASE = `${PROCTORING.wasm_base}@${MEDIAPIPE_VERSION}/wasm`
const MODEL_URL = PROCTORING.face_model_url
const OBJECT_MODEL_URL = PROCTORING.object_model_url
const MIN_FACE_DETECTION_CONFIDENCE = PROCTORING.min_face_detection_confidence

export const PROCTOR_EVENT_LABELS = {
  tab_switch: 'Left the interview window',
  gaze_away: 'Looked away from screen',
  multiple_faces: 'Multiple people in frame',
  phone_detected: 'Phone detected',
  secondary_monitor: 'External display connected',
  detection_unsupported: 'Some checks unavailable in this browser',
}

export function useProctoring(
  interviewId,
  active,
  stream,
  {
    onEvent,
    enableGaze = PROCTORING.enable_gaze,
    gazeThresholdMs = PROCTORING.gaze_threshold_ms,
    gazeIntervalMs = PROCTORING.gaze_interval_ms,
    enableMultiFace = PROCTORING.enable_multi_face,
    multiFaceThresholdMs = PROCTORING.multi_face_threshold_ms,
    multiFaceMinSizeRatio = PROCTORING.multi_face_min_size_ratio,
    enablePhone = PROCTORING.enable_phone,
    phoneThresholdMs = PROCTORING.phone_threshold_ms,
    phoneIntervalMs = PROCTORING.phone_interval_ms,
    phoneScore = PROCTORING.phone_score_threshold,
  } = {},
) {
  // Keep the latest stream without re-running the whole effect.
  const streamRef = useRef(stream)
  useEffect(() => {
    streamRef.current = stream
  }, [stream])

  useEffect(() => {
    if (!active || !interviewId) return

    let disposed = false
    const cleanups = []
    const report = (event) => {
      if (disposed) return
      const payload = { ts: Date.now() / 1000, ...event }
      onEvent?.(payload)
      reportProctorEvent(interviewId, payload)
    }

    // ── 1. Secondary monitor ────────────────────────────────────────────────
    // `screen.isExtended` is readable without permission in Chromium; the full
    // Window Management API (getScreenDetails) additionally gives a live
    // `screenschange` event and the screen count. Both are Chromium + secure
    // context only — anything else is reported as unsupported once. We re-report
    // periodically while a second screen stays connected, so the agent keeps
    // reminding until the candidate unplugs it.
    let screenDetails = null
    const evaluateMonitor = () => {
      if (disposed) return
      const extended = window.screen?.isExtended === true
      const count = screenDetails?.screens?.length ?? (extended ? 2 : 1)
      if (extended || count > 1) {
        report({
          kind: 'secondary_monitor',
          severity: 'high',
          detail: `${count} display(s) connected (extended=${extended}).`,
        })
      }
    }
    const monitorSupported =
      typeof window.screen?.isExtended === 'boolean' ||
      typeof window.getScreenDetails === 'function'
    if (typeof window.getScreenDetails === 'function') {
      window
        .getScreenDetails()
        .then((details) => {
          if (disposed) return
          screenDetails = details
          evaluateMonitor()
          details.addEventListener('screenschange', evaluateMonitor)
          cleanups.push(() =>
            details.removeEventListener('screenschange', evaluateMonitor),
          )
        })
        .catch((e) => {
          // Permission denied — fall back to isExtended only (handled below).
          if (typeof window.screen?.isExtended !== 'boolean' && !disposed) {
            report({
              kind: 'detection_unsupported',
              severity: 'info',
              detail: `Window Management permission unavailable: ${e?.message || e}`,
            })
          }
        })
    } else {
      evaluateMonitor()
    }
    if (monitorSupported) {
      const monitorTimer = setInterval(evaluateMonitor, MONITOR_REPEAT_MS)
      cleanups.push(() => clearInterval(monitorTimer))
    } else {
      report({
        kind: 'detection_unsupported',
        severity: 'info',
        detail:
          'This browser cannot detect external monitors (Window Management API ' +
          'requires Chromium over HTTPS).',
      })
    }

    // ── 2. Tab switch / window blur ──────────────────────────────────────────
    // Report the MOMENT the candidate leaves (after a short grace to ignore
    // focus blips), then keep re-reporting while they stay away, so the agent
    // nudges them right away instead of only after they come back. Both Chromium
    // events are used: `visibilitychange→hidden` fires when switching tabs or
    // minimizing; `blur` fires when focus moves to another window/app (e.g.
    // Edge → another Edge window or a different program).
    let awaySince = 0
    let awayTimer = null
    const clearAwayTimer = () => {
      if (awayTimer) {
        clearTimeout(awayTimer)
        awayTimer = null
      }
    }
    // `viaBlur` marks a bare window-blur trigger. A blur is noisy: an OS popup,
    // a Bluetooth / audio-device-switch dialog, or a system notification steals
    // focus for a fraction of a second without the candidate leaving. So a blur
    // waits the longer BLUR_GRACE_MS and is only counted if focus is STILL gone
    // when the timer fires. A real tab switch / minimize comes through
    // `visibilitychange → hidden`, which still reports on the short flicker grace.
    const goAway = (viaBlur = false) => {
      if (awaySince) return // already away — don't restart the timer
      awaySince = Date.now()
      const tick = () => {
        // Re-verify the candidate is genuinely away. A transient focus-steal
        // (e.g. connecting a Bluetooth headset pops an OS dialog) returns focus
        // quickly; if the window is visible and focused again it was not a real
        // departure — treat it as a return instead of reporting a false positive.
        if (document.visibilityState === 'visible' && document.hasFocus()) {
          comeBack()
          return
        }
        const ms = Date.now() - awaySince
        report({
          kind: 'tab_switch',
          severity: 'high',
          detail: `Left the interview window for ${(ms / 1000).toFixed(1)}s.`,
        })
        // Background tabs throttle timers (min ~1s), but they still fire — so a
        // candidate sitting on another tab keeps getting reminded.
        awayTimer = setTimeout(tick, TAB_REPEAT_MS)
      }
      awayTimer = setTimeout(tick, viaBlur ? BLUR_GRACE_MS : FLICKER_MS)
    }
    const comeBack = () => {
      clearAwayTimer()
      awaySince = 0
    }
    const onVisibility = () => {
      if (document.visibilityState === 'hidden') goAway(false)
      else comeBack()
    }
    const onBlur = () => goAway(true)
    document.addEventListener('visibilitychange', onVisibility)
    window.addEventListener('blur', onBlur)
    window.addEventListener('focus', comeBack)
    cleanups.push(() => {
      clearAwayTimer()
      document.removeEventListener('visibilitychange', onVisibility)
      window.removeEventListener('blur', onBlur)
      window.removeEventListener('focus', comeBack)
    })

    // ── 3. Gaze + multiple faces (MediaPipe FaceLandmarker on the camera) ─────
    if (enableGaze || enableMultiFace) {
      cleanups.push(startGazeDetection({
        getStream: () => streamRef.current,
        thresholdMs: gazeThresholdMs,
        intervalMs: gazeIntervalMs,
        enableGaze,
        enableMultiFace,
        multiFaceThresholdMs,
        multiFaceMinSizeRatio,
        report,
        isDisposed: () => disposed,
      }))
    }

    // ── 4. Phone in frame (MediaPipe ObjectDetector on the camera) ────────────
    if (enablePhone) {
      cleanups.push(startObjectDetection({
        getStream: () => streamRef.current,
        thresholdMs: phoneThresholdMs,
        intervalMs: phoneIntervalMs,
        scoreThreshold: phoneScore,
        report,
        isDisposed: () => disposed,
      }))
    }

    return () => {
      disposed = true
      cleanups.forEach((fn) => {
        try {
          fn?.()
        } catch {
          /* noop */
        }
      })
    }
  }, [
    interviewId,
    active,
    enableGaze,
    gazeThresholdMs,
    gazeIntervalMs,
    enableMultiFace,
    multiFaceThresholdMs,
    multiFaceMinSizeRatio,
    enablePhone,
    phoneThresholdMs,
    phoneIntervalMs,
    phoneScore,
    onEvent,
  ])
}

// Loads MediaPipe lazily, runs face-landmark detection on the camera stream, and
// reports two signals: `gaze_away` (off-screen / turned away beyond a threshold
// continuously) and `multiple_faces` (a second person in frame). Both ride the
// SAME face model. Returns a cleanup function; degrades gracefully if MediaPipe
// can't load.
function startGazeDetection({
  getStream,
  thresholdMs,
  intervalMs,
  enableGaze = true,
  enableMultiFace = true,
  multiFaceThresholdMs = 1500,
  multiFaceMinSizeRatio = 0,
  report,
  isDisposed,
}) {
  let landmarker = null
  let video = null
  let timer = null
  let awaySince = 0
  let lastGazeReport = 0
  let multiSince = 0
  let multiLastSeen = 0
  let lastMultiReport = 0
  let stopped = false

  const stop = () => {
    stopped = true
    if (timer) clearInterval(timer)
    timer = null
    try {
      landmarker?.close?.()
    } catch {
      /* noop */
    }
    if (video) {
      video.srcObject = null
      video.remove()
      video = null
    }
  }

  ;(async () => {
    let stream = getStream()
    if (!stream) {
      // Camera may attach slightly after connect — wait briefly.
      await new Promise((r) => setTimeout(r, 800))
      stream = getStream()
    }
    if (!stream || stopped || isDisposed()) return

    let FaceLandmarker, FilesetResolver
    try {
      ({ FaceLandmarker, FilesetResolver } = await import('@mediapipe/tasks-vision'))
    } catch (e) {
      report({
        kind: 'detection_unsupported',
        severity: 'info',
        detail: `Gaze detection unavailable (MediaPipe failed to load): ${e?.message || e}`,
      })
      return
    }

    try {
      const fileset = await FilesetResolver.forVisionTasks(WASM_BASE)
      landmarker = await FaceLandmarker.createFromOptions(fileset, {
        baseOptions: { modelAssetPath: MODEL_URL, delegate: 'GPU' },
        runningMode: 'VIDEO',
        // 2 faces is enough to flag "another person in frame" without the cost
        // of tracking a crowd.
        numFaces: enableMultiFace ? 2 : 1,
        // Require a confident detection so low-confidence blobs don't register
        // as a second face (a key source of multi-face false positives).
        ...(MIN_FACE_DETECTION_CONFIDENCE != null
          ? { minFaceDetectionConfidence: MIN_FACE_DETECTION_CONFIDENCE }
          : {}),
        // Blendshapes give per-eye look direction, so we catch the candidate
        // glancing left/right/up/down with their EYES even when the head stays
        // forward — head-turn landmarks alone miss that.
        outputFaceBlendshapes: true,
      })
    } catch (e) {
      report({
        kind: 'detection_unsupported',
        severity: 'info',
        detail: `Gaze model could not initialize: ${e?.message || e}`,
      })
      return
    }
    if (stopped || isDisposed()) return stop()

    video = document.createElement('video')
    video.muted = true
    video.playsInline = true
    video.srcObject = new MediaStream(stream.getVideoTracks())
    video.style.display = 'none'
    document.body.appendChild(video)
    try {
      await video.play()
    } catch {
      /* autoplay of a muted offscreen video is allowed; ignore */
    }

    timer = setInterval(() => {
      if (stopped || isDisposed() || !video || video.readyState < 2) return
      let result
      try {
        result = landmarker.detectForVideo(video, performance.now())
      } catch {
        return
      }
      const now = Date.now()
      // Only count faces big enough to be a real person in the room; small
      // background faces (posters, photos, reflections) are filtered out.
      const faceCount = significantFaceCount(result, multiFaceMinSizeRatio)

      // ── Multiple faces (another person in frame) ──────────────────────────
      if (enableMultiFace) {
        if (faceCount >= 2) multiLastSeen = now
        const present = multiLastSeen && now - multiLastSeen <= MULTI_GRACE_MS
        if (present) {
          if (!multiSince) {
            multiSince = now
            lastMultiReport = 0
          }
          if (
            now - multiSince >= multiFaceThresholdMs &&
            now - lastMultiReport >= FACE_REPEAT_MS
          ) {
            lastMultiReport = now
            report({
              kind: 'multiple_faces',
              severity: 'high',
              detail: `${faceCount} faces detected in the camera frame.`,
            })
          }
        } else {
          multiSince = 0
        }
      }

      // ── Gaze away ─────────────────────────────────────────────────────────
      if (enableGaze) {
        const away = isLookingAway(result)
        if (away) {
          if (!awaySince) {
            awaySince = now
            lastGazeReport = 0
          }
          // Once past the threshold, keep re-reporting every GAZE_REPEAT_MS while
          // they stay away so the agent keeps reminding until they look back.
          if (
            now - awaySince >= thresholdMs &&
            now - lastGazeReport >= GAZE_REPEAT_MS
          ) {
            lastGazeReport = now
            report({
              kind: 'gaze_away',
              severity: 'high',
              detail: `Candidate looked away / off-camera for over ${(
                thresholdMs / 1000
              ).toFixed(0)}s.`,
            })
          }
        } else {
          awaySince = 0
        }
      }
    }, intervalMs)
  })()

  return stop
}

// Loads a lightweight COCO object detector (EfficientDet-Lite0) lazily and runs
// it on the camera stream, reporting a `phone_detected` event when a "cell
// phone" stays in frame for longer than `thresholdMs` continuously. Separate
// model/loop from the face detector. Returns a cleanup function; degrades
// gracefully if MediaPipe / the model can't load.
function startObjectDetection({
  getStream,
  thresholdMs,
  intervalMs,
  scoreThreshold,
  report,
  isDisposed,
}) {
  let detector = null
  let video = null
  let timer = null
  let phoneSince = 0
  let phoneLastSeen = 0
  let lastReport = 0
  let stopped = false

  const stop = () => {
    stopped = true
    if (timer) clearInterval(timer)
    timer = null
    try {
      detector?.close?.()
    } catch {
      /* noop */
    }
    if (video) {
      video.srcObject = null
      video.remove()
      video = null
    }
  }

  ;(async () => {
    let stream = getStream()
    if (!stream) {
      await new Promise((r) => setTimeout(r, 800))
      stream = getStream()
    }
    if (!stream || stopped || isDisposed()) return

    let ObjectDetector, FilesetResolver
    try {
      ({ ObjectDetector, FilesetResolver } = await import('@mediapipe/tasks-vision'))
    } catch (e) {
      report({
        kind: 'detection_unsupported',
        severity: 'info',
        detail: `Phone detection unavailable (MediaPipe failed to load): ${e?.message || e}`,
      })
      return
    }

    try {
      const fileset = await FilesetResolver.forVisionTasks(WASM_BASE)
      detector = await ObjectDetector.createFromOptions(fileset, {
        baseOptions: { modelAssetPath: OBJECT_MODEL_URL, delegate: 'GPU' },
        runningMode: 'VIDEO',
        scoreThreshold,
        maxResults: 5,
      })
    } catch (e) {
      report({
        kind: 'detection_unsupported',
        severity: 'info',
        detail: `Phone detector could not initialize: ${e?.message || e}`,
      })
      return
    }
    if (stopped || isDisposed()) return stop()

    video = document.createElement('video')
    video.muted = true
    video.playsInline = true
    video.srcObject = new MediaStream(stream.getVideoTracks())
    video.style.display = 'none'
    document.body.appendChild(video)
    try {
      await video.play()
    } catch {
      /* autoplay of a muted offscreen video is allowed; ignore */
    }

    timer = setInterval(() => {
      if (stopped || isDisposed() || !video || video.readyState < 2) return
      let result
      try {
        result = detector.detectForVideo(video, performance.now())
      } catch {
        return
      }
      // Count a detection as a phone only when the detector's DOMINANT (top-
      // scoring) label for that box is a phone — not just any weak secondary
      // guess. COCO's only "phone" class is "cell phone"; other smart devices
      // (laptop, tv, remote, keyboard, monitor) carry their own labels, so this
      // never fires on them. Guarding on the top category stops a box the model
      // mainly reads as another device, with a faint "cell phone" runner-up,
      // from tripping a false alarm. Substring match keeps it resilient to minor
      // label-spelling changes across model versions.
      const hasPhone = (result?.detections ?? []).some((d) => {
        const cats = d.categories ?? []
        if (!cats.length) return false
        const top = cats.reduce((best, c) => (c.score > best.score ? c : best))
        return (
          top.score >= scoreThreshold &&
          (top.categoryName || '').toLowerCase().includes('phone')
        )
      })
      const now = Date.now()
      if (hasPhone) phoneLastSeen = now
      const present = phoneLastSeen && now - phoneLastSeen <= PHONE_GRACE_MS
      if (present) {
        if (!phoneSince) {
          phoneSince = now
          lastReport = 0
        }
        if (
          now - phoneSince >= thresholdMs &&
          now - lastReport >= PHONE_REPEAT_MS
        ) {
          lastReport = now
          report({
            kind: 'phone_detected',
            severity: 'high',
            detail: 'A phone was detected in the camera frame.',
          })
        }
      } else {
        phoneSince = 0
      }
    }, intervalMs)
  })()

  return stop
}

// Eye-gaze blendshape scores above this mean the eyes are pointed off-screen.
// Tuned LOOSE on purpose: the camera usually sits at the top of the screen, so
// simply reading the question/code lower on the SAME screen reads as a mild
// down/side glance. These thresholds only trip on a clear, deliberate look away
// from the screen — not normal on-screen reading — to cut false positives.
const EYE_LOOK_H_THRESHOLD = PROCTORING.eye_look_h_threshold
const EYE_LOOK_V_THRESHOLD = PROCTORING.eye_look_v_threshold

// Count the faces large enough to be a real person sitting in the room. Each
// MediaPipe face is a set of normalized landmarks; we take its horizontal span
// (maxX - minX) as the face width relative to the frame. A second face whose
// width is below `minWidthRatio` is treated as background noise (a poster,
// photo, or reflection) and ignored — that is the main source of multi-face
// false positives. With minWidthRatio = 0 the filter is off (every face counts).
function significantFaceCount(result, minWidthRatio) {
  const faces = result?.faceLandmarks ?? []
  if (!minWidthRatio) return faces.length
  let n = 0
  for (const lm of faces) {
    let minX = 1
    let maxX = 0
    for (const p of lm) {
      if (p.x < minX) minX = p.x
      if (p.x > maxX) maxX = p.x
    }
    if (maxX - minX >= minWidthRatio) n += 1
  }
  return n
}

// True when no face is visible, the EYES are pointed away (blendshapes), or the
// head is turned off-center (silhouette landmarks). Catches both glancing with
// the eyes and turning the head.
function isLookingAway(result) {
  const faces = result?.faceLandmarks
  if (!faces || faces.length === 0) return true // no face → looking away

  // 1) Eye gaze direction (head can stay forward). MediaPipe gives a per-eye
  //    look score in [0,1]; a clear glance to the side/up/down scores high.
  const cats = result.faceBlendshapes?.[0]?.categories
  if (cats && cats.length) {
    const score = (name) =>
      cats.find((c) => c.categoryName === name)?.score ?? 0
    const lookH = Math.max(
      score('eyeLookOutLeft'),
      score('eyeLookInLeft'),
      score('eyeLookOutRight'),
      score('eyeLookInRight'),
    )
    const lookV = Math.max(
      score('eyeLookUpLeft'),
      score('eyeLookUpRight'),
      score('eyeLookDownLeft'),
      score('eyeLookDownRight'),
    )
    if (lookH > EYE_LOOK_H_THRESHOLD || lookV > EYE_LOOK_V_THRESHOLD) return true
  }

  // 2) Head turn via face-silhouette landmarks (tightened thresholds).
  const lm = faces[0]
  const nose = lm[1]
  const left = lm[234]
  const right = lm[454]
  const top = lm[10]
  const bottom = lm[152]
  if (!nose || !left || !right || !top || !bottom) return false

  const hSpan = right.x - left.x
  const vSpan = bottom.y - top.y
  if (hSpan <= 0 || vSpan <= 0) return false

  const hRatio = (nose.x - left.x) / hSpan // ~0.5 when facing forward
  const vRatio = (nose.y - top.y) / vSpan // ~0.5..0.6 when facing forward
  // Widened from 0.4/0.6 and 0.34/0.74: a candidate glancing down at the screen
  // or shifting slightly in their seat should not register as "turned away".
  // Only a pronounced head turn off-center trips this.
  return hRatio < 0.3 || hRatio > 0.7 || vRatio < 0.24 || vRatio > 0.84
}
