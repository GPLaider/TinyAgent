package io.github.gplaider.tinyagent;

import android.app.Activity;
import android.content.ContextWrapper;
import android.os.Bundle;
import android.system.Os;
import android.widget.TextView;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.security.MessageDigest;
import java.util.*;
import java.util.concurrent.TimeUnit;
import org.json.JSONObject;

/** Debug-only disposable-root product test. No ADB, su, or user Fedora mutations. */
public final class DnfastProbeActivity extends Activity {
    private TextView status;
    private final StringBuilder report = new StringBuilder();
    private volatile LocalLinuxRuntime runtime;
    private volatile boolean closed;
    private File logFile;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        status = new TextView(this);
        status.setPadding(24, 48, 24, 24);
        setContentView(status);
        logFile = new File(getFilesDir(), "dnfast-product-probe.log");
        new Thread(this::probe, "dnfast-product-probe").start();
    }

    private synchronized void log(String text) throws IOException {
        report.append(text).append('\n');
        if (report.length() > 200000) report.delete(0, report.length() - 200000);
        Files.write(logFile.toPath(), report.toString().getBytes(StandardCharsets.UTF_8));
        String view = report.substring(Math.max(0, report.length() - 6000));
        runOnUiThread(() -> status.setText(view));
    }

    private static String hash(File file) throws Exception {
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        try (var input = new FileInputStream(file)) {
            byte[] buffer = new byte[65536];
            for (int n; (n = input.read(buffer)) != -1;) digest.update(buffer, 0, n);
        }
        return hex(digest.digest());
    }

    private static String hex(byte[] bytes) {
        StringBuilder value = new StringBuilder();
        for (byte b : bytes) value.append(String.format(Locale.ROOT, "%02x", b & 255));
        return value.toString();
    }

    private void probe() {
        try {
            String action = getIntent().getStringExtra("action");
            if (action == null) action = "check";
            if (action.equals("result-contract")) {
                DnfastResultCheck.run();
                log("PASS action=result-contract");
                return;
            }
            if (action.equals("network")) {
                nativeNetwork();
                log("PASS action=network");
                return;
            }
            if (action.equals("cancel-preparation")) {
                cancelPreparation();
                log("PASS action=cancel-preparation");
                return;
            }
            String candidate = getIntent().getStringExtra("candidate");
            if (candidate == null) candidate = "b754437";
            if (!candidate.matches("[0-9a-f]{7,40}")) throw new IOException("Invalid candidate ID");
            int timeoutSeconds = getIntent().getIntExtra("timeout_seconds", 900);
            if (timeoutSeconds < 1 || timeoutSeconds > 7200) throw new IOException("Invalid probe deadline");
            String[] operation = switch (action) {
                case "check" -> new String[]{"app-runtime", "check"};
                case "refresh" -> new String[]{"repo", "refresh"};
                case "plan" -> new String[]{"install", "--assumeno", "hello"};
                case "install" -> new String[]{"install", "--assumeyes", "hello"};
                case "recover" -> new String[]{"app-runtime", "recover"};
                case "verify" -> new String[]{"app-runtime", "check"};
                case "timeout-process" -> new String[]{"app-runtime", "check"};
                default -> throw new IOException("Unknown fixed probe action");
            };
            log("action=" + action + " actual_uid=" + android.os.Process.myUid());
            log("context=" + new String(Files.readAllBytes(Paths.get("/proc/self/attr/current")), StandardCharsets.UTF_8).trim());
            File owned = new File(getFilesDir(), "dnfast-product-" + candidate + "-v1").getCanonicalFile();
            runtime = new LocalLinuxRuntime(new ContextWrapper(this) {
                @Override public File getFilesDir() { return owned; }
            });
            for (File directory : List.of(runtime.base, runtime.rootfs, runtime.home, runtime.workspace,
                    new File(runtime.base, "shared"), new File(runtime.base, "tmp"), new File(runtime.rootfs, ".l2s"))) {
                Files.createDirectories(directory.toPath());
            }
            Os.chmod(runtime.rootfs.toString(), 0700);
            try (var input = getAssets().open("linux-launch.sh")) {
                Files.copy(input, new File(runtime.base, "launch.sh").toPath(), StandardCopyOption.REPLACE_EXISTING);
            }
            File marker = new File(runtime.base, "extracted");
            if (!marker.exists()) {
                // Refuse to overwrite a partially extracted root; preserve it for diagnosis.
                File started = new File(runtime.base, "extraction-started");
                if (!started.createNewFile()) throw new IOException("Incomplete extraction retained; inspect disposable root");
                File archive = new File(runtime.base, "fedora.tar.gz");
                try (var input = getAssets().open("fedora-44-arm64-rootfs.tar.gz.bin")) {
                    Files.copy(input, archive.toPath());
                }
                if (!hash(archive).equals("3a3661a77d5fdb1e4bd10be484142683630c1ffb4c371931d46a42459fd4c125"))
                    throw new IOException("Fedora asset hash mismatch");
                log("extracting pinned Fedora; no package-manager bootstrap");
                ProcessBuilder extraction = runtime.guest("/workspace");
                extraction.command(List.of(getApplicationInfo().nativeLibraryDir + "/libproot.so", "-0", "-l", "--kill-on-exit",
                        "/system/bin/tar", "-xzf", archive.toString(), "-C", runtime.rootfs.toString()));
                run(extraction, 180);
                Files.write(marker.toPath(), "verified\n".getBytes(StandardCharsets.US_ASCII));
            }
            runtime.refreshDns();
            if (action.equals("timeout-process")) {
                try {
                    run(runtime.guest("/workspace", "/usr/bin/sleep", "60"), 1);
                    throw new IOException("Timeout process returned success");
                } catch (java.util.concurrent.TimeoutException expected) {
                    log("timeout=true process_exited=true");
                }
                log("PASS action=timeout-process");
                return;
            }
            File staged = new File(getFilesDir(), "linux/shared/dnfast-product-" + candidate);
            JSONObject manifest = new JSONObject(new String(Files.readAllBytes(new File(staged, "manifest.json").toPath()), StandardCharsets.UTF_8));
            File overlay = new File(staged, "root-overlay.tar.gz");
            if (!hash(overlay).equals(manifest.getString("overlay_sha256"))) throw new IOException("Overlay hash mismatch");
            File applied = new File(runtime.base, "overlay-sha256");
            if (!applied.exists()) {
                ProcessBuilder extraction = runtime.guest("/workspace");
                extraction.command(List.of(getApplicationInfo().nativeLibraryDir + "/libproot.so", "-0", "-l", "--kill-on-exit",
                        "/system/bin/tar", "-xzf", overlay.toString(), "-C", runtime.rootfs.toString()));
                run(extraction, 120);
                Files.write(applied.toPath(), manifest.getString("overlay_sha256").getBytes(StandardCharsets.US_ASCII));
            }
            if (!new String(Files.readAllBytes(applied.toPath()), StandardCharsets.US_ASCII).equals(manifest.getString("overlay_sha256")))
                throw new IOException("Candidate changed; retained root must not be silently upgraded");
            String cli = hash(new File(runtime.rootfs, "usr/bin/dnfast"));
            String executor = hash(new File(runtime.rootfs, "usr/libexec/dnfast-executor"));
            if (!cli.equals(manifest.getString("dnfast_sha256")) || !executor.equals(manifest.getString("executor_sha256")))
                throw new IOException("Final ELF hashes differ");
            List<String> request = new ArrayList<>(List.of("/usr/bin/dnfast", "--app-proot"));
            request.addAll(List.of(operation));
            ProcessBuilder builder = runtime.guest("/workspace", request.toArray(new String[0]));
            builder.environment().put("DNFAST_REFRESH_TRACE", "1");
            List<String> proot = new ArrayList<>(builder.command());
            String binds = String.join("\u0000", proot.subList(1, proot.indexOf("/usr/bin/env")));
            String bindsHash = hex(MessageDigest.getInstance("SHA-256").digest(binds.getBytes(StandardCharsets.UTF_8)));
            String nativeDir = getApplicationInfo().nativeLibraryDir;
            String runtimeHash = hash(new File(nativeDir, "libproot.so"));
            List<String> launch = new ArrayList<>(List.of(nativeDir + "/libdnfastlaunch.so", runtime.rootfs.toString(),
                    Integer.toString(android.os.Process.myUid()), runtimeHash, bindsHash, cli, executor, "--"));
            launch.addAll(proot);
            log("root=" + runtime.rootfs + "\ndnfast_sha256=" + cli + "\nexecutor_sha256=" + executor
                    + "\nruntime_sha256=" + runtimeHash + "\nbinds_sha256=" + bindsHash);
            run(builder.command(launch), timeoutSeconds);
            requireDnfastResult(action);
            if (action.equals("verify")) {
                run(runtime.guest("/workspace", "/usr/bin/rpm", "-q", "hello", "info"), 30);
                run(runtime.guest("/workspace", "/usr/bin/hello"), 30);
            }
            log("PASS action=" + action);
        } catch (Exception error) {
            try { log("FAIL: " + error); } catch (IOException ignored) { }
        }
    }

    private void cancelPreparation() throws Exception {
        File owned = new File(getFilesDir(), "cancel-preparation-" + UUID.randomUUID());
        LocalLinuxRuntime runtime = new LocalLinuxRuntime(new ContextWrapper(this) {
            @Override public File getFilesDir() { return owned; }
        });
        boolean[] cancelled = {false}, completed = {false};
        log("action=cancel-preparation actual_uid=" + android.os.Process.myUid() + " root=" + owned);
        try {
            runtime.prepare(line -> {}, (label, percent) -> {
                if (label.equals("Fedora 압축 해제 완료")) completed[0] = true;
                if (!cancelled[0] && label.startsWith("Fedora 압축 해제 ·") && percent >= 1) {
                    cancelled[0] = true;
                    runtime.cancel();
                }
            });
            throw new IOException("Cancelled preparation returned success");
        } catch (InterruptedException expected) {
            if (!cancelled[0] || completed[0] || new File(owned, "linux/prepared-v1").exists())
                throw new IOException("Cancelled extraction reported completion");
            log("cancelled=true completion=false prepared_marker=false");
        } finally {
            runtime.cancel();
        }
    }

    private void requireDnfastResult(String action) throws Exception {
        DnfastResult.require(action, 0, report.toString());
    }

    private void nativeNetwork() throws Exception {
        long began = android.os.SystemClock.elapsedRealtime();
        log("action=network actual_uid=" + android.os.Process.myUid() + " transport=Android-HttpURLConnection no-PRoot");
        String expected = "1f1fdf58f26864c869884f854e92bc502d6fdf1769be2b2804783c243edf36a0";
        var connection = (java.net.HttpURLConnection) new java.net.URL("https://mirror.twds.com.tw/fedora/fedora/linux/releases/44/Everything/aarch64/os/repodata/" + expected + "-primary.xml.zst").openConnection();
        connection.setConnectTimeout(10000);
        connection.setReadTimeout(30000);
        connection.setRequestProperty("Accept-Encoding", "identity");
        connection.setRequestProperty("User-Agent", "dnfast/0.1.0");
        connection.setInstanceFollowRedirects(false);
        long count = 0;
        MessageDigest checksum = MessageDigest.getInstance("SHA-256");
        try {
            int code = connection.getResponseCode();
            log("http=" + code + " headers_ms=" + (android.os.SystemClock.elapsedRealtime() - began));
            if (code != 200) throw new IOException("HTTP " + code);
            try (var input = connection.getInputStream()) {
                byte[] buffer = new byte[65536];
                for (int n; (n = input.read(buffer)) != -1;) {
                    count += n;
                    if (closed || count > 67108864 || android.os.SystemClock.elapsedRealtime() - began > 120000)
                        throw new IOException("Native network probe limit");
                    checksum.update(buffer, 0, n);
                }
            }
            if (count != 14622908 || !hex(checksum.digest()).equals(expected)) throw new IOException("Metadata size/hash mismatch");
        } finally {
            connection.disconnect();
            log("bytes=" + count + " elapsed_ms=" + (android.os.SystemClock.elapsedRealtime() - began));
        }
    }

    private void run(ProcessBuilder builder, int timeoutSeconds) throws Exception {
        if (closed) throw new IOException("Activity stopped");
        Process process = runtime.start(builder.redirectErrorStream(true));
        var readFailure = new java.util.concurrent.atomic.AtomicReference<IOException>();
        Thread drain = new Thread(() -> {
            try (var reader = new BufferedReader(new InputStreamReader(process.getInputStream()))) {
                for (String line; (line = reader.readLine()) != null;) log(line);
            } catch (IOException error) { readFailure.set(error); }
        });
        drain.start();
        try {
            if (!process.waitFor(timeoutSeconds, TimeUnit.SECONDS)) {
                runtime.stop(process);
                if (!process.waitFor(5, TimeUnit.SECONDS)) throw new IOException("Owned process did not stop; inspect before retry");
                throw new java.util.concurrent.TimeoutException("Command timed out; inspect actual transaction before retry");
            }
            drain.join(5000);
            if (drain.isAlive() || readFailure.get() != null)
                throw new IOException("Incomplete command output", readFailure.get());
            if (closed) throw new IOException("Activity stopped; inspect actual transaction state");
            log("exit=" + process.exitValue());
            if (process.exitValue() != 0) throw new IOException("Command exit=" + process.exitValue());
        } finally {
            try {
                if (process.isAlive()) runtime.stop(process);
                else runtime.forget(process);
            } finally {
                process.getInputStream().close();
            }
        }
    }

    @Override public void onDestroy() {
        closed = true;
        if (runtime != null) runtime.cancel();
        super.onDestroy();
    }
}
