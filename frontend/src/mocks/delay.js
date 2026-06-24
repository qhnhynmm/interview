import { MOCK_DELAY_MS } from '@/constants/mock.js'

export function mockDelay(ms = MOCK_DELAY_MS) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}