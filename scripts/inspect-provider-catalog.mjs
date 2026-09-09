import {chromium} from '../../upstream/opencode/packages/app/node_modules/@playwright/test/index.mjs'
const b=await chromium.connectOverCDP('http://127.0.0.1:19222')
try {
 const p=b.contexts()[0].pages().find(p=>p.url().startsWith('http://127.0.0.1:4097'))
 console.log(JSON.stringify(await p.evaluate(async()=>{
  const r=await fetch('/provider',{headers:{'x-opencode-directory':'/workspace'}})
  const data=await r.json()
  return {connected:data.connected,models:data.all.filter(p=>p.id==='openai').flatMap(p=>Object.values(p.models).filter(m=>/luna|5\.6/i.test(m.id+' '+m.name)).map(m=>({id:m.id,name:m.name,status:m.status}))),url:location.href,body:document.body.innerText.slice(-2400)}
 }),null,2))
} finally {await b.close()}
