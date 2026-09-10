import {writeFile} from 'node:fs/promises'
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
 const timeout=setTimeout(()=>reject(new Error('CDP timeout')),10000)
 socket.onmessage=event=>{const data=JSON.parse(event.data);if(data.id===id){clearTimeout(timeout);if(data.error)reject(new Error(data.error.message));else resolve(data.result)}}
 socket.send(JSON.stringify({id,method,params}))
})
const evaluate=async expression=>(await call('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true})).result.value
const action=process.argv[2]??'theme'
if(action==='open-session') {
 const id=process.argv[3]
 if(!/^ses_[a-zA-Z0-9]+$/.test(id))throw Error('Invalid session ID')
 await call('Page.navigate',{url:'http://127.0.0.1:4097/'+Buffer.from('/workspace').toString('base64url')+'/session/'+id})
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
