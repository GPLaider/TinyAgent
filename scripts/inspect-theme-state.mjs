import {chromium} from '../../upstream/opencode/packages/app/node_modules/@playwright/test/index.mjs'
const browser=await chromium.connectOverCDP('http://127.0.0.1:19222')
try {
 const page=browser.contexts()[0].pages().find(p=>p.url().startsWith('http://127.0.0.1:4097/'))
 console.log(JSON.stringify(await page.evaluate(()=>{
  const state=()=>({at:new Date().toISOString(),saved:localStorage.getItem('opencode-color-scheme'),theme:localStorage.getItem('opencode-theme-id'),applied:document.documentElement.dataset.colorScheme,systemDark:matchMedia('(prefers-color-scheme: dark)').matches,visibility:document.visibilityState})
  if(!window.__tinyThemeAudit){
   window.__tinyThemeAudit=[state()]
   const record=()=>{window.__tinyThemeAudit.push(state());if(window.__tinyThemeAudit.length>100)window.__tinyThemeAudit.shift()}
   new MutationObserver(record).observe(document.documentElement,{attributes:true,attributeFilter:['data-color-scheme','data-theme']})
   matchMedia('(prefers-color-scheme: dark)').addEventListener('change',record)
   document.addEventListener('visibilitychange',record)
  }
  return {current:state(),events:window.__tinyThemeAudit}
 }),null,2))
}finally{await browser.close()}
