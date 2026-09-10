"""Phone-side isolated backend restart check; never reads existing user state."""
import base64
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import secrets
import signal
import subprocess
import sys
import tempfile
import time
import urllib.request


def main():
    crash = '--crash' in sys.argv
    binary = Path('/shared/opencode-runtime-recovery-1')
    with tempfile.TemporaryDirectory(prefix='tinyagent-runtime-check-') as directory:
        root = Path(directory)
        password = secrets.token_hex(32)
        env = dict(os.environ, HOME=str(root), XDG_CONFIG_HOME=str(root / 'config'),
                   XDG_DATA_HOME=str(root / 'data'), XDG_CACHE_HOME=str(root / 'cache'),
                   XDG_STATE_HOME=str(root / 'state'), OPENCODE_SERVER_PASSWORD=password,
                   OPENCODE_DISABLE_AUTOUPDATE='true')
        authorization = 'Basic ' + base64.b64encode(('opencode:' + password).encode()).decode()

        def request(path, payload=None):
            data = None if payload is None else json.dumps(payload).encode()
            req = urllib.request.Request('http://127.0.0.1:4108' + path, data=data,
                headers={'Authorization': authorization, 'Content-Type': 'application/json',
                         'x-opencode-directory': directory})
            started = time.monotonic()
            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.load(response)
            print(json.dumps({'endpoint': path, 'seconds': round(time.monotonic() - started, 3)}), flush=True)
            return result

        session_id = None
        def start_server(log):
            child = subprocess.Popen([str(binary), 'serve', '--hostname', '127.0.0.1',
                '--port', '4108'], cwd=root, env=env, stdout=log, stderr=log,
                start_new_session=True)
            return child

        def ready(process):
            deadline = time.monotonic() + 45
            while True:
                assert process.poll() is None, 'Candidate server exited before health'
                try:
                    assert request('/global/health')['healthy']
                    return
                except (OSError, ValueError):
                    if time.monotonic() >= deadline:
                        raise RuntimeError('Candidate server health timeout') from None
                    time.sleep(0.5)

        child_script = root / 'child.py'
        child_pid_file = root / 'child.pid'
        child_script.write_text('import os, pathlib, time\n'
            'pathlib.Path(__file__).with_suffix(".pid").write_text(str(os.getpid()))\n'
            'print("TINYAGENT_CANCEL_PARTIAL_OUTPUT", flush=True)\n'
            'time.sleep(120)\n')
        for round_number in range(1, 4):
            with (root / 'server.log').open('w') as log:
                process = start_server(log)
                try:
                    ready(process)
                    if session_id is None:
                        session_id = request('/session', {'title': 'Isolated runtime restart check'})['id']
                    assert request('/session/' + session_id)['id'] == session_id
                    child_pid_file.unlink(missing_ok=True)
                    with ThreadPoolExecutor(max_workers=1) as pool:
                        shell = pool.submit(request, '/session/' + session_id + '/shell',
                            {'agent': 'build', 'command': '/usr/bin/python3 ' + str(child_script)})
                        deadline = time.monotonic() + 20
                        while not child_pid_file.exists():
                            if shell.done():
                                raise AssertionError('Child did not start: ' + str(shell.result()))
                            assert time.monotonic() < deadline, 'Child startup timeout'
                            time.sleep(0.2)
                        child_pid = int(child_pid_file.read_text())
                        if crash:
                            # Kill only this isolated server and the exact child it started.
                            deadline = time.monotonic() + 10
                            while True:
                                before = request('/session/' + session_id + '/message')
                                if 'TINYAGENT_CANCEL_PARTIAL_OUTPUT' in json.dumps(before):
                                    break
                                assert time.monotonic() < deadline, 'Partial output not persisted'
                                time.sleep(0.2)
                            os.kill(process.pid, signal.SIGKILL)
                            process.wait(timeout=5)
                            os.kill(child_pid, signal.SIGKILL)
                            try:
                                shell.result(timeout=10)
                            except (OSError, ValueError):
                                pass  # The killed server cannot complete its HTTP response.
                            process = start_server(log)
                            ready(process)
                            orphan = request('/session/' + session_id + '/message')
                            assert any(p.get('state', {}).get('status') == 'running'
                                for m in orphan for p in m.get('parts', [])), 'No persisted orphan reproduced'
                        assert request('/session/' + session_id + '/abort', {}) is True
                        if not crash:
                            shell.result(timeout=10)
                    deadline = time.monotonic() + 5
                    while Path('/proc', str(child_pid)).exists():
                        stat = Path('/proc', str(child_pid), 'stat').read_text()
                        if stat.split(') ', 1)[1].startswith('Z '):
                            break
                        assert time.monotonic() < deadline, 'Cancelled child still alive'
                        time.sleep(0.1)
                    messages = request('/session/' + session_id + '/message')
                    parts = [p for m in messages for p in m.get('parts', []) if p['type'] == 'tool']
                    assert parts and all(p['state']['status'] not in ('running', 'pending') for p in parts)
                    assert 'TINYAGENT_CANCEL_PARTIAL_OUTPUT' in json.dumps(parts), 'Partial output lost'
                    print(json.dumps({'round': round_number, 'healthy': True,
                        'saved_session_readback': True, 'actual_child_stopped': True,
                        'partial_output_preserved': True, 'no_pending_tools': True,
                        'crash_orphan_recovered': crash}), flush=True)
                except Exception:
                    print((root / 'server.log').read_text(errors='replace')[-6000:].replace(password, '[redacted]'), flush=True)
                    raise
                finally:
                    if process.poll() is None:
                        os.killpg(process.pid, signal.SIGTERM)
                        try:
                            process.wait(timeout=8)
                        except subprocess.TimeoutExpired:
                            os.killpg(process.pid, signal.SIGKILL)
                            process.wait(timeout=5)
        print('PASS: three isolated starts, persisted session readbacks and actual process cancellation; no model call')


if __name__ == '__main__':
    main()
