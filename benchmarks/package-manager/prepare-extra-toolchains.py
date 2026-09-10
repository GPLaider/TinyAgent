"""Pinned ARM host inputs required by the six build workloads, separate from TinyAgent's JDK17."""
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import subprocess

assert os.environ.get('TINYAGENT_EXECUTION_PROVIDER') == 'fedora-local'
assert os.uname().machine == 'aarch64'
spec = importlib.util.spec_from_file_location('sdk_inputs', '/shared/prepare-android-sdk-fedora.py')
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)
base = Path('/opt/tinyagent-build/extra-inputs')
base.mkdir(parents=True, exist_ok=True)
pins = [
    ('jdk21.tar.gz', 'https://github.com/adoptium/temurin21-binaries/releases/download/jdk-21.0.12.1%2B1/OpenJDK21U-jdk_aarch64_linux_hotspot_21.0.12.1_1.tar.gz', 'sha256', '23e37e026f12f3e706f18938ff611db3032d075b09d0879a25d06718c773e223', 205641175),
    ('ndk29.tar.xz', 'https://github.com/HomuHomu833/android-ndk-custom/releases/download/r29/android-ndk-r29-aarch64-linux-musl.tar.xz', 'sha256', 'fcc3b0ba65318317899fc296df0c5795d472a0cc3870b6fbf659939c1dde63ca', 192051660),
    ('build-tools36.zip', 'https://dl.google.com/android/repository/build-tools_r36_linux.zip', 'sha1', 'b0b6376977657e8ad9b969bacf4093601da2c6fb', 63737259),
    ('platform35.zip', 'https://dl.google.com/android/repository/platform-35_r02.zip', 'sha1', '0bb560a90a7a2cbd0dd8348224d518b638fe7949', 64273788),
]
with (base / '.prepare.lock').open('a') as lock:
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    for name, url, algorithm, checksum, size in pins:
        target = base / name
        helper.download(url, target, algorithm, checksum, size)
        helper.unpack(target, base / (name + '.unpacked'))
        print('Verified input', name, flush=True)
    java = list((base / 'jdk21.tar.gz.unpacked').glob('*/bin/java'))
    ndk = list((base / 'ndk29.tar.xz.unpacked').glob('*/source.properties'))
    build = list((base / 'build-tools36.zip.unpacked').glob('*/source.properties'))
    platform = list((base / 'platform35.zip.unpacked').glob('*/source.properties'))
    assert len(java) == len(ndk) == len(build) == len(platform) == 1
    subprocess.run([str(java[0]), '-version'], check=True)
    properties = dict(line.split('=', 1) for line in ndk[0].read_text().splitlines() if '=' in line)
    revision = next(v.strip() for k, v in properties.items() if k.strip() == 'Pkg.Revision')
    assert all(c in '0123456789.' for c in revision)
    sdk = Path('/opt/tinyagent-build/android-sdk')
    for link, target in [(sdk/'build-tools/36.0.0', build[0].parent), (sdk/'ndk'/revision, ndk[0].parent), (sdk/'platforms/android-35', platform[0].parent)]:
        link.parent.mkdir(parents=True, exist_ok=True)
        if not link.exists(): link.symlink_to(target, target_is_directory=True)
        assert link.resolve() == target.resolve()
    config = dict(java21_home=str(java[0].parent.parent), ndk_home=str(ndk[0].parent), ndk_revision=revision,
                  ndk_origin='HomuHomu833 custom ARM64 musl rebuild; not Google Linux host binaries',
                  inputs=[dict(name=n,url=u,algorithm=a,checksum=h,size=s) for n,u,a,h,s in pins])
    (base/'toolchains.json').write_text(json.dumps(config, indent=2)+'\n')
    print('extra_toolchains_exit=0', flush=True)
