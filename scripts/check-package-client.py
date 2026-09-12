"""Host-only package client checks; never contacts Android or installs packages."""
import contextlib
import importlib.util
import io
from pathlib import Path

spec = importlib.util.spec_from_file_location('packages', Path(__file__).with_name('tinyagent-packages.py'))
client = importlib.util.module_from_spec(spec)
spec.loader.exec_module(client)
calls = []


def complete(name, method, path, payload=None):
    calls.append((method, path, payload))
    return {'status': 'running' if method == 'POST' else 'completed', 'exit_code': 0}


with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()) as err:
    assert client.execute('test', ['install', 'git'], 'fixed-id', complete, lambda _: None) == 0
    assert 'fixed-id' in err.getvalue()
assert [row[0] for row in calls] == ['POST', 'GET']
assert calls[0][2] == {'id': 'fixed-id', 'argv': ['install', '--assumeyes', 'git']}
assert calls[1][1] == '/packages/jobs/fixed-id'
calls.clear()


def disconnect(name, method, path, payload=None):
    calls.append(method)
    raise ConnectionResetError('lost submit response')


with contextlib.redirect_stderr(io.StringIO()) as err:
    try:
        client.execute('test', ['install', 'git'], 'recoverable-id', disconnect)
    except ConnectionResetError:
        pass
    else:
        raise AssertionError('Submission failure was hidden')
    assert 'recoverable-id' in err.getvalue()
assert calls == ['POST'], 'Uncertain submission must not be automatically repeated'
calls.clear()
with contextlib.redirect_stdout(io.StringIO()):
    assert client.execute('test', ['status'], 'existing-id', complete) == 0
assert calls == [('GET', '/packages/jobs/existing-id', None)]
updates = iter([
    {'status': 'running', 'output': 'metadata\n'},
    {'status': 'running', 'output': 'metadata\n'},
    {'status': 'running', 'output': 'metadata\ndownload\n'},
    {'status': 'completed', 'output': 'rotated tail\n', 'output_truncated': True},
])
with contextlib.redirect_stdout(io.StringIO()) as out, contextlib.redirect_stderr(io.StringIO()) as err:
    def progress(*args):
        return next(updates)
    def polling(_):
        assert 'metadata\n' in err.getvalue(), 'Progress must be visible before next poll'
    assert client.execute('test', ['repo', 'refresh'], 'progress-id', progress, polling) == 0
    assert err.getvalue().count('metadata\n') == 1
    assert 'download\n' in err.getvalue() and 'rotated tail\n' in err.getvalue()
    assert out.getvalue().count('"status"') == 1, 'stdout must remain one terminal JSON'
print('PASS: one submission, stable job ID, status polling, no retry after uncertain response')
