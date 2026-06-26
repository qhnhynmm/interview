'use client'

import RegisterPage from '@/src/legacy-pages/RegisterPage.jsx'

export default function RegisterClient() {
  function handleSuccess() {
    window.location.href = '/'
  }

  return (
    <RegisterPage
      onRegister={handleSuccess}
      onGoLogin={() => (window.location.href = '/login')}
    />
  )
}
