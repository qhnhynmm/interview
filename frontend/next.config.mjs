import path from 'path'

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
        destination: 'http://localhost:8000/api/:path*',
      },
    ]
  },
  // Output standalone for better Docker images (optional but recommended)
  output: 'standalone',
}

export default nextConfig
