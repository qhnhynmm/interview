import type { MetadataRoute } from 'next'

export default function robots(): MetadataRoute.Robots {
  const base = process.env.NEXT_PUBLIC_SITE_URL || 'http://localhost:3000'

  return {
    rules: [
      {
        userAgent: '*',
        allow: ['/interview/'],           // allow candidate interview links for previews
        disallow: [
          '/login',
          '/register',
          '/candidate/',
          '/?tab=interview',
          '/?tab=result',
        ],
      },
    ],
    sitemap: `${base}/sitemap.xml`,
  }
}
