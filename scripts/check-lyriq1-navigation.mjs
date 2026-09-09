import { chromium } from '../../upstream/opencode/packages/app/node_modules/@playwright/test/index.mjs'
import { writeFile } from 'node:fs/promises'
import { execFileSync } from 'node:child_process'
import { homedir } from 'node:os'
import { join } from 'node:path'
import assert from 'node:assert/strict'
const adb = join(homedir(),'AppData/Local/Android/Sdk/platform-tools/adb.exe')
const serial = '100.79.134.53:5555'
assert.equal(execFileSync(adb,['-s',serial,'shell','getprop','ro.serialno']).toString().trim(),'ZY22J58799')
const browser = await chromium.connectOverCDP('http://127.0.0.1:19222')
try {
  const page = browser.contexts()[0].pages().find(p=>p.url().startsWith('http://127.0.0.1:4097/'))
  assert(page)
  const results = []
  for (let i=1;i<=3;i++) {
    await page.getByText(`1호기 검증 ${i}`,{exact:true}).first().click()
    await page.getByRole('button',{name:'전송',exact:true}).waitFor()
    execFileSync(adb,['-s',serial,'shell','input','keyevent','4'])
    await page.getByText('최근 세션',{exact:true}).waitFor()
    results.push({round:i,sessionOpened:true,androidBackRestoredList:true})
  }
  await writeFile(new URL('../evidence/lyriq1-v17-navigation.json',import.meta.url),JSON.stringify(results,null,2))
  console.log(JSON.stringify(results))
} finally { await browser.close() }
