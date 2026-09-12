"""Run in the original build image; collect exact installed RPM attribution/notices."""
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile
import io

work = Path('/work')
manifest = json.loads((work / 'build-manifest.json').read_bytes())
records = []
installed = subprocess.check_output(['rpm', '-qa', '--qf',
    '%{NAME}-%{VERSION}-%{RELEASE}.%{ARCH}\t%{SOURCERPM}\n'], text=True).splitlines()
siblings = {}
for line in installed:
    package, source = line.split('\t')
    siblings.setdefault(source, []).append(package)
with tarfile.open(work / 'rpm-notices.tar', 'w') as archive:
    for package in sorted(set(manifest['library_packages'].values())):
        fields = subprocess.check_output(['rpm', '-q', '--qf',
            '%{NAME}-%{VERSION}-%{RELEASE}.%{ARCH}\n%{SOURCERPM}\n%{LICENSE}\n', package], text=True).splitlines()
        if fields[0] != package:
            raise ValueError('Build image package mismatch: ' + package)
        paths = subprocess.check_output(['rpm', '-q', '--licensefiles', package], text=True).splitlines()
        row = dict(package=package, source_rpm=fields[1], license_expression=fields[2], notices=[], missing=[])
        owners = {path: package for path in paths}
        if not paths:
            # RPM subpackages can share notices shipped by the same exact source RPM.
            for sibling in sorted(siblings.get(fields[1], [])):
                for path in subprocess.check_output(['rpm', '-q', '--licensefiles', sibling], text=True).splitlines():
                    owners.setdefault(path, sibling)
            paths = sorted(owners)
        for name in paths:
            path = Path(name)
            if not path.is_file():
                row['missing'].append(name)
                continue
            data = path.read_bytes()
            if len(data) > 2 * 1024 * 1024:
                raise ValueError('Oversized license: ' + name)
            member = package + '/' + (owners[name] + '/' if owners[name] != package else '') + path.name
            if any(item['member'] == member for item in row['notices']):
                raise ValueError('Duplicate notice name: ' + member)
            info = tarfile.TarInfo(member)
            info.size = len(data)
            info.mode = 0o644
            archive.addfile(info, io.BytesIO(data))
            row['notices'].append(dict(path=name, owner_package=owners[name], member=member, sha256=hashlib.sha256(data).hexdigest()))
        records.append(row)
report = dict(source_commit=manifest['candidate_commit'], packages=records,
              notice_archive_sha256=hashlib.sha256((work / 'rpm-notices.tar').read_bytes()).hexdigest(),
              complete_notices=all(row['notices'] and not row['missing'] for row in records),
              source_rpms_downloaded=False)
(work / 'rpm-notices.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(dict(packages=len(records), notices=sum(len(row['notices']) for row in records),
                     missing=sum(len(row['missing']) for row in records), complete=report['complete_notices'])))
