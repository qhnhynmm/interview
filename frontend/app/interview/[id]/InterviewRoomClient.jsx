'use client'

import dynamic from 'next/dynamic'

const InterviewRoomDynamic = dynamic(
  () => import('../../../src/legacy-pages/InterviewRoom.jsx'),
  {
    loading: () => (
      <div style={{ display: 'flex', height: '100vh', alignItems: 'center', justifyContent: 'center', color: '#9a7b82' }}>
        Loading interview room…
      </div>
    ),
  }
)

export default function InterviewRoomClient({ interviewId }) {
  return <InterviewRoomDynamic interviewId={interviewId} />
}
