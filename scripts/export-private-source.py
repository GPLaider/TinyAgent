"""Refresh the existing private release checkout with an explicit source allowlist."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import argparse

source = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--apk', type=Path, required=True, help='Exact verified APK associated with this source snapshot')
args = parser.parse_args()
assert args.apk.is_file() and args.apk.suffix == '.apk'
destination = source.parent/'github-private/TinyAgent'
assert subprocess.check_output(['git', '-C', str(destination), 'remote', 'get-url', 'origin'], text=True).strip() == 'https://github.com/GPLaider/TinyAgent.git'
snapshot = json.loads((destination/'SOURCE-SNAPSHOT.json').read_text())
names = set(snapshot['files_sha256'])
rpm_notices = json.loads((source/'runtime/dnfast-rpm-notices.json').read_text())
names.update('app/src/main/assets/licenses/dnfast-rpm/' + notice['member']
             for package in rpm_notices['packages'] for notice in package['notices'])
names.update('app/src/main/assets/licenses/' + notice['file']
             for notice in json.loads((source/'runtime/dnfast-source-notices.json').read_bytes()))
names.update(str(p.relative_to(source)).replace('\\', '/') for p in (source/'benchmarks/package-manager').glob('*') if p.suffix in {'.py', '.sh', '.md', '.json'})
for directory in ('app/src/main/java', 'app/src/debug/java', 'app/src/main/res'):
    names.update(str(p.relative_to(source)).replace('\\', '/') for p in (source/directory).rglob('*') if p.is_file())
names.update(('app/src/main/AndroidManifest.xml', 'app/src/debug/AndroidManifest.xml'))
names.update([
    'app/src/main/java/io/github/gplaider/tinyagent/DnfastRuntime.java',
    'app/src/main/java/io/github/gplaider/tinyagent/PackageJobs.java',
    'app/src/main/java/io/github/gplaider/tinyagent/RuntimeProcessOutput.java',
    'app/src/main/assets/licenses/dnfast-LICENSE.txt',
    'app/src/main/assets/licenses/dnfast-cargo-notices.tar',
    'runtime/dnfast-source-export.json',
    'runtime/dnfast-cargo-sources.json', 'scripts/collect-dnfast-cargo-sources.py',
    'runtime/dnfast-library-sources.json', 'scripts/collect-dnfast-library-sources.py',
    'runtime/dnfast-cargo-notices.json', 'scripts/collect-dnfast-cargo-notices.py',
    'runtime/dnfast-target-tree.txt', 'runtime/dnfast-target-tree-invocation.json',
    'runtime/dnfast-target-notices.json', 'scripts/check-dnfast-target-notices.py',
    'scripts/collect-dnfast-target-tree.py',
    'runtime/dnfast-additional-source-rpms.json', 'runtime/dnfast-source-notices.json',
    'scripts/stage-dnfast-source-notices.py',
    'native/app-memfd-probe.c', 'docs/DNFAST-PACMAN-MEMFD.md',
    'runtime/dnfast-library-provenance.json',
    'runtime/dnfast-rpm-notices.json',
    'scripts/collect-dnfast-rpm-notices.py', 'scripts/stage-dnfast-rpm-notices.py',
    'scripts/record-dnfast-library-provenance.py',
    'runtime/dnfast-1449710-manifest.json',
    'runtime/dnfast-1449710-root-overlay.tar.gz',
    'scripts/stage-dnfast-runtime.py', 'scripts/collect-dnfast-sources.py',
    'scripts/tinyagent-packages.py', 'scripts/check-package-client.py',
    'scripts/check-package-progress-live.py', 'scripts/verify-campaign-apks.py',
    'scripts/check-package-planning.py',
    'scripts/check-process-exit-report.py',
    'scripts/export-gui-patch.py',
    'docs/PRERELEASE-CURRENT.md',
    'docs/RELEASE-0.0.1-ALPHA.1.md',
    'docs/DNFAST-UPGRADE.md',
    'docs/ARM-BUILD-CASEBOOK.md',
    'scripts/upgrade-dnfast-empty.py', 'scripts/upgrade-dnfast-checked.py', 'scripts/check-dnfast-empty-upgrade.py',
    'scripts/check-phone-package-cancel.py',
    'app/src/main/java/io/github/gplaider/tinyagent/AndroidJobs.java',
    'scripts/android-job.sh', 'scripts/tinyagent-android.py',
    'scripts/check-android-jobs-live.py', 'docs/ANDROID-EXECUTION-INTEGRATION.md',
    'docs/DEEPSEEK-CAMPAIGN-OBSERVATIONS.md',
    'scripts/inspect-live-session.mjs',
    'scripts/dispatch-deepseek-build.mjs',
    'scripts/check-package-jobs-cancel.py', 'scripts/RuntimeProcessOutputCheck.java',
    'scripts/check-dnfast-self-build-inputs.py', 'docs/DNFAST-PRODUCT-INTEGRATION.md',
    'native/fd-gate/probe.c', 'native/fd-gate/executor_fd.c',
    'native/fd-gate/dnfast_native.h', 'native/fd-gate/LICENSE', 'native/fd-gate/PROVENANCE.json',
    'app/src/main/java/io/github/gplaider/tinyagent/DnfastResult.java',
    'app/src/debug/java/io/github/gplaider/tinyagent/DnfastResultCheck.java',
    'scripts/collect-pacman-build.py', 'scripts/export-private-source.py',
    'scripts/verify-source-snapshot.py',
    'scripts/check-luna-development-evidence.py',
    'scripts/check-luna-screenoff-evidence.py', 'scripts/check-startup-placeholder.mjs',
    'scripts/check-video-navigation.py',
    'scripts/check-luna-reconnect.mjs',
    'scripts/check-runtime-candidate.py',
    'scripts/package-opencode-runtime.py',
    'scripts/RuntimeExecutableCheck.java',
    'scripts/RuntimeProcessIdentityCheck.java',
    'app/src/main/java/io/github/gplaider/tinyagent/RuntimeProcessIdentity.java',
    'app/src/debug/java/io/github/gplaider/tinyagent/RuntimeRecoveryProbeActivity.java',
    'app/src/main/java/io/github/gplaider/tinyagent/RuntimeExecutable.java',
    'runtime/models-runtime-recovery-1.json', 'runtime/opencode-runtime-recovery-1.json',
    'runtime/opencode-runtime-recovery-1.patch',
    'patches/proot-exitkill.patch',
    'scripts/build-proot-candidate.py', 'scripts/package-proot-candidate.py',
    'runtime/proot-exitkill-1.json', 'runtime/proot-exitkill-1.tar.gz',
    'patches/proot-fchmodat2.patch', 'scripts/build-proot-fchmodat2.py',
    'runtime/proot-fchmodat2-2.json', 'runtime/proot-fchmodat2-2.tar.gz',
    'tests/proot-chmod/probe.c', 'tests/proot-chmod/Probe.java',
    'tests/proot-chmod/AndroidManifest.xml', 'scripts/build-proot-chmod-probe.py',
    'docs/PROOT-FCHMODAT2-VALIDATION.md',
    'docs/PROOT-EXITKILL-VALIDATION.md',
    'benchmarks/package-manager/luna-proot-integration.txt',
    'scripts/check-luna-proot-integration.py',
    'runtime/opencode-runtime-recovery-2.json', 'runtime/opencode-runtime-recovery-2.patch',
    'runtime/opencode-notification-3.json', 'runtime/opencode-notification-3.patch',
    'runtime/opencode-snapshot-4.json', 'runtime/opencode-snapshot-4.patch',
    'runtime/opencode-snapshot-12.json', 'runtime/opencode-snapshot-12.patch', 'runtime/opencode-snapshot-11.json', 'runtime/opencode-snapshot-11.patch', 'runtime/opencode-snapshot-10.json', 'runtime/opencode-snapshot-10.patch', 'runtime/opencode-snapshot-9.json', 'runtime/opencode-snapshot-9.patch', 'runtime/opencode-snapshot-8.json', 'runtime/opencode-snapshot-8.patch', 'runtime/opencode-snapshot-7.json', 'runtime/opencode-snapshot-7.patch', 'runtime/opencode-snapshot-6.json', 'runtime/opencode-snapshot-6.patch', 'runtime/opencode-snapshot-5.json', 'runtime/opencode-snapshot-5.patch',
    'docs/SNAPSHOT-LATENCY.md',
    'docs/SNAPSHOT-WRITER-ISOLATION.md',
    'docs/STARTUP-RECOVERY-VALIDATION.md',
    'scripts/check-native-stop-recovery.py',
    'scripts/check-screen-off-runtime.py',
    'docs/SCREEN-OFF-CURRENT-VALIDATION.md',
    'docs/GUI-PRODUCTION-CHANNEL.md',
    'docs/RELEASE-SIGNING.md', 'scripts/prepare-release-signing.py',
    'scripts/check-phone-build-variant.py',
    'scripts/check-runtime-input-separation.py',
    'scripts/configure-arm-aidl.py',
    'benchmarks/package-manager/luna-self-build-preflight.txt',
    'benchmarks/package-manager/luna-current-self-build.txt',
    'benchmarks/package-manager/luna-installed-runtime-inputs.txt',
    'scripts/serve-one-source-bundle.py', 'docs/LYRIQ1-CURRENT-SELF-BUILD.md',
    'benchmarks/package-manager/luna-startup-recovery-check.txt',
    'app/src/main/java/io/github/gplaider/tinyagent/VideoPreviewActivity.java',
    'benchmarks/package-manager/luna-development-acceptance.txt',
    'benchmarks/package-manager/luna-media-acceptance.txt',
    'benchmarks/package-manager/luna-video-fixture.txt',
    'docs/PREVIEW4.md', 'docs/PRERELEASE-4-VALIDATION.md',
    'docs/PREVIEW5.md',
    'docs/SESSION-RECONNECT-VALIDATION.md',
    'docs/ACCESS-POLICY-VALIDATION.md',
    'docs/PACMAN-PHANTOM-PROCESS-FAILURE.md',
    'docs/ORPHAN-CANCELLATION-VALIDATION.md', 'patches/opencode-runtime-recovery.patch',
])
hashes = {}
raw_normalized = {}
changed = []
for name in sorted(names):
    relative = Path(name)
    assert not relative.is_absolute() and '..' not in relative.parts
    assert relative.suffix not in {'.keystore', '.jks', '.apk', '.bin'}
    original, target = source/relative, destination/relative
    assert original.is_file(), name
    data = original.read_bytes()
    if not target.exists() or target.read_bytes() != data:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(original, target)
        changed.append(name)
    oid = subprocess.check_output(['git', '-C', str(destination), 'hash-object', '-w', '--path='+name, '--stdin'], input=data).decode().strip()
    canonical = subprocess.check_output(['git', '-C', str(destination), 'cat-file', '--filters', '--path='+name, oid])
    hashes[name] = hashlib.sha256(canonical).hexdigest()
    if canonical != data:
        raw_normalized[name] = hashlib.sha256(data).hexdigest()
snapshot.update(base_commit=subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip(),
                includes_working_tree_changes=True, files_sha256=hashes,
                original_files_sha256_before_git_normalization=raw_normalized,
                file_hash_scope='Git archive bytes after repository checkout filters and EOL attributes; original hashes retained for normalized working files',
                apk_sha256=hashlib.sha256(args.apk.read_bytes()).hexdigest())
(destination/'SOURCE-SNAPSHOT.json').write_text(json.dumps(snapshot, indent=2)+'\n')
print(json.dumps(dict(files=len(hashes), changed=changed), indent=2))
