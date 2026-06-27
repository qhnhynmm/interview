import { ImageResponse } from 'next/og'
import { fetchInterview } from '@/lib/interview'

export const runtime = 'edge'
export const alt = 'Aurelia AI Interview'
export const size = { width: 1200, height: 630 }
export const contentType = 'image/png'

export default async function TwitterImage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  const data = await fetchInterview(id)

  const candidate = data?.candidate_name || 'Candidate'
  const position = data?.position || 'Role'
  const scheduled = data?.scheduled_at
    ? new Date(data.scheduled_at).toLocaleDateString('en-US', { month: 'long', day: 'numeric' })
    : ''

  return new ImageResponse(
    (
      <div
        style={{
          height: '100%',
          width: '100%',
          display: 'flex',
          flexDirection: 'column',
          backgroundColor: '#090407',
          color: 'white',
          padding: 60,
          fontFamily: 'system-ui',
        }}
      >
        <div style={{ fontSize: 28, opacity: 0.8, marginBottom: 8 }}>Aurelia AI Interview</div>
        <div style={{ fontSize: 58, fontWeight: 800, lineHeight: 1.1 }}>{candidate}</div>
        <div style={{ fontSize: 34, color: '#f4728b', marginTop: 4 }}>{position}</div>
        {scheduled && <div style={{ fontSize: 22, marginTop: 20, color: '#d8c2c7' }}>📅 {scheduled}</div>}
        <div style={{ marginTop: 'auto', fontSize: 18, color: '#9a7b82' }}>Powered by 4 specialized AI agents</div>
      </div>
    ),
    { ...size }
  )
}
