package io.github.gplaider.tinyagent;

import android.content.Context;
import android.net.ConnectivityManager;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.security.*;
import java.util.*;
import java.util.function.Consumer;
import java.util.function.BiConsumer;

/** Fedora belongs to the app UID; Android administration is a separate transport. */
final class LocalLinuxRuntime {
    final Context context;
    final File base, rootfs, workspace, home;
    private volatile Process active;
    private final Map<Process, File> pids = new java.util.concurrent.ConcurrentHashMap<>();
    private volatile boolean cancelled;
    private volatile Integer lastExitCode;
    Integer lastExitCode() { return lastExitCode; }
    private boolean previousRuntimeStopped;
    private BiConsumer<String, Integer> measured = (label, percent) -> {};
    LocalLinuxRuntime(Context context) {
        this.context = context.getApplicationContext();
        base = new File(context.getFilesDir(), "linux");
        rootfs = new File(base, "rootfs");
        workspace = new File(base, "workspace");
        home = new File(base, "home");
    }
    void prepare(Consumer<String> progress, BiConsumer<String, Integer> reporter) throws Exception {
        this.measured = reporter;
        for (File dir : List.of(base, rootfs, workspace, home, new File(base, "shared"), new File(rootfs, "shared"), new File(rootfs, ".l2s"), new File(base, "tmp")))
            Files.createDirectories(dir.toPath());
        recoverPreviousProcesses(base);
        previousRuntimeStopped = true;
        try (var input = context.getAssets().open("linux-launch.sh")) {
            Files.copy(input, new File(base, "launch.sh").toPath(), StandardCopyOption.REPLACE_EXISTING);
        }
        File ready = new File(base, "prepared-v1");
        if (!ready.isFile()) {
            progress.accept("앱 내부 Fedora 파일 준비 중…");
            unpack("fedora-44-arm64-rootfs.tar.gz.bin", "3a3661a77d5fdb1e4bd10be484142683630c1ffb4c371931d46a42459fd4c125", rootfs, "Fedora", 5638);
            for (String path : List.of("workspace", "shared", "root", "proc", "dev", "tmp"))
                Files.createDirectories(new File(rootfs, path).toPath());
            Files.write(ready.toPath(), "fedora=44\n".getBytes(StandardCharsets.UTF_8));
        }
        File bin = new File(rootfs, "usr/local/bin");
        Files.createDirectories(bin.toPath());
        String backendHash = "5e64f096fbc1e7a891d5382d86fc657a7d2b316fe2546a2025a28fb531a1fc6e";
        Path executable = new File(bin, "opencode").toPath();
        progress.accept("OpenCode 실행 파일 확인 중…");
        if (!RuntimeExecutable.matches(executable, backendHash)) {
            Path staging = Files.createTempDirectory(bin.toPath(), ".opencode-update-");
            try {
                unpack("opencode-linux-arm64.tar.gz.bin", "b877f7baa8d60611b9a638209c84868e5dea9139c8dec622943d25f29c07f205", staging.toFile(), "OpenCode 업데이트", 1);
                if (cancelled) throw new InterruptedException("환경 준비 중단");
                RuntimeExecutable.replace(staging.resolve("opencode"), executable, backendHash);
            } finally {
                Files.deleteIfExists(staging.resolve("opencode"));
                Files.deleteIfExists(staging);
            }
        }
        // The installed APK is immutable to this app UID; expose its exact runtime inputs for self-builds.
        new File(rootfs, "tinyagent-installed.apk").createNewFile();
        refreshDns();
        progress.accept("dnfast 패키지 실행환경 확인 중…");
        DnfastRuntime.prepare(this);
        // The minimal Fedora image lacks development tools. Also repair earlier installs.
        if (!List.of("git", "python3", "make", "gcc", "unzip").stream()
                .allMatch(name -> new File(rootfs, "usr/bin/" + name).isFile())) {
            progress.accept("Fedora 개발 도구 설치 중 · 네트워크 연결이 필요합니다. 실패하면 환경 준비를 다시 누르세요.");
            var network = context.getSystemService(ConnectivityManager.class).getActiveNetwork();
            if (network == null) throw new IOException("인터넷 연결이 필요합니다. Wi-Fi 또는 모바일 데이터 연결 후 다시 시도하세요.");
            progress.accept("개발 도구 준비 · 이전 패키지 작업 확인 중…");
            runPackages("check",line -> {},"app-runtime","check");
            progress.accept("개발 도구 준비 · 패키지 목록 갱신 중…");
            runPackages("refresh",line -> {},"repo","refresh");
            progress.accept("개발 도구 준비 · 패키지 다운로드·설치 중…");
            // dnfast currently emits a terminal JSON result, not byte/package progress.
            // Keep the native indeterminate bar and elapsed clock until measured progress exists.
            runPackages("install", line -> {}, "install", "--assumeyes", "git", "python3", "make", "gcc", "unzip", "tar", "gzip");
        }
        run(guest("/workspace", "/usr/bin/git", "--version"));
        File auth = new File(context.getNoBackupFilesDir(), "stock-backend-auth");
        if (!auth.isFile()) {
            byte[] bytes = new byte[32]; new SecureRandom().nextBytes(bytes);
            android.util.AtomicFile atomic = new android.util.AtomicFile(auth);
            FileOutputStream output = atomic.startWrite();
            try { output.write(hex(bytes).getBytes(StandardCharsets.US_ASCII)); atomic.finishWrite(output); }
            catch (Exception error) { atomic.failWrite(output); throw error; }
        }
        if (!password().matches("[0-9a-f]{64}")) throw new IOException("로컬 인증 파일 오류");
        progress.accept("Fedora 실행 확인 중 · Android UID=" + android.os.Process.myUid());
        StringBuilder backendVersion = new StringBuilder();
        run(guest("/workspace", "/usr/local/bin/opencode", "--version"),
                line -> backendVersion.append(line).append('\n'));
        File harness = new File(home, ".tinyagent"); Files.createDirectories(harness.toPath());
        File bootstrap = new File(harness, "bootstrap"); Files.createDirectories(bootstrap.toPath());
        for (String name : context.getAssets().list("bootstrap")) {
            try (var input = context.getAssets().open("bootstrap/" + name)) {
                Files.copy(input, new File(bootstrap, name).toPath(), StandardCopyOption.REPLACE_EXISTING);
            }
        }
        for (String name : List.of("AGENTS.md", "STOCK.md", "ADB.md", "ROOT.md")) {
            try (var input = context.getAssets().open(name)) {
                Files.copy(input, new File(harness, name).toPath(), StandardCopyOption.REPLACE_EXISTING);
            }
        }
        String measured = "# TinyAgent measured environment\n\nMeasured: " + java.time.Instant.now()
                + "\nAndroid device: " + android.os.Build.DEVICE + "\nAndroid version: " + android.os.Build.VERSION.RELEASE
                + "\nDevice serial: unavailable to ordinary app; do not infer it.\nAndroid UID: " + android.os.Process.myUid()
                + "\nExecution provider: fedora-local\nRuntime: TinyAgent-patched PRoot 5.1.107.92-tinyagent.1, Fedora 44"
                + "\nOpenCode --version (exit 0): " + backendVersion.toString().strip()
                + "\nPermission: app-sandbox. Guest uid=0 is emulated and is not Android root."
                + "\nFedora tool: OpenCode bash tool; commands run directly in the guest. Try `cat /etc/fedora-release`, `id`, `pwd`."
                + "\nAndroid tool: read /root/.tinyagent/ANDROID_TOOL.md for this runtime's actual connection. tinyagent-android.py exposes verified Developer/Root shell and installation jobs; Stock Fedora never requires ADB."
                + "\nWorkspace: /workspace = " + workspace + "\nHome: /root = " + home
                + "\nPrivate internal exchange: /shared = " + new File(base, "shared")
                + "\nAll paths above are app-private, NOT browsable in Android Files. Copying to /shared does not export."
                + "\nUser file export: 작업 환경 > APK 설치 > workspace-relative path > 작업공간 파일 내보내기 > Android save dialog. See AGENTS.md."
                + "\nSelf-build runtime inputs: TINYAGENT_APK=/tinyagent-installed.apk is this app's installed APK, read-only to the app UID. Reuse its hash-verified runtime archives; do not recompress them or change their pinned hashes."
                + "\nBackend: " + LocalPolicy.BACKEND_ORIGIN + " owned by RuntimeSetupService."
                + "\nStop: native Work Environment > diagnostics > stop; signals PRoot to terminate its tracees."
                + "\nRecovery: reopen the app; an explicitly stopped runtime requires Prepare. Check real session state before repeating writes."
                + "\nRuntime diagnostics: TinyAgent work environment > diagnostics. Android-private log mapping (not a Fedora path): " + new File(base, "backend.log")
                + "\nAndroid Root last detected: " + context.getSharedPreferences("connection", Context.MODE_PRIVATE).getBoolean("rootAvailable", false)
                + " (automatically detected; each Root operation must reverify self-device and UID 0).\n";
        Files.write(new File(harness, "TINYAGENT_ENVIRONMENT.md").toPath(), measured.getBytes(StandardCharsets.UTF_8));
        recordAndroidTool("Android diagnostic bridge is not connected yet. Fedora remains available.\n");
        Files.deleteIfExists(new File(home, ".tinyagent/PACKAGE_SOCKET").toPath());
    }
    void recordPackageSocket(String name) throws IOException {
        Files.write(new File(home, ".tinyagent/PACKAGE_SOCKET").toPath(), name.getBytes(StandardCharsets.UTF_8));
    }
    void recordAndroidTool(String text) throws IOException {
        Files.write(new File(home, ".tinyagent/ANDROID_TOOL.md").toPath(), text.getBytes(StandardCharsets.UTF_8));
    }
    void refreshDns() throws IOException {
        ConnectivityManager manager = context.getSystemService(ConnectivityManager.class);
        var network = manager.getActiveNetwork();
        var properties = network == null ? null : manager.getLinkProperties(network);
        // Offline work still starts; reconnect refreshes DNS through the service callback.
        if (properties == null || properties.getDnsServers().isEmpty()) return;
        StringBuilder text = new StringBuilder();
        for (var address : properties.getDnsServers()) text.append("nameserver ").append(address.getHostAddress()).append('\n');
        text.append("options timeout:2 attempts:2\n");
        Path path = new File(rootfs, "etc/resolv.conf").toPath();
        if (Files.isSymbolicLink(path)) throw new IOException("DNS 경로가 심볼릭 링크입니다.");
        Files.write(path, text.toString().getBytes(StandardCharsets.UTF_8));
    }
    private String password() throws IOException {
        return new String(Files.readAllBytes(new File(context.getNoBackupFilesDir(), "stock-backend-auth").toPath()), StandardCharsets.US_ASCII);
    }

    String[] sessionNotification() throws Exception {
        var states = new org.json.JSONObject(backendJson("/session/status?scope=server"));
        var active = new ArrayList<String>();
        for (var keys = states.keys(); keys.hasNext();) {
            String id = keys.next();
            if (!"idle".equals(states.getJSONObject(id).optString("type")) && id.matches("ses_[A-Za-z0-9]+")) active.add(id);
        }
        if (active.isEmpty()) return new String[] {"TinyAgent · 작업 대기", "실행 중인 세션이 없습니다. 앱에서 작업을 시작하세요."};
        Collections.sort(active);
        String id = active.get(0);
        var session = new org.json.JSONObject(backendJson("/session/" + id));
        String title = session.optString("title", "작업 중");
        String detail = "에이전트 응답 중";
        if ("retry".equals(states.getJSONObject(id).optString("type"))) detail = "모델 연결 재시도 중";
        var messages = new org.json.JSONArray(backendJson("/session/" + id + "/message?limit=1"));
        if (messages.length() > 0) {
            var parts = messages.getJSONObject(messages.length() - 1).optJSONArray("parts");
            for (int i = parts == null ? -1 : parts.length() - 1; i >= 0; i--) {
                var part = parts.getJSONObject(i);
                var state = part.optJSONObject("state");
                if (state == null || !("running".equals(state.optString("status")) || "pending".equals(state.optString("status")))) continue;
                String task = state.optString("title", "").strip();
                detail = task.isEmpty() ? part.optString("tool", "도구") + " 실행 중" : task;
                break;
            }
        }
        if (active.size() > 1) detail += " · 그 외 " + (active.size() - 1) + "개 세션 실행 중";
        return new String[] {title.length() > 80 ? title.substring(0, 80) + "…" : title,
                detail.length() > 200 ? detail.substring(0, 200) + "…" : detail};
    }

    private String backendJson(String path) throws Exception {
        var connection = (java.net.HttpURLConnection) new java.net.URL(LocalPolicy.BACKEND_ORIGIN + path).openConnection();
        connection.setConnectTimeout(1500); connection.setReadTimeout(2000);
        connection.setRequestProperty("Authorization", "Basic " + android.util.Base64.encodeToString(
                ("opencode:" + password()).getBytes(StandardCharsets.UTF_8), android.util.Base64.NO_WRAP));
        try (var input = connection.getInputStream(); var output = new ByteArrayOutputStream()) {
            byte[] buffer = new byte[8192];
            for (int n; (n = input.read(buffer)) != -1;) {
                if (output.size() + n > 1024 * 1024) throw new IOException("Session state response too large");
                output.write(buffer, 0, n);
            }
            return output.toString(StandardCharsets.UTF_8.name());
        } finally { connection.disconnect(); }
    }
    Process startBackend() throws Exception {
        if (!previousRuntimeStopped) throw new IOException("이전 실행환경 종료 확인이 필요합니다.");
        ProcessBuilder builder = guest("/workspace", "/usr/local/bin/opencode", "serve", "--hostname", "127.0.0.1", "--port", "4097");
        builder.environment().put("TINYAGENT_PREVIOUS_RUNTIME_STOPPED", "1");
        builder.environment().put("OPENCODE_SERVER_PASSWORD", password());
        // Keep the existing production database when the bundled build channel changes.
        builder.environment().put("OPENCODE_DISABLE_CHANNEL_DB", "1");
        builder.environment().put("OPENCODE_CONFIG_CONTENT", "{\"instructions\":[\"/root/.tinyagent/AGENTS.md\",\"/root/.tinyagent/STOCK.md\",\"/root/.tinyagent/ADB.md\",\"/root/.tinyagent/ROOT.md\",\"/root/.tinyagent/TINYAGENT_ENVIRONMENT.md\",\"/root/.tinyagent/ANDROID_TOOL.md\"]}");
        File log = new File(base, "backend.log");
        if (log.length() > 1024 * 1024) Files.move(log.toPath(), new File(base, "backend.previous.log").toPath(), StandardCopyOption.REPLACE_EXISTING);
        return start(builder.redirectOutput(ProcessBuilder.Redirect.appendTo(log)));
    }
    void awaitBackend(Process backend) throws Exception {
        long deadline = android.os.SystemClock.elapsedRealtime() + 60000;
        while (backend.isAlive() && android.os.SystemClock.elapsedRealtime() < deadline) {
            if (Thread.currentThread().isInterrupted()) throw new InterruptedException();
            var connection = (java.net.HttpURLConnection) new java.net.URL(LocalPolicy.BACKEND_ORIGIN + "/global/health").openConnection();
            try {
                connection.setConnectTimeout(1000); connection.setReadTimeout(1000);
                connection.setRequestProperty("Authorization", "Basic " + android.util.Base64.encodeToString(
                        ("opencode:" + password()).getBytes(StandardCharsets.UTF_8), android.util.Base64.NO_WRAP));
                if (connection.getResponseCode() == 200) return;
            } catch (IOException ignored) { }
            finally { connection.disconnect(); }
            Thread.sleep(250);
        }
        throw new IOException("로컬 백엔드 응답 확인 실패 · linux/backend.log 확인");
    }
    ProcessBuilder guest(String cwd, String... command) {
        var args = new ArrayList<>(List.of("-0", "-l", "--kill-on-exit", "-r", rootfs.toString(),
                "-b", "/dev", "-b", "/proc", "-b", home + ":/root", "-b", workspace + ":/workspace",
                "-b", new File(base, "shared") + ":/shared",
                "-b", context.getApplicationInfo().sourceDir + ":/tinyagent-installed.apk",
                "-b", new File(rootfs, ".l2s") + ":" + new File(rootfs, ".l2s"), "-w", cwd,
                "/usr/bin/env", "-u", "LD_LIBRARY_PATH", "HOME=/root", "PATH=/usr/local/bin:/usr/bin", "TMPDIR=/tmp",
                "TINYAGENT_EXECUTION_PROVIDER=fedora-local", "TINYAGENT_PERMISSION=app-sandbox", "TINYAGENT_APK=/tinyagent-installed.apk"));
        args.addAll(List.of(command));
        return process(args);
    }
    private ProcessBuilder process(List<String> args) {
        String nativeDir = context.getApplicationInfo().nativeLibraryDir;
        var command = new ArrayList<String>(); command.add(nativeDir + "/libproot.so"); command.addAll(args);
        ProcessBuilder builder = new ProcessBuilder(command).directory(base).redirectErrorStream(true);
        // PRoot's optional seccomp acceleration is incompatible with some stock kernels.
        // This changes PRoot tracing only, not Android's sandbox or SELinux policy.
        builder.environment().put("PROOT_NO_SECCOMP", "1");
        builder.environment().put("LD_LIBRARY_PATH", nativeDir);
        builder.environment().put("PROOT_LOADER", nativeDir + "/libproot_loader.so");
        builder.environment().put("PROOT_TMP_DIR", new File(base, "tmp").toString());
        builder.environment().put("PROOT_L2S_DIR", new File(rootfs, ".l2s").toString());
        return builder;
    }
    void unpack(String asset, String expected, File destination, String label, int entries) throws Exception {
        File archive = new File(base, "input.tar.gz");
        MessageDigest hash = MessageDigest.getInstance("SHA-256");
        long length;
        try (var descriptor = context.getAssets().openFd(asset)) { length = descriptor.getLength(); }
        measured.accept(label + " 파일 복사", 0);
        try (var input = context.getAssets().open(asset); var output = new FileOutputStream(archive)) {
            byte[] buffer = new byte[65536];
            long copied = 0;
            int last = -1;
            for (int n; (n = input.read(buffer)) != -1;) {
                if (cancelled) throw new InterruptedException("환경 준비 중단");
                hash.update(buffer, 0, n); output.write(buffer, 0, n); copied += n;
                int percent = (int)(copied * 100 / length);
                if (percent != last) { measured.accept(label + " 파일 복사", percent); last = percent; }
            }
        }
        if (!hex(hash.digest()).equals(expected)) throw new IOException("런타임 파일 SHA256 불일치");
        // Entry totals belong to the SHA256-pinned archives above, not an estimated duration.
        int[] extracted = {0};
        measured.accept(label + " 압축 해제", 0);
        // Some stock devices allow Java to read toybox but deny native child reads.
        // Copy the device's own tar executable; retain argv[0] and PRoot link emulation.
        Path systemTar = new File("/system/bin/tar").getCanonicalFile().toPath();
        Path readableTar = Files.createTempFile(base.toPath(), ".bootstrap-tar-", ".bin");
        try {
            Files.copy(systemTar, readableTar, StandardCopyOption.REPLACE_EXISTING);
            if (!readableTar.toFile().setExecutable(true, true)) throw new IOException("압축 해제 도구 실행 권한 설정 실패");
            run(process(List.of("-0", "-l", "--kill-on-exit", "-b", readableTar + ":" + systemTar,
                    "/system/bin/tar", "-xvzf", archive.toString(), "-C", destination.toString())), line -> {
                if (!line.startsWith("proot") && !line.startsWith("tar:") && !line.isBlank()) {
                    extracted[0]++;
                    measured.accept(label + " 압축 해제 · " + Math.min(extracted[0], entries) + "/" + entries + " 항목", Math.min(99, extracted[0] * 100 / entries));
                }
            });
        } finally { Files.deleteIfExists(readableTar); }
        measured.accept(label + " 압축 해제 완료", 100);
        Files.delete(archive.toPath());
    }
    void runPackages(String action, Consumer<String> lines, String... operation) throws Exception {
        // One in-process writer also covers initial preparation. The launcher retains its root lock.
        synchronized (DnfastRuntime.class) {
            if (action.equals("install") && !DnfastRuntime.planningCurrent(this)) {
                lines.accept("dnfast: 실행환경 변경 확인 · 설치 계획 갱신 중");
                runPackages("check", lines, "app-runtime", "check");
                // Native migrate refuses Started/RpmResult; never replay or rewrite those journals.
                runPackages("migrate", lines, "app-runtime", "migrate");
                runPackages("verify", lines, "app-runtime", "check");
                runPackages("refresh", lines, "repo", "refresh");
            }
            runPackageCommand(action, lines, operation);
        }
    }
    private void runPackageCommand(String action, Consumer<String> lines, String... operation) throws Exception {
        String planningIdentity = action.equals("refresh") ? DnfastRuntime.planningIdentity(this) : null;
        StringBuilder terminal = new StringBuilder();
        run(DnfastRuntime.command(this,operation), line -> {
            lines.accept(line);
            if (line.startsWith("{") && line.contains("dnfast.cli.v1")) {
                terminal.setLength(0); terminal.append(line);
            }
        });
        DnfastResult.require(action,0,terminal.toString());
        if (action.equals("refresh")) DnfastRuntime.rememberPlanning(this, planningIdentity);
    }
    void run(ProcessBuilder builder) throws Exception {
        run(builder, line -> {});
    }
    void run(ProcessBuilder builder, Consumer<String> lines) throws Exception {
        lastExitCode = null;
        Process process = start(builder);
        active = process;
        StringBuilder output = new StringBuilder();
        int code;
        try {
            code = RuntimeProcessOutput.read(process, line -> {
                lines.accept(line);
                output.append(line).append('\n');
                if (output.length() > 8192) output.delete(0, output.length() - 8192);
            }, this::stop);
        } finally {
            if (!process.isAlive()) {
                lastExitCode = process.exitValue();
                forget(process); active = null;
            }
        }
        if (cancelled) throw new InterruptedException("환경 준비 중단");
        if (code != 0) throw new IOException("Fedora exit=" + code + "\n" + output);
    }
    synchronized Process start(ProcessBuilder builder) throws Exception {
        if (cancelled) throw new InterruptedException("환경 준비 중단");
        File pid = File.createTempFile("process-", ".pid", base);
        var command = new ArrayList<>(List.of("/system/bin/sh", new File(base, "launch.sh").toString(), pid.toString()));
        command.addAll(builder.command());
        Process process = builder.command(command).start();
        pids.put(process, pid);
        for (int i = 0; i < 100 && pid.length() == 0 && process.isAlive(); i++) Thread.sleep(10);
        return process;
    }
    synchronized void cancel() {
        cancelled = true;
        for (Process process : pids.keySet()) stop(process);
    }
    void stop(Process process) {
        if (!process.isAlive()) { forget(process); return; }
        File file = pids.get(process);
        if (file == null) return;
        try {
            String record = readText(file.toPath());
            int pid = Integer.parseInt(record.split("\\R", 2)[0]);
            if (pid <= 1 || android.system.Os.stat("/proc/" + pid).st_uid != android.os.Process.myUid())
                throw new IOException("프로세스 UID 확인 실패");
            if (!sameProcess(pid, record)) throw new IOException("프로세스 시작 정보 불일치");
            // PRoot ignores TERM. QUIT invokes its kill_all_tracees handler; KILL alone orphans guests.
            android.system.Os.kill(pid, android.system.OsConstants.SIGQUIT);
        } catch (Exception error) { android.util.Log.e("TinyAgentRuntime", "Owned process stop failed", error); }
    }
    void forget(Process process) {
        if (process.isAlive()) return;
        File file = pids.remove(process); if (file != null) file.delete();
    }
    private static String readText(Path file) throws IOException {
        return new String(Files.readAllBytes(file), StandardCharsets.UTF_8);
    }
    private boolean sameProcess(int pid, String record) throws IOException {
        Path stat = Paths.get("/proc", Integer.toString(pid), "stat");
        if (!Files.exists(stat)) return false;
        try {
            String current = readText(stat);
            if (current.substring(current.lastIndexOf(") ") + 2).startsWith("Z ")) return false;
            return RuntimeProcessIdentity.matches(record, readText(Paths.get("/proc/sys/kernel/random/boot_id")), current);
        } catch (java.nio.file.NoSuchFileException gone) { return false; }
    }
    void recoverPreviousProcesses(File directory) throws Exception {
        File[] records = directory.listFiles((dir, name) -> name.startsWith("process-") && name.endsWith(".pid"));
        if (records == null) return;
        for (File file : records) {
            String record = readText(file.toPath()).trim();
            if (record.isEmpty()) { Files.delete(file.toPath()); continue; }
            int pid = Integer.parseInt(record.split("\\R", 2)[0]);
            if (pid <= 1) throw new IOException("이전 실행 PID 오류");
            if (Files.exists(Paths.get("/proc", Integer.toString(pid)))) {
                if (android.system.Os.stat("/proc/" + pid).st_uid != android.os.Process.myUid()) {
                    Files.delete(file.toPath()); // The PID now belongs to another UID; never signal it.
                    continue;
                }
                if (record.split("\\R", 3).length != 3)
                    throw new IOException("이전 버전의 실행이 남아 있습니다. 종료 후 다시 시도하세요.");
                if (sameProcess(pid, record)) {
                    if (android.system.Os.stat("/proc/" + pid).st_uid != android.os.Process.myUid())
                        throw new IOException("이전 실행 UID 불일치");
                    android.system.Os.kill(pid, android.system.OsConstants.SIGQUIT);
                    long deadline = android.os.SystemClock.elapsedRealtime() + 5000;
                    while (sameProcess(pid, record) && android.os.SystemClock.elapsedRealtime() < deadline) Thread.sleep(50);
                    if (sameProcess(pid, record)) throw new IOException("이전 실행 종료를 확인하지 못했습니다.");
                }
            }
            Files.delete(file.toPath());
        }
    }
    private static String hex(byte[] bytes) { StringBuilder result = new StringBuilder(); for (byte b : bytes) result.append(String.format("%02x", b & 255)); return result.toString(); }
}
