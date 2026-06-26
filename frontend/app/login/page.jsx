import LoginClient from './LoginClient'

/** @type {import('next').Metadata} */
export const metadata = {
  title: 'Sign in',
  description: 'Sign in to InterviewAI Aurelia to manage AI interviews.',
  robots: {
    index: false,
    follow: false,
  },
}

export default function LoginPage() {
  return <LoginClient />
}
