import { useRef, useState } from 'react'
import { Icon, Spinner } from '../components/icons.jsx'
import { login } from '../utils/auth.js'

export default function LoginPage({ onLogin, onGoRegister }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPw, setShowPw] = useState(false)
  const [loading, setLoading] = useState(false)
  // A quick, auto-dismissing popup instead of a persistent red error block.
  const [popup, setPopup] = useState(null)
  const popupTimer = useRef(null)

  function flashPopup(msg) {
    setPopup(msg)
    clearTimeout(popupTimer.current)
    popupTimer.current = setTimeout(() => setPopup(null), 2600)
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setLoading(true)
    try {
      await login(email, password)
      onLogin()
    } catch {
      // The backend returns the same 401 whether the email is unregistered or
      // the password is wrong, so we can't tell them apart — flash a neutral
      // popup and leave the "Create one" link for users without an account.
      flashPopup('Incorrect email or password')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-page">
      {popup && (
        <div className="auth-toast" role="alert">
          <Icon name="x" size={14} />
          {popup}
        </div>
      )}
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
            <h3>AI-powered interview platform</h3>
            <p>
              Upload a CV and job description — our 4-agent panel runs the
              entire virtual interview and delivers a detailed evaluation report.
            </p>
            <div className="auth-panel-left__features">
              <div className="auth-panel-left__feature">
                <span className="auth-panel-left__feature-dot" />
                Automated interview planning
              </div>
              <div className="auth-panel-left__feature">
                <span className="auth-panel-left__feature-dot" />
                Live candidate assessment
              </div>
              <div className="auth-panel-left__feature">
                <span className="auth-panel-left__feature-dot" />
                Instant evaluation reports
              </div>
            </div>
          </div>
        </div>

        <div className="auth-panel-right">
          <h2 className="auth-title">Welcome back</h2>
          <p className="auth-sub">Sign in to your HR account</p>

          <form onSubmit={handleSubmit} className="auth-form">
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
              <label>Password</label>
              <div className="pw-wrap">
                <input
                  className="input"
                  type={showPw ? 'text' : 'password'}
                  required
                  autoComplete="current-password"
                  placeholder="••••••••"
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
              {loading ? <Spinner size={16} /> : 'Sign in'}
            </button>
          </form>

          <p className="auth-switch">
            Don&apos;t have an account?{' '}
            <button className="auth-link" type="button" onClick={() => onGoRegister(email)}>
              Create one
            </button>
          </p>
        </div>
      </div>
    </div>
  )
}
