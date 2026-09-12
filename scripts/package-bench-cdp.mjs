import {writeFile} from 'node:fs/promises'
const port=Number(process.argv[2]), name=process.argv[3]
if(![19222,19223,19224].includes(port)||!/^lyriq[12]$/.test(name))throw Error('Explicit bench device required')
const targets=await(await fetch(`http://127.0.0.1:${port}/json/list`)).json()
const target=targets.find(t=>t.type==='page'&&t.url.startsWith('http://127.0.0.1:4097/'))
if(!target)throw Error('TinyAgent local WebView is not open')
const ws=new WebSocket(target.webSocketDebuggerUrl)
await new Promise((resolve,reject)=>{ws.onopen=resolve;ws.onerror=reject})
const expression=`(async()=>{
 const headers={'Content-Type':'application/json','x-opencode-directory':'/workspace'};
 const post=async(p,body)=>{const r=await fetch(p,{method:'POST',headers,body:JSON.stringify(body)});if(!r.ok)throw Error('API '+r.status);return r.json()};
 const session=await post('/session',{title:'Package benchmark: environment preflight'});
 const results=[];
 for(const command of ${JSON.stringify(process.argv[4]?[process.argv[4]]:['/usr/bin/id','/usr/bin/cat /etc/fedora-release','/usr/bin/cat /proc/self/status','/usr/bin/rpm -q microdnf dnf5 rpm libsolv libdnf libdnf5','/usr/bin/df -h /workspace','/usr/bin/uname -a'])}) {
   results.push({command,result:await post('/session/'+session.id+'/shell',{agent:'build',command})});
 }
 return {session:session.id,results};
})()`
const output=await new Promise((resolve,reject)=>{
 const timeout=setTimeout(()=>reject(Error('Preflight timeout; inspect created session before retry')),120000)
 ws.onmessage=e=>{const d=JSON.parse(e.data);if(d.id!==1)return;clearTimeout(timeout);if(d.error||d.result.exceptionDetails)reject(Error(JSON.stringify(d.error||d.result.exceptionDetails)));else resolve(d.result.result.value)}
 ws.send(JSON.stringify({id:1,method:'Runtime.evaluate',params:{expression,awaitPromise:true,returnByValue:true}}))
})
ws.close()
await writeFile(`D:/TinyAgent-work/tinyagent/evidence/package-bench-${name}-${process.argv[4]?'probe-'+Date.now():'preflight'}.json`,JSON.stringify(output,null,2))
console.log(JSON.stringify(output.results.map(r=>({command:r.command,parts:r.result.parts?.map(p=>({tool:p.tool,status:p.state?.status,output:p.state?.output}))}))))
