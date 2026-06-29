// New-interview page: the empty form state.

import { DEFAULT_LIVE_VOICE } from './voices.js'

export const EMPTY = {
  candidateName: '',
  email: '',
  role: '',
  seniority: 'Mid',
  language: 'en',
  voice: DEFAULT_LIVE_VOICE,
  jd: '',
  requests: '',
  cvFile: null,
}
