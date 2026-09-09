import {chromium} from '../../upstream/opencode/packages/app/node_modules/@playwright/test/index.mjs'
import assert from 'node:assert/strict'
import {writeFile} from 'node:fs/promises'
const browser=await chromium.connectOverCDP('http://127.0.0.1:19222')
try {
 const page=browser.contexts()[0].pages().find(p=>p.url().startsWith('http://127.0.0.1:4097/'))
 assert(page)
 const info=await page.evaluate(async()=>{
  const h={'Content-Type':'application/json','x-opencode-directory':'/workspace'}
  const providers=await (await fetch('/provider',{headers:h})).json()
  const old=await fetch('/session/ses_f7e5bcd52ffeVyPP08izzF4nSU',{headers:h})
  if(!old.ok) throw new Error('Existing user session lost')
  const r=await fetch('/session',{method:'POST',headers:h,body:JSON.stringify({title:'권한 UI 실응답 검증'})})
  if(!r.ok) throw new Error('Session creation failed')
  return {session:await r.json(),connected:providers.connected}
 })
 assert(info.connected.includes('openai'))
 const id=info.session.id
 await page.goto(`http://127.0.0.1:4097/${Buffer.from('/workspace').toString('base64url')}/session/${id}`)
 const mode=page.getByLabel('에이전트 승인 모드',{exact:true})
 await mode.waitFor()
 await mode.selectOption('read')
 await page.waitForFunction(async id=>{
  const s=await (await fetch(`/session/${id}`,{headers:{'x-opencode-directory':'/workspace'}})).json()
  return s.permission?.some(r=>r.permission==='*'&&r.action==='ask')
 },id)
 await page.evaluate(async id=>{
  const r=await fetch(`/session/${id}/prompt_async`,{method:'POST',headers:{'Content-Type':'application/json','x-opencode-directory':'/workspace'},body:JSON.stringify({model:{providerID:'openai',modelID:'gpt-6-astra'},parts:[{type:'text',text:'권한 UI 검증입니다. 반드시 bash 도구로 /usr/bin/pwd 명령을 딱 한 번 실행하고 결과 경로만 알려주세요. 다른 파일 읽기나 변경은 하지 마세요.'}]})})
  if(!r.ok) throw new Error(`Prompt ${r.status}`)
 },id)
 await page.getByRole('region',{name:'승인 대기',exact:true}).waitFor({timeout:120000})
 console.log('PASS: actual model tool reached visible approval card')
 await page.screenshot({path:'D:/TinyAgent-work/tinyagent/evidence/lyriq1-permission-pending-v26.png'})
 await mode.selectOption('yolo')
 await page.waitForFunction(async id=>{
  const msgs=await (await fetch(`/session/${id}/message`,{headers:{'x-opencode-directory':'/workspace'}})).json()
  return msgs.some(m=>m.parts.some(p=>p.tool==='bash'&&p.state?.status==='completed'&&p.state.output?.includes('/workspace')))
 },id,{timeout:120000})
 await page.reload()
 await mode.waitFor()
 await page.waitForFunction(()=>document.querySelector('select[aria-label="에이전트 승인 모드"]')?.value==='yolo')
 const report={session:id,oauthConnected:true,existingUserSessionPreserved:true,readModeAsked:true,approvalCardVisible:true,yoloReleasedActualTool:true,yoloReloadPreserved:true}
 await writeFile(new URL('../evidence/lyriq1-permission-ui-v26.json',import.meta.url),JSON.stringify(report,null,2))
 console.log(JSON.stringify(report))
} finally {await browser.close()}
