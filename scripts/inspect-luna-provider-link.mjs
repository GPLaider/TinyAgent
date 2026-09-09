import { chromium } from '../../upstream/opencode/packages/app/node_modules/@playwright/test/index.mjs'
import { writeFile } from 'node:fs/promises'
import assert from 'node:assert/strict'

const browser = await chromium.connectOverCDP('http://127.0.0.1:19222')
try {
  const page = browser.contexts()[0].pages().find(p => p.url().startsWith('http://127.0.0.1:4097/'))
  assert(page, 'Lyriq1 WebView unavailable')
  const report = await page.evaluate(async () => {
    const headers = {'x-opencode-directory': '/workspace'}
    const get = async path => {
      const response = await fetch(path, {headers})
      if (!response.ok) throw new Error(`${path}: ${response.status}`)
      return response.json()
    }
    const id = 'ses_f7e5bcd52ffeVyPP08izzF4nSU'
    const providers = await get('/provider')
    const messages = await get(`/session/${id}/message`)
    const openai = providers.all.find(p => p.id === 'openai')
    return {
      capturedAt: new Date().toISOString(),
      connected: providers.connected,
      openaiSource: openai?.source,
      lunaAvailable: Boolean(openai?.models?.['gpt-5.6-luna']),
      session: id,
      status: (await get('/session/status'))[id],
      pendingPermissions: (await get('/permission')).filter(p => p.sessionID === id).length,
      lunaMessages: messages.filter(m => m.info.role === 'assistant' && m.info.modelID === 'gpt-5.6-luna').map(m => ({
        provider: m.info.providerID, model: m.info.modelID, completed: Boolean(m.info.time.completed),
        tools: m.parts.filter(p => p.type === 'tool').map(p => ({tool: p.tool, status: p.state.status})),
      })),
    }
  })
  assert(report.connected.includes('openai'))
  assert(report.lunaAvailable)
  assert(report.lunaMessages.some(m => m.provider === 'openai' && m.tools.some(t => t.status === 'completed')))
  await writeFile(new URL('../evidence/lyriq1-luna-provider-link.json', import.meta.url), JSON.stringify(report, null, 2))
  console.log(JSON.stringify(report, null, 2))
} finally {
  await browser.close()
}
