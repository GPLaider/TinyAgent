"""Build a signed, code-free APK solely for TinyAgent installer acceptance."""
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parents[1]
sdk = Path.home() / 'AppData/Local/Android/Sdk'
tools = sdk / 'build-tools/36.1.0'
out = root / 'evidence/install-fixture'
out.mkdir(parents=True, exist_ok=True)
manifest = out / 'AndroidManifest.xml'
manifest.write_text('''<manifest xmlns:android="http://schemas.android.com/apk/res/android"
package="io.github.gplaider.tinyagent.installfixture" android:versionCode="1" android:versionName="1">
<uses-sdk android:minSdkVersion="30" android:targetSdkVersion="36"/>
<application android:hasCode="false" android:label="TinyAgent Install Check" android:allowBackup="false"/>
</manifest>''', encoding='utf-8')
subprocess.run([str(tools / 'aapt2.exe'), 'link', '--manifest', str(manifest), '-I', str(sdk / 'platforms/android-36/android.jar'), '-o', str(out / 'unsigned.apk')], check=True)
subprocess.run([str(tools / 'zipalign.exe'), '-f', '4', str(out / 'unsigned.apk'), str(out / 'aligned.apk')], check=True)
subprocess.run(['java', '-jar', str(tools / 'lib/apksigner.jar'), 'sign', '--ks', str(Path.home() / '.android/debug.keystore'), '--ks-pass', 'pass:android', '--out', str(out / 'fixture.apk'), str(out / 'aligned.apk')], check=True)
subprocess.run(['java', '-jar', str(tools / 'lib/apksigner.jar'), 'verify', str(out / 'fixture.apk')], check=True)
print(out / 'fixture.apk')
