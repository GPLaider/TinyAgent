// Read rendered diagnostics from the explicitly forwarded debug WebView only.
const targets = await (await fetch('http://127.0.0.1:19222/json/list')).json()
const target = targets.find(t => t.type === 'page' && t.url.startsWith('http://127.0.0.1:4097/'))
if (!target) throw new Error('Expected TinyAgent WebView')
const ws = new WebSocket(target.webSocketDebuggerUrl)
await new Promise(resolve => ws.addEventListener('open', resolve, {once:true}))
ws.addEventListener('message', event => {
  const message = JSON.parse(event.data)
  if (message.id === 1) { console.log(JSON.stringify(message.result)); ws.close() }
})
ws.send(JSON.stringify({id:1, method:'Runtime.evaluate', params:{expression:'JSON.stringify({text:document.body.innerText.slice(0,8000),ua:navigator.userAgent})',returnByValue:true}}))
