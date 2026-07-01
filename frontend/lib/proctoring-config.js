// Proctoring configuration for Next.js (single source of truth).
// Override via NEXT_PUBLIC_PROCTORING_* env vars when needed.

const defaults = {
  flicker_ms: 50,
  blur_grace_ms: 1200,
  monitor_repeat_ms: 8000,
  gaze_repeat_ms: 5000,
  tab_repeat_ms: 3000,
  face_repeat_ms: 400,
  phone_repeat_ms: 250,
  multi_grace_ms: 700,
  phone_grace_ms: 500,

  enable_gaze: true,
  enable_multi_face: true,
  enable_phone: true,

  gaze_threshold_ms: 3000,
  gaze_interval_ms: 250,
  eye_look_h_threshold: 0.72,
  eye_look_v_threshold: 0.8,

  multi_face_threshold_ms: 2500,
  min_face_detection_confidence: 0.78,
  multi_face_min_size_ratio: 0.12,

  phone_threshold_ms: 500,
  phone_interval_ms: 400,
  phone_score_threshold: 0.5,

  medipipe_version: '0.10.18',
  wasm_base: 'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision',
  face_model_url:
    'https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task',
  object_model_url:
    'https://storage.googleapis.com/mediapipe-models/object_detector/efficientdet_lite2/float16/1/efficientdet_lite2.tflite',
}

// Merge with any public env overrides (NEXT_PUBLIC_PROCTORING_...)
function getProctoringConfig() {
  const env = typeof process !== 'undefined' ? process.env : {}

  const cfg = { ...defaults }

  // Simple overrides if present (add more as needed)
  if (env.NEXT_PUBLIC_PROCTORING_ENABLE_GAZE != null) {
    cfg.enable_gaze = env.NEXT_PUBLIC_PROCTORING_ENABLE_GAZE === 'true'
  }
  if (env.NEXT_PUBLIC_PROCTORING_ENABLE_MULTI_FACE != null) {
    cfg.enable_multi_face = env.NEXT_PUBLIC_PROCTORING_ENABLE_MULTI_FACE === 'true'
  }
  if (env.NEXT_PUBLIC_PROCTORING_ENABLE_PHONE != null) {
    cfg.enable_phone = env.NEXT_PUBLIC_PROCTORING_ENABLE_PHONE === 'true'
  }

  return cfg
}

export const PROCTORING = getProctoringConfig()

// For hooks that previously read global __PROCTORING__
export const getProctoring = () => PROCTORING
