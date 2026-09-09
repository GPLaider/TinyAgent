// Exercise the real WebView's authenticated local API without exporting credentials.
import { chromium } from '../../upstream/opencode/packages/app/node_modules/@playwright/test/index.mjs'
import { readFile, writeFile } from 'node:fs/promises'
import { execFileSync } from 'node:child_process'
import { homedir } from 'node:os'
import { join } from 'node:path'
import assert from 'node:assert/strict'
const adb = join(homedir(), 'AppData/Local/Android/Sdk/platform-tools/adb.exe')
const device = process.argv[3] || 'lyriq1'
assert(['lyriq1','pacman'].includes(device))
const serial = device === 'pacman' ? '000501423003390' : '100.79.134.53:5555'
const hardware = device === 'pacman' ? serial : 'ZY22J58799'
const version = process.argv[2] || 'v16'
assert.match(version, /^v\d+$/)
const previous = version === 'v16' || device === 'pacman' ? [] : JSON.parse(await readFile(new URL('../evidence/lyriq1-v16-webview.json',import.meta.url),'utf8')).rounds.map(r=>r.session)
const appPid = execFileSync(adb,['-s',serial,'shell','pidof','io.github.gplaider.tinyagent.debug']).toString().trim()
assert.match(appPid,/^\d+$/)
const appUid = execFileSync(adb,['-s',serial,'shell','ps','-p',appPid,'-o','UID=']).toString().trim()
assert(Number(appUid)>=10000)
assert.equal(execFileSync(adb, ['-s',serial,'shell','getprop','ro.serialno']).toString().trim(), hardware)
const browser = await chromium.connectOverCDP('http://127.0.0.1:19222')
try {
  const page = browser.contexts()[0].pages().find(p => p.url().startsWith('http://127.0.0.1:4097/'))
  assert(page)
  const report = await page.evaluate(async ({previous,version,appPid,appUid,device}) => {
    async function request(path, payload) {
      const response = await fetch(path, {method:payload ? 'POST':'GET', headers:{'Content-Type':'application/json','x-opencode-directory':'/workspace'}, body:payload ? JSON.stringify(payload):undefined})
      if (!response.ok) throw new Error(`API ${path}: ${response.status}`)
      return response.json()
    }
    const health = await request('/global/health')
    if (!health.healthy) throw new Error('Backend unhealthy')
    for (const id of previous) {
      const messages = await request(`/session/${id}/message`)
      if (!messages.length) throw new Error(`Previous session lost: ${id}`)
    }
    const config = await request('/config')
    for (const name of ['AGENTS','STOCK','ADB','ROOT','TINYAGENT_ENVIRONMENT','ANDROID_TOOL'])
      if (!config.instructions.includes(`/root/.tinyagent/${name}.md`)) throw new Error(`Missing harness ${name}`)
    const rounds = []
    const failures = []
    for (let i=0; i<3; i++) {
      const session = await request('/session', {title:`${device} 검증 ${i+1}`})
      const results = []
      for (const command of ['/usr/bin/cat /etc/fedora-release','/usr/bin/id','/usr/bin/git --version']) {
        const result = await request(`/session/${session.id}/shell`, {agent:'build',command})
        const states = result.parts.filter(p=>p.type==='tool').map(p=>p.state)
        if (!states.some(s=>s.status==='completed')) throw new Error(`Command failed: ${command}`)
        results.push({command,states})
        const output = states.map(s=>s.output || '').join('\n')
        const expected = command.includes('fedora-release') ? /Fedora release 44/ : command.endsWith('/id') ? /uid=0\(root\)/ : /git version \d/
        if (!expected.test(output)) failures.push({command,output})
      }
      rounds.push({session:session.id,results})
    }
    const android = []
    if (Number(version.slice(1))>=19) {
      for (const mode of ['stock','developer']) {
        const command = `/usr/bin/curl --silent --show-error --max-time 90 --abstract-unix-socket tinyagent-android-${appUid}-${appPid} http://localhost/inspect/${mode}`
        const result = await request(`/session/${rounds[0].session}/shell`,{agent:'build',command})
        const output = result.parts.filter(p=>p.type==='tool').map(p=>p.state.output || '').join('\n')
        const measured = JSON.parse(output)
        if (mode==='developer' && device==='pacman' && !JSON.stringify(measured).includes('Stock 모드')) throw new Error('Stock must reject Developer access')
        if (mode==='developer' && device!=='pacman' && (!measured.verified_self || measured.execution_uid!==2000)) throw new Error('Developer bridge did not verify shell UID')
        if (mode==='stock' && device==='pacman' && measured.selected_transport!=='stock') throw new Error('Fresh installation is not Stock')
        if (mode==='stock' && measured.execution_uid!==Number(appUid)) throw new Error('Stock app UID changed')
        android.push(measured)
      }
    }
    return {health,harnessLoaded:true,preservedSessions:previous,rounds,failures,android}
  }, {previous,version,appPid,appUid,device})
  assert.match(JSON.stringify(report.rounds), /Fedora release 44/)
  report.scope = `${device}; real WebView and phone-local shell API, no model inference`
  report.serial = hardware
  await writeFile(new URL(`../evidence/${device}-${version}-webview.json`,import.meta.url), JSON.stringify(report,null,2))
  assert.deepEqual(report.failures, [], 'Required Fedora command output missing')
  await page.reload()
  await page.locator('body').waitFor()
  await page.screenshot({path:new URL(`../evidence/${device}-${version}-home.png`, import.meta.url).pathname.replace(/^\/([A-Z]:)/,'$1')})
  await writeFile(new URL(`../evidence/${device}-${version}-webview.json`,import.meta.url), JSON.stringify(report,null,2))
  assert.deepEqual(report.failures, [], 'Required Fedora command output missing')
  console.log(JSON.stringify(report))
} finally { await browser.close() }
