#!/usr/bin/env node
/**
 * Capture Aurelia UI screenshots for README (uses system Chrome).
 *
 * Usage:
 *   node scripts/capture-screenshots.mjs \
 *     --base http://localhost:8080 \
 *     --api http://localhost:8000 \
 *     --token <JWT> \
 *     --interview-rules <id> \
 *     --interview-code <id> \
 *     --interview-done <id>
 */
import puppeteer from 'puppeteer-core'
import { mkdir } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const OUT_DIR = path.join(__dirname, '..', 'docs', 'screenshots')

const args = process.argv.slice(2)
function arg(name, fallback = '') {
  const i = args.indexOf(name)
  return i >= 0 && args[i + 1] ? args[i + 1] : fallback
}

const BASE = arg('--base', 'http://localhost:8080').replace(/\/$/, '')
const API = arg('--api', 'http://localhost:8000').replace(/\/$/, '')
const TOKEN = arg('--token')
const ID_RULES = arg('--interview-rules', arg('--interview'))
const ID_CODE = arg('--interview-code')
const ID_DONE = arg('--interview-done')

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

async function setToken(page, token) {
  if (!token) return
  await page.goto(`${BASE}/`, { waitUntil: 'domcontentloaded', timeout: 60000 })
  await page.evaluate((t) => localStorage.setItem('aurelia_access_token', t), token)
}

async function shot(page, name, { waitMs = 1200 } = {}) {
  if (waitMs) await new Promise((r) => setTimeout(r, waitMs))
  const file = path.join(OUT_DIR, `${name}.png`)
  await page.screenshot({ path: file, fullPage: false })
  console.log('saved', file)
}

async function goto(page, url) {
  await page.goto(url, { waitUntil: 'networkidle2', timeout: 90000 })
}

async function acceptRules(page) {
  await page.waitForFunction(
    () => document.body.innerText.includes('Tôi đã hiểu') || document.body.innerText.includes('I understand'),
    { timeout: 15000 },
  )
  const clicked = await page.evaluate(() => {
    const buttons = Array.from(document.querySelectorAll('button'))
    const confirm = buttons.find((b) => {
      const t = (b.textContent || '').toLowerCase()
      return t.includes('hiểu') || t.includes('understand') || t.includes('continue')
    })
    if (confirm) {
      confirm.click()
      return true
    }
    return false
  })
  if (!clicked) throw new Error('Could not find rules confirm button')
  await new Promise((r) => setTimeout(r, 1200))
}

async function main() {
  await mkdir(OUT_DIR, { recursive: true })
  const executablePath = await resolveChrome()

  const browser = await puppeteer.launch({
    executablePath,
    headless: 'new',
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--window-size=1440,900',
      '--use-fake-ui-for-media-stream',
      '--use-fake-device-for-media-stream',
    ],
    defaultViewport: { width: 1440, height: 900 },
  })

  const page = await browser.newPage()

  // ── Public / HR workspace ──────────────────────────────────────────────────
  await goto(page, `${BASE}/`)
  await shot(page, '01-home')

  await goto(page, `${BASE}/login`)
  await shot(page, '02-login')

  if (TOKEN) {
    await setToken(page, TOKEN)
    await goto(page, `${BASE}/?tab=interview`)
    await shot(page, '03-interview-form', { waitMs: 1800 })

    await goto(page, `${BASE}/?tab=result`)
    await shot(page, '04-results', { waitMs: 2000 })
  }

  // ── Candidate: rules modal ───────────────────────────────────────────────
  if (ID_RULES) {
    await goto(page, `${BASE}/interview/${ID_RULES}`)
    await shot(page, '05-interview-rules', { waitMs: 2000 })
  }

  // ── Candidate: welcome / ready to join ─────────────────────────────────────
  if (ID_RULES) {
    await goto(page, `${BASE}/interview/${ID_RULES}`)
    await acceptRules(page)
    await shot(page, '07-interview-ready', { waitMs: 1200 })
  }

  // ── Candidate: code assignment panel ───────────────────────────────────────
  if (ID_CODE) {
    await goto(page, `${BASE}/interview/${ID_CODE}`)
    await shot(page, '08-code-panel', { waitMs: 2500 })
  }

  // ── Candidate: session complete ────────────────────────────────────────────
  if (ID_DONE) {
    await goto(page, `${BASE}/interview/${ID_DONE}`)
    await shot(page, '09-interview-complete', { waitMs: 2000 })
  }

  // ── HR: candidate dossier with report ──────────────────────────────────────
  if (TOKEN && ID_DONE) {
    await setToken(page, TOKEN)
    await goto(page, `${BASE}/candidate/${ID_DONE}`)
    await shot(page, '10-candidate-report', { waitMs: 2500 })
  }

  await browser.close()
  console.log('Done — screenshots in docs/screenshots/')
}

main().catch((err) => {
  console.error(err)
  process.exit(1)
})