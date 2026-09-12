package io.github.gplaider.tinyagent;

import android.app.*;
import android.content.Intent;
import android.os.*;
import java.util.concurrent.*;

/** User-started pairing notification, independent of the Fedora runtime. */
public final class WirelessPairingService extends Service {
    static final String PAIR = "io.github.gplaider.tinyagent.PAIR_WIRELESS";
    static final String CONNECT = "io.github.gplaider.tinyagent.CONNECT_WIRELESS";
    private final ExecutorService worker = Executors.newSingleThreadExecutor();
    private final Handler expiry = new Handler(Looper.getMainLooper());
    private volatile boolean busy;
    private volatile WirelessAdb pairing;
    private volatile SelfAdbClient verification;
    @Override public IBinder onBind(Intent intent) { return null; }
    @Override public int onStartCommand(Intent intent,int flags,int startId) {
        var manager = getSystemService(NotificationManager.class);
        manager.createNotificationChannel(new NotificationChannel("wireless-pairing","무선 ADB 페어링",NotificationManager.IMPORTANCE_DEFAULT));
        var input = new RemoteInput.Builder("code").setLabel("페어링 코드 6자리").build();
        var reply = PendingIntent.getService(this,2,new Intent(this,WirelessPairingService.class).setAction(PAIR),PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_MUTABLE);
        var open = PendingIntent.getActivity(this,3,new Intent(this,DeveloperActivity.class),PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        var stop = PendingIntent.getService(this,4,new Intent(this,WirelessPairingService.class).setAction("stop"),PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        startForeground(2,new Notification.Builder(this,"wireless-pairing").setSmallIcon(android.R.drawable.stat_sys_data_bluetooth)
                .setContentTitle("TinyAgent · 페어링 코드 입력").setContentText("Android 페어링 창을 유지한 채 코드 6자리를 입력하세요.")
                .setContentIntent(open).setOngoing(true)
                .addAction(new Notification.Action.Builder(null,"코드 입력",reply).addRemoteInput(input).build())
                .addAction(new Notification.Action.Builder(null,"중단",stop).build()).build());
        if (intent != null && "stop".equals(intent.getAction())) { stopSelf(); return START_NOT_STICKY; }
        expiry.removeCallbacksAndMessages(null); expiry.postDelayed(this::stopSelf,10*60*1000L);
        if (intent == null || intent.getAction() == null) { save("Android 설정에서 페어링 창을 열고 TinyAgent 알림에 코드를 입력하세요."); return START_NOT_STICKY; }
        if (busy) return START_NOT_STICKY;
        boolean shouldPair = PAIR.equals(intent.getAction());
        var result = RemoteInput.getResultsFromIntent(intent);
        String code = result != null ? String.valueOf(result.getCharSequence("code","")) : intent.getStringExtra("code");
        if (shouldPair && (code == null || !code.matches("[0-9]{6}"))) { save("코드는 6자리 숫자입니다. 알림에서 다시 입력하세요."); return START_NOT_STICKY; }
        busy = true;
        worker.submit(() -> {
            try {
                if (shouldPair) {
                    save("이 폰의 페어링 서비스 찾는 중…");
                    try (var client = new WirelessAdb(this)) { pairing = client; client.pairLocal(code); }
                    finally { pairing = null; }
                }
                getSharedPreferences("connection",0).edit().putString("transport","wireless").remove("rootAllowed").putBoolean("rootAvailable",false).apply();
                save("무선 ADB 연결과 자기 기기 UID 확인 중…");
                try (var client = new SelfAdbClient(this)) {
                    verification = client;
                    var proof = client.inspect(0,false);
                    if (!proof.verifiedSelf) throw new java.io.IOException("shell UID 2000을 확인하지 못했습니다.");
                    save("✓ Developer 확인 완료 · shell UID 2000\n기기: " + Build.MODEL + "\n연결: local wireless debugging\n작업마다 연결·권한을 다시 확인합니다.");
                } finally { verification = null; }
            } catch (Exception error) {
                save("Developer 연결 실패 · " + error.getClass().getSimpleName() + "\n페어링 창과 Wi-Fi를 확인하세요. 코드가 만료됐으면 새 코드로 다시 시도하세요. Stock은 계속 사용할 수 있습니다.");
            } finally { busy = false; stopSelf(); }
        });
        return START_NOT_STICKY;
    }
    private void save(String status) { getSharedPreferences("connection",0).edit().putString("wirelessStatus",status).apply(); }
    @Override public void onDestroy() {
        expiry.removeCallbacksAndMessages(null);
        if (verification != null) verification.close();
        if (pairing != null) try { pairing.close(); } catch (Exception ignored) { }
        worker.shutdownNow(); stopForeground(STOP_FOREGROUND_REMOVE); super.onDestroy();
    }
}
