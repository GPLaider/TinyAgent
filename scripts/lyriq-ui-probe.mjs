import {chromium} from '../../upstream/opencode/packages/app/node_modules/@playwright/test/index.mjs'
const browser=await chromium.connectOverCDP('http://127.0.0.1:19222')
try {
 const page=browser.contexts()[0].pages().find(p=>p.url().startsWith('http://127.0.0.1:4097'))
 const action=process.argv[2]||'inspect'
 if(action==='geometry') {
  console.log(JSON.stringify(await page.getByRole('button').evaluateAll(ns=>ns.map(n=>({name:n.getAttribute('aria-label'),text:n.textContent?.slice(0,40),rect:n.getBoundingClientRect().toJSON(),display:getComputedStyle(n).display,visibility:getComputedStyle(n).visibility}))),null,2))
  await page.screenshot({path:'D:/TinyAgent-work/tinyagent/evidence/lyriq1-ui-geometry.png'})
  process.exitCode=0
 } else {
 if(action==='model') await page.locator('[data-action="prompt-model"]').click()
 if(action==='luna') await page.getByText('GPT-5.6 Luna',{exact:true}).click()
 if(action==='click') await page.getByRole('button',{name:process.argv[3],exact:true}).click()
 if(action==='text') await page.getByText(process.argv[3],{exact:true}).click()
 if(action==='search') await page.getByRole('textbox').last().fill(process.argv[3])
 console.log(JSON.stringify({url:page.url(),body:await page.locator('body').innerText(),buttons:await page.getByRole('button').evaluateAll(nodes=>nodes.map(n=>({text:n.textContent,aria:n.getAttribute('aria-label'),title:n.getAttribute('title')}))),inputs:await page.locator('input,textarea,[contenteditable=true]').evaluateAll(nodes=>nodes.map(n=>({type:n.getAttribute('type'),placeholder:n.getAttribute('placeholder'),'aria-label':n.getAttribute('aria-label')})))},null,2))
 }
} finally {await browser.close()}
