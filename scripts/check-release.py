"""Check evidence completeness, not device behavior. No network or device writes.

Usage: python scripts/check-release.py evidence/candidate.json
       python scripts/check-release.py --self-check
"""
import argparse
import hashlib
import json
import tempfile
from pathlib import Path

JOURNEYS = (
    'first-install', 'sessions', 'self-root-adb', 'fedora-development',
    'android-fedora-exchange', 'interruption-recovery', 'app-update',
)


def digest(path):
    with path.open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def checked_file(base, value):
    path = Path(value['path'])
    if path.is_absolute() or '..' in path.parts:
        raise ValueError('Evidence paths must be relative to the candidate directory')
    resolved = (base / path).resolve()
    if not resolved.is_relative_to(base.resolve()) or not resolved.is_file():
        raise ValueError('Evidence file missing or outside candidate directory')
    if resolved.stat().st_size == 0 or digest(resolved) != value['sha256']:
        raise ValueError('Evidence file is empty or its checksum differs')
    return resolved


def check(candidate, base):
    if candidate['schema'] != 1:
        raise ValueError('Unsupported evidence schema')
    apk = checked_file(base, candidate['apk'])
    if apk.suffix != '.apk':
        raise ValueError('Candidate artifact must be an APK')
    checked_file(base, candidate['apk']['signer_report'])
    if type(candidate['apk']['version_code']) is not int or candidate['apk']['version_code'] < 1 or not candidate['apk']['version_name']:
        raise ValueError('APK version code and name are required')
    for name in ('certificate_sha256', 'source_commit'):
        value = candidate['apk'][name]
        size = 64 if name == 'certificate_sha256' else 40
        if len(value) != size or any(c not in '0123456789abcdef' for c in value):
            raise ValueError('Invalid ' + name)
    if candidate['apk'].get('dirty_source') is not False:
        raise ValueError('Release source must be recorded as clean')
    for name in ('serial', 'model', 'android', 'abi'):
        if not candidate['device'].get(name):
            raise ValueError('Missing device identity: ' + name)
    if candidate['device']['abi'] != 'arm64-v8a':
        raise ValueError('This release gate covers Android ARM64 only')
    # Three complete consecutive rounds on the same APK and device, not three
    # selected successes with failures silently omitted between them.
    rounds = candidate['rounds']
    if len(rounds) < 3:
        raise ValueError('At least three complete rounds are required')
    last = rounds[-3:]
    used_logs = set()
    for index, run in enumerate(last):
        if type(run['sequence']) is not int or run['sequence'] < 1:
            raise ValueError('Round sequence must be a positive integer')
        if index and run['sequence'] != last[index - 1]['sequence'] + 1:
            raise ValueError('Final three round numbers are not consecutive')
        if run['apk_sha256'] != candidate['apk']['sha256'] or run['serial'] != candidate['device']['serial']:
            raise ValueError('Round targets a different APK or device')
        if set(run['journeys']) != set(JOURNEYS):
            raise ValueError('A mandatory journey is missing or misspelled')
        for journey in JOURNEYS:
            result = run['journeys'][journey]
            if result['status'] != 'pass':
                raise ValueError('Unpassed journey: ' + journey)
            log = checked_file(base, result['log'])
            if log in used_logs:
                raise ValueError('Each journey execution needs its own evidence log')
            used_logs.add(log)
            if journey == 'fedora-development':
                change = result['change']
                if type(change['before_exit']) is not int or type(change['after_exit']) is not int or change['before_exit'] == 0 or change['after_exit'] != 0:
                    raise ValueError('Development needs failing-before/passing-after tests')
                checked_file(base, change['diff'])
        checked_file(base, run['resource_report'])
    providers = candidate['providers']
    if not providers or not any(p.get('response_and_tool') == 'pass' for p in providers):
        raise ValueError('No provider has a recorded response and tool execution')
    for provider in providers:
        if not provider.get('name') or not provider.get('scope'):
            raise ValueError('Provider validation scope is required')
        if provider.get('response_and_tool') == 'pass':
            checked_file(base, provider['log'])
    for name in ('runtime_manifest', 'harness_report', 'license_report', 'user_guide', 'known_issues'):
        checked_file(base, candidate[name])
    return {'evidence_complete': True, 'apk_sha256': candidate['apk']['sha256'], 'serial': candidate['device']['serial'], 'rounds': [r['sequence'] for r in last]}


def self_check():
    # Synthetic unit evidence only. Never used as device acceptance evidence.
    with tempfile.TemporaryDirectory() as directory:
        base = Path(directory)
        def file(name):
            path = base / name
            path.write_text('synthetic unit-test evidence: ' + name, encoding='utf-8')
            return {'path': name, 'sha256': digest(path)}
        candidate = {
            'schema': 1,
            'apk': {**file('unit.apk'), 'certificate_sha256': 'a' * 64, 'source_commit': 'b' * 40,
                    'version_code': 1, 'version_name': 'unit', 'dirty_source': False, 'signer_report': file('signer.log')},
            'device': {'serial': 'UNIT-ONLY', 'model': 'unit', 'android': '16', 'abi': 'arm64-v8a'},
            'rounds': [],
            'providers': [{'name': 'unit', 'scope': 'synthetic parser test', 'response_and_tool': 'pass', 'log': file('provider.log')}],
            **{name: file(name + '.txt') for name in ('runtime_manifest', 'harness_report', 'license_report', 'user_guide', 'known_issues')},
        }
        for sequence in range(1, 4):
            journeys = {name: {'status': 'pass', 'log': file(f'{sequence}-{name}.log')} for name in JOURNEYS}
            journeys['fedora-development']['change'] = {'before_exit': 1, 'after_exit': 0, 'diff': file(f'{sequence}.diff')}
            candidate['rounds'].append({'sequence': sequence, 'serial': 'UNIT-ONLY', 'apk_sha256': candidate['apk']['sha256'], 'journeys': journeys, 'resource_report': file(f'resources-{sequence}.txt')})
        assert check(candidate, base)['evidence_complete']
        def rejected(change):
            sample = json.loads(json.dumps(candidate))
            change(sample)
            try:
                check(sample, base)
            except (ValueError, KeyError, TypeError):
                return
            raise AssertionError('Incomplete or inconsistent evidence accepted')
        rejected(lambda x: x['rounds'].pop())
        rejected(lambda x: x['rounds'][-1].update(sequence=5))
        rejected(lambda x: x['rounds'][-1].update(sequence=True))
        rejected(lambda x: x['rounds'][-1].update(serial='OTHER'))
        rejected(lambda x: x['rounds'][-1]['journeys']['sessions'].update(status='fail'))
        rejected(lambda x: x['rounds'][-1]['journeys']['fedora-development']['change'].update(before_exit=0))
        rejected(lambda x: x['rounds'][-1]['journeys']['fedora-development']['change'].update(before_exit='1'))
        rejected(lambda x: x['apk'].update(version_code=0))
        rejected(lambda x: x['providers'][0].update(response_and_tool='not-tested'))
        rejected(lambda x: x['apk'].update(sha256='0' * 64))
        rejected(lambda x: x['apk'].update(path='../outside.apk'))
        rejected(lambda x: x['rounds'][1]['journeys']['sessions'].update(log=x['rounds'][0]['journeys']['sessions']['log']))
    print('Release evidence guards passed (synthetic unit checks only).')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('candidate', nargs='?', type=Path)
    parser.add_argument('--self-check', action='store_true')
    args = parser.parse_args()
    if args.self_check:
        self_check()
    elif args.candidate:
        try:
            print(json.dumps(check(json.loads(args.candidate.read_text(encoding='utf-8')), args.candidate.parent)))
        except (ValueError, KeyError, TypeError, OSError) as error:
            print(json.dumps({'evidence_complete': False, 'error': str(error)}))
            raise SystemExit(1)
    else:
        parser.error('candidate or --self-check is required')
