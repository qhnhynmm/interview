import CandidateProfile from '@/src/legacy-pages/CandidateProfile.jsx'

export async function generateMetadata({ params }) {
  const baseUrl = process.env.NEXT_PUBLIC_SITE_URL || 'http://localhost:3000'
  const canonical = `${baseUrl}/candidate/${params.id}`

  return {
    title: `Candidate Profile • ${params.id}`,
    description: 'Detailed candidate evaluation and interview recording.',
    alternates: { canonical },
    robots: {
      index: false,
      follow: false,
    },
  }
}

export default function CandidatePage({ params }) {
  return <CandidateProfile candidateId={params.id} />
}
