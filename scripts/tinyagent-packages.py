#!/usr/bin/python3
"""Submit work to the root's selected package manager through the app, without ADB."""
import argparse
import http.client
import json
from pathlib import Path
import socket
import sys
import time
import uuid

class BridgeResponseError(RuntimeError):
    """The bridge replied with a rejection, rather than losing the connection."""


def request(name, method, path, payload=None):
    body = None if payload is None else json.dumps(payload).encode()
    connection = http.client.HTTPConnection('localhost', timeout=10)
    connection.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    connection.sock.settimeout(10)
    try:
        connection.sock.connect('\0' + name)
        connection.request(method, path, body, {'Content-Type': 'application/json'})
        response = connection.getresponse()
        body = response.read(1048577)
        if len(body) > 1048576:
            raise RuntimeError('Bridge response exceeds 1 MiB')
        data = json.loads(body)
        if response.status != 200:
            raise BridgeResponseError(data.get('error', 'Bridge HTTP ' + str(response.status)))
        return data
    finally:
        connection.close()


def execute(name, operation, job_id, call=request, sleep=time.sleep):
    path = '/packages/jobs/' + job_id
    if operation == ['status']:
        result = call(name, 'GET', path)
    elif operation == ['cancel']:
        result = call(name, 'DELETE', path)
    else:
        if operation[0] == 'install':
            operation = ['install', '--assumeyes', *operation[1:]]
        # Print before submitting: even a lost HTTP response leaves a recoverable ID.
        print('package_job_id=' + job_id, file=sys.stderr, flush=True)
        result = call(name, 'POST', '/packages/jobs', {'id': job_id, 'argv': operation})
        previous = ''
        while True:
            output = result.get('output', '')
            if output != previous:
                if output.startswith(previous):
                    print(output[len(previous):], end='', file=sys.stderr, flush=True)
                else:
                    print('[package log tail refreshed]\n' + output, end='', file=sys.stderr, flush=True)
                previous = output
            if result['status'] not in ('running', 'cancel_requested'):
                break
            sleep(1)
            result = call(name, 'GET', path)
    print(json.dumps(result, ensure_ascii=False), flush=True)
    return 0 if result['status'] == 'completed' else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--id', help='Reuse this UUID for status/cancel or an uncertain submission')
    parser.add_argument('operation', nargs='+', help='install PACKAGES; repo refresh; app-runtime check/recover/migrate; status; cancel')
    args = parser.parse_args()
    if args.operation in (['status'], ['cancel']) and not args.id:
        parser.error('status/cancel requires --id')
    job_id = str(uuid.UUID(args.id)) if args.id else str(uuid.uuid4())
    name = Path('/root/.tinyagent/PACKAGE_SOCKET').read_text().strip()
    if not name.startswith('tinyagent-android-') or '\0' in name:
        raise RuntimeError('Invalid package bridge descriptor')
    try:
        return execute(name, args.operation, job_id)
    except BridgeResponseError as error:
        print(f'Bridge rejected the request: {error}', file=sys.stderr)
        return 2
    except (OSError, ValueError, RuntimeError, http.client.HTTPException) as error:
        print(f'{error}\nTask outcome unknown. Inspect with --id {job_id} status before retrying. '
              'Interrupting this client does not cancel the package transaction.', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
