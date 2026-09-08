// Browser plugin unavailable; use installed Playwright against the real Android WebView.
import { chromium } from '../../upstream/opencode/packages/app/node_modules/@playwright/test/index.mjs'
import { fileURLToPath } from 'node:url'
import { execFileSync } from 'node:child_process'
import { homedir } from 'node:os'
import { join } from 'node:path'
import { mkdir, writeFile } from 'node:fs/promises'
const browser = await chromium.connectOverCDP('http://127.0.0.1:19222')
const page = browser.contexts()[0].pages().find(p => p.url().startsWith('http://127.0.0.1:4097/'))
if (!page) throw new Error('Expected TinyAgent WebView')
const out = new URL('../evidence/mobile-workspace-v14/', import.meta.url)
await mkdir(out, {recursive:true})
try {
  await page.getByRole('button', {name:'홈', exact:true}).waitFor()
  if (!await page.getByText('최근 세션', {exact:true}).isVisible())
    await page.getByRole('button', {name:'홈', exact:true}).click()
  await page.getByText('최근 세션', {exact:true}).waitFor()
  await page.screenshot({path:fileURLToPath(new URL('home.png',out))})
  await writeFile(new URL('home.txt',out), await page.locator('body').ariaSnapshot())
  const results = []
  for (let i=0; i<3; i++) {
    await page.getByRole('button', {name:'새 세션', exact:true}).first().click()
    await page.getByRole('button', {name:'전송', exact:true}).waitFor()
    await page.getByRole('button', {name:'홈', exact:true}).click()
    await page.getByText('최근 세션', {exact:true}).waitFor()
    results.push({iteration:i+1, newDraftOpened:true, homeRestored:true})
  }
  const adb = join(homedir(), 'AppData/Local/Android/Sdk/platform-tools/adb.exe')
  for (let i=0; i<3; i++) {
    await page.getByRole('button', {name:`w 검증 · 화면 복구 ${i} workspace`, exact:true}).click()
    await page.getByRole('button', {name:'전송', exact:true}).waitFor()
    for (let back=0; back<2; back++) {
      execFileSync(adb, ['-s','USB_TEST_SERIAL','shell','input','keyevent','4'])
      if (await page.getByText('최근 세션', {exact:true}).isVisible()) break
    }
    await page.getByText('최근 세션', {exact:true}).waitFor()
    results[i].savedSessionOpened = true
    results[i].androidBackRestoredHome = true
  }
  const apk = execFileSync(adb, ['-s','USB_TEST_SERIAL','shell','pm','path','io.github.gplaider.tinyagent.debug']).toString().trim().replace(/^package:/,'')
  const apk_sha256 = execFileSync(adb, ['-s','USB_TEST_SERIAL','shell','sha256sum',apk]).toString().split(/\s/)[0]
  await writeFile(new URL('result.json',out), JSON.stringify({scope:'Actual Android WebView; no mock backend', apk_sha256, results},null,2))
  console.log(JSON.stringify(results))
} finally { await browser.close() }
