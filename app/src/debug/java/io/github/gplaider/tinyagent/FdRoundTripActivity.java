package io.github.gplaider.tinyagent;

import android.app.Activity;
import android.net.LocalServerSocket;
import android.net.LocalSocket;
import android.os.Bundle;
import android.os.Process;
import android.widget.TextView;
import java.io.File;
import java.io.FileDescriptor;
import java.io.RandomAccessFile;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.Arrays;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;

/** Debug-only fixed Java -> PRoot -> Java file consumption check. */
public final class FdRoundTripActivity extends Activity {
    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        TextView view = new TextView(this);
        view.setText("Java → Fedora FD 왕복 검증 중");
        setContentView(view);
        new Thread(() -> {
            String result;
            try { result = getIntent().getBooleanExtra("seed", false) ? seed() : check(); }
            catch (Exception error) { result = "FAIL: " + error; }
            try { Files.write(new File(getFilesDir(), "fd-roundtrip.log").toPath(), result.getBytes(StandardCharsets.UTF_8)); }
            catch (Exception error) { result += "\nReport write failed: " + error; }
            String text = result;
            runOnUiThread(() -> view.setText(text));
        }, "fd-roundtrip").start();
    }

    private String seed() throws Exception {
        LocalLinuxRuntime runtime = new LocalLinuxRuntime(this);
        boolean loader = getIntent().getBooleanExtra("loader", false);
        boolean anonymous = getIntent().getBooleanExtra("anonymous", false);
        String libs = "/workspace/tinyagent-package-bench-20260909/fixed-4717e11-direct/dnfast/lib";
        ProcessBuilder builder = runtime.guest("/workspace");
        var args = new ArrayList<>(List.of(getApplicationInfo().nativeLibraryDir + "/libfdgate.so",
                anonymous ? "seed-app-anon-v1" : "seed", runtime.rootfs.toString(), Integer.toString(Process.myUid()), loader ? "loader" : "direct",
                "/workspace/fd-app-anon-linux", loader ? libs + "/ld-linux-aarch64.so.1" : "-",
                loader ? libs : "-", "--"));
        args.addAll(builder.command());
        File log = new File(getFilesDir(), "fd-seed-" + (loader ? "loader" : "direct") + ".log");
        builder.command(args).redirectOutput(log);
        java.lang.Process running = launch(runtime, builder);
        if (!running.waitFor(30, TimeUnit.SECONDS)) {
            running.destroyForcibly();
            throw new IllegalStateException("Seed timed out");
        }
        return "seed_exit=" + running.exitValue() + "\n" + new String(Files.readAllBytes(log.toPath()), StandardCharsets.UTF_8);
    }

    private java.lang.Process launch(LocalLinuxRuntime runtime, ProcessBuilder builder) throws Exception {
        File pid = File.createTempFile("fd-probe-", ".pid", runtime.base);
        var args = new ArrayList<>(List.of("/system/bin/sh", new File(runtime.base, "launch.sh").toString(), pid.toString()));
        args.addAll(builder.command());
        return builder.command(args).start();
    }

    private String check() throws Exception {
        LocalLinuxRuntime runtime = new LocalLinuxRuntime(this);
        File directory = Files.createTempDirectory(runtime.workspace.toPath(), "fd-roundtrip-").toFile();
        File payload = new File(directory, "payload");
        // Abstract namespace avoids sockaddr_un's 108-byte filesystem-path limit.
        String socketName = "tinyagent-fd-" + Process.myPid() + "-" + System.nanoTime();
        byte[] before = "tinyagent-before".getBytes(StandardCharsets.US_ASCII);
        byte[] after = "tinyagent-after!".getBytes(StandardCharsets.US_ASCII);
        var timeout = Executors.newSingleThreadScheduledExecutor();
        java.lang.Process child = null;
        try (RandomAccessFile file = new RandomAccessFile(payload, "rw");
             LocalServerSocket server = new LocalServerSocket(socketName)) {
            file.write(before);
            file.getFD().sync();
            timeout.schedule(() -> { try { server.close(); } catch (Exception ignored) {} }, 30, TimeUnit.SECONDS);
            child = launch(runtime, runtime.guest("/workspace", "/workspace/fd-roundtrip-linux", "@" + socketName)
                    .redirectOutput(new File(directory, "guest.log")));
            java.lang.Process running = child;
            timeout.schedule(running::destroyForcibly, 30, TimeUnit.SECONDS);
            try (LocalSocket peer = server.accept()) {
                peer.setSoTimeout(20000);
                if (peer.getPeerCredentials().getUid() != Process.myUid())
                    throw new IllegalStateException("Peer UID differs");
                peer.setFileDescriptorsForSend(new FileDescriptor[]{file.getFD()});
                peer.getOutputStream().write('F');
                peer.setFileDescriptorsForSend(null);
                if (peer.getInputStream().read() != 'K') throw new IllegalStateException("Guest acknowledgement missing");
            }
            if (!child.waitFor(20, TimeUnit.SECONDS) || child.exitValue() != 0)
                throw new IllegalStateException("Guest failed or timed out");
            byte[] actual = new byte[16];
            file.seek(0);
            file.readFully(actual);
            if (!Arrays.equals(actual, after) || !Arrays.equals(Files.readAllBytes(payload.toPath()), after))
                throw new IllegalStateException("Android readback differs");
            return "PASS: Java-opened FD read/written/fsynced by Fedora; Android retained FD and reopened path match.\n"
                    + "actual_uid=" + Process.myUid() + "\ncontext="
                    + new String(Files.readAllBytes(new File("/proc/self/attr/current").toPath()), StandardCharsets.UTF_8).trim() + "\n"
                    + new String(Files.readAllBytes(new File(directory, "guest.log").toPath()), StandardCharsets.UTF_8);
        } finally {
            if (child != null && child.isAlive()) child.destroyForcibly();
            timeout.shutdownNow();
            // Keep this small per-run directory as evidence; never touch user workspaces.
        }
    }
}
