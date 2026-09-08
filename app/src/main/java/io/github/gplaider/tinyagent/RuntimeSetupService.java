package io.github.gplaider.tinyagent;

import android.app.*;
import android.content.Intent;
import android.net.*;
import android.os.IBinder;
import java.util.concurrent.*;

/** Owns the ordinary-UID Linux backend while the user keeps the runtime running. */
public final class RuntimeSetupService extends Service {
    public static final String STOP = "io.github.gplaider.tinyagent.STOP_BACKEND";
    private final ExecutorService worker = Executors.newSingleThreadExecutor();
    private volatile Process backend;
    private volatile LocalLinuxRuntime runtime;
    private volatile AndroidDiagnosticsBridge androidBridge;
    private volatile boolean running, stopping;
    private ConnectivityManager.NetworkCallback networkCallback;
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
        if (running) return START_NOT_STICKY;
        getSharedPreferences("runtime", MODE_PRIVATE).edit().putBoolean("wanted", true).apply();
        running = true; stopping = false;
        save("로컬 실행 환경 다시 연결 중…");
        var notifications = getSystemService(NotificationManager.class);
        notifications.createNotificationChannel(new NotificationChannel("runtime-setup", "로컬 실행 환경", NotificationManager.IMPORTANCE_LOW));
        var open = PendingIntent.getActivity(this, 0, new Intent(this, AppActivity.class), PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT);
        var stop = PendingIntent.getService(this, 1, new Intent(this, RuntimeSetupService.class).setAction(STOP), PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT);
        startForeground(1, new Notification.Builder(this, "runtime-setup").setSmallIcon(android.R.drawable.stat_sys_download)
                .setContentTitle("TinyAgent · 이 폰에서 실행 중").setContentText("앱 권한으로 Fedora와 에이전트를 실행합니다.")
                .setContentIntent(open).setOngoing(true).addAction(new Notification.Action.Builder(null, "중단", stop).build()).build());
        worker.submit(() -> {
            try {
                runtime = new LocalLinuxRuntime(this);
                runtime.prepare(this::save);
                if (stopping) return;
                try {
                    androidBridge = new AndroidDiagnosticsBridge(this);
                    String prefix = "curl --fail-with-body --silent --show-error --max-time 90 --abstract-unix-socket " + AndroidDiagnosticsBridge.socketName();
                    runtime.recordAndroidTool("# Live Android diagnostic tool\n\nKernel peer UID must equal the TinyAgent app UID. This tool performs read-only inspection.\n"
                            + "\nStock: `" + prefix + " http://localhost/inspect/stock`\n"
                            + "Developer: `" + prefix + " http://localhost/inspect/developer` (requires authorized self-ADB UID 2000).\n"
                            + "Root: `" + prefix + " http://localhost/inspect/root` (requires the user's Root option and verified self-ADB UID 0).\n"
                            + "A failed optional ADB probe does not stop Fedora work. Do not claim arbitrary Android command execution is available.\n"
                            + "Save returned JSON under /shared or the session workspace to process it in Fedora. Each request remeasures identity and authority.\n");
                } catch (Exception error) {
                    if (androidBridge != null) androidBridge.close();
                    androidBridge = null;
                    runtime.recordAndroidTool("Android diagnostic bridge unavailable: " + error.getClass().getSimpleName() + ". Fedora remains available.\n");
                }
                if (stopping) return;
                backend = runtime.startBackend();
                runtime.awaitBackend(backend);
                networkCallback = new ConnectivityManager.NetworkCallback() {
                    @Override public void onLinkPropertiesChanged(Network network, LinkProperties properties) {
                        try { runtime.refreshDns(); } catch (Exception error) { save("네트워크 변경 확인 필요: " + error.getMessage()); }
                    }
                };
                getSystemService(ConnectivityManager.class).registerDefaultNetworkCallback(networkCallback);
                save(LocalPolicy.RUNTIME_READY);
                int code = backend.waitFor();
                save(stopping ? "로컬 백엔드를 중단했습니다. 다시 준비하면 작업을 이어갑니다." : "환경 준비 실패: 백엔드 종료 exit=" + code + " · linux/backend.log 확인");
            } catch (Exception error) { save("환경 준비 실패: " + error.getClass().getSimpleName() + ": " + error.getMessage()); }
            finally {
                if (androidBridge != null) { androidBridge.close(); androidBridge = null; }
                if (backend != null && runtime != null) { runtime.stop(backend); runtime.forget(backend); }
                if (networkCallback != null) { getSystemService(ConnectivityManager.class).unregisterNetworkCallback(networkCallback); networkCallback = null; }
                backend = null; running = false;
                stopForeground(STOP_FOREGROUND_REMOVE); stopSelf();
            }
        });
        return START_NOT_STICKY;
    }
    private void save(String status) { getSharedPreferences("runtime", MODE_PRIVATE).edit().putString("status", status).putLong("updated", System.currentTimeMillis()).apply(); }
    @Override public void onDestroy() {
        stopping = true;
        if (androidBridge != null) androidBridge.close();
        if (runtime != null) runtime.cancel();
        if (backend != null && runtime != null) runtime.stop(backend);
        worker.shutdownNow(); super.onDestroy();
    }
}
