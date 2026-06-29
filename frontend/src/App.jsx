'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import './App.css'
import { Icon } from './components/icons.jsx'
import Home from './legacy-pages/Home.jsx'
import Interview from './legacy-pages/Interview.jsx'
import Result from './legacy-pages/Result.jsx'
import LoginPage from './legacy-pages/LoginPage.jsx'
import RegisterPage from './legacy-pages/RegisterPage.jsx'
import { loadInterviews, submitInterview } from './utils/interviews.js'
import { fetchMe, logout } from './utils/auth.js'
import { POLL_MS, TABS } from './constants/app.js'

const PROTECTED = new Set(['interview', 'result'])

export default function App() {
  const [tab, setTab] = useState('home')

  // Safe client-only initial tab from URL (prevents window is not defined during SSR)
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const p = new URLSearchParams(window.location.search).get('tab')
      if (p) setTab(p)
    }
  }, [])
  const [interviews, setInterviews] = useState([])
  const [loadError, setLoadError] = useState(null)
  const [loading, setLoading] = useState(false)
  const inFlight = useRef(false)

  // null = checking token, false = guest, object = logged-in user
  const [user, setUser] = useState(null)
  // 'login' | 'register' | null
  const [authView, setAuthView] = useState(null)
  const [pendingTab, setPendingTab] = useState(null)
  // Email carried over from a failed login so Register pre-fills it.
  const [prefillEmail, setPrefillEmail] = useState('')

  // Avatar dropdown
  const [dropdownOpen, setDropdownOpen] = useState(false)
  const dropdownRef = useRef(null)

  // Restore session on mount
  useEffect(() => {
    fetchMe().then((u) => setUser(u ?? false))
  }, [])

  // Close dropdown when clicking outside
  useEffect(() => {
    function onOutsideClick(e) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setDropdownOpen(false)
      }
    }
    document.addEventListener('mousedown', onOutsideClick)
    return () => document.removeEventListener('mousedown', onOutsideClick)
  }, [])

  const refresh = useCallback(async () => {
    if (inFlight.current) return
    inFlight.current = true
    setLoading(true)
    try {
      const list = await loadInterviews()
      setInterviews(list)
      setLoadError(null)
    } catch (err) {
      setLoadError(err.message)
    } finally {
      setLoading(false)
      inFlight.current = false
    }
  }, [])

  const selectTab = useCallback(
    (id) => {
      if (PROTECTED.has(id) && !user) {
        setPendingTab(id)
        setAuthView('login')
        return
      }
      setAuthView(null)
      setPendingTab(null)
      setTab(id)
      if (id === 'result') refresh()
    },
    [user, refresh],
  )

  async function handleAuthSuccess() {
    const u = await fetchMe()
    setUser(u ?? false)
    setAuthView(null)
    const dest = pendingTab ?? 'interview'
    setPendingTab(null)
    setTab(dest)
    if (dest === 'result') refresh()
  }

  function handleLogout() {
    logout()
    setUser(false)
    setDropdownOpen(false)
    setTab('home')
    setAuthView(null)
    setPendingTab(null)
  }

  // Poll for fresh state while Result tab is open
  useEffect(() => {
    if (tab !== 'result') return
    const id = setInterval(refresh, POLL_MS)
    return () => clearInterval(id)
  }, [tab, refresh])

  // Refetch on browser focus
  useEffect(() => {
    function onVisible() {
      if (document.visibilityState === 'visible' && tab === 'result') refresh()
    }
    document.addEventListener('visibilitychange', onVisible)
    window.addEventListener('focus', onVisible)
    return () => {
      document.removeEventListener('visibilitychange', onVisible)
      window.removeEventListener('focus', onVisible)
    }
  }, [tab, refresh])

  async function handleCreate(form) {
    const record = form.__record ?? (await submitInterview(form))
    setInterviews((list) => [record, ...list])
    return record
  }

  function goHomeStart(target = 'interview') {
    selectTab(target)
  }

  // Shared nav right — changes based on auth state
  function NavRight() {
    if (user === null) {
      // Still checking token — render nothing to avoid flicker
      return <div className="nav__right" />
    }

    if (!user) {
      return (
        <div className="nav__right">
          <button
            className="btn btn--ghost btn--sm"
            onClick={() => { setPendingTab(null); setAuthView('login') }}
          >
            Sign in
          </button>
          <button
            className="btn btn--primary btn--sm"
            onClick={() => { setPendingTab(null); setAuthView('register') }}
          >
            Register
          </button>
        </div>
      )
    }

    const initial = user.username?.[0]?.toUpperCase() ?? '?'
    return (
      <div className="nav__right" ref={dropdownRef}>
        <button
          className="user-avatar-btn"
          onClick={() => setDropdownOpen((v) => !v)}
          aria-expanded={dropdownOpen}
        >
          <div className="user-avatar">{initial}</div>
          <span className="user-avatar__name">{user.username}</span>
          <Icon name="chevron" size={14} style={{ transform: dropdownOpen ? 'rotate(180deg)' : 'rotate(0deg)', transition: 'transform 0.18s' }} />
        </button>

        {dropdownOpen && (
          <div className="user-dropdown">
            <div className="user-dropdown__info">
              <div className="user-dropdown__avatar">{initial}</div>
              <div>
                <div className="user-dropdown__name">{user.username}</div>
                <div className="user-dropdown__email">{user.email}</div>
              </div>
            </div>
            <div className="user-dropdown__divider" />
            <button className="user-dropdown__item user-dropdown__item--danger" onClick={handleLogout}>
              <Icon name="logout" size={15} />
              Sign out
            </button>
          </div>
        )}
      </div>
    )
  }

  // Shared tabs nav
  function NavTabs({ activeTab }) {
    return (
      <nav className="tabs">
        {TABS.map((t) => (
          <button
            key={t.id}
            className={`tab${activeTab === t.id && !authView ? ' is-active' : ''}`}
            onClick={() => {
              if (!PROTECTED.has(t.id)) {
                setAuthView(null)
                setPendingTab(null)
                setTab(t.id)
              } else {
                selectTab(t.id)
              }
            }}
          >
            {t.label}
          </button>
        ))}
      </nav>
    )
  }

  // Auth view (login/register) — no navigation pane, same background tone
  if (authView) {
    return (
      <div className="app auth-app">
        <main className="app__main auth-app__main">
          <button
            className="auth-back-btn"
            onClick={() => { setAuthView(null); setPendingTab(null) }}
          >
            <Icon name="arrow" size={14} style={{ transform: 'rotate(180deg)' }} />
            Back to home
          </button>

          {authView === 'register' ? (
            <RegisterPage
              onRegister={handleAuthSuccess}
              onGoLogin={() => setAuthView('login')}
              initialEmail={prefillEmail}
            />
          ) : (
            <LoginPage
              onLogin={handleAuthSuccess}
              onGoRegister={(email) => { setPrefillEmail(email || ''); setAuthView('register') }}
            />
          )}
        </main>

        <footer className="footer">
          <div className="container" style={{ display: 'flex', justifyContent: 'space-between', width: '100%', flexWrap: 'wrap', gap: 8 }}>
            <span>© 2026 InterviewAI Aurelia — internal HR tool.</span>
            <span>Powered by Aurelia · 4-agent interview panel</span>
          </div>
        </footer>
      </div>
    )
  }

  return (
    <div className="app">
      <header className="nav">
        <div className="container nav__inner">
          <div className="brand">
            <div className="brand__mark"><Icon name="spark" size={21} /></div>
            <div>
              <div className="brand__name">InterviewAI Aurelia</div>
              <div className="brand__sub">AI interview assistant · Aurelia</div>
            </div>
          </div>

          <NavTabs activeTab={tab} />
          <NavRight />
        </div>
      </header>

      <main className="app__main">
        {tab === 'home' && <Home onStart={goHomeStart} />}
        {tab === 'interview' && <Interview onCreate={handleCreate} />}
        {tab === 'result' && (
          <Result
            interviews={interviews}
            loadError={loadError}
            loading={loading}
            onNew={() => selectTab('interview')}
            onRefresh={refresh}
          />
        )}
      </main>

      <footer className="footer">
        <div className="container" style={{ display: 'flex', justifyContent: 'space-between', width: '100%', flexWrap: 'wrap', gap: 8 }}>
          <span>© 2026 InterviewAI Aurelia — internal HR tool.</span>
          <span>Powered by Aurelia · 4-agent interview panel</span>
        </div>
      </footer>
    </div>
  )
}
