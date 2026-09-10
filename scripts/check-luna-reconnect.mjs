import { writeFile } from 'node:fs/promises'
import { execFileSync } from 'node:child_process'
const round = process.argv[2]
if (!/^[1-3]$/.test(round)) throw Error('Round must be 1..3')
const expectedApk = process.argv[3] ?? '8f39db6fddd6dd6062515e3935f8b9ff5629a3a7e915161a2376fbb22ef94170'
if (!/^[0-9a-f]{64}$/.test(expectedApk)) throw Error('Expected APK SHA256 required')
const adb = 'C:/Users/Administrator/AppData/Local/Android/Sdk/platform-tools/adb.exe'
const shell = (...args) => execFileSync(adb, ['-s', '100.79.134.53:5555', 'shell', ...args], { encoding: 'utf8', timeout: 30000 }).trim()
if (shell('getprop', 'ro.serialno') !== 'ZY22J58799') throw Error('Wrong device')
const apk = shell('sha256sum', shell('pm', 'path', 'io.github.gplaider.tinyagent.debug').replace('package:', '')).split(/\s/)[0]
if (apk !== expectedApk) throw Error('Wrong APK')
const targets = await (await fetch('http://127.0.0.1:19222/json/list')).json()
const target = targets.find(t => t.type === 'page' && t.url.startsWith('http://127.0.0.1:4097/'))
if (!target) throw Error('WebView missing')
const socket = new WebSocket(target.webSocketDebuggerUrl)
await new Promise((resolve, reject) => { socket.onopen = resolve; socket.onerror = reject })
let next = 0
const pending = new Map()
socket.onmessage = event => {
  const data = JSON.parse(event.data)
  const request = pending.get(data.id)
  if (!request) return
  pending.delete(data.id)
  clearTimeout(request.timer)
  if (data.error) request.reject(Error(data.error.message))
  else request.resolve(data.result)
}
const call = (method, params = {}) => new Promise((resolve, reject) => {
  const id = ++next
  const timer = setTimeout(() => { pending.delete(id); reject(Error('CDP timeout: ' + method)) }, 30000)
  pending.set(id, { resolve, reject, timer })
  socket.send(JSON.stringify({ id, method, params }))
})
const evaluate = async expression => {
  const result = await call('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true })
  if (result.exceptionDetails) throw Error(result.exceptionDetails.exception?.description ?? result.exceptionDetails.text)
  return result.result.value
}
const request = (path, body) => evaluate(`(async()=>{const r=await fetch(${JSON.stringify(path)},{headers:{'x-opencode-directory':'/workspace','Content-Type':'application/json'},${body === undefined ? '' : `method:'POST',body:${JSON.stringify(JSON.stringify(body))},`}});if(!r.ok)throw Error('HTTP '+r.status);return r.status===204?null:r.json()})()`)
const wait = ms => new Promise(resolve => setTimeout(resolve, ms))
const report = { apk, round: Number(round), scope: 'Real Luna tool run with WebView-only network emulation; Android/Fedora networking unchanged' }
const output = `D:/TinyAgent-work/tinyagent/evidence/lyriq1-luna-reconnect-${process.argv[3] ? apk.slice(0,12)+'-' : ''}${round}.json`
let offline = false
try {
  const session = await request('/session', { title: `Luna reconnect verification ${round}`, permission: [{ permission: '*', pattern: '*', action: 'allow' }] })
  report.sessionID = session.id
  await writeFile(output, JSON.stringify(report, null, 2))
  await call('Page.navigate', { url: 'http://127.0.0.1:4097/' + Buffer.from('/workspace').toString('base64url') + '/session/' + session.id })
  const ready = Date.now() + 30000
  while (!await evaluate(`!!document.querySelector('[data-component="tinyagent-access"]')`)) {
    if (Date.now() > ready) throw Error('Conversation not ready')
    await wait(300)
  }
  const marker = `TINYAGENT_RECONNECT_${round}_PASS`
  await request('/session/' + session.id + '/prompt_async', { agent: 'build', model: { providerID: 'openai', modelID: 'gpt-5.6-luna' }, parts: [{ type: 'text', text: `검증입니다. bash 도구를 정확히 한 번 호출해 pwd, uname -m, cat /etc/fedora-release를 실행하세요. 파일·설정 변경과 ADB/root 사용은 금지합니다. 실제 결과를 확인한 뒤 최종 답변은 ${marker} 와 작업 디렉터리·아키텍처·Fedora 버전을 짧게 보고하세요.` }] })
  await call('Network.enable')
  report.offlineStart = await evaluate('Date.now()')
  offline = true
  await call('Network.emulateNetworkConditions', { offline: true, latency: 0, downloadThroughput: -1, uploadThroughput: -1 })
  console.log(JSON.stringify({ round, sessionID: session.id, phase: 'WebView offline; backend continues' }))
  await wait(30000)
  report.offlineEnd = await evaluate('Date.now()')
  await call('Network.emulateNetworkConditions', { offline: false, latency: 0, downloadThroughput: -1, uploadThroughput: -1 })
  offline = false
  const deadline = Date.now() + 90000
  while (true) {
    const messages = await request('/session/' + session.id + '/message')
    const statuses = await request('/session/status')
    const final = messages.filter(m => m.info.role === 'assistant' && m.parts.some(p => p.type === 'text' && p.text.includes(marker))).at(-1)
    const visible = await evaluate(`Array.from(document.querySelectorAll('[data-component="markdown"]')).some(n=>n.innerText.includes(${JSON.stringify(marker)}))`)
    if (final && !statuses[session.id] && visible) {
      report.messages = messages
      report.completed = final.info.time.completed
      report.completedWhileOffline = report.completed >= report.offlineStart && report.completed <= report.offlineEnd
      report.visibleWithoutNavigation = visible
      report.toolCalls = messages.flatMap(m => m.parts).filter(p => p.type === 'tool').map(p => ({ tool: p.tool, state: p.state }))
      if (messages.some(m => m.info.role === 'assistant' && (m.info.modelID !== 'gpt-5.6-luna' || m.info.providerID !== 'openai'))) throw Error('Unexpected provider/model')
      if (report.toolCalls.length !== 1 || report.toolCalls.some(t => t.tool !== 'bash' || t.state.status !== 'completed' || t.state.metadata?.exit !== 0)) throw Error('Successful single bash call missing')
      if (!report.completedWhileOffline) throw Error('Final answer did not complete inside offline interval')
      report.passed = true
      break
    }
    if (Date.now() > deadline) {
      report.messages = messages
      report.status = statuses[session.id] ?? { type: 'idle' }
      report.finalFound = !!final
      report.visibleWithoutNavigation = visible
      throw Error('Final answer did not recover in mounted UI')
    }
    await wait(1000)
  }
} catch (error) {
  report.error = String(error)
  throw error
} finally {
  if (offline) await call('Network.emulateNetworkConditions', { offline: false, latency: 0, downloadThroughput: -1, uploadThroughput: -1 })
  await writeFile(output, JSON.stringify(report, null, 2))
  socket.close()
}
console.log(JSON.stringify({ passed: report.passed, sessionID: report.sessionID, completedWhileOffline: report.completedWhileOffline, visibleWithoutNavigation: report.visibleWithoutNavigation }))
