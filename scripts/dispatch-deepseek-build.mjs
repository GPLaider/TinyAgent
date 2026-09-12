// Invoke only after the supervisor verifies dnfast deployment on all three phones.
import {chromium} from '../../upstream/opencode/packages/app/node_modules/@playwright/test/index.mjs'
import {readFile,mkdir,writeFile} from 'node:fs/promises'
import {execFileSync} from 'node:child_process'
import {homedir} from 'node:os'
import assert from 'node:assert/strict'

const [device,job,mode]=process.argv.slice(2)
assert(mode==='--prepare'||mode==='--submit','Specify --prepare or --submit')
const root=new URL('../',import.meta.url)
const spec=JSON.parse(await readFile(new URL('benchmarks/package-manager/deepseek-campaign.json',root)))
const assignment=spec.devices.find(d=>d.name===device)
assert(assignment?.jobs.includes(job),'Job is not assigned to this device')
const inputs=JSON.parse(await readFile(new URL('benchmarks/package-manager/workloads.json',root)))
const input=inputs.workloads.find(w=>w.name.toLowerCase().replaceAll(' ','-')===job)
assert(input && /^[a-f0-9]{40}$/.test(input.commit))
const prompt=[spec.common_prompt,
 `Your only assigned app is ${input.name}. Source: ${input.url}. Baseline revision: ${input.commit}. Inspect /workspace/tinyagent-six-builds/${job} and other existing checkouts first. Preserve existing changes; report any revision difference instead of resetting them. Read this project's build instructions and diagnose its actual failures. Previous artifacts do not count as a new successful build.`,
 assignment.concurrency>1?spec.parallel_prompt:spec.sequential_prompt].join('\n\n')
if(mode==='--prepare') {
 console.log(JSON.stringify({device,job,model:spec.model,prompt},null,2))
 process.exit(0)
}
const transports={pacman:['000501423003390',19222],lyriq1:['100.79.134.53:5555',19223],lyriq2:['100.79.65.42:5555',19224]}
const [serial,port]=transports[device]
const workspace=`/workspace/tinyagent-six-builds/${job}`
const adb=(...args)=>execFileSync(homedir()+'/AppData/Local/Android/Sdk/platform-tools/adb.exe',['-s',serial,...args],{encoding:'utf8',timeout:30000}).trim()
assert.equal(adb('shell','getprop','ro.serialno'),assignment.hardware_serial)
const apk=adb('shell','pm','path','io.github.gplaider.tinyagent.debug')
assert(/^package:\/data\/app\/[^\r\n]+\/base\.apk$/.test(apk),'Expected one installed base APK')
const apkHash=adb('shell','sha256sum',apk.slice(8)).split(/\s+/)[0]
assert(/^[a-f0-9]{64}$/.test(apkHash),'Missing installed APK hash')
const pid=adb('shell','pidof','io.github.gplaider.tinyagent.debug')
assert(/^\d+$/.test(pid),'App must already be running')
adb('forward','tcp:'+port,'localabstract:webview_devtools_remote_'+pid)
const directory=new URL('evidence/go-campaign/',root)
await mkdir(directory,{recursive:true})
const file=new URL(`${device}-${job}-run.json`,directory)
const record={device,job,hardware_serial:assignment.hardware_serial,installed_apk_sha256:apkHash,model:spec.model,baseline:input.commit,prompt,status:'reserved',created_at:new Date().toISOString()}
// A lost response is uncertain. Never automatically create or submit another job.
await writeFile(file,JSON.stringify(record,null,2),{flag:'wx'})
const browser=await chromium.connectOverCDP('http://127.0.0.1:'+port)
try {
 const page=browser.contexts()[0].pages().find(p=>p.url().startsWith('http://127.0.0.1:4097/'))
 assert(page,'No local backend WebView')
 const session=await page.evaluate(async({title,model,workspace})=>{
  const headers={'Content-Type':'application/json','x-opencode-directory':workspace}
  const catalogResponse=await fetch('/provider',{headers,signal:AbortSignal.timeout(30000)})
  if(!catalogResponse.ok)throw Error('Provider catalog unavailable')
  const catalog=await catalogResponse.json()
  if(!catalog.connected.includes(model.providerID)||!catalog.all.find(p=>p.id===model.providerID)?.models[model.modelID])throw Error('Requested model unavailable')
  const response=await fetch('/session',{method:'POST',headers,body:JSON.stringify({title,permission:[{permission:'*',pattern:'*',action:'allow'}]}),signal:AbortSignal.timeout(30000)})
  if(!response.ok)throw Error('Session create HTTP '+response.status)
  return response.json()
 },{title:'DeepSeek 4.1 · '+input.name,model:spec.model,workspace})
 record.session=session.id;record.status='created'
 await writeFile(file,JSON.stringify(record,null,2))
 await page.evaluate(async({session,model,prompt,workspace})=>{
  const response=await fetch('/session/'+session+'/prompt_async',{method:'POST',headers:{'Content-Type':'application/json','x-opencode-directory':workspace},body:JSON.stringify({agent:'build',model,parts:[{type:'text',text:prompt}]}),signal:AbortSignal.timeout(30000)})
  if(!response.ok)throw Error('Prompt HTTP '+response.status)
 },{session:session.id,model:spec.model,prompt,workspace})
 record.status='submitted';record.submitted_at=new Date().toISOString()
 await writeFile(file,JSON.stringify(record,null,2))
 console.log(JSON.stringify({device,job,session:session.id,status:record.status}))
} finally {await browser.close()}
