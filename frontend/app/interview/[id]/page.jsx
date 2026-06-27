import JsonLd from '@/app/components/JsonLd'
import { fetchInterview } from '@/lib/interview'
import InterviewRoomClient from './InterviewRoomClient'

export async function generateMetadata({ params }) {
  const { id } = await params
  const data = await fetchInterview(id)

  const candidate = data?.candidate_name || 'Candidate'
  const position = data?.position || 'Position'
  const scheduled = data?.scheduled_at
    ? new Date(data.scheduled_at).toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
      })
    : null

  const title = `${candidate} — ${position} Interview`
  const description = scheduled
    ? `Your Aurelia AI interview for ${position} is scheduled for ${scheduled}. Join the session on time.`
    : `Join your AI-powered interview on Aurelia for the ${position} role.`

  const baseUrl = process.env.NEXT_PUBLIC_SITE_URL || 'http://localhost:3000'
  const canonical = `${baseUrl}/interview/${id}`
  const lang = data?.language || 'en'

  return {
    title,
    description,
    alternates: {
      canonical,
      languages: {
        'en': `${baseUrl}/interview/${id}`,
        'vi': `${baseUrl}/interview/${id}`,
      },
    },
    openGraph: {
      title: `${title} | Aurelia`,
      description,
      url: canonical,
      locale: lang === 'vi' ? 'vi_VN' : 'en_US',
      images: [{ url: '/favicon.svg' }],
    },
    robots: {
      index: false,
      follow: true,
    },
  }
}

export default async function InterviewPage({ params }) {
  const { id } = await params
  const data = await fetchInterview(id)

  // Advanced Structured Data: JobPosting + Interview context
  const jobSchema = data
    ? {
        '@context': 'https://schema.org',
        '@type': 'JobPosting',
        title: data.position,
        description: data.jd_text || 'AI-powered technical interview',
        datePosted: data.created_at || new Date().toISOString(),
        validThrough: data.scheduled_at,
        hiringOrganization: {
          '@type': 'Organization',
          name: 'InterviewAI Aurelia',
        },
        jobLocation: {
          '@type': 'Place',
          address: {
            '@type': 'PostalAddress',
            addressCountry: 'Remote / Virtual',
          },
        },
        employmentType: 'CONTRACTOR',
        directApply: false,
      }
    : null

  const interviewEvent = data
    ? {
        '@context': 'https://schema.org',
        '@type': 'Event',
        name: `${data.position} Interview with Aurelia`,
        startDate: data.scheduled_at,
        eventStatus: 'https://schema.org/EventScheduled',
        eventAttendanceMode: 'https://schema.org/OnlineEventAttendanceMode',
        location: {
          '@type': 'VirtualLocation',
          url: `${process.env.NEXT_PUBLIC_SITE_URL || 'http://localhost:3000'}/interview/${id}`,
        },
        organizer: {
          '@type': 'Organization',
          name: 'Aurelia AI Interview Platform',
        },
        description: `AI interview conducted by 4 specialized agents for the ${data.position} role.`,
      }
    : null

  const breadcrumbSchema = {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: [
      {
        '@type': 'ListItem',
        position: 1,
        name: 'Aurelia',
        item: process.env.NEXT_PUBLIC_SITE_URL || 'http://localhost:3000',
      },
      {
        '@type': 'ListItem',
        position: 2,
        name: 'Interview',
        item: `${process.env.NEXT_PUBLIC_SITE_URL || 'http://localhost:3000'}/interview/${id}`,
      },
    ],
  }

  return (
    <main>
      {jobSchema && <JsonLd data={jobSchema} />}
      {interviewEvent && <JsonLd data={interviewEvent} />}
      <JsonLd data={breadcrumbSchema} />
      <InterviewRoomClient interviewId={id} />
    </main>
  )
}



