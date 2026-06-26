'use client'

import { useEffect } from 'react'

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  useEffect(() => {
    console.error('Interview page error:', error)
  }, [error])

  return (
    <div style={{
      height: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: '#090407',
      color: '#fff',
      padding: 24,
      textAlign: 'center',
    }}>
      <div>
        <h2 style={{ fontSize: 20, marginBottom: 12 }}>Something went wrong</h2>
        <p style={{ color: '#9a7b82', marginBottom: 20 }}>Unable to load the interview session.</p>
        <button
          onClick={() => reset()}
          style={{
            background: '#be123c',
            color: 'white',
            border: 'none',
            padding: '10px 20px',
            borderRadius: 8,
            cursor: 'pointer',
          }}
        >
          Try again
        </button>
      </div>
    </div>
  )
}
