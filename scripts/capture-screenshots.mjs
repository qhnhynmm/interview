#!/usr/bin/env node
/**
 * Capture Aurelia UI screenshots for README (uses system Chrome).
 * Usage: node scripts/capture-screenshots.mjs [--base http://localhost:8080] [--token JWT]
 */
import puppeteer from 'puppeteer-core'
import { mkdir } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const OUT_DIR = path.join(__dirname, '..', 'docs', 'screenshots')

const args = process.argv.slice(2)
function arg(name, fallback) {
  const i = args.indexOf(name)
  return i >= 0 && args[i + 1] ? args[i + 1] : fallback
}

const BASE = arg('--base', 'http://localhost:8080').replace(/\/$/, '')
const TOKEN = arg('--token', '')
const INTERVIEW_ID = arg('--interview', '')

const CHROME_CANDIDATES = [
  '/usr/bin/google-chrome',
  '/usr/bin/google-chrome-stable',
  '/usr/bin/chromium-browser',
  '/usr/bin/chromium',
]

async function resolveChrome() {
  const { access } = await import('node:fs/promises')
  for (const p of CHROME_CANDIDATES) {
    try {
      await access(p)
      return p
    } catch {
      /* try next */
    }
  }
  throw new Error('Chrome/Chromium not found')
}

async function shot(page, name, url, { waitMs = 1200, before } = {}) {
  if (before) await before(page)
  await page.goto(url, { waitUntil: 'networkidle2', timeout: 60000 })
  if (waitMs) await new Promise((r) => setTimeout(r, waitMs))
  const file = path.join(OUT_DIR, `${name}.png`)
  await page.screenshot({ path: file, fullPage: false })
  console.log('saved', file)
}

async function main() {
  await mkdir(OUT_DIR, { recursive: true })
  const executablePath = await resolveChrome()

  const browser = await puppeteer.launch({
    executablePath,
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--window-size=1440,900'],
    defaultViewport: { width: 1440, height: 900 },
  })

  const page = await browser.newPage()

  await shot(page, '01-home', `${BASE}/`)

  await shot(page, '02-login', `${BASE}/login`)

  if (TOKEN) {
    await shot(page, '03-interview-form', `${BASE}/?tab=interview`, {
      waitMs: 1800,
      before: async (p) => {
        await p.goto(`${BASE}/`, { waitUntil: 'domcontentloaded' })
        await p.evaluate((t) => localStorage.setItem('aurelia_access_token', t), TOKEN)
      },
    })

    await shot(page, '04-results', `${BASE}/?tab=result`, {
      waitMs: 2000,
      before: async (p) => {
        await p.goto(`${BASE}/`, { waitUntil: 'domcontentloaded' })
        await p.evaluate((t) => localStorage.setItem('aurelia_access_token', t), TOKEN)
      },
    })
  }

  if (INTERVIEW_ID) {
    await shot(page, '05-interview-room', `${BASE}/interview/${INTERVIEW_ID}`, {
      waitMs: 2500,
    })
  }

  if (TOKEN && INTERVIEW_ID) {
    await shot(page, '06-candidate-profile', `${BASE}/candidate/${INTERVIEW_ID}`, {
      waitMs: 2000,
      before: async (p) => {
        await p.goto(`${BASE}/`, { waitUntil: 'domcontentloaded' })
        await p.evaluate((t) => localStorage.setItem('aurelia_access_token', t), TOKEN)
      },
    })
  }

  await browser.close()
  console.log('Done — screenshots in docs/screenshots/')
}

main().catch((err) => {
  console.error(err)
  process.exit(1)
})