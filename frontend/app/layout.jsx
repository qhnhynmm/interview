import './globals.css'

export const metadata = {
  metadataBase: new URL(
    process.env.NEXT_PUBLIC_SITE_URL || 
    (process.env.VERCEL_URL ? `https://${process.env.VERCEL_URL}` : 'http://localhost:3000')
  ),
  title: {
    default: 'InterviewAI Aurelia — AI Interview Platform',
    template: '%s | Aurelia',
  },
  description:
    'Aurelia — AI-powered virtual interview platform with 4 cooperating agents. HR create interviews, candidates join live sessions, and receive detailed evaluation reports.',
  icons: {
    icon: '/favicon.svg',
  },
  openGraph: {
    title: 'InterviewAI Aurelia — AI Interview Platform',
    description:
      'Run smarter interviews. Upload a CV + JD. Four specialized AI agents conduct the full virtual interview and deliver a detailed report.',
    images: [
      {
        url: '/favicon.svg',
        width: 1200,
        height: 630,
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'InterviewAI Aurelia — AI Interview Platform',
    description: 'AI-powered virtual interviews with detailed evaluation reports.',
  },
  robots: {
    index: true,
    follow: true,
  },
  alternates: {
    canonical: '/',
  },
}

export const viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 1,
}

import JsonLd from './components/JsonLd'

export default function RootLayout({ children }) {
  const orgSchema = {
    '@context': 'https://schema.org',
    '@type': 'Organization',
    name: 'InterviewAI Aurelia',
    url: process.env.NEXT_PUBLIC_SITE_URL || 'http://localhost:3000',
    logo: (process.env.NEXT_PUBLIC_SITE_URL || 'http://localhost:3000') + '/favicon.svg',
    description: 'AI-powered virtual interview platform with 4 cooperating agents.',
    sameAs: [],
  }

  const softwareSchema = {
    '@context': 'https://schema.org',
    '@type': 'SoftwareApplication',
    name: 'Aurelia - AI Interview Platform',
    applicationCategory: 'BusinessApplication',
    operatingSystem: 'Web',
    offers: {
      '@type': 'Offer',
      price: '0',
      priceCurrency: 'USD',
    },
  }

  return (
    <html lang="en">
      <body>
        <JsonLd data={orgSchema} />
        <JsonLd data={softwareSchema} />
        {children}
      </body>
    </html>
  )
}
