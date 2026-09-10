package io.github.gplaider.tinyagent;

import android.content.Context;
import android.os.Build;
import android.system.Os;

import java.io.File;
import java.io.IOException;
import java.net.Inet4Address;
import java.net.NetworkInterface;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.StandardCopyOption;
import java.util.UUID;
import java.util.Collections;
import java.util.LinkedHashSet;
import java.util.function.Consumer;

import dadb.AdbKeyPair;
import dadb.AdbShellResponse;
import dadb.Dadb;

/** All runtime writes require successful self-device nonce verification on this connection. */
final class SelfAdbClient implements AutoCloseable {
    private final File privateDirectory;
    private final Context context;
    private volatile WirelessAdb wireless;
    private volatile Dadb connection;
    private volatile boolean closed;
    private volatile boolean verifiedRoot;
    private volatile int verifiedUid = -1;

    SelfAdbClient(Context context) {
        this.context = context.getApplicationContext();
        privateDirectory = context.getNoBackupFilesDir();
    }

    static final class Result {
        final String transcript;
        final boolean verifiedSelf;
        Result(String transcript, boolean verifiedSelf) {
            this.transcript = transcript;
            this.verifiedSelf = verifiedSelf;
        }
    }

    Result inspect(int port, boolean rootAllowed) throws Exception {
        if (!rootAllowed && "stock".equals(WirelessAdb.transport(context)))
            throw new IOException("Stock 모드입니다. Developer 연결 설정에서 권한을 연결하세요.");
        verifiedRoot = false;
        verifiedUid = -1;
        String connectedHost;
        if (!rootAllowed && WirelessAdb.selected(context)) {
            wireless = new WirelessAdb(context);
            ensureOpen();
            connectedHost = wireless.connectLocal();
        } else {
        // Some root-adbd deployments bind only the phone's VPN address, not loopback.
        // Probe only addresses assigned to this phone; never discover remote devices.
        LinkedHashSet<String> addresses = new LinkedHashSet<>();
        addresses.add(LocalPolicy.ADB_HOST);
        for (NetworkInterface network : Collections.list(NetworkInterface.getNetworkInterfaces())) {
            if (!network.isUp()) continue;
            for (var address : Collections.list(network.getInetAddresses())) {
                if (address instanceof Inet4Address && !address.isLoopbackAddress()) {
                    addresses.add(address.getHostAddress());
                }
            }
        }
        AdbKeyPair identity = keyPair();
        connectedHost = null;
        StringBuilder failures = new StringBuilder();
        for (String address : addresses) {
            ensureOpen();
            try {
                attach(Dadb.create(address, port, identity, 1500, 60000, true));
                // Dadb.create is lazy: the first shell request actually connects/authenticates.
                if (connection.shell("pwd").getExitCode() != 0) {
                    throw new IOException("ADB 작업 디렉터리 조회 실패");
                }
                connectedHost = address;
                break;
            } catch (IOException error) {
                if (connection != null) {
                    try { connection.close(); } catch (Exception ignored) { }
                    connection = null;
                }
                failures.append(address).append(':').append(port).append(" · ")
                        .append(error.getMessage()).append('\n');
            }
        }
        if (connectedHost == null) throw new IOException("이 폰의 ADB 주소 연결 실패\n" + failures);
        }
        ensureOpen();
        StringBuilder transcript = new StringBuilder("대상: " + connectedHost + (port == 0 ? "" : ":" + port) + "\n");
        String directory = read("pwd", transcript);
        String serial = read("getprop ro.serialno", transcript);
        String device = read("getprop ro.product.device", transcript);
        String id = read("id", transcript);
        int uid = LocalPolicy.uid(id);
        if (directory.isEmpty() || serial.isEmpty() || device.isEmpty()) {
            throw new IOException(transcript + "\n기기 정보가 비어 있어 대상 확인을 완료하지 못했습니다.");
        }
        if (!device.equals(Build.DEVICE)) {
            throw new IOException(transcript + "\n이 앱이 실행되는 기기(" + Build.DEVICE + ")와 다릅니다.");
        }
        if (!rootAllowed) {
            if (uid != 2000) return new Result(transcript + "\nDeveloper 경로에는 UID=2000이 필요합니다. 현재 UID=" + uid, false);
            // Shell cannot read the app sandbox. A fresh loopback challenge proves this device.
            try (var server = new java.net.ServerSocket(0, 1, java.net.InetAddress.getByName("127.0.0.1"))) {
                server.setSoTimeout(5000);
                String nonce = UUID.randomUUID().toString();
                Thread responder = new Thread(() -> {
                    try (var socket = server.accept()) {
                        socket.getOutputStream().write((nonce + "\n").getBytes(StandardCharsets.US_ASCII));
                    } catch (IOException ignored) { }
                }, "self-adb-challenge");
                responder.start();
                String actual = read("toybox nc -w 5 127.0.0.1 " + server.getLocalPort(), null);
                if (!java.security.MessageDigest.isEqual(nonce.getBytes(StandardCharsets.US_ASCII), actual.getBytes(StandardCharsets.US_ASCII)))
                    throw new IOException("자기 기기 loopback 확인 실패");
                verifiedUid = 2000;
                return new Result(transcript + "\n자기 Android 확인 · Developer UID=2000", true);
            }
        }
        if (uid != 0) {
            return new Result(transcript + "\nroot ADB 필요: 실제 UID=" + uid
                    + ". root adbd 준비 후 다시 연결하세요. 앱이 adbd를 재시작하지 않습니다.", false);
        }
        File challenge = File.createTempFile("self-probe-", ".txt", privateDirectory);
        try {
            Os.chmod(challenge.getAbsolutePath(), 0600);
            String nonce = UUID.randomUUID().toString();
            Files.write(challenge.toPath(), nonce.getBytes(StandardCharsets.UTF_8));
            String actual = read("cat " + LocalPolicy.shellPath(challenge.getAbsolutePath()), null);
            LocalPolicy.verifySelf(device, Build.DEVICE, id, nonce, actual);
            ensureOpen();
            verifiedRoot = true;
            verifiedUid = 0;
            return new Result(transcript + "\n앱 비공개 파일 일치: 자기 Android 확인. 실행 UID=0.\n"
                    + "이번 연결은 읽기 전용 진단만 수행했습니다.", true);
        } finally {
            Files.deleteIfExists(challenge.toPath());
        }
    }

    private synchronized void attach(Dadb candidate) throws IOException {
        if (closed || Thread.currentThread().isInterrupted()) {
            try { candidate.close(); } catch (Exception ignored) { }
            throw new IOException("연결이 중단되었습니다.");
        }
        connection = candidate;
    }

    void install(File apk, boolean root) throws Exception {
        ensureOpen();
        LocalPolicy.verifyInstallerUid(verifiedUid, LocalPolicy.uid(read("id", null)), root);
        if (wireless != null) { wireless.install(apk); ensureOpen(); return; }
        // Use Dadb's streaming PackageManager path; its legacy fallback does not verify success.
        if (!connection.supportsFeature("cmd")) throw new IOException("이 ADB는 검증 가능한 streaming 설치를 지원하지 않습니다.");
        connection.install(apk, "-r");
        ensureOpen();
    }

    void prepareRuntime(Context context, Consumer<String> progress) throws Exception {
        ensureVerifiedRoot();
        File directory = new File(privateDirectory, "runtime-input");
        Files.createDirectories(directory.toPath());
        Os.chmod(directory.getAbsolutePath(), 0700);
        String[] names = {"prepare.sh", "fedora-44-arm64-rootfs.tar.gz", "opencode-linux-arm64.tar.gz", "preroot.sh", "enter.sh"};
        for (String name : names) {
            ensureVerifiedRoot();
            progress.accept("설치 파일 준비: " + name);
            File target = new File(directory, name);
            try (var input = context.getAssets().open(name.endsWith(".gz") ? name + ".bin" : name)) {
                Files.copy(input, target.toPath(), StandardCopyOption.REPLACE_EXISTING);
            }
            Os.chmod(target.getAbsolutePath(), 0600);
        }
        ensureVerifiedRoot();
        String command = "/system/bin/sh " + LocalPolicy.shellPath(new File(directory, names[0]).getAbsolutePath())
                + " " + LocalPolicy.shellPath(new File(directory, names[1]).getAbsolutePath())
                + " " + LocalPolicy.shellPath(new File(directory, names[2]).getAbsolutePath());
        progress.accept("Fedora 검증·설치 중…");
        // Fixed script emits bounded phase records, never provider credentials.
        String report = read(command, new StringBuilder());
        if (!report.contains("phase=prepared root=/data/local/tinyagent/runtime/0.1.2/rootfs")) {
            throw new IOException("설치 완료 상태를 확인하지 못했습니다.");
        }
        progress.accept("Fedora 내부 OpenCode 실행 확인 중…");
        String version = read("/system/bin/sh " + LocalPolicy.shellPath(new File(directory, "preroot.sh").getAbsolutePath())
                + " /data/local/tinyagent/runtime/0.1.2/rootfs unrestricted-root exec /workspace"
                + " /usr/local/bin/opencode --version", new StringBuilder());
        if (!version.equals("1.18.29")) throw new IOException("설치된 OpenCode 버전 불일치");
        for (String name : names) {
            if (name.endsWith(".gz")) Files.deleteIfExists(new File(directory, name).toPath());
        }
    }

    void startBackend(Context context) throws Exception {
        ensureVerifiedRoot();
        File directory = stageControl(context);
        read("/system/bin/sh " + LocalPolicy.shellPath(new File(directory, "backend.sh").getAbsolutePath())
                + " unrestricted-root start", new StringBuilder());
        String password = read("cat /data/local/tinyagent/data/.tinyagent-server-password", null);
        if (!password.matches("[0-9a-f]{64}")) throw new IOException("백엔드 인증 파일 형식 오류");
        File auth = new File(privateDirectory, "backend-auth");
        android.util.AtomicFile atomic = new android.util.AtomicFile(auth);
        java.io.FileOutputStream output = null;
        try {
            output = atomic.startWrite();
            Os.fchmod(output.getFD(), 0600);
            output.write(password.getBytes(StandardCharsets.US_ASCII));
            atomic.finishWrite(output);
        } catch (Exception error) {
            if (output != null) atomic.failWrite(output);
            throw error;
        }
    }

    void stopBackend(Context context) throws Exception {
        ensureVerifiedRoot();
        File directory = stageControl(context);
        read("/system/bin/sh " + LocalPolicy.shellPath(new File(directory, "backend.sh").getAbsolutePath())
                + " unrestricted-root stop", new StringBuilder());
    }

    private File stageControl(Context context) throws Exception {
        File directory = new File(privateDirectory, "runtime-input");
        Files.createDirectories(directory.toPath());
        Os.chmod(directory.getAbsolutePath(), 0700);
        for (String name : new String[] {"preroot.sh", "enter.sh", "backend.sh"}) {
            ensureVerifiedRoot();
            File target = new File(directory, name);
            try (var input = context.getAssets().open(name)) {
                Files.copy(input, target.toPath(), StandardCopyOption.REPLACE_EXISTING);
            }
            Os.chmod(target.getAbsolutePath(), 0600);
        }
        return directory;
    }

    private void ensureVerifiedRoot() throws IOException {
        ensureOpen();
        if (!verifiedRoot) throw new IOException("자기 기기 root 인증이 필요합니다.");
    }

    private String read(String command, StringBuilder transcript) throws Exception {
        ensureOpen();
        if (wireless != null) {
            String output = wireless.shell(command).trim();
            ensureOpen();
            if (transcript != null) transcript.append("\n$ ").append(command).append('\n').append(output).append("\nexit=0\n");
            return output;
        }
        AdbShellResponse response = connection.shell(command);
        ensureOpen();
        if (transcript != null) {
            transcript.append("\n$ ").append(command).append("\n")
                    .append(response.getAllOutput().trim()).append("\nexit=").append(response.getExitCode()).append("\n");
        }
        if (response.getExitCode() != 0) {
            // Never include the private challenge content, key material or arbitrary error payloads.
            throw new IOException((transcript == null ? "자기 기기 비공개 파일 확인" : transcript.toString())
                    + " 실패 (exit=" + response.getExitCode() + ").");
        }
        return response.getOutput().trim();
    }

    private AdbKeyPair keyPair() throws Exception {
        File directory = new File(privateDirectory, "adb-identity");
        if (!directory.exists()) {
            File staged = Files.createTempDirectory(privateDirectory.toPath(), "adb-identity-pending-").toFile();
            File privateKey = new File(staged, "adbkey");
            File publicKey = new File(staged, "adbkey.pub");
            try {
                Os.chmod(staged.getAbsolutePath(), 0700);
                AdbKeyPair.generate(privateKey, publicKey);
                Os.chmod(privateKey.getAbsolutePath(), 0600);
                Os.chmod(publicKey.getAbsolutePath(), 0600);
                Files.move(staged.toPath(), directory.toPath(), StandardCopyOption.ATOMIC_MOVE);
            } finally {
                Files.deleteIfExists(privateKey.toPath());
                Files.deleteIfExists(publicKey.toPath());
                Files.deleteIfExists(staged.toPath());
            }
        }
        File privateKey = new File(directory, "adbkey");
        File publicKey = new File(directory, "adbkey.pub");
        if (!privateKey.isFile() || !publicKey.isFile()) {
            throw new IOException("앱 ADB 키 파일이 손상되었습니다. 기존 키를 자동 교체하지 않았습니다.");
        }
        Os.chmod(directory.getAbsolutePath(), 0700);
        Os.chmod(privateKey.getAbsolutePath(), 0600);
        Os.chmod(publicKey.getAbsolutePath(), 0600);
        return AdbKeyPair.read(privateKey, publicKey);
    }

    private void ensureOpen() throws IOException {
        if (closed || Thread.currentThread().isInterrupted()) {
            close();
            throw new IOException("진단 연결이 중단되었습니다.");
        }
    }

    @Override public synchronized void close() {
        closed = true;
        verifiedRoot = false;
        verifiedUid = -1;
        if (wireless != null) try { wireless.close(); } catch (Exception ignored) { }
        Dadb active = connection;
        if (active != null) {
            try { active.close(); } catch (Exception ignored) { }
        }
    }
}
