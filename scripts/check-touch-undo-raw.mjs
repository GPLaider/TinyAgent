import {execFileSync} from 'node:child_process'
import {writeFile} from 'node:fs/promises'
const adb='C:/Users/Administrator/AppData/Local/Android/Sdk/platform-tools/adb.exe'
const serial='100.79.65.42:5555'
const shell=(...args)=>execFileSync(adb,['-s',serial,...args],{timeout:30000}).toString().trim()
if(shell('shell','getprop','ro.serialno')!=='ZY22HZPLL8')throw Error('Wrong device')
const installedApk=shell('shell','pm','path','io.github.gplaider.tinyagent.debug').replace('package:','')
const apkSha256=shell('shell','sha256sum',installedApk).split(/\s+/)[0]
const secret=shell('exec-out','run-as','io.github.gplaider.tinyagent.debug','cat','no_backup/stock-backend-auth')
const headers={'Authorization':'Basic '+Buffer.from('opencode:'+secret).toString('base64'),'Content-Type':'application/json','x-opencode-directory':'/workspace'}
const api=async(path,body)=>{
 const response=await fetch('http://127.0.0.1:14098'+path,{headers,method:body?'POST':'GET',body:body?JSON.stringify(body):undefined,signal:AbortSignal.timeout(15000)})
 if(!response.ok)throw Error('API '+response.status)
 return response.json()
}
const seed=Date.now()
// Old fixtures can leave the recent-session window when other tests add sessions.
const sessions=[]
for(const suffix of ['A','B'])sessions.push(await api('/session',{title:`Touch QA ${seed} ${suffix}`}))
await writeFile('D:/TinyAgent-work/tinyagent/evidence/touch-undo-phone-sessions.json',JSON.stringify(sessions.map(s=>({id:s.id,title:s.title}))))
const targets=await(await fetch('http://127.0.0.1:19222/json/list')).json()
const target=targets.find(t=>t.type==='page'&&t.url.startsWith('http://127.0.0.1:4097/'))
if(!target)throw Error('WebView missing')
const ws=new WebSocket(target.webSocketDebuggerUrl)
await new Promise((resolve,reject)=>{ws.onopen=resolve;ws.onerror=reject})
let sequence=0
const call=(method,params={})=>new Promise((resolve,reject)=>{
 const id=++sequence, timeout=setTimeout(()=>reject(Error('CDP '+method+' timeout')),15000)
 ws.onmessage=e=>{const data=JSON.parse(e.data);if(data.id!==id)return;clearTimeout(timeout);data.error?reject(Error(JSON.stringify(data.error))):resolve(data.result)}
 ws.send(JSON.stringify({id,method,params}))
})
const evaluate=async expression=>{const result=await call('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(result.exceptionDetails)throw Error(JSON.stringify(result.exceptionDetails));return result.result.value}
const wait=async expression=>{const end=Date.now()+12000;while(Date.now()<end){if(await evaluate(expression))return;await new Promise(r=>setTimeout(r,80))}throw Error('UI condition failed: '+expression)}
const row=title=>`[...document.querySelectorAll('[data-component="home-session-row"]')].find(n=>n.textContent.includes(${JSON.stringify(title)}))`
const button=(name,scope='document')=>`[...${scope}.querySelectorAll('button')].find(n=>(n.textContent.trim()===${JSON.stringify(name)}||n.getAttribute('aria-label')===${JSON.stringify(name)})&&n.checkVisibility()&&getComputedStyle(n).visibility!=='hidden'&&!n.closest('[aria-hidden="true"]'))`
const point=async expression=>{
 await evaluate(`(${expression}).scrollIntoView({block:'center',behavior:'instant'})`)
 let previous='', stable=0
 for(let i=0;i<40;i++){
  await evaluate(`(${expression}).scrollIntoView({block:'center',behavior:'instant'})`)
  const p=await evaluate(`(()=>{const n=${expression};if(!n)throw Error('Target absent');const r=n.getBoundingClientRect();const p={x:r.x+Math.min(90,r.width/2),y:r.y+r.height/2};if(!n.contains(document.elementFromPoint(p.x,p.y)))return null;return p})()`)
  const value=JSON.stringify(p)
  stable=p&&value===previous?stable+1:0; previous=value
  if(stable>=2)return p
  await new Promise(r=>setTimeout(r,80))
 }
 throw Error('Target did not settle: '+expression+' '+JSON.stringify(await evaluate(`(()=>{const n=${expression};const r=n?.getBoundingClientRect();return {rect:r?.toJSON(),row:n?.closest('.home-session-item')?.outerHTML,hit:r&&document.elementFromPoint(r.x+r.width/2,r.y+r.height/2)?.outerHTML}})()`)))
}
const tap=async expression=>{const p=await point(expression);await call('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[p]});await call('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]})}
const swipe=async(expression,distance)=>{
 const p=await point(expression)
 shell('shell','uiautomator','dump','/sdcard/tinyagent-touch-bounds.xml')
 const xml=shell('shell','cat','/sdcard/tinyagent-touch-bounds.xml')
 const bounds=xml.match(/<node[^>]*class="android\.webkit\.WebView"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"/)
 if(!bounds)throw Error('Native WebView bounds absent')
 const [left,top,right]=bounds.slice(1).map(Number), scale=(right-left)/await evaluate('innerWidth')
 const x=Math.round(left+(p.x+90)*scale), y=Math.round(top+p.y*scale)
 shell('shell','input','swipe',String(x),String(y),String(Math.round(x-distance*scale)),String(y),'220')
}
const screenshot=async name=>{const r=await call('Page.captureScreenshot',{format:'png'});await writeFile('D:/TinyAgent-work/tinyagent/evidence/'+name+'.png',Buffer.from(r.data,'base64'))}
const previousStay=shell('shell','settings','get','global','stay_on_while_plugged_in')
const previousTimeout=shell('shell','settings','get','system','screen_off_timeout')
if(!/^(null|\d+)$/.test(previousStay))throw Error('Unexpected stay-on setting')
if(!/^\d+$/.test(previousTimeout))throw Error('Unexpected screen timeout')
try {
 if(!shell('shell','dumpsys','trust').includes('deviceLocked=0'))throw Error('Unlock the test device first')
 shell('shell','input','keyevent','224')
 shell('shell','wm','dismiss-keyguard')
 shell('shell','am','start','-n','io.github.gplaider.tinyagent.debug/io.github.gplaider.tinyagent.AppActivity')
 shell('shell','svc','power','stayon','true') // UI-only control; separate screen-off acceptance uses stay-on=0.
 shell('shell','settings','put','system','screen_off_timeout','600000')
 await wait(`document.visibilityState==='visible'`)
 await call('Input.dispatchTouchEvent',{type:'touchCancel',touchPoints:[]}).catch(()=>{})
 await call('Page.addScriptToEvaluateOnNewDocument',{source:`window.__touchEvents=[];for(const type of ['pointerdown','pointerup','pointercancel','touchstart','touchend','contextmenu','click'])document.addEventListener(type,e=>window.__touchEvents.push({type,button:e.button,pointerType:e.pointerType,x:e.clientX,y:e.clientY,target:e.target.closest('[data-component]')?.getAttribute('data-component'),title:e.target.closest('[data-component="home-session-row"]')?.textContent}),true)`})
 await evaluate('window.__touchBeforeReload = true')
 if(await evaluate('location.pathname')!=='/')await call('Page.navigate',{url:'http://127.0.0.1:4097/'})
 else await call('Page.reload')
 await wait(`!window.__touchBeforeReload && document.readyState==='complete' && !!${row(sessions[0].title)}`)
 await evaluate(`(()=>{window.__touchEvents=[];for(const type of ['pointerdown','pointerup','pointercancel','touchstart','touchend','contextmenu','click'])document.addEventListener(type,e=>window.__touchEvents.push({type,button:e.button,pointerType:e.pointerType,x:e.clientX,y:e.clientY,target:e.target.closest('[data-component]')?.getAttribute('data-component'),title:e.target.closest('[data-component="home-session-row"]')?.textContent}),true)})()`)
 const p=await point(row(sessions[0].title))
 await call('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[p]})
 await wait(`document.body.textContent.includes('1개 선택')`)
 await call('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]})
 console.log('after hold release',await evaluate(`({selection:document.querySelector('.home-selection-bar')?.textContent,url:location.href})`))
 await tap(row(sessions[1].title))
 await wait(`document.body.textContent.includes('2개 선택')`)
 await screenshot('touch-multiselect-lyriq2')
 await tap(button('삭제',`document.querySelector('.home-selection-bar')`))
 await wait(`!!document.querySelector('[role="dialog"]')`)
 await tap(button('삭제',`document.querySelector('[role="dialog"]')`))
 await wait(`!!document.querySelector('.home-undo-bar')`)
 await screenshot('touch-undo-lyriq2')
 await tap(button('되돌리기',`document.querySelector('.home-undo-bar')`))
 await wait(`!!${row(sessions[0].title)}&&!!${row(sessions[1].title)}`)
 // Swipe one disposable session, assert no modal, then undo it too.
 await swipe(row(sessions[0].title),140)
 await tap(button('삭제',`${row(sessions[0].title)}.closest('.home-session-item')`))
 await wait(`!!document.querySelector('.home-undo-bar')&&!document.querySelector('[role="dialog"]')`)
 await tap(button('되돌리기',`document.querySelector('.home-undo-bar')`))
 await wait(`!!${row(sessions[0].title)}`)
 const remaining=await api('/session')
 if(!sessions.every(s=>remaining.some(r=>r.id===s.id)))throw Error('Undo did not preserve sessions')
 for(const pinned of [true,false]) {
  await swipe(row(sessions[0].title),140)
  await tap(`${row(sessions[0].title)}.closest('.home-session-item').querySelector('.home-session-actions button')`)
  await wait(`!!${row(sessions[0].title)} && ${row(sessions[0].title)}.textContent.includes('📌') === ${pinned}`)
  await evaluate('window.__touchPinBeforeReload = true')
  await call('Page.reload')
  await wait(`!window.__touchPinBeforeReload && document.readyState==='complete' && !!${row(sessions[0].title)} && ${row(sessions[0].title)}.textContent.includes('📌') === ${pinned}`)
  await evaluate(`window.__touchEvents=[];for(const type of ['pointerdown','pointermove','pointerup','pointercancel','click'])document.addEventListener(type,e=>window.__touchEvents.push({type,x:e.clientX,y:e.clientY,title:e.target.closest('[data-component="home-session-row"]')?.textContent}),true)`)
 }
 await tap(`document.querySelector('.home-project-picker > summary')`)
 const project=`[...document.querySelectorAll('[data-component="home-project-row"]')].find(n=>n.textContent.includes('ui-folder-check-0909'))`
 await wait(`!!${project}`)
 const projectPoint=await point(project)
 await call('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[projectPoint]})
 await wait(`document.body.textContent.includes('1개 선택')`)
 await call('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]})
 await tap(button('삭제',`document.querySelector('.home-selection-bar')`))
 await wait(`!!document.querySelector('[role="dialog"]')`)
 await tap(button('삭제',`document.querySelector('[role="dialog"]')`))
 await wait(`!!document.querySelector('.home-undo-bar')`)
 await tap(button('되돌리기',`document.querySelector('.home-undo-bar')`))
 await wait(`!!${project}`)
 await swipe(project,72)
 await tap(button('삭제',`${project}.closest('.home-project-item')`))
 await wait(`!!document.querySelector('.home-undo-bar')&&!document.querySelector('[role="dialog"]')`)
 await screenshot('touch-project-undo-lyriq2')
 await tap(button('되돌리기',`document.querySelector('.home-undo-bar')`))
 await wait(`!!${project}`)
 const report={serial,hardware:'ZY22HZPLL8',apkSha256,sessions:sessions.map(s=>s.id),longPress:true,multiSelect:2,bulkUndo:true,swipeWithoutDialog:true,swipeUndo:true,pinUnpinPersisted:true,serverSessionsPreserved:true,projectLongPress:true,projectBulkUndo:true,projectSwipeUndo:true,theme:await evaluate(`localStorage.getItem('opencode-color-scheme')`)}
 await writeFile('D:/TinyAgent-work/tinyagent/evidence/touch-undo-lyriq2.json',JSON.stringify(report,null,2))
 console.log(JSON.stringify(report))
} catch(error) {
 await screenshot('touch-preview3-failure').catch(()=>{})
 console.log(JSON.stringify(await evaluate(`({events:window.__touchEvents,visibility:document.visibilityState,viewport:[innerWidth,innerHeight,devicePixelRatio]})`)))
 throw error
} finally {
 await call('Input.dispatchTouchEvent',{type:'touchCancel',touchPoints:[]}).catch(()=>{});ws.close()
 if(previousStay==='null')shell('shell','settings','delete','global','stay_on_while_plugged_in')
 else shell('shell','settings','put','global','stay_on_while_plugged_in',previousStay)
 shell('shell','settings','put','system','screen_off_timeout',previousTimeout)
}
