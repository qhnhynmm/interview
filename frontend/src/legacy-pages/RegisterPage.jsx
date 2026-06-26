'use client'

import { useState } from 'react'
import { Icon, Spinner } from '../components/icons.jsx'
import { register } from '../utils/auth.js'

export default function RegisterPage({ onRegister, onGoLogin, initialEmail = '' }) {
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState(initialEmail)
  const [password, setPassword] = useState('')
  const [showPw, setShowPw] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  async function handleSubmit(e) {
    e.preventDefault()
    setError(null)
    if (password.length < 8) {
      setError('Password must be at least 8 characters')
      return
    }
    setLoading(true)
    try {
      await register(username, email, password)
      onRegister()
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card card">
        <div className="auth-panel-left">
          <div className="auth-panel-left__brand">
            <div className="brand__mark">
              <Icon name="spark" size={22} />
            </div>
            <div>
              <div className="brand__name">InterviewAI</div>
              <div className="brand__sub">Aurelia · HR Platform</div>
            </div>
          </div>

          <div className="auth-panel-left__tagline">
            <h3>Start your free HR account</h3>
            <p>
              Join your team on InterviewAI Aurelia and manage AI-assisted
              interviews from candidate submission to final report.
            </p>
            <div className="auth-panel-left__features">
              <div className="auth-panel-left__feature">
                <span className="auth-panel-left__feature-dot" />
                4-agent interview panel
              </div>
              <div className="auth-panel-left__feature">
                <span className="auth-panel-left__feature-dot" />
                Coding assignment sandbox
              </div>
              <div className="auth-panel-left__feature">
                <span className="auth-panel-left__feature-dot" />
                Detailed scoring & reports
              </div>
            </div>
          </div>
        </div>

        <div className="auth-panel-right">
          <h2 className="auth-title">Create account</h2>
          <p className="auth-sub">Register your HR account to get started</p>

          {error && <div className="auth-error">{error}</div>}

          <form onSubmit={handleSubmit} className="auth-form">
            <div className="field">
              <label>Username</label>
              <input
                className="input"
                type="text"
                required
                autoComplete="name"
                placeholder="Jane Smith"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
              />
            </div>

            <div className="field">
              <label>Email</label>
              <input
                className="input"
                type="email"
                required
                autoComplete="email"
                placeholder="hr@company.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>

            <div className="field">
              <label>Password <span className="hint">(min 8 characters)</span></label>
              <div className="pw-wrap">
                <input
                  className="input"
                  type={showPw ? 'text' : 'password'}
                  required
                  autoComplete="new-password"
                  placeholder="••••••••"
                  minLength={8}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
                <button
                  type="button"
                  className="pw-toggle"
                  aria-label={showPw ? 'Hide password' : 'Show password'}
                  onClick={() => setShowPw((v) => !v)}
                >
                  <Icon name={showPw ? 'eye-off' : 'eye'} size={16} />
                </button>
              </div>
            </div>

            <button className="btn btn--primary auth-submit" disabled={loading} type="submit">
              {loading ? <Spinner size={16} /> : 'Create account'}
            </button>
          </form>

          <p className="auth-switch">
            Already have an account?{' '}
            <button className="auth-link" type="button" onClick={onGoLogin}>
              Sign in
            </button>
          </p>
        </div>
      </div>
    </div>
  )
}
