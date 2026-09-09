"""Export existing APK delta spans for Android's built-in toybox dd; no Python on phone."""
import base64
import hashlib
import json
from pathlib import Path
import re
import sys

plan=json.loads(Path(sys.argv[1]).read_text())
out=Path(sys.argv[2])
output_name=sys.argv[3] if len(sys.argv)>3 else 'tinyagent-touch-guard.apk'
assert re.fullmatch(r'[A-Za-z0-9_-]+\.apk',output_name)
assert all(re.fullmatch('[0-9a-f]{64}',plan[key]) for key in ('old','new'))
payload=bytearray()
commands=[]
position=0
for span in plan['spans']:
    if isinstance(span,list):
        start,size=span
        assert isinstance(start,int) and isinstance(size,int) and start>=0 and size>=0
        source='"$1"'
    else:
        data=base64.b64decode(span,validate=True)
        start,size=len(payload),len(data)
        payload.extend(data)
        source='"$2"'
    if size:
        commands.append(f'dd if={source} of="$patch_output" bs=1048576 skip={start} count={size} seek={position} iflag=skip_bytes,count_bytes oflag=seek_bytes conv=notrunc status=none')
    position+=size
assert position==plan['size']
out.with_suffix('.bin').write_bytes(payload)
script=['#!/system/bin/sh','set -eu',
        'patch_output=/data/local/tmp/'+output_name,
        '[ ! -e "$patch_output" ]',
        f'[ "$(sha256sum "$1" | cut -d " " -f 1)" = {plan["old"]} ]',
        f'[ "$(sha256sum "$2" | cut -d " " -f 1)" = {hashlib.sha256(payload).hexdigest()} ]',
        ': > "$patch_output"',*commands,
        f'[ "$(sha256sum "$patch_output" | cut -d " " -f 1)" = {plan["new"]} ]',
        'echo "Verified exact signed APK: $patch_output"']
out.with_suffix('.sh').write_text('\n'.join(script)+'\n',encoding='utf-8',newline='\n')
print(json.dumps({'payload_bytes':len(payload),'copy_spans':len(commands),'apk_sha256':plan['new']}))
