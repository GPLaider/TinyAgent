# Pacman Stock self-build — 2026-09-09

Source: 4075f73514c6484dc0550f7256a26ff16dc7cde1 (v20 app implementation).
Host supplied a Git bundle and the existing development signer to app-private
storage. Pacman cloned the bundle through its local OpenCode shell API and ran
scripts/self-build-complete-fedora.sh in /workspace/tinyagent.

Target: Pacman 000501423003390, app Android UID10227, selected transport Stock.
No TinyAgent ADB pairing or root. Host ADB used only for staging and observation.
JDK17, Android ARM64 SDK, Bun1.3.14, OpenCode GUI and Gradle8.13 ran on the phone.
GUI built in 2m19s; Gradle BUILD SUCCESSFUL in 7m34s, 37 tasks executed.
Fixed harness, 4 bootstrap scripts, 4 PRoot components, native notices,
952 GUI assets, and 2 runtime archives passed packaged-byte validation.
Final script marker: tinyagent_self_build_exit=0.

Build session: ses_f7e7ea0daffem4Mm1Su3Gzn53m.
Full output: evidence/pacman-self-build.json.
APK: /workspace/tinyagent/app/build/outputs/apk/debug/app-debug.apk.
Host copy: D:/TinyAgent-work/artifacts/tinyagent-pacman-stock-built.apk.
Bytes: 136587837.
SHA256: a614e1666afb2642c99e940f3f7d61f060401cdfca98b7acd62140d16d518611.
Verified development signer SHA256:
a3ef78ae0bfdfc30307e3448e138eca29adf39d966f89af116bbce151abc1ed2.
This is a development-signed APK, not a production-signed release.

User authorized deleting TinyAgent on Lyriq1 ZY22J58799 and fresh installation
of this exact phone-built APK. Installation verification follows below.

Lyriq1 installation completed: verified hardware serial, verified staged APK
SHA256, force-stopped and uninstalled the old app (Success), installed phone-built
APK (Success), launched AppActivity. UI showed Work Environment and not prepared,
confirming fresh setup. Installed base.apk hash equals the Pacman output above.
Evidence: evidence/pacman-built-lyriq1-install.json. Fedora preparation on this
fresh Lyriq installation has not been repeated. Pacman retains its source/build
workspace and running Stock backend. Transfer server and build host monitor ended.
