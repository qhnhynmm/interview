import type { MetadataRoute } from 'next'

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: 'Aurelia - AI Interview Platform',
    short_name: 'Aurelia',
    description: 'AI-powered virtual interviews with 4 cooperating agents.',
    start_url: '/',
    display: 'standalone',
    background_color: '#090407',
    theme_color: '#be123c',
    icons: [
      {
        src: '/favicon.svg',
        sizes: 'any',
        type: 'image/svg+xml',
      },
    ],
  }
}
