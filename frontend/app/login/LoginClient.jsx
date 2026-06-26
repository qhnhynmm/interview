'use client'

import LoginPage from '@/src/legacy-pages/LoginPage.jsx'

export default function LoginClient() {
  function handleSuccess() {
    window.location.href = '/'
  }

  return (
    <LoginPage
      onLogin={handleSuccess}
      onGoRegister={() => (window.location.href = '/register')}
    />
  )
}
