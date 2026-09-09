import { chromium } from '../../upstream/opencode/packages/app/node_modules/@playwright/test/index.mjs'
const browser=await chromium.connectOverCDP('http://127.0.0.1:19222')
try {
 const page=browser.contexts()[0].pages().find(p=>p.url().startsWith('http://127.0.0.1:4097/'))
 if(!page) throw new Error('No local backend WebView')
 const report=await page.evaluate(async({resume,pause})=>{
  const get=async path=>{const r=await fetch(path,{headers:{'x-opencode-directory':'/workspace'}}); if(!r.ok) return {http:r.status}; return r.json()}
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
 },{resume:process.argv.includes('--resume-safe-reads'),pause:process.argv.includes('--pause-for-update')})
 console.log(JSON.stringify(report,null,2))
} finally {await browser.close()}
