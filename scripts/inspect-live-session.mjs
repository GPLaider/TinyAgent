import { chromium } from '../../upstream/opencode/packages/app/node_modules/@playwright/test/index.mjs'
import {execFileSync} from 'node:child_process'
import {mkdir,writeFile} from 'node:fs/promises'
import {homedir} from 'node:os'
import assert from 'node:assert/strict'
const capture=process.argv[2]==='--capture'
const device=process.argv[3], session=process.argv[4]
let port=19222
if(capture) {
 const targets={pacman:['000501423003390','000501423003390',19222],lyriq1:['100.79.134.53:5555','ZY22J58799',19223],lyriq2:['100.79.65.42:5555','ZY22HZPLL8',19224]}
 assert(targets[device] && /^ses_[A-Za-z0-9]+$/.test(session),'Use --capture <device> <session>')
 const [serial,hardware,selectedPort]=targets[device];port=selectedPort
 const adb=(...args)=>execFileSync(homedir()+'/AppData/Local/Android/Sdk/platform-tools/adb.exe',['-s',serial,...args],{encoding:'utf8',timeout:30000}).trim()
 assert.equal(adb('shell','getprop','ro.serialno'),hardware)
 const pid=adb('shell','pidof','io.github.gplaider.tinyagent.debug')
 assert(/^\d+$/.test(pid),'App must already be running; capture does not start it')
 adb('forward','tcp:'+port,'localabstract:webview_devtools_remote_'+pid)
}
const browser=await chromium.connectOverCDP('http://127.0.0.1:'+port)
try {
 const page=browser.contexts()[0].pages().find(p=>p.url().startsWith('http://127.0.0.1:4097/'))
 if(!page) throw new Error('No local backend WebView')
 const report=await page.evaluate(async({resume,pause,capture,session,recent})=>{
  const get=async path=>{const r=await fetch(path,{headers:{'x-opencode-directory':'/workspace'},signal:AbortSignal.timeout(30000)}); if(!r.ok) return {http:r.status}; return r.json()}
  if(capture) {
   const [detail,status,messages,permissions]=await Promise.all([get('/session/'+session),get('/session/status?scope=server'),get('/session/'+session+'/message'+(recent?'?limit=10':'')),get('/permission')])
   if(detail.http || status.http || !Array.isArray(messages) || !Array.isArray(permissions)) throw Error('Session capture incomplete; inspect API status')
   return {capture_scope:recent?'latest-10-messages':'full-history',session:detail,status:status[session]??{type:'idle'},messages,permissions:permissions.filter(p=>p.sessionID===session)}
  }
  const sessions=await get('/session')
  const status=await get('/session/status')
  const permissions=await get('/permission')
  if(pause) {
   const id='ses_f7e5bcd52ffeVyPP08izzF4nSU'
   const messages=await get(`/session/${id}/message`)
   const active=messages.flatMap(m=>m.parts).filter(p=>p.type==='tool' && p.state?.status==='running')
   if(active.some(p=>p.tool!=='read')) throw new Error('Active non-read work; do not interrupt for update')
   const r=await fetch(`/session/${id}/abort`,{method:'POST',headers:{'x-opencode-directory':'/workspace'}})
   if(!r.ok) throw new Error(`Pause failed ${r.status}`)
   return {pausedForUpdate:true,session:id,activeReadCount:active.length}
  }
  const resumed=[]
  if(resume) {
   const allowed=new Set(['/root/.tinyagent/TINYAGENT_ENVIRONMENT.md','/root/.tinyagent/ANDROID_TOOL.md','/etc/os-release'])
   for(const p of permissions) {
    if(p.sessionID!=='ses_f7e5bcd52ffeVyPP08izzF4nSU' || p.permission!=='external_directory' || !allowed.has(p.metadata?.filepath)) continue
    const messages=await get(`/session/${p.sessionID}/message`)
    const read=messages.flatMap(m=>m.parts).find(t=>t.callID===p.tool?.callID && t.tool==='read' && t.state?.input?.filePath===p.metadata.filepath)
    if(!read) continue
    const r=await fetch(`/permission/${p.id}/reply`,{method:'POST',headers:{'Content-Type':'application/json','x-opencode-directory':'/workspace'},body:JSON.stringify({reply:'once'})})
    if(!r.ok) throw new Error(`Permission reply ${r.status}`)
    resumed.push(p.metadata.filepath)
   }
  }
  const reports=[]
  for(const s of sessions.slice(0,4)) {
   const messages=await get(`/session/${s.id}/message`)
   reports.push({id:s.id,title:s.title,time:s.time,messages:Array.isArray(messages)?messages.slice(-4).map(m=>({role:m.info.role,time:m.info.time,model:m.info.modelID,provider:m.info.providerID,error:m.info.error,finish:m.info.finish,
    parts:m.parts.map(p=>({type:p.type,tool:p.tool,status:p.state?.status,file:p.tool==='read'?p.state?.input?.filePath:undefined,time:p.time||p.state?.time,error:p.state?.error,text:p.type==='text'?p.text?.slice(0,500):undefined}))})):messages})
  }
  return {status,resumed,permissions:Array.isArray(permissions)?permissions.map(p=>({id:p.id,sessionID:p.sessionID,permission:p.permission,patterns:p.patterns})):permissions,sessions:reports}
 },{resume:process.argv.includes('--resume-safe-reads'),pause:process.argv.includes('--pause-for-update'),capture,session,recent:process.argv.includes('--recent')})
 if(capture) {
  const directory=new URL('../evidence/go-campaign/',import.meta.url)
  await mkdir(directory,{recursive:true})
  const file=device+'-'+session+'-'+Date.now()+'.json'
  await writeFile(new URL(file,directory),JSON.stringify({device,captured_at:new Date().toISOString(),...report},null,2))
  console.log(JSON.stringify({device,session,status:report.status,messages:report.messages.length,file}))
 } else console.log(JSON.stringify(report,null,2))
} finally {await browser.close()}
