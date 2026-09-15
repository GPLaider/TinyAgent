package io.github.gplaider.tinyagent;

import android.content.*;
import java.io.File;

/** Restarts an installed runtime after this package is replaced. */
public final class RuntimeResumeReceiver extends BroadcastReceiver {
    @Override public void onReceive(Context context, Intent intent) {
        if (!Intent.ACTION_MY_PACKAGE_REPLACED.equals(intent.getAction())) return;
        var prefs = context.getSharedPreferences("runtime", Context.MODE_PRIVATE);
        Boolean wanted = prefs.contains("wanted") ? prefs.getBoolean("wanted", false) : null;
        if (!LocalPolicy.resumeRuntime(new File(context.getFilesDir(), "linux/prepared-v1").isFile(),
                wanted, prefs.getString("status", ""))) return;
        try {
            context.startForegroundService(new Intent(context, RuntimeSetupService.class));
        } catch (RuntimeException error) {
            prefs.edit().putString("status", "환경 자동 재개 실패: " + error.getClass().getSimpleName()).apply();
        }
    }
}
