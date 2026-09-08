# Dadb 1.2.10 pinned source evidence

- Maven coordinates: `dev.mobile:dadb:1.2.10`
- Retrieved source: https://repo.maven.apache.org/maven2/dev/mobile/dadb/1.2.10/dadb-1.2.10-sources.jar
- Local file: `dadb-1.2.10-sources.jar`
- Observed retrieval: 2026-09-08, one direct request. No further network retrieval was attempted after the parent reported its network restriction.
- SHA256: `1d6f2122445a11ec044bc31f98d27cc39924c226a7110dba48a51ce484f036f1`
- Source headers: Copyright (c) 2021 mobile.dev inc.; Apache License, Version 2.0.
- The archive has source files and manifest; it does not contain a separate LICENSE or NOTICE entry.
- Complete Apache 2.0 sections 1–9 were copied from the installed Gradle 8.13 LICENSE into `app/src/main/assets/licenses/dadb-LICENSE.txt`; Dadb copyright attribution is in THIRD-PARTY-NOTICES.txt. The license appendix is an application template, not an additional license condition.

## Observed Java-facing API

`dadb/Dadb.kt` has `@JvmStatic @JvmOverloads` on `create`:

```java
Dadb.create(String host, int port, AdbKeyPair keyPair,
            int connectTimeout, int socketTimeout, boolean keepAlive)
```

`Dadb` extends `AutoCloseable`; its `shell(String)` returns `AdbShellResponse`.
Timeouts are passed to `Socket.connect(..., connectTimeout)` and `socket.soTimeout = socketTimeout` in `dadb/DadbImpl.kt`; callers pass milliseconds.
The connection is lazy on first `open`/`shell`. Its `close()` closes the established ADB connection.
An in-flight initial handshake is still bounded by the configured socket timeout; the app does not claim instantaneous cancellation of an unpublished connection.

`dadb/AdbKeyPair.kt` declares static Java bridges:

```java
AdbKeyPair.generate(File privateKeyFile, File publicKeyFile)
AdbKeyPair.read(File privateKeyFile, File publicKeyFile)
```

Generation uses RSA 2048, writes a PKCS8 PEM private key and Android ADB-format public key.
The app always passes explicit app-private paths; it never calls `readDefault()` or uses host ADB keys.

`dadb/AdbShell.kt` defines Kotlin properties that expose Java getters:

```java
String AdbShellResponse.getOutput()
String AdbShellResponse.getErrorOutput()
int AdbShellResponse.getExitCode()
String AdbShellResponse.getAllOutput()
```

The library's full `shell` method accumulates command output in memory; this initial client only issues fixed short `pwd`, `getprop`, `id`, and private nonce `cat` commands. It is not the streaming arbitrary-job executor.

No binary JAR, POM, runtime dependency resolution, Android compilation, auth handshake or device execution was verified by this source inspection.
