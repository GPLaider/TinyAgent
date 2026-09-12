package io.github.gplaider.tinyagent;

import android.app.*;
import android.content.Intent;
import android.net.*;
import android.os.IBinder;
import java.util.concurrent.*;

/** Owns the ordinary-UID Linux backend while the user keeps the runtime running. */
public final class RuntimeSetupService extends Service {
    static volatile boolean preparing;
    public static final String STOP = "io.github.gplaider.tinyagent.STOP_BACKEND";
    private final ExecutorService worker = Executors.newSingleThreadExecutor();
    private final ScheduledExecutorService sessionMonitor = Executors.newSingleThreadScheduledExecutor();
    private String sessionTitle = "TinyAgent · 작업 대기", sessionDetail = "세션 상태 확인 중…";
    private volatile Process backend;
    private volatile LocalLinuxRuntime runtime;
    private volatile AndroidDiagnosticsBridge androidBridge;
    private volatile boolean running, stopping;
    private ConnectivityManager.NetworkCallback networkCallback;
    private android.os.PowerManager.WakeLock runtimeLock;
    private NotificationManager notifications;
    private PendingIntent open, stop, retry;
    private long started, lastProgress;
    private String latest = "환경 준비 시작 중…";
    private int percent = -1;
    private final android.os.Handler timer = new android.os.Handler(android.os.Looper.getMainLooper());
    private final Runnable tick = new Runnable() {
        public void run() {
            if (!preparing) return;
            publish();
            timer.postDelayed(this, 1000);
        }
    };
    @Override public IBinder onBind(Intent intent) { return null; }
    @Override public int onStartCommand(Intent intent, int flags, int startId) {
        if (intent != null && STOP.equals(intent.getAction())) {
            getSharedPreferences("runtime", MODE_PRIVATE).edit().putBoolean("wanted", false).apply();
            stopping = true;
            if (androidBridge != null) androidBridge.close();
            save("로컬 백엔드 중단 중…");
            if (runtime != null) runtime.cancel();
            if (backend != null && runtime != null) runtime.stop(backend);
            if (!running) stopSelf();
            return START_NOT_STICKY;
        }
        if (running) {
            getSharedPreferences("runtime", MODE_PRIVATE).edit().putLong("updated", System.currentTimeMillis()).apply();
            return START_NOT_STICKY;
        }
        getSharedPreferences("runtime", MODE_PRIVATE).edit().putBoolean("wanted", true).apply();
        running = true; stopping = false; preparing = true;
        started = android.os.SystemClock.elapsedRealtime();
        notifications = getSystemService(NotificationManager.class);
        notifications.createNotificationChannel(new NotificationChannel("runtime-setup", "로컬 실행 환경", NotificationManager.IMPORTANCE_LOW));
        open = PendingIntent.getActivity(this, 0, new Intent(this, AppActivity.class), PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT);
        stop = PendingIntent.getService(this, 1, new Intent(this, RuntimeSetupService.class).setAction(STOP), PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT);
        retry = PendingIntent.getForegroundService(this, 2, new Intent(this, RuntimeSetupService.class), PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT);
        startForeground(1, notification());
        save("로컬 실행 환경 다시 연결 중…");
        timer.post(tick);
        worker.submit(() -> {
            try {
                acquireRuntimeLock();
                getSharedPreferences("runtime", MODE_PRIVATE).edit().putString("previousProcessExit",
                        previousExit(getSystemService(ActivityManager.class), getPackageName())).apply();
                runtime = new LocalLinuxRuntime(this);
                runtime.prepare(this::save, this::saveProgress);
                if (stopping) return;
                try {
                    androidBridge = new AndroidDiagnosticsBridge(this);
                    runtime.recordPackageSocket(AndroidDiagnosticsBridge.socketName());
                    String prefix = "curl --fail-with-body --silent --show-error --max-time 90 --abstract-unix-socket " + AndroidDiagnosticsBridge.socketName();
                    runtime.recordAndroidTool("# Live Android tool\n\nKernel peer UID must equal the TinyAgent app UID. Inspection is read-only; authorized jobs use the same verified self-ADB transport.\n"
                            + "\nStock: `" + prefix + " http://localhost/inspect/stock`\n"
                            + "Developer: `" + prefix + " http://localhost/inspect/developer` (requires authorized self-ADB UID 2000).\n"
                            + "Root: `" + prefix + " http://localhost/inspect/root` (automatically discovers the endpoint and verifies self-ADB UID 0; no Root toggle).\n"
                            + "Android commands: `python3 /root/.tinyagent/bootstrap/tinyagent-android.py --mode developer --cwd / shell 'id'`. Use --mode root only for authorized Root work.\n"
                            + "APK installation: same client, `--mode developer install 'project/app.apk'`, path relative to /workspace. No Fedora adb server is needed.\n"
                            + "Retain the printed UUID. `--id UUID status` rechecks interrupted jobs; `--id UUID cancel` terminates the verified process group. Unknown installation outcomes require checking PackageManager before retry.\n"
                            + "A failed optional ADB probe does not stop Fedora work. Stock installation uses the existing artifact action and Android user approval.\n"
                            + "Save returned JSON under /shared or the session workspace to process it in Fedora. Each request remeasures identity and authority.\n");
                } catch (Exception error) {
                    if (androidBridge != null) androidBridge.close();
                    androidBridge = null;
                    runtime.recordAndroidTool("Android diagnostic bridge unavailable: " + error.getClass().getSimpleName() + ". Fedora remains available.\n");
                }
                if (stopping) return;
                save("OpenCode 백엔드 시작·응답 확인 중…");
                backend = runtime.startBackend();
                runtime.awaitBackend(backend);
                networkCallback = new ConnectivityManager.NetworkCallback() {
                    @Override public void onLinkPropertiesChanged(Network network, LinkProperties properties) {
                        try { runtime.refreshDns(); } catch (Exception error) { save("네트워크 변경 확인 필요: " + error.getMessage()); }
                    }
                };
                getSystemService(ConnectivityManager.class).registerDefaultNetworkCallback(networkCallback);
                preparing = false;
                save(LocalPolicy.RUNTIME_READY);
                sessionMonitor.scheduleWithFixedDelay(() -> {
                    if (stopping || backend == null || !backend.isAlive()) return;
                    try {
                        String[] current = runtime.sessionNotification();
                        synchronized (this) {
                            if (stopping) return;
                            sessionTitle = current[0]; sessionDetail = current[1];
                            notifications.notify(1, notification());
                        }
                    } catch (Exception error) {
                        synchronized (this) {
                            if (stopping) return;
                            sessionDetail = "세션 상태 확인 중…";
                            notifications.notify(1, notification());
                        }
                    }
                }, 0, 3, TimeUnit.SECONDS);
                int code = backend.waitFor();
                save(stopping ? "로컬 백엔드를 중단했습니다. 다시 준비하면 작업을 이어갑니다." : "환경 준비 실패: 백엔드 종료 exit=" + code + " · linux/backend.log 확인");
            } catch (Exception error) { preparing = false; save(stopping ? "환경 준비를 중단했습니다. 다시 시도할 수 있습니다." : "환경 준비 실패: " + error.getClass().getSimpleName() + ": " + error.getMessage()); }
            finally {
                if (androidBridge != null) { androidBridge.close(); androidBridge = null; }
                if (backend != null && runtime != null) { runtime.stop(backend); runtime.forget(backend); }
                if (networkCallback != null) { getSystemService(ConnectivityManager.class).unregisterNetworkCallback(networkCallback); networkCallback = null; }
                backend = null; running = false; preparing = false;
                sessionMonitor.shutdownNow();
                releaseRuntimeLock(); timer.removeCallbacks(tick);
                getSharedPreferences("runtime", MODE_PRIVATE).edit().putLong("updated", System.currentTimeMillis()).apply();
                stopForeground(stopping ? STOP_FOREGROUND_REMOVE : STOP_FOREGROUND_DETACH); stopSelf();
            }
        });
        return START_NOT_STICKY;
    }
    static String previousExit(ActivityManager manager, String packageName) {
        try {
            ApplicationExitInfo latest = null;
            for (var entry : manager.getHistoricalProcessExitReasons(packageName, 0, 16)) {
                if (!packageName.equals(entry.getProcessName())) continue;
                int reason = entry.getReason();
                if (reason != ApplicationExitInfo.REASON_LOW_MEMORY && reason != ApplicationExitInfo.REASON_CRASH
                        && reason != ApplicationExitInfo.REASON_CRASH_NATIVE && reason != ApplicationExitInfo.REASON_ANR) continue;
                if (latest == null || entry.getTimestamp() > latest.getTimestamp()) latest = entry;
            }
            if (latest == null) return "";
            String cause = switch (latest.getReason()) {
                case ApplicationExitInfo.REASON_LOW_MEMORY -> "Android 메모리 부족";
                case ApplicationExitInfo.REASON_ANR -> "앱 응답 없음 (ANR)";
                case ApplicationExitInfo.REASON_CRASH_NATIVE -> "네이티브 프로세스 오류";
                default -> "앱 오류";
            };
            String when = java.time.Instant.ofEpochMilli(latest.getTimestamp()).atZone(java.time.ZoneId.systemDefault())
                    .format(java.time.format.DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm"));
            return "최근 비정상 앱 종료 · " + when + "\n" + cause
                    + "\n당시 작업이 중단됐을 수 있습니다. 저장된 세션과 로그를 확인한 뒤 이어가세요.";
        } catch (RuntimeException error) { return "이전 앱 종료 기록을 읽지 못했습니다."; }
    }

    private synchronized void save(String status) { latest = status; percent = -1; publish(); }
    private synchronized void saveProgress(String status, Integer value) {
        if (stopping) return;
        latest = status; percent = value;
        long now = android.os.SystemClock.elapsedRealtime();
        if (now - lastProgress >= 500 || value == 100) { lastProgress = now; publish(); }
    }
    private synchronized void publish() {
        long seconds = Math.max(0, (android.os.SystemClock.elapsedRealtime() - started) / 1000);
        String detail = latest + (percent >= 0 ? " · " + percent + "%" : "")
                + (preparing ? "\n경과 " + seconds / 60 + "분 " + seconds % 60 + "초 · 다른 앱을 사용해도 계속 준비합니다." : "");
        getSharedPreferences("runtime", MODE_PRIVATE).edit().putString("status", latest).putString("progressDetail", detail)
                .putInt("percent", percent).putLong("updated", System.currentTimeMillis()).apply();
        if (notifications != null) notifications.notify(1, notification());
    }
    private synchronized Notification notification() {
        boolean failed = latest.startsWith("환경 준비 실패");
        String detail = latest + (percent >= 0 ? " · " + percent + "%" : "");
        boolean sessions = !preparing && !failed && !stopping && running;
        if (sessions) detail = sessionDetail;
        if (detail.length() > 240) detail = detail.substring(0,240) + "… 앱에서 진단 확인";
        var builder = new Notification.Builder(this, "runtime-setup").setSmallIcon(android.R.drawable.stat_sys_download)
                .setContentTitle(preparing ? "TinyAgent · 환경 준비 중" : failed ? "TinyAgent · 준비 실패" : sessions ? sessionTitle : "TinyAgent · 로컬 환경")
                .setContentText(detail).setStyle(new Notification.BigTextStyle().bigText(detail))
                .setContentIntent(open).setOnlyAlertOnce(true).setOngoing(preparing || (!failed && !stopping))
                .setWhen(System.currentTimeMillis() - (android.os.SystemClock.elapsedRealtime() - started))
                .setUsesChronometer(preparing);
        builder.setVisibility(Notification.VISIBILITY_PRIVATE);
        if (preparing) builder.setProgress(100, Math.max(0,percent), percent < 0);
        builder.addAction(new Notification.Action.Builder(null, failed ? "다시 시도" : preparing ? "준비 중단" : "실행 환경 중단", failed ? retry : stop).build());
        if (!preparing) builder.addAction(new Notification.Action.Builder(null, "앱 열기", open).build());
        return builder.build();
    }
    private synchronized void acquireRuntimeLock() throws java.io.IOException {
        if (stopping) throw new java.io.IOException("Runtime stopped before worker start");
        runtimeLock = getSystemService(android.os.PowerManager.class).newWakeLock(android.os.PowerManager.PARTIAL_WAKE_LOCK, "TinyAgent:LocalRuntime");
        // ponytail: keep the user-enabled runtime awake; narrow to jobs when all native jobs are tracked.
        runtimeLock.acquire();
    }
    private synchronized void releaseRuntimeLock() {
        if (runtimeLock != null && runtimeLock.isHeld()) runtimeLock.release();
    }
    @Override public void onDestroy() {
        stopping = true;
        preparing = false; timer.removeCallbacks(tick); releaseRuntimeLock();
        if (androidBridge != null) androidBridge.close();
        if (runtime != null) runtime.cancel();
        if (backend != null && runtime != null) runtime.stop(backend);
        worker.shutdownNow(); super.onDestroy();
        sessionMonitor.shutdownNow();
    }
}
