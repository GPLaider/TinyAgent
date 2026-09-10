"""One measured phone build; retain failures and never count an older APK as output."""
import fcntl
import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import time

assert os.environ.get('TINYAGENT_EXECUTION_PROVIDER') == 'fedora-local'
assert os.uname().machine == 'aarch64'
base = Path('/workspace/tinyagent-six-builds')
parser = argparse.ArgumentParser()
parser.add_argument('workload', choices=['antennapod', 'termux', 'tailscale-android', 'organic-maps', 'vlc-android', 'appflowy'])
args = parser.parse_args()
source = base/args.workload
manifest = json.loads(Path('/shared/workloads.json').read_text())
workload = next(w for w in manifest['workloads'] if w['name'].lower().replace(' ', '-') == args.workload)
revision = workload['commit']
assert subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD']).decode().strip() == revision
build = Path('/opt/tinyagent-build')
deadline = time.monotonic() + 900
while not all(p.exists() for p in [build/'android-build.json', build/'extra-inputs/toolchains.json']):
    if time.monotonic() > deadline: raise RuntimeError('Toolchain preparation not ready; inspect its session')
    print('Waiting for verified Android SDK and Java21', flush=True)
    time.sleep(15)
config = json.loads((build/'android-build.json').read_text())
extra = json.loads((build/'extra-inputs/toolchains.json').read_text())
env = dict(os.environ, JAVA_HOME=extra['java21_home'], ANDROID_HOME=config['android_home'],
           ANDROID_SDK_ROOT=config['android_home'], GRADLE_USER_HOME=str(base/'gradle-cache'),
           PATH=extra['java21_home']+'/bin:'+os.environ['PATH'])
env.update({'ORG_GRADLE_PROJECT_android.aapt2FromMavenOverride': config['aapt2'],
            'PERL': '/usr/bin/perl',
            'GRADLE_OPTS': '-Dorg.gradle.daemon=false -Dorg.gradle.workers.max=2',
            'GOMAXPROCS': '2', 'GOFLAGS': '-p=2', 'ANDROID_NDK_HOME': extra['ndk_home']})
task = ':app:assembleFreeDebug' if args.workload == 'antennapod' else ':app:assembleDebug'
command = ['/usr/bin/bash', './gradlew', task, '--no-daemon', '--max-workers=2',
           '--console=plain', '-Dorg.gradle.jvmargs=-Xmx2g -XX:MaxMetaspaceSize=512m',
           '-Pandroid.aapt2FromMavenOverride='+config['aapt2']]
patterns = ['app/build/outputs/apk/**/*.apk']
cwd = source
if args.workload == 'appflowy':
    env['JAVA_HOME'] = config['java_home']
    env['PATH'] = config['java_home']+'/bin:'+env['PATH']
    command = ['/usr/bin/bash', '/shared/build-appflowy.sh']
    patterns = ['frontend/appflowy_flutter/build/app/outputs/flutter-apk/*.apk']
if args.workload == 'organic-maps':
    cwd = source/'android'
    command[2] = ':app:assembleFdroidDebug'
    command += ['-Parm64', '-Pnjobs=2']
    patterns = ['android/app/build/outputs/apk/**/*.apk']
if args.workload == 'vlc-android':
    env.update(ANDROID_NDK=extra['ndk_home'], ANDROID_SDK=config['android_home'], MAKEFLAGS='-j2')
    env.update(GIT_AUTHOR_NAME='TinyAgent build', GIT_AUTHOR_EMAIL='build@localhost',
               GIT_COMMITTER_NAME='TinyAgent build', GIT_COMMITTER_EMAIL='build@localhost')
    command = ['/usr/bin/bash', 'buildsystem/compile.sh', '-a', 'arm64']
    patterns = ['application/vlc-android/build/outputs/apk/**/*.apk']
if args.workload == 'tailscale-android':
    strip = Path(extra['ndk_home'])/'toolchains/llvm/prebuilt/linux-arm64/bin/llvm-objcopy'
    assert strip.is_file()
    command = ['make', 'apk', 'NDK_ROOT='+extra['ndk_home'], 'STRIP_TOOL='+str(strip)]
    patterns = ['android/build/outputs/apk/**/*.apk', 'tailscale-debug.apk']
def apks():
    return [p for pattern in patterns for p in source.glob(pattern)]
env['PWD'] = str(cwd)
with (base/'.build.lock').open('a') as lock:
    # ponytail: one build per phone; keep memory contention out of acceptance runs.
    print('Waiting for phone build slot', flush=True)
    fcntl.flock(lock, fcntl.LOCK_EX)
    if args.workload == 'tailscale-android':
        subprocess.run(['/usr/bin/python3', '/shared/prepare-tailscale-arm.py'], cwd=source, env=env, check=True)
        # gomobile invokes plain go; use the same pinned toolchain as tool/go.
        goroot = subprocess.check_output(['/usr/bin/bash', './tool/go', 'env', 'GOROOT'], cwd=source, env=env, text=True).strip()
        assert Path(goroot, 'bin/go').is_file()
        env['PATH'] = goroot+'/bin:'+env['PATH']
    run = base/(args.workload+'-build-'+str(time.time_ns()))
    run.mkdir()
    before = {str(p): p.stat().st_mtime_ns for p in apks()}
    if args.workload == 'organic-maps':
        # Preserve the failed run's APK and force packaging to produce this run's output.
        for apk in apks():
            previous = run/'previous-apks'/apk.relative_to(source)
            previous.parent.mkdir(parents=True, exist_ok=True)
            apk.rename(previous)
        checker = cwd/'groovy/permission-checker.gradle'
        old = 'task.aapt2Executable = project.androidComponents.sdkComponents.aapt2.get().executable.getAsFile()'
        new = "task.aapt2Executable = project.findProperty('android.aapt2FromMavenOverride') ? project.file(project.property('android.aapt2FromMavenOverride')) : project.androidComponents.sdkComponents.aapt2.get().executable.getAsFile()"
        content = checker.read_text()
        assert content.count(old) == 1 or content.count(new) == 1
        checker.write_text(content.replace(old, new))
        local = cwd/'local.properties'
        content = local.read_text() if local.exists() else ''
        if not any(line.startswith('cmake.dir=') for line in content.splitlines()):
            local.write_text(content+'\ncmake.dir=/usr\n')
    report = dict(workload=workload['name'], commit=revision, cwd=str(cwd), command=command,
                  java_home=env['JAVA_HOME'], android_home=env['ANDROID_HOME'], status='running',
                  scope='Phone ARM build in shared development root; not fresh package-manager timing')
    result_path = run/'result.json'
    (run/'source.patch').write_bytes(subprocess.check_output(['git', '-C', str(source), 'diff', '--binary', 'HEAD']))
    result_path.write_text(json.dumps(report, indent=2)+'\n')
    print('BUILD_RESULT', result_path, flush=True)
    started = time.monotonic()
    with (run/'build.log').open('wb') as log:
        process = subprocess.Popen(command, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        report['pid'] = process.pid
        result_path.write_text(json.dumps(report, indent=2)+'\n')
        for line in process.stdout:
            log.write(line)
            log.flush()
            print(line.decode(errors='replace'), end='', flush=True)
        code = process.wait()
    report.update(exit_code=code, seconds=round(time.monotonic()-started, 3),
                  max_single_child_rss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss)
    outputs = []
    for apk in apks():
        if before.get(str(apk)) == apk.stat().st_mtime_ns: continue
        with apk.open('rb') as stream: checksum = hashlib.file_digest(stream, 'sha256').hexdigest()
        outputs.append(dict(path=str(apk), size=apk.stat().st_size, sha256=checksum))
    report.update(apks=outputs, status='passed' if code == 0 and outputs else 'failed')
    result_path.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report), flush=True)
    print((run/'build.log').read_text(errors='replace')[-6000:], flush=True)
    raise SystemExit(0 if report['status'] == 'passed' else 1)
