"""One bounded request using the connected zero-cost provider; no user conversations touched."""
import base64,json,subprocess,time,urllib.request
from pathlib import Path
root=Path(__file__).resolve().parents[1]
adb=Path.home()/'AppData/Local/Android/Sdk/platform-tools/adb.exe'
serial='100.79.65.42:5555'
package='io.github.gplaider.tinyagent.debug'
def run(*args):return subprocess.check_output([str(adb),'-s',serial,*args],timeout=30).decode().strip()
assert run('shell','getprop','ro.serialno')=='ZY22HZPLL8'
secret=run('exec-out','run-as',package,'cat','no_backup/stock-backend-auth')
run('forward','tcp:14098','tcp:4097')
headers={'Authorization':'Basic '+base64.b64encode(('opencode:'+secret).encode()).decode(),
         'Content-Type':'application/json','x-opencode-directory':'/workspace'}
def request(path,body=None):
    req=urllib.request.Request('http://127.0.0.1:14098'+path,data=None if body is None else json.dumps(body).encode(),headers=headers)
    with urllib.request.urlopen(req,timeout=30) as response:
        data=response.read()
        return json.loads(data) if data else None
catalog=request('/provider')
assert 'opencode' in catalog['connected']
model=next(p for p in catalog['all'] if p['id']=='opencode')['models']['big-pickle']
assert model['cost']['input']==model['cost']['output']==0
session=request('/session',{'title':'Preview3 provider smoke','permission':[
    {'permission':'bash','pattern':'/usr/bin/pwd','action':'allow'},
    {'permission':'bash','pattern':'pwd','action':'allow'}]})
report={'serial':serial,'session':session['id'],'model':'opencode/big-pickle','passed':False}
began=time.monotonic()
try:
    request('/session/'+session['id']+'/prompt_async',{'agent':'build','model':{'providerID':'opencode','modelID':'big-pickle'},
      'parts':[{'type':'text','text':'Use the bash tool to run exactly /usr/bin/pwd. No other commands, file reads, writes or network. Report its output and TINYAGENT_PREVIEW_OK.'}]})
    while time.monotonic()-began<180:
        messages=request('/session/'+session['id']+'/message')
        parts=[p for m in messages for p in m['parts']]
        tools=[p for p in parts if p['type']=='tool']
        if any(m['info'].get('error') for m in messages):raise AssertionError('Provider returned an error')
        if any(p.get('type')=='text' and 'TINYAGENT_PREVIEW_OK' in p.get('text','') for m in messages if m['info']['role']=='assistant' for p in m['parts']):
            assert any(p['tool']=='bash' and p['state']['status']=='completed' and '/workspace' in p['state'].get('output','') for p in tools)
            report.update(passed=True,tools=[{'tool':p['tool'],'status':p['state']['status']} for p in tools])
            break
        pending=[p for p in request('/permission') if p['sessionID']==session['id']]
        if pending:raise AssertionError('Unexpected permission request for bounded pwd task')
        time.sleep(2)
    assert report['passed'],'Model deadline exceeded'
finally:
    report['elapsed_seconds']=time.monotonic()-began
    if not report['passed']:request('/session/'+session['id']+'/abort',{})
    (root/'evidence/preview3-provider-smoke.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))
