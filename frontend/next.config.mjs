import path from 'path'

// Docker build: BACKEND_URL=http://127.0.0.1:8000 (host network, same as backend container)
const backendUrl = (process.env.BACKEND_URL || 'http://localhost:8000').replace(/\/$/, '')

/** @type {import('next').NextConfig} */
const nextConfig = {
  // Support the existing @/ alias (matches jsconfig)
  webpack: (config) => {
    config.resolve.alias = {
      ...config.resolve.alias,
      '@': path.resolve(process.cwd(), 'src'),
      '@/src': path.resolve(process.cwd(), 'src'),
      '@/legacy-pages': path.resolve(process.cwd(), 'src/legacy-pages'),
      '@/components': path.resolve(process.cwd(), 'src/components'),
    }
    return config
  },
  // Dev proxy so /api calls go to backend (same as old Vite proxy)
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${backendUrl}/api/:path*`,
      },
    ]
  },
  // Output standalone for better Docker images (optional but recommended)
  output: 'standalone',
}

export default nextConfig
