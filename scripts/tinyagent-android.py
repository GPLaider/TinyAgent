#!/usr/bin/python3
"""Use TinyAgent's verified self-ADB; no Fedora adb server is required."""
import argparse
import json
from pathlib import Path
import runpy
import sys
import time
import uuid

bridge = runpy.run_path(str(Path(__file__).with_name('tinyagent-packages.py')))
request, BridgeResponseError = bridge['request'], bridge['BridgeResponseError']

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--id', help='Existing UUID for status/cancel or uncertain submission')
    parser.add_argument('--mode', choices=['developer','root'], default='developer')
    parser.add_argument('--cwd', default='/', help='Android working directory, not a Fedora path')
    parser.add_argument('action', choices=['shell','install','status','cancel'])
    parser.add_argument('value', nargs='?', help='Shell command, or workspace-relative APK path')
    args=parser.parse_args()
    if args.action in ('status','cancel') and not args.id:parser.error('status/cancel requires --id')
    if args.action in ('shell','install') and not args.value:parser.error('command/path is required')
    job_id=str(uuid.UUID(args.id)) if args.id else str(uuid.uuid4())
    name=Path('/root/.tinyagent/PACKAGE_SOCKET').read_text().strip()
    if not name.startswith('tinyagent-android-') or '\0' in name:raise RuntimeError('Invalid Android bridge descriptor')
    path='/android/jobs/'+job_id
    print('android_job_id='+job_id,file=sys.stderr,flush=True)
    try:
        if args.action in ('status','cancel'):
            row=request(name,'POST',path+'/inspect',{}) if args.action=='status' else request(name,'DELETE',path)
        else:
            payload={'id':job_id,'mode':args.mode,'action':args.action,'cwd':args.cwd,
                     'command':args.value if args.action=='shell' else '', 'path':args.value if args.action=='install' else ''}
            row=request(name,'POST','/android/jobs',payload)
        while row['status'] in ('queued','starting','checking','running','cancel_requested'):
            time.sleep(1)
            row=request(name,'GET',path)
        print(json.dumps(row,ensure_ascii=False),flush=True)
        return 0 if row['status']=='completed' else 1
    except BridgeResponseError as error:
        print(f'Android bridge rejected the request: {error}',file=sys.stderr)
        return 2
    except Exception as error:
        print(f'{error}\nOutcome unknown. Query --id {job_id} status; do not resubmit. '
              'Use cancel explicitly to stop the recorded process group.',file=sys.stderr)
        return 2

if __name__=='__main__':sys.exit(main())
