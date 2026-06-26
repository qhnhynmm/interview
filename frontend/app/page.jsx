import HRDashboardClient from './HRDashboardClient'

/** @type {import('next').Metadata} */
export const metadata = {
  title: 'HR Dashboard',
  description: 'Manage AI-powered interviews, view results, and generate candidate links.',
  robots: {
    index: false, // Internal tool
    follow: false,
  },
}

export default function RootHRShell() {
  return <HRDashboardClient />
}
