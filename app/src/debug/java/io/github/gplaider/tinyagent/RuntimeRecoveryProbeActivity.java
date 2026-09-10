package io.github.gplaider.tinyagent;

import android.app.Activity;
import android.os.Bundle;
import android.widget.TextView;
import java.io.File;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;

/** Fixed debug probe: only its temporary directory and self-created PRoot are used. */
public final class RuntimeRecoveryProbeActivity extends Activity {
    private static final AtomicBoolean running = new AtomicBoolean();
    private TextView view;
    private final StringBuilder report = new StringBuilder();
    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        view = new TextView(this); view.setTextSize(16); view.setPadding(32, 64, 32, 32); setContentView(view);
        if (!running.compareAndSet(false, true)) { view.setText("Recovery probe already running"); return; }
        new Thread(this::probe, "runtime-recovery-probe").start();
    }
    private void log(String value) {
        report.append(value).append('\n');
        try { Files.write(new File(getFilesDir(), "runtime-recovery-probe.log").toPath(), report.toString().getBytes(StandardCharsets.UTF_8)); }
        catch (Exception ignored) { }
        runOnUiThread(() -> view.setText(report));
    }
    private static String text(Path file) throws Exception { return new String(Files.readAllBytes(file), StandardCharsets.UTF_8); }
    private void probe() {
        try {
            if (android.os.Process.myUid() < 10000) throw new IllegalStateException("App UID required");
            log("uid=" + android.os.Process.myUid());
            boolean killParent = getIntent().getBooleanExtra("kill_parent", false);
            log("mode=" + (killParent ? "parent SIGKILL" : "live recovery"));
            LocalLinuxRuntime runtime = new LocalLinuxRuntime(this);
            String nativeDir = getApplicationInfo().nativeLibraryDir;
            boolean candidate = getIntent().getBooleanExtra("candidate", false);
            String tracer = candidate ? "/libproot_candidate.so" : "/libproot.so";
            String loader = candidate ? "/libproot_candidate_loader.so" : "/libproot_loader.so";
            log("runtime=" + (candidate ? "EXITKILL candidate" : "installed baseline"));
            for (int round = 1; round <= 3; round++) {
                Path dir = Files.createTempDirectory(getFilesDir().toPath(), "recovery-probe-");
                Path launcher = dir.resolve("launch.sh"), record = dir.resolve("process-test.pid"), child = dir.resolve("child.identity");
                try (var input = getAssets().open("linux-launch.sh")) { Files.copy(input, launcher); }
                ProcessBuilder builder = new ProcessBuilder("/system/bin/sh", launcher.toString(), record.toString(),
                        nativeDir + tracer, "-0", "-l", "--kill-on-exit",
                        "/system/bin/sh", launcher.toString(), child.toString(), "/system/bin/sleep", "120");
                builder.environment().put("PROOT_NO_SECCOMP", "1");
                builder.environment().put("PROOT_LOADER", nativeDir + loader);
                builder.environment().put("LD_LIBRARY_PATH", nativeDir);
                builder.environment().put("PROOT_TMP_DIR", dir.toString());
                builder.redirectErrorStream(true).redirectOutput(dir.resolve("process.log").toFile());
                Process process = builder.start();
                try {
                    long deadline = android.os.SystemClock.elapsedRealtime() + 10000;
                    while (!Files.exists(child) && process.isAlive() && android.os.SystemClock.elapsedRealtime() < deadline) Thread.sleep(50);
                    if (!Files.exists(child) || !process.isAlive()) throw new IllegalStateException("Child not running: " + text(dir.resolve("process.log")));
                    String identity = text(child);
                    int pid = Integer.parseInt(identity.split("\\R", 2)[0]);
                    if (android.system.Os.stat("/proc/" + pid).st_uid != android.os.Process.myUid()) throw new IllegalStateException("Child UID mismatch");
                    if (killParent) {
                        String parent = text(record);
                        int parentPid = Integer.parseInt(parent.split("\\R", 2)[0]);
                        if (!RuntimeProcessIdentity.matches(parent, text(Paths.get("/proc/sys/kernel/random/boot_id")),
                                text(Paths.get("/proc", Integer.toString(parentPid), "stat"))))
                            throw new IllegalStateException("Parent identity changed");
                        android.system.Os.kill(parentPid, android.system.OsConstants.SIGKILL);
                        if (!process.waitFor(5, TimeUnit.SECONDS)) throw new IllegalStateException("Test parent did not exit");
                    }
                    runtime.recoverPreviousProcesses(dir.toFile());
                    if (!process.waitFor(5, TimeUnit.SECONDS) || Files.exists(record)) throw new IllegalStateException("Parent still running or marker retained");
                    Path stat = Paths.get("/proc", Integer.toString(pid), "stat");
                    if (Files.exists(stat)) {
                        String current = text(stat);
                        if (!current.substring(current.lastIndexOf(") ") + 2).startsWith("Z ")
                                && RuntimeProcessIdentity.matches(identity, text(Paths.get("/proc/sys/kernel/random/boot_id")), current))
                            throw new IllegalStateException("Child survived recovery");
                    }
                    log("round=" + round + " PASS parent stopped, child stopped, marker removed");
                } finally {
                    if (process.isAlive()) runtime.recoverPreviousProcesses(dir.toFile());
                    // A failed parent-death assertion must not leave this test's sleep alive.
                    if (Files.exists(child)) {
                        String identity = text(child);
                        int pid = Integer.parseInt(identity.split("\\R", 2)[0]);
                        Path stat = Paths.get("/proc", Integer.toString(pid), "stat");
                        if (Files.exists(stat) && android.system.Os.stat("/proc/" + pid).st_uid == android.os.Process.myUid()
                                && RuntimeProcessIdentity.matches(identity, text(Paths.get("/proc/sys/kernel/random/boot_id")), text(stat)))
                            android.system.Os.kill(pid, android.system.OsConstants.SIGKILL);
                    }
                }
            }
            log("PASS: 3 real PRoot recovery rounds; existing backend untouched");
        } catch (Exception error) { log("FAIL: " + error); }
        finally { running.set(false); }
    }
}
