package io.github.gplaider.tinyagent;

import android.content.*;
import android.content.pm.PackageInstaller;

/** The system retains this callback across activity and installer process restarts. */
public final class InstallResultReceiver extends BroadcastReceiver {
    @Override public void onReceive(Context context, Intent intent) {
        int status = intent.getIntExtra(PackageInstaller.EXTRA_STATUS, PackageInstaller.STATUS_FAILURE);
        var prefs = context.getSharedPreferences("installer", Context.MODE_PRIVATE);
        int session = intent.getIntExtra(PackageInstaller.EXTRA_SESSION_ID, -1);
        if (session != prefs.getInt("session", -2)) return;
        var edit = prefs.edit().putInt("code", status).remove("confirmation");
        if (status == PackageInstaller.STATUS_PENDING_USER_ACTION) {
            Intent confirmation = intent.getParcelableExtra(Intent.EXTRA_INTENT);
            if (confirmation != null) edit.putString("confirmation", confirmation.toUri(Intent.URI_INTENT_SCHEME));
            edit.putString("status", "Android 설치 승인 대기 · 승인 화면 열기를 누르세요.");
        } else {
            edit.putString("status", status == PackageInstaller.STATUS_SUCCESS ? "설치 완료"
                    : status == PackageInstaller.STATUS_FAILURE_ABORTED ? "설치를 취소했습니다. APK를 다시 선택해 재시도할 수 있습니다."
                    : "설치 실패 또는 취소 · code=" + status + "\n" + intent.getStringExtra(PackageInstaller.EXTRA_STATUS_MESSAGE));
        }
        edit.commit();
    }
}
