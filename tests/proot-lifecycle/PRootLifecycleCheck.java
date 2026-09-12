package io.github.gplaider.tinyagent;

import android.app.*;
import android.content.*;
import android.os.Bundle;
import android.os.SystemClock;
import android.system.*;
import java.io.*;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicReference;

/** Current production Java + native PRoot + pinned Fedora, all in a separate app UID. */
public final class PRootLifecycleCheck extends Instrumentation {
    private static final Path BOOT = Paths.get("/proc/sys/kernel/random/boot_id");
    private final StringBuilder report = new StringBuilder();
    private int checks;
    @Override public void onCreate(Bundle args) { super.onCreate(args); start(); }
    private interface Check { boolean ready() throws Exception; }
    private void await(Check check, String message) throws Exception {
        long until = SystemClock.elapsedRealtime() + 10000;
        while (!check.ready()) {
            if (SystemClock.elapsedRealtime() > until) throw new AssertionError(message);
            Thread.sleep(20);
        }
        checks++;
    }
    private void require(boolean value, String message) {
        checks++;
        if (!value) throw new AssertionError(message);
    }
    static String identity(int pid) throws Exception {
        return pid + "\n" + Files.readString(BOOT).trim() + "\n" + Files.readString(Paths.get("/proc", Integer.toString(pid), "stat"));
    }
    private static int pid(String record) { return Integer.parseInt(record.split("\\R", 2)[0]); }
    private static boolean alive(String record) throws Exception {
        int pid = pid(record);
        Path path = Paths.get("/proc", Integer.toString(pid), "stat");
        try {
            String stat = Files.readString(path);
            return !stat.substring(stat.lastIndexOf(") ") + 2).startsWith("Z ")
                    && RuntimeProcessIdentity.matches(record, Files.readString(BOOT), stat);
        } catch (NoSuchFileException gone) { return false; }
    }
    private static void killOwned(String record) throws Exception {
        if (alive(record) && Os.stat("/proc/" + pid(record)).st_uid == android.os.Process.myUid())
            Os.kill(pid(record), OsConstants.SIGKILL);
    }
    private static List<Path> records(LocalLinuxRuntime runtime) throws Exception {
        try (var files = Files.list(runtime.base.toPath())) {
            return files.filter(p -> p.getFileName().toString().startsWith("process-")
                    && p.getFileName().toString().endsWith(".pid")).collect(java.util.stream.Collectors.toList());
        }
    }
    private static void force(LocalLinuxRuntime runtime, Process process) throws Exception {
        var signal = LocalLinuxRuntime.class.getDeclaredMethod("signal", Process.class, int.class);
        signal.setAccessible(true);
        signal.invoke(runtime, process, OsConstants.SIGKILL);
    }
    @SuppressWarnings("unchecked")
    private static Map<Process, File> owned(LocalLinuxRuntime runtime) throws Exception {
        var field = LocalLinuxRuntime.class.getDeclaredField("pids"); field.setAccessible(true);
        return (Map<Process, File>) field.get(runtime);
    }
    private void copyLauncher(LocalLinuxRuntime runtime) throws Exception {
        try (var input = getTargetContext().getAssets().open("linux-launch.sh")) {
            Files.copy(input, runtime.base.toPath().resolve("launch.sh"), StandardCopyOption.REPLACE_EXISTING);
        }
    }
    private Path marker(LocalLinuxRuntime runtime, String name) { return runtime.base.toPath().resolve("shared/" + name); }
    private ProcessBuilder guest(LocalLinuxRuntime runtime, Path child) {
        return runtime.guest("/workspace", "/usr/bin/bash", "/shared/launch.sh",
                "/shared/" + child.getFileName(), "/usr/bin/sleep", "120");
    }
    private void checkStop(String mode, int round) throws Exception {
        LocalLinuxRuntime runtime = new LocalLinuxRuntime(getTargetContext());
        Path child = marker(runtime, mode + "-" + round + ".identity");
        Process parent = runtime.start(guest(runtime, child));
        try {
            await(() -> Files.exists(child), "Fedora child missing: " + mode);
            String record = Files.readString(child);
            require(parent.isAlive() && alive(record), "child exited before test");
            require(Os.stat("/proc/" + pid(record)).st_uid == android.os.Process.myUid(), "guest escaped app UID");
            if (mode.equals("cancel")) runtime.cancel();
            else if (mode.equals("kill")) force(runtime, parent);
            else new LocalLinuxRuntime(getTargetContext()).recoverPreviousProcesses(runtime.base);
            require(parent.waitFor(5, TimeUnit.SECONDS), "PRoot parent survived " + mode);
            await(() -> !alive(record), "Fedora child survived " + mode);
            runtime.forget(parent);
            new LocalLinuxRuntime(getTargetContext()).recoverPreviousProcesses(runtime.base);
            require(records(runtime).isEmpty(), "PID record retained after " + mode);
            report.append(mode).append(" round=").append(round).append(" PASS parent/tracee death, app UID, PID cleanup\n");
        } finally {
            force(runtime, parent); parent.waitFor(5, TimeUnit.SECONDS);
            if (Files.exists(child)) killOwned(Files.readString(child));
            runtime.forget(parent);
        }
    }
    private void checkFailedStart(boolean interrupt) throws Exception {
        LocalLinuxRuntime runtime = new LocalLinuxRuntime(getTargetContext());
        Path child = marker(runtime, interrupt ? "interrupt.identity" : "timeout.identity");
        // The real launcher publishes its PID before exec. Block before that point;
        // no guest may run while its outer launcher has not published ownership.
        Files.writeString(runtime.base.toPath().resolve("launch.sh"), "#!/system/bin/sh\nwhile :; do :; done\n");
        AtomicReference<Throwable> failure = new AtomicReference<>();
        Thread starter = new Thread(() -> {
            try { runtime.start(guest(runtime, child)); }
            catch (Throwable error) { failure.set(error); }
        }, "audit-failed-start");
        try {
            starter.start();
            await(() -> !owned(runtime).isEmpty(), "failed-start launcher never became live");
            Process launcher = owned(runtime).keySet().iterator().next();
            if (interrupt) starter.interrupt();
            starter.join(7000);
            require(!starter.isAlive(), "failed start thread hung");
            require(interrupt ? failure.get() instanceof InterruptedException : failure.get() instanceof IOException,
                    "wrong failed-start result: " + failure.get());
            require(!launcher.isAlive(), "failed start left Android launcher alive");
            require(!Files.exists(child), "guest launched before PID publication");
            require(records(runtime).isEmpty(), "failed start retained PID record");
            report.append(interrupt ? "interrupt" : "timeout").append(" PASS Android launcher cleanup before PID handshake; no guest launched\n");
        } finally {
            starter.interrupt(); starter.join(7000);
            if (Files.exists(child)) killOwned(Files.readString(child));
            copyLauncher(runtime);
            runtime.cancel();
        }
    }
    private void checkStaleRecords() throws Exception {
        LocalLinuxRuntime runtime = new LocalLinuxRuntime(getTargetContext());
        Path sentinelRecord = marker(runtime, "sentinel.identity");
        Process sentinel = new ProcessBuilder("/system/bin/sh", runtime.base.toPath().resolve("launch.sh").toString(),
                sentinelRecord.toString(), "/system/bin/sleep", "120").start();
        try {
            await(() -> Files.exists(sentinelRecord), "sentinel identity missing");
            String record = Files.readString(sentinelRecord);
            Path stale = runtime.base.toPath().resolve("process-stale.pid");
            Files.writeString(stale, record.replace(Files.readString(BOOT).trim(), "another-boot"));
            runtime.recoverPreviousProcesses(runtime.base);
            require(sentinel.isAlive() && !Files.exists(stale), "stale boot signalled sentinel");
            String[] lines = record.split("\\R", 3);
            String stat = lines[2]; int end = stat.lastIndexOf(") ") + 2;
            String[] fields = stat.substring(end).trim().split("\\s+");
            fields[19] = Long.toString(Long.parseLong(fields[19]) + 1);
            Files.writeString(stale, lines[0] + "\n" + lines[1] + "\n" + stat.substring(0, end) + String.join(" ", fields));
            runtime.recoverPreviousProcesses(runtime.base);
            require(sentinel.isAlive() && !Files.exists(stale), "reused PID signalled sentinel");
            Files.writeString(stale, ""); runtime.recoverPreviousProcesses(runtime.base);
            require(!Files.exists(stale), "empty record retained");
            report.append("stale-records PASS real sentinel survives wrong boot/start ticks; empty record removed\n");
        } finally { sentinel.destroyForcibly(); sentinel.waitFor(5, TimeUnit.SECONDS); }
    }
    private void checkOwnerDeath() throws Exception {
        Context context = getTargetContext();
        LocalLinuxRuntime runtime = new LocalLinuxRuntime(context);
        Intent intent = new Intent(context, CrashOwnerService.class);
        Path ready = marker(runtime, "remote-owner.ready"), owner = marker(runtime, "remote-owner.identity"), child = marker(runtime, "remote-child.identity");
        try {
            context.startService(intent);
            await(() -> Files.exists(ready) && Files.exists(child), "remote owner failed to start");
            String ownerIdentity = Files.readString(owner), childIdentity = Files.readString(child);
            String command = Files.readString(Paths.get("/proc", Integer.toString(pid(ownerIdentity)), "cmdline"));
            // Android may pad argv storage with extra NUL bytes; compare argv[0].
            int end = command.indexOf('\0');
            String name = end < 0 ? command : command.substring(0, end);
            require(name.equals(context.getPackageName() + ":crash_owner"), "unexpected Java owner process: " + name);
            killOwned(ownerIdentity);
            await(() -> !alive(ownerIdentity), "Java owner survived SIGKILL");
            new LocalLinuxRuntime(context).recoverPreviousProcesses(runtime.base);
            await(() -> !alive(childIdentity), "Fedora child survived owner-death recovery");
            require(records(runtime).isEmpty(), "owner-death recovery retained PID record");
            report.append("owner-death PASS killed only remote audit Java process; fresh runtime reaped PRoot/Fedora child\n");
        } finally {
            context.stopService(intent);
            if (Files.exists(owner)) killOwned(Files.readString(owner));
            if (Files.exists(child)) killOwned(Files.readString(child));
            runtime.recoverPreviousProcesses(runtime.base);
        }
    }
    @Override public void onStart() {
        boolean passed = false;
        try {
            LocalLinuxRuntime runtime = new LocalLinuxRuntime(getTargetContext());
            for (var directory : List.of(runtime.base, runtime.rootfs, runtime.workspace, runtime.home,
                    marker(runtime, "").toFile(), runtime.base.toPath().resolve("tmp").toFile(), runtime.rootfs.toPath().resolve(".l2s").toFile()))
                Files.createDirectories(directory.toPath());
            copyLauncher(runtime);
            Files.copy(runtime.base.toPath().resolve("launch.sh"), marker(runtime, "launch.sh"));
            runtime.unpack("fedora-44-arm64-rootfs.tar.gz.bin", "3a3661a77d5fdb1e4bd10be484142683630c1ffb4c371931d46a42459fd4c125", runtime.rootfs, "Fedora audit", 5638);
            for (String directory : List.of("root", "workspace", "shared", "dev", "proc", "tmp")) Files.createDirectories(runtime.rootfs.toPath().resolve(directory));
            Files.createFile(runtime.rootfs.toPath().resolve("tinyagent-installed.apk"));
            StringBuilder version = new StringBuilder();
            runtime.run(runtime.guest("/workspace", "/usr/bin/cat", "/etc/fedora-release"), line -> version.append(line));
            require(version.toString().contains("Fedora release 44"), "wrong Fedora image");
            report.append("runtime ").append(version).append(" Android UID=").append(android.os.Process.myUid()).append('\n');
            for (String mode : List.of("cancel", "recover", "kill")) for (int round=1; round<=3; round++) checkStop(mode, round);
            checkFailedStart(true); checkFailedStart(false); checkStaleRecords(); checkOwnerDeath();
            passed = true;
        } catch (Throwable error) { report.append("FAIL ").append(error).append('\n'); }
        Bundle result = new Bundle();
        result.putString("stream", report + (passed ? "PASS: real PRoot/Fedora lifecycle; " + checks + " assertions\n" : ""));
        finish(passed ? Activity.RESULT_OK : Activity.RESULT_CANCELED, result);
    }
}
