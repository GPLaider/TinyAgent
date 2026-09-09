import { chromium } from '../../upstream/opencode/packages/app/node_modules/@playwright/test/index.mjs'
import { readFile,writeFile } from 'node:fs/promises'
import { execFileSync } from 'node:child_process'
import { homedir } from 'node:os'
import { join } from 'node:path'
import assert from 'node:assert/strict'
const adb = join(homedir(),'AppData/Local/Android/Sdk/platform-tools/adb.exe')
const serial = '100.79.134.53:5555'
const version = process.argv[2] || 'v20'
assert.match(version,/^v\d+$/)
assert.equal(execFileSync(adb,['-s',serial,'shell','getprop','ro.serialno']).toString().trim(),'ZY22J58799')
const pid = execFileSync(adb,['-s',serial,'shell','pidof','io.github.gplaider.tinyagent.debug']).toString().trim()
assert.match(pid,/^\d+$/)
const previous = JSON.parse(await readFile(new URL('../evidence/lyriq1-v19-webview.json',import.meta.url),'utf8'))
const browser = await chromium.connectOverCDP('http://127.0.0.1:19222')
try {
  const page = browser.contexts()[0].pages().find(p=>p.url().startsWith('http://127.0.0.1:4097/'))
  assert(page)
  const report = await page.evaluate(async ({pid,session})=> {
    async function shell(command) {
      const r = await fetch(`/session/${session}/shell`,{method:'POST',headers:{'Content-Type':'application/json','x-opencode-directory':'/workspace'},body:JSON.stringify({agent:'build',command})})
      if (!r.ok) throw new Error(`API ${r.status}`)
      return (await r.json()).parts.filter(p=>p.type==='tool').map(p=>p.state.output || '').join('\n')
    }
    const prefix = `/usr/bin/curl --silent --show-error --max-time 90 --abstract-unix-socket tinyagent-android-10000-${pid} http://localhost/inspect/`
    const stock = JSON.parse(await shell(prefix+'stock'))
    const denied = JSON.parse(await shell(prefix+'developer'))
    const git = await shell('/usr/bin/git --version')
    return {stock,denied,git}
  },{pid,session:previous.rounds[0].session})
  const apk = execFileSync(adb,['-s',serial,'shell','pm','path','io.github.gplaider.tinyagent.debug']).toString().trim().replace(/^package:/,'')
  report.apk_sha256 = execFileSync(adb,['-s',serial,'shell','sha256sum',apk]).toString().split(/\s/)[0]
  await writeFile(new URL(`../evidence/lyriq1-${version}-stock-isolation.json`,import.meta.url),JSON.stringify(report,null,2))
  assert.equal(report.stock.selected_transport,'stock')
  assert.equal(report.stock.execution_uid,10000)
  assert.match(JSON.stringify(report.denied),/Stock 모드/)
  assert.match(report.git,/git version 2\.55\.0/)
  console.log(JSON.stringify(report))
} finally { await browser.close() }
