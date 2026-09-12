package io.github.gplaider.tinyagent;

import android.app.Service;
import android.content.Intent;
import android.os.IBinder;
import java.nio.file.Files;

/** Test-only remote Java owner; the instrumentation kills only this process. */
public final class CrashOwnerService extends Service {
    @Override public IBinder onBind(Intent intent) { return null; }
    @Override public int onStartCommand(Intent intent, int flags, int startId) {
        new Thread(() -> {
            try {
                LocalLinuxRuntime runtime = new LocalLinuxRuntime(this);
                runtime.start(runtime.guest("/workspace", "/usr/bin/bash", "/shared/launch.sh",
                        "/shared/remote-child.identity", "/usr/bin/sleep", "120"));
                var shared = runtime.base.toPath().resolve("shared");
                Files.writeString(shared.resolve("remote-owner.identity"), PRootLifecycleCheck.identity(android.os.Process.myPid()));
                Files.writeString(shared.resolve("remote-owner.ready"), "ready");
            } catch (Exception error) {
                try { Files.writeString(getFilesDir().toPath().resolve("linux/shared/remote-owner.error"), error.toString()); }
                catch (Exception ignored) { }
            }
        }, "audit-crash-owner").start();
        return START_NOT_STICKY;
    }
}
