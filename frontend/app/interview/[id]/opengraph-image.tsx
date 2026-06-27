import { ImageResponse } from 'next/og'
import { fetchInterview } from '@/lib/interview'

export const runtime = 'edge'

export const alt = 'Aurelia AI Interview'
export const size = {
  width: 1200,
  height: 630,
}
export const contentType = 'image/png'

async function fetchData(id: string) {
  return fetchInterview(id)
}

export default async function Image({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  const data = await fetchData(id) || {}

  const candidate = data?.candidate_name || 'Candidate'
  const position = data?.position || 'Role'
  const language = data?.language === 'vi' ? 'Tiếng Việt' : 'English'
  const scheduled = data?.scheduled_at
    ? new Date(data.scheduled_at).toLocaleString('en-US', {
        month: 'long',
        day: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
      })
    : 'Scheduled soon'

  return new ImageResponse(
    (
      <div
        style={{
          height: '100%',
          width: '100%',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: '#090407',
          backgroundImage: 'radial-gradient(circle at 25% 20%, #be123c 0%, transparent 50%)',
          color: 'white',
          fontFamily: 'system-ui, sans-serif',
          padding: 60,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 30 }}>
          <div
            style={{
              width: 64,
              height: 64,
              borderRadius: 12,
              background: 'linear-gradient(135deg, #e85d75, #be123c)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: 32,
              fontWeight: 800,
            }}
          >
            A
          </div>
          <div style={{ fontSize: 28, fontWeight: 700 }}>Aurelia</div>
        </div>

        <div style={{ fontSize: 52, fontWeight: 800, textAlign: 'center', lineHeight: 1.05, maxWidth: 1000, marginBottom: 8 }}>
          {candidate}
        </div>
        <div style={{ fontSize: 32, color: '#f4728b', marginBottom: 16 }}>
          {position}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 24, marginBottom: 32 }}>
          <div style={{ fontSize: 22, color: '#d8c2c7' }}>
            📅 {scheduled}
          </div>
          <div style={{ fontSize: 22, color: '#d8c2c7' }}>
            🗣️ {language}
          </div>
        </div>

        <div
          style={{
            padding: '10px 24px',
            background: 'rgba(190, 18, 60, 0.25)',
            border: '1px solid #be123c',
            borderRadius: 999,
            fontSize: 18,
            display: 'flex',
            alignItems: 'center',
            gap: 10,
            fontWeight: 600,
          }}
        >
          <span>🤖</span> 4 AI Agents • Live Interview
        </div>

        <div style={{ position: 'absolute', bottom: 36, fontSize: 16, color: '#9a7b82', letterSpacing: '0.5px' }}>
          AURELIA • AI-POWERED INTERVIEWS
        </div>
      </div>
    ),
    {
      ...size,
    }
  )
}
