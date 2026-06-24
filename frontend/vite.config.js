import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { readFileSync } from 'fs'
import { fileURLToPath } from 'url'

const configPath = fileURLToPath(
  new URL('../configs/frontend-services.yml', import.meta.url),
)
const srcPath = fileURLToPath(new URL('./src', import.meta.url))

function parseYml(content) {
  const cfg = {}
  const lines = content.split('\n')
  let currentSection = null
  let currentSub = null
  let indent = 0

  for (const line of lines) {
    // Skip comments and empty lines
    if (line.trim().startsWith('#') || !line.trim()) continue

    // Check for section headers (e.g., "proctoring:")
    const sectionMatch = line.match(/^(\w+):\s*$/)
    if (sectionMatch && !line.includes(': "') && !line.includes(": '")) {
      currentSection = sectionMatch[1]
      cfg[currentSection] = {}
      currentSub = null
      continue
    }

    // Check for nested key-value
    const m = line.match(/^[ \t]+(\w+):\s*["']?(.+?)["']?\s*$/)
    if (m) {
      const key = m[1]
      const value = m[2].trim()
      // Try to parse as number
      let parsedValue = value
      if (!isNaN(value) && value !== '') {
        parsedValue = Number(value)
      } else if (value === 'true') {
        parsedValue = true
      } else if (value === 'false') {
        parsedValue = false
      }

      if (currentSection) {
        cfg[currentSection][key] = parsedValue
      } else {
        cfg[key] = parsedValue
      }
    }
  }
  return cfg
}

const cfg = parseYml(readFileSync(configPath, 'utf8'))

// Flatten proctoring config for easier access
const proctoring = cfg.proctoring || {}

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { '@': srcPath },
  },
  define: {
    // Expose proctoring config as global constants
    'process.env.PROCTORING': JSON.stringify(proctoring),
    __PROCTORING__: JSON.stringify(proctoring),
  },
  server: {
    port: Number(cfg.frontend?.dev_port || 5173),
    proxy: {
      '/api': {
        target: cfg.frontend?.backend_url || 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
