package io.github.gplaider.tinyagent;

import android.app.*;
import android.content.*;
import android.os.*;
import java.lang.Process;
import java.util.concurrent.*;
import java.util.function.*;

/** Real Android service/Handler/FGS/wakelock, with an isolated sleep-backed runtime. */
public final class RuntimeServiceDeviceCheck extends Instrumentation {
    @Override public void onCreate(Bundle args) { super.onCreate(args); start(); }
    private static Object field(Object target, String name) throws Exception {
        var field = target.getClass().getDeclaredField(name); field.setAccessible(true); return field.get(target);
    }
    private static void require(boolean value, String message) {
        if (!value) throw new AssertionError(message);
    }
    private interface Check { boolean ready() throws Exception; }
    private static void await(Check check, String message) throws Exception {
        long until = SystemClock.elapsedRealtime() + 10000;
        while (!check.ready()) {
            if (SystemClock.elapsedRealtime() > until) throw new AssertionError(message);
            Thread.sleep(20);
        }
    }
    @Override public void onStart() {
        StringBuilder report = new StringBuilder();
        boolean passed = false;
        Context context = getTargetContext();
        Intent start = new Intent(context, RuntimeSetupService.class);
        Intent stop = new Intent(context, RuntimeSetupService.class).setAction(RuntimeSetupService.STOP);
        try {
            for (int round = 1; round <= 3; round++) {
                LocalLinuxRuntime.created = 0;
                LocalLinuxRuntime.atCleanup = new CountDownLatch(1);
                LocalLinuxRuntime.releaseCleanup = new CountDownLatch(1);
                context.startForegroundService(start);
                require(LocalLinuxRuntime.atCleanup.await(10, TimeUnit.SECONDS), "initial owner did not reach cleanup");
                RuntimeSetupService service = LocalLinuxRuntime.service;
                require((boolean) field(service, "finishing"), "cleanup owner not marked finishing");
                context.startForegroundService(start);
                await(() -> (boolean) field(service, "restartRequested"), "retry was not queued");
                LocalLinuxRuntime.releaseCleanup.countDown();
                await(() -> LocalLinuxRuntime.created == 2 && field(service, "backend") instanceof Process
                        && ((Process) field(service, "backend")).isAlive(), "retry backend did not start");
                require(LocalLinuxRuntime.service == service, "unexpected service replacement");
                require(!(boolean) field(service, "destroyed"), "old cleanup destroyed retry service");
                require(!((ScheduledExecutorService) field(service, "sessionMonitor")).isShutdown(), "retry monitor shut down");
                require(((PowerManager.WakeLock) field(service, "runtimeLock")).isHeld(), "retry lost CPU lock");
                require(context.getSharedPreferences("runtime", 0).getBoolean("wanted", false), "retry intent lost");
                Process child = (Process) field(service, "backend");
                context.startService(stop);
                await(() -> (boolean) field(service, "destroyed"), "STOP did not destroy service");
                require(!child.isAlive(), "test child survived STOP");
                require(!((PowerManager.WakeLock) field(service, "runtimeLock")).isHeld(), "STOP leaked CPU lock");
                require(!context.getSharedPreferences("runtime", 0).getBoolean("wanted", true), "STOP intent lost");
                report.append("round=").append(round).append(" PASS cleanup retry, monitor, wakelock, explicit STOP and child exit\n");
            }
            passed = true;
        } catch (Throwable error) { report.append("FAIL ").append(error).append('\n'); }
        finally {
            LocalLinuxRuntime.releaseCleanup.countDown();
            context.stopService(start);
            for (Process child : LocalLinuxRuntime.children) child.destroyForcibly();
        }
        Bundle results = new Bundle();
        results.putString("stream", report + (passed ? "PASS: Android runtime-service lifecycle; sleep-backed test runtime, no PRoot/agent claim\n" : ""));
        finish(passed ? Activity.RESULT_OK : Activity.RESULT_CANCELED, results);
    }
}

final class LocalLinuxRuntime {
    static volatile RuntimeSetupService service;
    static volatile int created;
    static CountDownLatch atCleanup = new CountDownLatch(1), releaseCleanup = new CountDownLatch(1);
    static final java.util.List<Process> children = new java.util.concurrent.CopyOnWriteArrayList<>();
    final int number;
    private volatile Process child;
    private volatile boolean cancelled;
    LocalLinuxRuntime(Context context) { service = (RuntimeSetupService) context; number = ++created; }
    void prepare(Consumer<String> progress, BiConsumer<String, Integer> measured) throws Exception {
        if (cancelled) throw new InterruptedException();
    }
    Process startBackend() throws Exception {
        if (cancelled) throw new InterruptedException();
        child = new ProcessBuilder("/system/bin/sleep", number == 1 ? "0.1" : "30").start();
        children.add(child); return child;
    }
    void cancel() {
        cancelled = true;
        if (child != null) child.destroy();
        if (number == 1 && Looper.myLooper() != Looper.getMainLooper()) {
            atCleanup.countDown();
            try { if (!releaseCleanup.await(10, TimeUnit.SECONDS)) throw new IllegalStateException("cleanup gate timeout"); }
            catch (InterruptedException error) { Thread.currentThread().interrupt(); }
        }
    }
    void stop(Process child) { child.destroy(); }
    void forget(Process child) {}
    void awaitBackend(Process child) {}
    void refreshDns() {}
    void recordPackageSocket(String value) {}
    void recordAndroidTool(String value) {}
    String[] sessionNotification() { return new String[] {"Runtime audit", "Isolated test"}; }
}

final class AndroidDiagnosticsBridge {
    AndroidDiagnosticsBridge(Context context) {}
    static String socketName() { return "unused-runtime-audit"; }
    void close() {}
}
