"""Lyriq2 update evidence: compare session IDs and private credential fingerprints."""
import argparse, base64, hashlib, json, subprocess, urllib.request
from pathlib import Path
parser=argparse.ArgumentParser()
parser.add_argument('phase',choices=['before','after'])
parser.add_argument('--serial', choices=['100.79.65.42:5555', '100.79.134.53:5555', '000501423003390'], default='100.79.65.42:5555')
parser.add_argument('--label', default='preview3')
parser.add_argument('--expected-apk', default='e097d180038d1ba5b03bdda48440098f11c558861cd4c346a5baae0d82082858')
args=parser.parse_args()
assert args.label.replace('-', '').isalnum()
assert len(args.expected_apk) == 64 and all(c in '0123456789abcdef' for c in args.expected_apk)
root=Path(__file__).resolve().parents[1]
adb=Path.home()/'AppData/Local/Android/Sdk/platform-tools/adb.exe'
serial=args.serial
hardware, port={'100.79.65.42:5555':('ZY22HZPLL8',14098), '100.79.134.53:5555':('ZY22J58799',14099), '000501423003390':('000501423003390',14097)}[serial]
package='io.github.gplaider.tinyagent.debug'
def run(*argv):
    return subprocess.check_output([str(adb),'-s',serial,*argv],timeout=30).decode().strip()
assert run('shell','getprop','ro.serialno')==hardware
secret=run('exec-out','run-as',package,'cat','no_backup/stock-backend-auth')
assert len(secret)==64
run('forward','tcp:'+str(port),'tcp:4097')
auth='Basic '+base64.b64encode(('opencode:'+secret).encode()).decode()
def get(path):
    req=urllib.request.Request('http://127.0.0.1:'+str(port)+path,headers={'Authorization':auth,'x-opencode-directory':'/workspace'})
    with urllib.request.urlopen(req,timeout=30) as response:return json.load(response)
assert get('/global/health')['healthy']
ids=sorted(s['id'] for s in get('/session'))
assert ids,'No persisted sessions to verify'
provider=get('/provider')
apk=run('shell','pm','path',package).removeprefix('package:')
report={'serial':serial,'apk_sha256':run('shell','sha256sum',apk).split()[0],
        'session_ids':ids,'backend_credential_sha256':hashlib.sha256(secret.encode()).hexdigest(),
        'connected_providers':sorted(provider['connected'])}
if args.phase=='after':
    old=json.loads((root/f'evidence/{args.label}-update-before.json').read_text())
    # New sessions can push older IDs outside the server's default list page.
    for identifier in set(old['session_ids'])-set(ids):
        assert get('/session/'+identifier)['id']==identifier,'Saved session lost'
    assert old['backend_credential_sha256']==report['backend_credential_sha256'],'Backend credential changed'
    assert old['connected_providers']==report['connected_providers'],'Provider connection changed'
    assert report['apk_sha256']==args.expected_apk
(root/f'evidence/{args.label}-update-{args.phase}.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'phase':args.phase,'sessions':len(ids),'providers':report['connected_providers'],'checks_passed':True}))
