package io.github.gplaider.tinyagent;

import android.content.*;
import java.io.File;

/** Compile-only install dependencies: export probes must never execute them. */
final class SelfAdbClient implements AutoCloseable {
    SelfAdbClient(Context context){throw new AssertionError("Installation is outside the export probe");}
    void inspect(int port,boolean root){throw new AssertionError();}
    void install(File file,boolean root){throw new AssertionError();}
    public void close(){}
}
final class WirelessAdb { static String transport(Context context){return "stock";} }
final class InstallResultReceiver extends BroadcastReceiver {
    public void onReceive(Context context,Intent intent){throw new AssertionError("Unexpected install callback");}
}
final class R { static final class style { static final int ArtifactPopup=android.R.style.Theme_Material_Light_Dialog_Alert; } }
