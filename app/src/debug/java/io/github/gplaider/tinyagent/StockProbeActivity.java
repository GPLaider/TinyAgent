package io.github.gplaider.tinyagent;

import android.app.Activity;
import android.os.Bundle;
import android.os.Process;
import android.widget.TextView;
import java.io.File;
import java.nio.file.Files;
import java.security.MessageDigest;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;

/** Debug-only fixed probe. Never contacts ADB or invokes root commands. */
public final class StockProbeActivity extends Activity {
    private TextView status;
    private final StringBuilder report = new StringBuilder();
    private volatile java.lang.Process child;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        status = new TextView(this);
        status.setTextSize(16);
        status.setPadding(32, 64, 32, 32);
        setContentView(status);
        new Thread(this::probe, "stock-probe").start();
    }

    private void log(String value) {
        report.append(value).append('\n');
        try { Files.write(new File(getFilesDir(), "stock-probe.log").toPath(), report.toString().getBytes(StandardCharsets.UTF_8)); }
        catch (Exception ignored) { }
        runOnUiThread(() -> status.setText(report.toString()));
    }

    private void probe() {
        try {
            log("host_uid=" + Process.myUid());
            log("host_context=" + new String(Files.readAllBytes(new File("/proc/self/attr/current").toPath()), StandardCharsets.UTF_8).trim());
            if (Process.myUid() < 10000) throw new IllegalStateException("Ordinary app UID required");
            if (getIntent().getBooleanExtra("filesystem_only", false)) {
                for (String path : List.of("/system/bin/toybox", "/system/bin/linker64",
                        getApplicationInfo().nativeLibraryDir + "/libproot.so")) {
                    try (var input = Files.newInputStream(new File(path).toPath())) {
                        log("read " + path + " first_byte=" + input.read());
                    } catch (Exception error) { log("read " + path + " failed=" + error); }
                }
                File directory = Files.createTempDirectory(getFilesDir().toPath(), "link-probe-").toFile();
                File target = new File(directory, "target");
                Files.write(target.toPath(), new byte[] {42});
                try {
                    android.system.Os.symlink("target", new File(directory, "symbolic").toString());
                    log("symlink=PASS");
                } catch (Exception error) { log("symlink failed=" + error); }
                try {
                    android.system.Os.link(target.toString(), new File(directory, "hard").toString());
                    log("hardlink=PASS");
                } catch (Exception error) { log("hardlink failed=" + error); }
                log("filesystem_probe_done");
                File nativeBase = new File(getFilesDir(), "stock-probe-noseccomp-v1");
                run(nativeBase, List.of("-v", "9", "/system/bin/true"));
                return;
            }
            File base = new File(getFilesDir(), "stock-probe-toybox-copy-v1");
            File rootfs = new File(base, "rootfs");
            File links = new File(rootfs, ".l2s");
            File temp = new File(base, "tmp");
            Files.createDirectories(links.toPath());
            Files.createDirectories(temp.toPath());
            File toybox = new File(base, "toybox");
            Files.copy(new File("/system/bin/toybox").toPath(), toybox.toPath(), java.nio.file.StandardCopyOption.REPLACE_EXISTING);
            if (!toybox.setExecutable(true, true)) throw new IllegalStateException("Toybox mode failed");
            run(base, List.of("-b", toybox + ":/system/bin/toybox", "/system/bin/true"));
            log("Direct Android executable probe:");
            child = new ProcessBuilder("/system/bin/true").start();
            int directExit = child.waitFor();
            child = null;
            log("direct_true_exit=" + directExit);
            if (directExit != 0) throw new IllegalStateException("Direct Android executable failed");
            File archive = new File(base, "fedora.tar.gz");
            if (!new File(base, "extracted").isFile()) {
                try (var in = getAssets().open("fedora-44-arm64-rootfs.tar.gz.bin")) {
                    Files.copy(in, archive.toPath(), java.nio.file.StandardCopyOption.REPLACE_EXISTING);
                }
                MessageDigest digest = MessageDigest.getInstance("SHA-256");
                try (var in = Files.newInputStream(archive.toPath())) {
                    byte[] buffer = new byte[65536];
                    for (int n; (n = in.read(buffer)) >= 0;) digest.update(buffer, 0, n);
                }
                StringBuilder hash = new StringBuilder();
                for (byte b : digest.digest()) hash.append(String.format("%02x", b & 255));
                if (!hash.toString().equals("3a3661a77d5fdb1e4bd10be484142683630c1ffb4c371931d46a42459fd4c125"))
                    throw new IllegalStateException("Fedora archive hash mismatch");
                log("archive_sha256=" + hash);
                log("PRoot extraction with app-readable toybox and link emulation:");
                run(base, List.of("-0", "-l", "-b", toybox + ":/system/bin/toybox",
                        "/system/bin/tar", "-xzf", archive.toString(), "-C", rootfs.toString()));
                Files.write(new File(base, "extracted").toPath(), "verified\n".getBytes(StandardCharsets.UTF_8));
            }
            var args = new ArrayList<>(List.of("-0", "-l", "-r", rootfs.toString(),
                    "-b", "/dev", "-b", "/proc", "-b", links + ":" + links, "-w", "/root"));
            var cat = new ArrayList<>(args);
            cat.addAll(List.of("/usr/bin/cat", "/etc/fedora-release"));
            run(base, cat);
            args.addAll(List.of("/usr/bin/id"));
            run(base, args);
            log("PASS: Fedora userspace ran under the ordinary Android app UID. Guest uid=0 is emulated.");
        } catch (Exception error) { log("FAIL: " + error); }
    }

    private void run(File base, List<String> args) throws Exception {
        String nativeDir = getApplicationInfo().nativeLibraryDir;
        var command = new ArrayList<String>();
        command.add(nativeDir + (new File(nativeDir, "libproot_probe.so").isFile() ? "/libproot_probe.so" : "/libproot.so"));
        command.addAll(args);
        log("argv=" + command);
        ProcessBuilder builder = new ProcessBuilder(command).redirectErrorStream(true).directory(base);
        builder.environment().put("PROOT_NO_SECCOMP", "1");
        builder.environment().put("LD_LIBRARY_PATH", nativeDir);
        builder.environment().put("PROOT_LOADER", nativeDir + "/libproot_loader.so");
        builder.environment().put("PROOT_TMP_DIR", new File(base, "tmp").toString());
        builder.environment().put("PROOT_L2S_DIR", new File(base, "rootfs/.l2s").toString());
        execute(builder);
    }

    private void execute(ProcessBuilder builder) throws Exception {
        child = builder.start();
        try (var in = new java.io.BufferedReader(new java.io.InputStreamReader(child.getInputStream()))) {
            for (String line; (line = in.readLine()) != null;) {
                if (report.length() < 40000) log(line);
            }
        }
        int exit = child.waitFor();
        child = null;
        log("exit=" + exit);
        if (exit != 0) throw new IllegalStateException("Probe command failed: " + exit);
    }

    @Override public void onDestroy() {
        if (child != null) child.destroy();
        super.onDestroy();
    }
}
