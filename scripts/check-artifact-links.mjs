import {readFileSync} from 'node:fs'
import vm from 'node:vm'
import assert from 'node:assert/strict'
const source=readFileSync('D:/TinyAgent-work/upstream/opencode/packages/session-ui/src/components/markdown.tsx','utf8')
const body=source.slice(source.indexOf('const urlPattern ='),source.indexOf('function createCopyButton(')).replace('text: string','text')
const context={URL,location:{origin:'http://127.0.0.1:4097'}}
vm.createContext(context);vm.runInContext(body,context)
const link=s=>context.codeUrl(s)
assert.equal(link('/workspace/test 한글.mp4'),'http://127.0.0.1:4097/tinyagent/file?path=test%20%ED%95%9C%EA%B8%80.mp4')
assert.equal(link('/data/user/0/io.github.gplaider.tinyagent.debug/files/linux/workspace/a.apk'),link('/workspace/a.apk'))
for(const p of ['/workspace/../secret','/workspace/a\nsecret','/shared/a.apk']) assert.equal(link(p),undefined)
context.location.origin='https://example.com'
assert.equal(link('/workspace/a.apk'),undefined)
assert.equal(link('https://example.com/a'),'https://example.com/a')
console.log('Artifact path boundary: PASS')
