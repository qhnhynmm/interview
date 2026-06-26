import RegisterClient from './RegisterClient'

/** @type {import('next').Metadata} */
export const metadata = {
  title: 'Create account',
  description: 'Create an HR account on InterviewAI Aurelia.',
  robots: {
    index: false,
    follow: false,
  },
}

export default function RegisterPage() {
  return <RegisterClient />
}
