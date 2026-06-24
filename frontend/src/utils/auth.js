import { MOCK_DEMO_EMAIL, MOCK_DEMO_PASSWORD, USE_MOCK_API } from '@/constants/mock.js'
import { mockDelay } from '@/mocks/delay.js'
import { clearMockUser, getMockUser, setMockUser } from '@/mocks/store.js'

const TOKEN_KEY = 'gt_access_token'

export function getToken() {
  return localStorage.getItem(TOKEN_KEY)
}

function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY)
}

export function authHeaders() {
  const token = getToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
}

export async function login(email, password) {
  if (USE_MOCK_API) {
    await mockDelay()
    const ok = (email === MOCK_DEMO_EMAIL && password === MOCK_DEMO_PASSWORD)
      || password.length >= 4
    if (!ok) throw new Error('Invalid email or password (mock: use hr@demo.com / demo123)')
    const user = { id: 1, username: email.split('@')[0], email }
    setMockUser(user)
    setToken('mock_access_token')
    return { access_token: 'mock_access_token', user }
  }

  // const res = await fetch(`${API}/auth/login`, {
  //   method: 'POST',
  //   headers: { 'Content-Type': 'application/json' },
  //   body: JSON.stringify({ email, password }),
  // })
  // if (!res.ok) {
  //   const err = await res.json().catch(() => ({}))
  //   throw new Error(err.detail || 'Login failed')
  // }
  // const data = await res.json()
  // setToken(data.access_token)
  // return data
  throw new Error('Backend API is disabled. Set USE_MOCK_API = true in src/constants/mock.js')
}

export async function register(username, email, password) {
  if (USE_MOCK_API) {
    await mockDelay()
    if (!username?.trim() || !email?.trim() || password.length < 4) {
      throw new Error('Please fill in all fields (password min 4 chars)')
    }
    const user = { id: Date.now(), username: username.trim(), email: email.trim() }
    setMockUser(user)
    setToken('mock_access_token')
    return { access_token: 'mock_access_token', user }
  }

  // const res = await fetch(`${API}/auth/register`, {
  //   method: 'POST',
  //   headers: { 'Content-Type': 'application/json' },
  //   body: JSON.stringify({ username, email, password }),
  // })
  // if (!res.ok) {
  //   const err = await res.json().catch(() => ({}))
  //   throw new Error(err.detail || 'Registration failed')
  // }
  // const data = await res.json()
  // setToken(data.access_token)
  // return data
  throw new Error('Backend API is disabled. Set USE_MOCK_API = true in src/constants/mock.js')
}

export async function fetchMe() {
  if (USE_MOCK_API) {
    await mockDelay(150)
    const token = getToken()
    if (!token) return null
    return getMockUser() ?? { id: 1, username: 'hr_demo', email: MOCK_DEMO_EMAIL }
  }

  // const token = getToken()
  // if (!token) return null
  // const res = await fetch(`${API}/auth/me`, {
  //   headers: { Authorization: `Bearer ${token}` },
  // })
  // if (!res.ok) {
  //   clearToken()
  //   return null
  // }
  // return res.json()
  const token = getToken()
  if (!token) return null
  clearToken()
  return null
}

export function logout() {
  clearToken()
  if (USE_MOCK_API) clearMockUser()
}