// Verify first paint while the application module is unavailable; no phone or OAuth access.
import { createRequire } from 'node:module'
import { readFile } from 'node:fs/promises'
import assert from 'node:assert/strict'
import { execFileSync } from 'node:child_process'
const upstream = process.argv[2] || 'D:/TinyAgent-work/upstream/opencode'
const require = createRequire(upstream + '/packages/app/package.json')
const { chromium } = require('@playwright/test')
const html = process.argv.includes('--baseline')
  ? execFileSync('git', ['-C', upstream, 'show', 'HEAD:packages/app/index.html'], { encoding: 'utf8' })
  : await readFile(upstream + '/packages/app/index.html', 'utf8')
const preload = await readFile(upstream + '/packages/app/public/oc-theme-preload.js', 'utf8')
const browser = await chromium.launch({ executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe', headless: true })
try {
  for (const mode of ['light', 'dark']) {
    const page = await browser.newPage({ viewport: { width: 360, height: 640 }, colorScheme: mode })
    await page.route('http://tinyagent.test/**', async route => {
      const path = new URL(route.request().url()).pathname
      if (path === '/') return route.fulfill({ contentType: 'text/html', body: html })
      if (path === '/oc-theme-preload.js') return route.fulfill({ contentType: 'text/javascript', body: preload })
      return route.abort()
    })
    await page.goto('http://tinyagent.test/')
    const loader = page.locator('#tinyagent-startup')
    assert(await loader.isVisible(), 'Blank startup when module cannot load')
    assert(await loader.locator('progress:indeterminate').isVisible(), 'Unknown progress must not show a percentage')
    assert.equal(await page.locator('html').getAttribute('data-color-scheme'), mode)
    const box = await loader.boundingBox()
    assert(box.width <= 360 && box.height <= 640, 'Startup overflows mobile viewport')
    assert.equal(await loader.evaluate(el => getComputedStyle(el).color), mode === 'dark' ? 'rgb(244, 244, 244)' : 'rgb(37, 37, 37)')
    await page.close()
  }
  console.log('PASS: mobile initial HTML visible before bundle, light/dark, indeterminate progress')
} finally { await browser.close() }
