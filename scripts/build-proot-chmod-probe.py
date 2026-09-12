"""Build an isolated app-UID regression APK; production APK inputs stay unchanged."""
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

root = Path(__file__).resolve().parents[1]
source = root/'tests/proot-chmod'
out = root/'.checks/proot-chmod-probe'
out.mkdir(exist_ok=True)
sdk = Path.home()/'AppData/Local/Android/Sdk'
tools = sdk/'build-tools/37.0.0'
android = sdk/'platforms/android-36/android.jar'
cc = sdk/'ndk/28.0.13004108/toolchains/llvm/prebuilt/windows-x86_64/bin/clang.exe'
def run(*args): subprocess.run(list(map(str,args)),check=True)
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
native = root/'app/src/main/jniLibs/arm64-v8a'
baseline = root/'.checks/proot-exitkill-build/libproot.so'
candidate = root/'.checks/proot-fchmodat2-build/libproot.so'
assert sha(baseline) == '4220f05ce95ccec3be75f5b3f9968ce611d48660be43542416433011bca9729f'
assert sha(candidate) == 'ccea97386ab59d764d3e5f921f8f1804bceaf8153644e28375e1b39b6da004a1'
run(cc,'--target=aarch64-linux-android30','-O2','-Wl,-z,max-page-size=16384',source/'probe.c','-o',out/'libchmodprobe.so')
classes = out/'classes'; classes.mkdir(exist_ok=True)
run('javac','-source','17','-target','17','-classpath',android,'-d',classes,source/'Probe.java')
run('java','-cp',tools/'lib/d8.jar','com.android.tools.r8.D8','--lib',android,'--min-api','30','--output',out,*classes.rglob('*.class'))
run(tools/'aapt2.exe','link','--manifest',source/'AndroidManifest.xml','-I',android,'-o',out/'unsigned.apk')
with zipfile.ZipFile(out/'unsigned.apk','a',compression=zipfile.ZIP_DEFLATED) as apk:
    apk.write(out/'classes.dex','classes.dex')
    apk.write(out/'fedora-tar-root.zip','assets/fedora-tar-root.zip')
    for name,file in {'libproot_baseline.so':baseline,'libproot_candidate.so':candidate,
                     'libproot_loader.so':native/'libproot_loader.so','libtalloc.so':native/'libtalloc.so',
                     'libandroid-shmem.so':native/'libandroid-shmem.so','libchmodprobe.so':out/'libchmodprobe.so'}.items():
        apk.write(file,'lib/arm64-v8a/'+name)
run(tools/'zipalign.exe','-f','4',out/'unsigned.apk',out/'aligned.apk')
apk = out/'probe.apk'
run('java','-jar',tools/'lib/apksigner.jar','sign','--ks',Path.home()/'.android/debug.keystore','--ks-pass','pass:android','--out',apk,out/'aligned.apk')
certificate = subprocess.check_output(['java','-jar',str(tools/'lib/apksigner.jar'),'verify','--print-certs',str(apk)],text=True)
assert 'a3ef78ae0bfdfc30307e3448e138eca29adf39d966f89af116bbce151abc1ed2' in certificate
proof = {'apk':str(apk),'sha256':sha(apk),'package':'io.github.gplaider.tinyagent.chmodprobe','phone_test':'pending'}
(out/'build.json').write_text(json.dumps(proof,indent=2))
print(json.dumps(proof))
