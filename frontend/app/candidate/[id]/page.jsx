import CandidateProfile from '@/src/legacy-pages/CandidateProfile.jsx'

export async function generateMetadata({ params }) {
  const { id } = await params
  const baseUrl = process.env.NEXT_PUBLIC_SITE_URL || 'http://localhost:3000'
  const canonical = `${baseUrl}/candidate/${id}`

  return {
    title: `Candidate Profile • ${id}`,
    description: 'Detailed candidate evaluation and interview recording.',
    alternates: { canonical },
    robots: {
      index: false,
      follow: false,
    },
  }
}

export default async function CandidatePage({ params }) {
  const { id } = await params
  return <CandidateProfile candidateId={id} />
}
