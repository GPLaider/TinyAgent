# Stock and Developer access — v20

Stock is a normal mode: the app-owned Fedora/OpenCode runtime works without
self-ADB. The user can add Developer access using Android Wireless debugging.
Root remains the separately selected, verified root-ADB route; pairing does not
grant root or change Fedora's Android UID.

## First connection

1. Open **Developer 연결 설정**. Enable Developer options in Android if needed.
2. Connect Wi-Fi and enable **무선 디버깅**. Some ROMs open the Developer options
   list instead of the wireless subpage; select Wireless debugging there.
3. Enable **페어링 알림 켜기** in TinyAgent. In Android, choose pairing with a code.
   Keep that dialog open, expand notifications, and submit the six-digit code
   through TinyAgent's **코드 입력** notification action.

Pairing uses `_adb-tls-pairing._tcp`; connections use `_adb-tls-connect._tcp`.
Only addresses assigned to this phone are accepted. Ports are discovered each
time, so the user does not enter an IP/port or run `adb tcpip`. If notifications
are declined, the app also accepts the code in split-screen while the Android
pairing dialog stays open. This alternate input has not been device-tested yet.

The key/certificate live in app no_backup storage, with private file permissions.
The code is not saved. Pairing and transport success are followed by device
identity, actual shell UID2000 and a fresh local nonce check. An old success is
not reused as authorization for a new install or diagnostic request.

Use **기존 페어링으로 다시 연결** after changing networks or toggling wireless
debugging. Use **Stock으로 돌아가기** to disallow Developer ADB requests while
retaining the key for a later user-initiated connection. Fedora keeps running.

## Actual Lyriq 1 evidence, 2026-09-08

- v18: Android pairing dialog -> TinyAgent RemoteInput notification -> Android
  registered TinyAgent -> app verified its own shell UID2000.
- Saved-key reconnection: three consecutive successes.
- Toggled wireless debugging through Android UI. Connection port changed from
  41255 to34377; automatic reconnection passed three more times without pairing
  again or entering a port.
- v19 update: app TLS installation of the signed 8.5KB test APK passed three
  times. PackageManager paths changed and installed APK hashes were recorded.
- The real phone-local OpenCode shell called the Android bridge: Stock returned
  Android UID10000; Developer returned verified_self=true and execution_uid=2000
  on the newly discovered port34377. Fedora/Git commands and old sessions passed.
- v20: explicitly returning to Stock rejected the Developer request with a
  Stock-mode explanation, while the same Fedora session continued to run Git.
  Stock inspection reported actual Android UID10000 and selected_transport=stock.
- Final v20 then passed saved-key reconnection three times and in-app TLS APK
  installation three times. Its APK hash is recorded with installation evidence.

The host ADB transport was only used for APK delivery, UI actions and observation.
It did not perform the application's wireless pairing, key import or test APK
installation. This device runs a custom Android16 ROM; Flip7 was not touched.
The user explicitly chose Lyriq1 as the test device.

## Build and limits

v20 APK SHA256: `0cfbd92efea5445df2d9ddedd1491f84d7a01151b4a3b48c184248cb4d405f3d`.
Same development signing certificate as earlier previews. Internal app version
remains0.1.0-dev/code1; this is a private development preview, not production signing.
Build, lint and packaged runtime/harness/GUI checks passed.

Source/dependency provenance: third_party/libadb/PROVENANCE.md. Source commit
0bab7639f7110a4c0a09a2ff2b6c61cf19ac70d5 with a bounded socket/cancellation patch;
BouncyCastle1.84. License texts are packaged with the APK.

Remaining: stock-vendor coverage, declined-notification/split-screen pairing,
expired/wrong-code UI acceptance, arbitrary agent-callable Android commands,
SAF workspace-directory integration, personal OpenAI OAuth, production signing
and the full release journey matrix. The current agent bridge provides Android
inspection; native APK installation is separate. Do not advertise unsupported
public APIs or permission flows as implemented capabilities.
