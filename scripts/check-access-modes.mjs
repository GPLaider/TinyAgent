import { chromium } from '../../upstream/opencode/packages/app/node_modules/@playwright/test/index.mjs'
import assert from 'node:assert/strict'
import { writeFile } from 'node:fs/promises'
const browser=await chromium.connectOverCDP('http://127.0.0.1:19223')
try {
 const page=browser.contexts()[0].pages().find(p=>p.url().startsWith('http://127.0.0.1:4097'))
 assert(page)
 const session=await page.evaluate(async()=>{
  const r=await fetch('/session',{method:'POST',headers:{'Content-Type':'application/json','x-opencode-directory':'/workspace'},body:JSON.stringify({title:'승인 모드 회귀 검증'})})
  if(!r.ok) throw new Error(`create ${r.status}`)
  return r.json()
 })
 console.log('route',page.url(),'session',session.id)
 await page.goto(`http://127.0.0.1:4097/${Buffer.from('/workspace').toString('base64url')}/session/${session.id}`)
 const select=page.getByLabel('에이전트 승인 모드',{exact:true})
 await select.waitFor({timeout:30000})
 const rounds=[]
 for(const mode of ['read','yolo','basic','yolo','read','basic']) {
  await select.selectOption(mode)
  await page.waitForFunction(async ({id,mode})=>{
   const s=await (await fetch(`/session/${id}`,{headers:{'x-opencode-directory':'/workspace'}})).json()
   const rules=s.permission||[]
   const wildcard=rules.filter(r=>r.permission==='*').at(-1)?.action
   const external=rules.filter(r=>r.permission==='external_directory').at(-1)?.action
   return wildcard===(mode==='read'?'ask':'allow') && external===(mode==='yolo'?'allow':'ask')
  },{id:session.id,mode})
  await page.reload()
  await select.waitFor()
  await page.waitForFunction(mode=>document.querySelector('select[aria-label="에이전트 승인 모드"]')?.value===mode,mode)
  rounds.push({mode,backendSaved:true,reloadPreserved:true})
 }
 const report={session:session.id,rounds,scope:'Real native WebView UI and backend persisted session rules; no model inference'}
 await writeFile(new URL('../evidence/pacman-access-v25.json',import.meta.url),JSON.stringify(report,null,2))
 console.log(JSON.stringify(report))
} finally {await browser.close()}
