import {readFile,writeFile} from 'node:fs/promises'
// Use raw CDP: Playwright 1.59 applies light media emulation on attachment.
// This probe must preserve the phone's real prefers-color-scheme value.
const targets=await (await fetch('http://127.0.0.1:19222/json/list')).json()
const target=targets.find(t=>t.type==='page'&&t.url.startsWith('http://127.0.0.1:4097/'))
if(!target) throw new Error('Target missing')
const socket=new WebSocket(target.webSocketDebuggerUrl)
await new Promise((resolve,reject)=>{socket.onopen=resolve;socket.onerror=reject})
let next=0
const call=(method,params)=>new Promise((resolve,reject)=>{
 const id=++next
 const timeout=setTimeout(()=>reject(new Error('CDP timeout')),30000)
 socket.onmessage=event=>{const data=JSON.parse(event.data);if(data.id===id){clearTimeout(timeout);if(data.error)reject(new Error(data.error.message));else resolve(data.result)}}
 socket.send(JSON.stringify({id,method,params}))
})
const evaluate=async expression=>{
 const result=await call('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true})
 if(result.exceptionDetails)throw Error(result.exceptionDetails.exception?.description??result.exceptionDetails.text)
 return result.result.value
}
const action=process.argv[2]??'theme'
if(action==='access-policy-state') {
 const state=await evaluate(`(async()=>{const r=await fetch('/session/ses_f761a8a35ffevxs65Wf07SNgIr',{headers:{'x-opencode-directory':'/workspace'}});if(!r.ok)throw Error('HTTP '+r.status);return {permission:(await r.json()).permission,mode:document.querySelector('select[aria-label="에이전트 승인 모드"]')?.value}})()`)
 const effective=state.permission.slice(state.permission.findLastIndex(r=>r.permission==='*'&&r.pattern==='*'))
 if(effective.length!==1||effective[0].action!=='allow'||state.mode!=='yolo')throw Error('Original QA allow-all policy is not effective')
 const file='D:/TinyAgent-work/tinyagent/evidence/lyriq1-access-policy-rounds.json'
 const report=JSON.parse(await readFile(file,'utf8'))
 if(report.rounds.length!==9||!report.passed)throw Error('Mode changes incomplete')
 report.restorationAudit={effectivePolicyRestored:true,exactRuleHistoryRestored:false,retainedRules:state.permission.length,reason:'OpenCode PATCH appends rules; final blanket allow matches original QA policy'}
 await writeFile(file,JSON.stringify(report,null,2))
 console.log(JSON.stringify(report.restorationAudit))
}
if(action==='check-access-policy') {
 const id='ses_f761a8a35ffevxs65Wf07SNgIr'
 const url='http://127.0.0.1:4097/'+Buffer.from('/workspace').toString('base64url')+'/session/'+id
 const get=()=>evaluate(`(async()=>{const r=await fetch('/session/'+${JSON.stringify(id)},{headers:{'x-opencode-directory':'/workspace'}});if(!r.ok)throw Error('Session '+r.status);return r.json()})()`)
 const original=(await get()).permission??[]
 const report={sessionID:id,scope:'Dedicated QA session; select change handler, backend readback and reload persistence, not physical touch',rounds:[]}
 const waitMode=async mode=>{
  const end=Date.now()+20000
  while(!await evaluate(`(()=>{const s=document.querySelector('select[aria-label="에이전트 승인 모드"]');return s&&!s.disabled&&s.value===${JSON.stringify(mode)}})()`)) {
   if(Date.now()>end)throw Error('Mode not reflected: '+mode)
   await new Promise(resolve=>setTimeout(resolve,300))
  }
 }
 try {
  await call('Page.navigate',{url})
  await waitMode('yolo')
  for(let round=1;round<=3;round++) for(const mode of ['basic','read','yolo']) {
   await evaluate(`(()=>{const s=document.querySelector('select[aria-label="에이전트 승인 모드"]');if(!s||s.disabled)throw Error('Select unavailable');s.value=${JSON.stringify(mode)};s.dispatchEvent(new Event('change',{bubbles:true}))})()`)
   await waitMode(mode)
   const rules=(await get()).permission
   const rule=name=>rules.filter(r=>r.permission===name&&r.pattern==='*').at(-1)?.action
   if(rule('*')!==(mode==='read'?'ask':'allow')||rule('external_directory')!==(mode==='yolo'?'allow':'ask')||rule('doom_loop')!==(mode==='yolo'?'allow':'ask'))throw Error('Stored policy mismatch')
   await call('Page.navigate',{url})
   await waitMode(mode)
   report.rounds.push({round,mode,rules,reloaded:true})
  }
  report.passed=true
 } catch(error) {report.error=String(error);throw error}
 finally {
  await evaluate(`(async()=>{const r=await fetch('/session/'+${JSON.stringify(id)},{method:'PATCH',headers:{'Content-Type':'application/json','x-opencode-directory':'/workspace'},body:JSON.stringify({permission:${JSON.stringify(original)}})});if(!r.ok)throw Error('Restore '+r.status)})()`)
  const restored=(await get()).permission
  const effective=rules=>rules.slice(rules.findLastIndex(r=>r.permission==='*'&&r.pattern==='*'))
  report.exactRulesRestored=JSON.stringify(restored)===JSON.stringify(original)
  report.restored=JSON.stringify(effective(restored))===JSON.stringify(effective(original))
  report.restorationScope='Effective policy restored; OpenCode PATCH appends rules and retains earlier history'
  await writeFile('D:/TinyAgent-work/tinyagent/evidence/lyriq1-access-policy-rounds.json',JSON.stringify(report,null,2))
 }
 if(!report.restored)throw Error('Original policy not restored')
 console.log(JSON.stringify({passed:report.passed,checks:report.rounds.length,restored:report.restored}))
}
if(action==='development-files'||action==='integration-files') {
 const id=process.argv[3]
 if(!/^ses_[a-zA-Z0-9]+$/.test(id))throw Error('Invalid session ID')
 const files={}
 const integration=action==='integration-files'
 const names=integration ? ['result.json',...[1,2,3].flatMap(r=>['calculator.py','test_calculator.py','before.log','after.log'].map(n=>'round-'+r+'/'+n))] : ['calculator.py','test_calculator.py','before.log','after.log','result.json']
 for(const name of names) {
  const path=(integration?'/workspace/.tinyagent-qa/'+id:'/workspace/luna-acceptance-'+id)+'/'+name
  files[name]=await evaluate(`(async()=>{const r=await fetch('/file/content?path='+encodeURIComponent(${JSON.stringify(path)}),{headers:{'x-opencode-directory':'/workspace'}});if(!r.ok)throw Error('File '+r.status);return r.json()})()`)
 }
 await writeFile('D:/TinyAgent-work/tinyagent/evidence/'+id+'-files.json',JSON.stringify(files,null,2))
 console.log(JSON.stringify(files))
}
if(action==='provider-ui-audit') {
 const report=await evaluate(`(async()=>{const r=await fetch('/provider',{headers:{'x-opencode-directory':'/workspace'}});if(!r.ok)throw Error('Provider '+r.status);const catalog=await r.json();const openai=catalog.all.find(p=>p.id==='openai');const section=document.querySelector('[data-component="connected-providers-section"]');if(!section)throw Error('Open provider settings first');return {connected:catalog.connected,openai:{source:openai?.source,lunaAvailable:!!openai?.models?.['gpt-5.6-luna']},visibleConnected:section.innerText,theme:localStorage.getItem('opencode-color-scheme')}})()`)
 if(!report.connected.includes('openai')||!report.openai.lunaAvailable||!report.visibleConnected.includes('OpenAI'))throw Error('Provider UI/backend mismatch')
 await writeFile('D:/TinyAgent-work/tinyagent/evidence/lyriq1-provider-ui-audit.json',JSON.stringify(report,null,2))
 console.log(JSON.stringify(report))
}
if(action==='check-compact-access') {
 const state=()=>evaluate(`(()=>{const n=document.querySelector('[data-component="tinyagent-access"]');if(!n)throw Error('Permission control missing');const d=n.querySelector('details'),s=n.querySelector('summary'),m=n.querySelector('select');if(!d||!s||!m)throw Error('Compact controls missing');const r=s.getBoundingClientRect();return {open:d.open,height:n.getBoundingClientRect().height,mode:m.value,disabled:m.disabled,x:r.x+r.width/2,y:r.y+r.height/2,touchHeight:r.height}})()`)
 const before=await state()
 if(before.open||before.disabled||before.touchHeight<44)throw Error('Initial control state invalid')
 const rounds=[]
 for(let i=0;i<3;i++) {
  for(const open of [true,false]) {
   const box=await state()
   await call('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[{x:box.x,y:box.y}]})
   await call('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]})
   const after=await state()
   if(after.open!==open||after.mode!==before.mode)throw Error('Details touch changed mode or failed')
   if(open&&after.height<=before.height)throw Error('Explanation did not expand')
   rounds.push(after)
  }
 }
 await writeFile('D:/TinyAgent-work/tinyagent/evidence/lyriq1-compact-access-touch.json',JSON.stringify({before,rounds},null,2))
 console.log(JSON.stringify({before,rounds}))
}
if(action==='update-snapshot') {
 const phase=process.argv[3]
 const name=process.argv[4]??'lyriq1-preview4'
 if(!/^[a-zA-Z0-9-]+$/.test(name))throw Error('Invalid snapshot name')
 if(!['before','after'].includes(phase))throw Error('Invalid phase')
 const report=await evaluate(`(async()=>{const get=async p=>{const r=await fetch(p,{headers:{'x-opencode-directory':'/workspace'}});if(!r.ok)throw Error('HTTP '+r.status);return r.json()};return {health:await get('/global/health'),sessionIds:(await get('/session')).map(s=>s.id).sort(),providers:(await get('/provider')).connected.sort(),active:await get('/session/status'),theme:localStorage.getItem('opencode-color-scheme')}})()`)
 if(Object.keys(report.active).length)throw Error('Active sessions: do not update')
 if(phase==='after') {
  const before=JSON.parse(await readFile('D:/TinyAgent-work/tinyagent/evidence/'+name+'-before.json','utf8'))
  if(before.sessionIds.some(id=>!report.sessionIds.includes(id)))throw Error('Missing saved session')
  if(JSON.stringify(before.providers)!==JSON.stringify(report.providers)||before.theme!==report.theme)throw Error('Provider/theme changed')
 }
 await writeFile('D:/TinyAgent-work/tinyagent/evidence/'+name+'-'+phase+'.json',JSON.stringify(report,null,2))
 console.log(JSON.stringify({phase,sessions:report.sessionIds.length,providers:report.providers,theme:report.theme}))
}
if(action==='recovery-job-cleanup') {
 const {id}=JSON.parse(await readFile('D:/TinyAgent-work/tinyagent/evidence/lyriq1-native-stop-session.json','utf8'))
 if(!/^ses_[a-zA-Z0-9]+$/.test(id))throw Error('Invalid saved probe ID')
 const result=await evaluate(`(async()=>{const headers={'Content-Type':'application/json','x-opencode-directory':'/workspace'};const r=await fetch('/session/'+${JSON.stringify(id)}+'/message',{headers});if(!r.ok)throw Error('Probe read failed');const messages=await r.json();const tools=messages.flatMap(m=>m.parts).filter(p=>p.type==='tool');if(tools.length!==1||tools[0].state.input.command!=='/usr/bin/sleep 180')throw Error('Not the isolated sleep probe');const response=await fetch('/session/'+${JSON.stringify(id)}+'/abort',{method:'POST',headers,body:'{}'});if(!response.ok)throw Error('Abort failed');return response.json()})()`)
 console.log(JSON.stringify({id,cleaned:result}))
}
if(action==='screen-off-job-start') {
 const session=await evaluate(`(async()=>{const headers={'Content-Type':'application/json','x-opencode-directory':'/workspace'};if(Object.keys(await (await fetch('/session/status',{headers})).json()).length)throw Error('Other work active');const r=await fetch('/session',{method:'POST',headers,body:JSON.stringify({title:'TinyAgent screen-off runtime probe'})});if(!r.ok)throw Error('Create '+r.status);const session=await r.json();void fetch('/session/'+session.id+'/shell',{method:'POST',headers,body:JSON.stringify({agent:'build',command:'/usr/bin/sleep 65'})}).catch(()=>{});return session})()`)
 console.log(JSON.stringify({session:session.id}))
}
if(action==='recovery-job-start') {
 const session=await evaluate(`(async()=>{const headers={'Content-Type':'application/json','x-opencode-directory':'/workspace'};const status=await (await fetch('/session/status',{headers})).json();if(Object.keys(status).length)throw Error('Other work active');const r=await fetch('/session',{method:'POST',headers,body:JSON.stringify({title:'TinyAgent native stop recovery probe'})});if(!r.ok)throw Error('Create '+r.status);const session=await r.json();void fetch('/session/'+session.id+'/shell',{method:'POST',headers,body:JSON.stringify({agent:'build',command:'/usr/bin/sleep 180'})}).catch(()=>{});return session})()`)
 await writeFile('D:/TinyAgent-work/tinyagent/evidence/lyriq1-native-stop-session.json',JSON.stringify({id:session.id,command:'/usr/bin/sleep 180'},null,2))
 console.log(JSON.stringify({session:session.id}))
}
if(action==='luna-probe-start') {
 const task=process.argv[3] ? await readFile(process.argv[3],'utf8') : undefined
 const session=await evaluate(`(async()=>{const r=await fetch('/session',{method:'POST',headers:{'Content-Type':'application/json','x-opencode-directory':'/workspace'},body:JSON.stringify({title:'Lyriq1 Luna release verification',permission:[{permission:'*',pattern:'*',action:'allow'}]})});if(!r.ok)throw Error('Create '+r.status);return r.json()})()`)
 if(!session?.id)throw Error('Session creation not confirmed')
 await writeFile('D:/TinyAgent-work/tinyagent/evidence/lyriq1-luna-release-session.json',JSON.stringify({id:session.id,scope:'Dedicated user-authorized QA session; existing sessions and credentials unchanged'},null,2))
 const prompt=task?.replaceAll('{{SESSION_ID}}',session.id)??'릴리즈 검증입니다. 실제 bash 도구로 pwd, uname -m, cat /etc/fedora-release를 실행하고 결과를 짧게 보고하세요. 파일이나 설정은 변경하지 마세요. ADB나 root를 요청하지 마세요.'
 const status=await evaluate(`(async()=>{const r=await fetch('/session/'+${JSON.stringify(session.id)}+'/prompt_async',{method:'POST',headers:{'Content-Type':'application/json','x-opencode-directory':'/workspace'},body:JSON.stringify({agent:'build',model:{providerID:'openai',modelID:'gpt-5.6-luna'},parts:[{type:'text',text:${JSON.stringify(prompt)}}]})});if(!r.ok)throw Error('Prompt '+r.status);return r.status})()`)
 console.log(JSON.stringify({session:session.id,status}))
}
if(action==='probe-session') {
 const id=process.argv[3]
 if(!/^ses_[a-zA-Z0-9]+$/.test(id))throw Error('Invalid session ID')
 const report=await evaluate(`(async()=>{const get=async p=>{const r=await fetch(p,{headers:{'x-opencode-directory':'/workspace'}});if(!r.ok)throw Error('HTTP '+r.status);return r.json()};return {id:${JSON.stringify(id)},status:(await get('/session/status'))[${JSON.stringify(id)}]??{type:'idle'},messages:await get('/session/'+${JSON.stringify(id)}+'/message')}})()`)
 await writeFile('D:/TinyAgent-work/tinyagent/evidence/'+id+'-probe.json',JSON.stringify(report,null,2))
 console.log(JSON.stringify({id:report.id,status:report.status,messages:report.messages.map(m=>({role:m.info.role,model:m.info.modelID,error:m.info.error,parts:m.parts.filter(p=>['tool','text'].includes(p.type)).map(p=>({type:p.type,text:p.text,tool:p.tool,state:p.state}))}))}))
}
if(action==='backend-summary') {
 const report=await evaluate(`(async()=>{const get=async p=>{const r=await fetch(p,{headers:{'x-opencode-directory':'/workspace'}});if(!r.ok)throw Error('HTTP '+r.status);return r.json()};const provider=await get('/provider');return {health:await get('/global/health'),connected:provider.connected,sessionCount:(await get('/session')).length,status:await get('/session/status'),lunaModels:provider.all.filter(p=>provider.connected.includes(p.id)).flatMap(p=>Object.entries(p.models).filter(([id,m])=>/luna/i.test(id+' '+m.name)).map(([id,m])=>({provider:p.id,id,name:m.name})))}})()`)
 console.log(JSON.stringify(report))
}
if(action==='open-session') {
 const id=process.argv[3]
 if(!/^ses_[a-zA-Z0-9]+$/.test(id))throw Error('Invalid session ID')
 await call('Page.navigate',{url:'http://127.0.0.1:4097/'+Buffer.from('/workspace').toString('base64url')+'/session/'+id})
 const deadline=Date.now()+30000
 while(!await evaluate(`location.pathname.endsWith(${JSON.stringify('/session/'+id)})&&!!document.querySelector('[data-component="tinyagent-access"]')`)) {
  if(Date.now()>deadline)throw Error('Session UI did not become ready')
  await new Promise(resolve=>setTimeout(resolve,500))
 }
}
if(action==='buttons') console.log(await evaluate(`[...document.querySelectorAll('button')].filter(n=>n.checkVisibility()&&getComputedStyle(n).visibility!=='hidden'&&!n.closest('[aria-hidden="true"]')).map(n=>({text:n.textContent,label:n.getAttribute('aria-label')}))`))
if(action==='session-swipe') {
 const box=await evaluate(`(()=>{const n=document.querySelector('[data-component="home-session-row"]');if(!n)throw Error('No session row');const r=n.getBoundingClientRect();return {x:r.right-70,y:r.y+r.height/2}})()`)
 await call('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[box]})
 for(const distance of [15,40,80,140]) await call('Input.dispatchTouchEvent',{type:'touchMove',touchPoints:[{x:box.x-distance,y:box.y}]})
 await call('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]})
 console.log(await evaluate(`[...document.querySelectorAll('.home-session-actions:not([aria-hidden="true"]) button')].map(n=>n.textContent)`))
}
if(action==='popup-state') {
 const state=await evaluate(`({url:location.href,theme:localStorage.getItem('opencode-color-scheme'),scroll:[...document.querySelectorAll('*')].filter(n=>n.scrollTop>0).map(n=>({tag:n.tagName,slot:n.getAttribute('data-slot'),top:n.scrollTop}))})`)
 await writeFile('D:/TinyAgent-work/tinyagent/evidence/'+process.argv[3]+'.json',JSON.stringify(state,null,2));console.log(state)
}
if(action==='trace-tap') console.log(await evaluate(`(()=>{window.__tap=[];for(const t of ['pointerdown','pointerup','touchstart','touchend','click']) window.addEventListener(t,e=>window.__tap.push({type:t,target:e.target.outerHTML?.slice(0,180)}),true);return 'armed'})()`))
if(action==='trace-result') console.log(await evaluate('window.__tap'))
if(action==='file-probe') console.log(await evaluate(`({hook:window.__tinyagentFiles,ready:document.readyState,links:[...document.querySelectorAll('a[href*="tinyagent/file"]')].map(a=>({target:a.target,html:a.outerHTML.slice(0,400)}))})`))
if(action==='file-self-test') console.log(await evaluate(`(()=>{const a=[...document.querySelectorAll('a[href*="tinyagent/file"]')].find(a=>a.href.includes('app-debug.apk'));a.target='_self';a.click();return 'native navigation requested'})()`))
if(action==='links') {
 await call('Performance.enable',{})
 const links=await evaluate(`(()=>({paths:[...document.querySelectorAll(':not(pre)>code')].filter(n=>n.textContent.trim().startsWith('/workspace/')).map(n=>({text:n.textContent,href:n.closest('a')?.href})),scheme:localStorage.getItem('opencode-color-scheme')}))()`)
 const metrics=await call('Performance.getMetrics',{})
 const report={links,metrics:metrics.metrics.filter(m=>['Nodes','JSHeapUsedSize','TaskDuration','LayoutDuration'].includes(m.name))}
 await writeFile('D:/TinyAgent-work/tinyagent/evidence/'+process.argv[3]+'.json',JSON.stringify(report,null,2))
 console.log(JSON.stringify(report))
}
if(action==='tap'||action==='tap-selector') {
 const name=process.argv[3]
 const box=await evaluate(`(()=>{const ns=[...document.querySelectorAll(${JSON.stringify(action==='tap-selector'?name:'button,[role="tab"]')})];const n=ns.reverse().find(n=>(${action==='tap-selector'?'true':`n.getAttribute('aria-label')===${JSON.stringify(name)}||n.textContent.trim()===${JSON.stringify(name)}`})&&n.checkVisibility()&&getComputedStyle(n).visibility!=="hidden"&&!n.closest('[aria-hidden="true"]'));if(!n)throw Error('Visible target missing');n.scrollIntoView({block:'center'});const r=n.getBoundingClientRect();const x=r.x+r.width/2,y=r.y+r.height/2;if(!n.contains(document.elementFromPoint(x,y)))throw Error('Target covered');return {x,y}})()`)
 if(!box)throw new Error('Visible target missing')
 await call('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[{x:box.x,y:box.y}]})
 await call('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]})
}
if(action==='screenshot') {
 const capture=await call('Page.captureScreenshot',{format:'png'})
 const path='D:/TinyAgent-work/tinyagent/evidence/'+process.argv[3]+'.png'
 await writeFile(path,Buffer.from(capture.data,'base64'))
 console.log(path)
}
if(action==='type') await call('Input.insertText',{text:process.argv[3]})
if(action==='ventoid-result') {
 const r=await evaluate(`(async()=>{const headers={'x-opencode-directory':'/workspace'};const ms=await(await fetch('/session/ses_f7e5bcd52ffeVyPP08izzF4nSU/message',{headers})).json();return {messages:ms.slice(-4).map(m=>({time:m.info.time,parts:m.parts.filter(p=>p.type==='tool'||p.type==='text').map(p=>({type:p.type,text:p.text,tool:p.tool,status:p.state?.status,exit:p.state?.metadata?.exit,command:p.state?.input?.command,output:p.state?.output?.slice(-2000)}))}))}})()`)
 await writeFile('D:/TinyAgent-work/tinyagent/evidence/lyriq1-ventoid-result.json',JSON.stringify(r,null,2))
 console.log(JSON.stringify(r))
}
if(action==='ventoid') console.log(JSON.stringify(await evaluate(`(async()=>{const headers={'x-opencode-directory':'/workspace'};const id='ses_f7e5bcd52ffeVyPP08izzF4nSU';const messages=await(await fetch('/session/'+id+'/message',{headers})).json();return {now:Date.now(),status:await(await fetch('/session/status',{headers})).json(),messages:messages.slice(-4).map(m=>({model:m.info.modelID,time:m.info.time,error:m.info.error,parts:m.parts.filter(p=>p.type==='text'||p.type==='tool').map(p=>({type:p.type,text:p.text,tool:p.tool,state:p.state?.status,time:p.state?.time,command:p.state?.input?.command,output:p.state?.output?.slice(-4500),metadata:p.state?.metadata?{exit:p.state.metadata.exit,output:p.state.metadata.output?.slice(-3000)}:undefined}))}))}})()`)))
if(action==='verify-luna') {
 const report=await evaluate(`(async()=>{const headers={'x-opencode-directory':'/workspace'};const get=async p=>{const r=await fetch(p,{headers});if(!r.ok)throw Error(r.status);return r.json()};const id='ses_f7e337fb5ffet066kklJBM1m2O';const providers=await get('/provider');return {connected:providers.connected,status:await get('/session/status'),messages:(await get('/session/'+id+'/message')).map(m=>({role:m.info.role,model:m.info.modelID,provider:m.info.providerID,complete:!!m.info.time.completed,parts:m.parts.filter(p=>p.type==='text'||p.type==='tool').map(p=>({type:p.type,text:p.text,tool:p.tool,state:p.state?.status,output:p.state?.output}))})),scheme:localStorage.getItem('opencode-color-scheme'),systemDark:matchMedia('(prefers-color-scheme: dark)').matches}})()`)
 await writeFile('D:/TinyAgent-work/tinyagent/evidence/lyriq1-luna-ui-conversation.json',JSON.stringify(report,null,2))
 console.log(JSON.stringify(report))
}
if(action==='theme')console.log(await evaluate('JSON.stringify({saved:localStorage.getItem("opencode-color-scheme"),applied:document.documentElement.dataset.colorScheme,systemDark:matchMedia("(prefers-color-scheme: dark)").matches})'))
else if(action==='inspect') console.log(await evaluate('JSON.stringify({url:location.href,body:document.body.innerText.slice(-6500),buttons:[...document.querySelectorAll("button,[role=tab]")].filter(n=>n.checkVisibility()).map(n=>({name:n.getAttribute("aria-label"),text:n.textContent.trim().slice(0,80)}))})'))
socket.close()
