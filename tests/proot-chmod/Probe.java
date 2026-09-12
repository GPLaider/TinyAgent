package io.github.gplaider.tinyagent.chmodprobe;
import android.app.Activity;
import android.os.Bundle;
import android.widget.TextView;
import java.nio.file.*;
import java.util.concurrent.TimeUnit;
import java.util.zip.ZipInputStream;

public final class Probe extends Activity {
    private TextView view;
    private String report = "";
    private void log(String text) throws Exception {
        report += text + "\n";
        Files.writeString(getFilesDir().toPath().resolve("result.txt"), report);
        runOnUiThread(() -> view.setText(report));
    }
    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        view = new TextView(this); view.setTextSize(16); setContentView(view);
        new Thread(() -> {
            try {
                if (android.os.Process.myUid() < 10000) throw new Exception("App UID required");
                log("Android UID=" + android.os.Process.myUid());
                String lib = getApplicationInfo().nativeLibraryDir;
                for (String kind : new String[]{"baseline", "candidate"}) {
                    Path dir = Files.createTempDirectory(getFilesDir().toPath(), kind);
                    ProcessBuilder builder = new ProcessBuilder(lib + "/libproot_" + kind + ".so", "-0", "-l", "--kill-on-exit",
                        "-b", dir + ":/probe", "-w", "/probe", lib + "/libchmodprobe.so", kind);
                    builder.environment().put("PROOT_NO_SECCOMP", "1");
                    builder.environment().put("PROOT_LOADER", lib + "/libproot_loader.so");
                    builder.environment().put("LD_LIBRARY_PATH", lib);
                    builder.environment().put("PROOT_TMP_DIR", dir.toString());
                    builder.redirectErrorStream(true).redirectOutput(dir.resolve("output.txt").toFile());
                    Process process = builder.start();
                    if (!process.waitFor(20, TimeUnit.SECONDS)) {
                        process.destroyForcibly();
                        process.waitFor(5, TimeUnit.SECONDS);
                        throw new Exception("Owned probe timeout " + kind);
                    }
                    log(kind + " exit=" + process.exitValue() + "\n" + Files.readString(dir.resolve("output.txt")));
                    if (process.exitValue() != 0) throw new Exception("Probe failed " + kind);
                }
                Path guest = Files.createTempDirectory(getFilesDir().toPath(), "tar-root-");
                try (ZipInputStream zip = new ZipInputStream(getAssets().open("fedora-tar-root.zip"))) {
                    java.util.zip.ZipEntry entry;
                    while ((entry = zip.getNextEntry()) != null) {
                        Path file = guest.resolve(entry.getName()).normalize();
                        if (!file.startsWith(guest)) throw new Exception("Unsafe test payload");
                        Files.createDirectories(file.getParent());
                        Files.copy(zip, file);
                        file.toFile().setExecutable(true, true);
                    }
                }
                Files.createDirectories(guest.resolve("tmp"));
                for (String kind : new String[]{"baseline", "candidate"}) {
                    Path dir = Files.createTempDirectory(getFilesDir().toPath(), "tar-" + kind);
                    Files.createDirectories(dir.resolve("extract"));
                    ProcessBuilder builder = new ProcessBuilder(lib + "/libproot_" + kind + ".so", "-0", "-l", "--kill-on-exit",
                        "-r", guest.toString(), "-b", "/dev", "-b", "/proc", "-b", dir + ":/tmp", "-w", "/tmp/extract",
                        "/usr/bin/tar", "-xf", "/fixture.tar");
                    builder.environment().put("PROOT_NO_SECCOMP", "1");
                    builder.environment().put("PROOT_LOADER", lib + "/libproot_loader.so");
                    builder.environment().put("LD_LIBRARY_PATH", lib);
                    builder.environment().put("PROOT_TMP_DIR", dir.toString());
                    builder.redirectErrorStream(true).redirectOutput(dir.resolve("output.txt").toFile());
                    Process process = builder.start();
                    if (!process.waitFor(20, TimeUnit.SECONDS)) {
                        process.destroyForcibly();
                        process.waitFor(5, TimeUnit.SECONDS);
                        throw new Exception("Tar probe timeout");
                    }
                    String output = Files.readString(dir.resolve("output.txt"));
                    log("tar " + kind + " exit=" + process.exitValue() + "\n" + output);
                    if (kind.equals("candidate")) {
                        if (process.exitValue() != 0 || !Files.readString(dir.resolve("extract/cargo-1.85.0-aarch64-unknown-linux-gnu/components")).equals("cargo\n"))
                            throw new Exception("Candidate tar extraction failed");
                    } else if (process.exitValue() != 2 || !output.contains("Cannot change mode")) {
                        throw new Exception("Expected baseline tar failure missing");
                    }
                }
                log("PASS Fedora tar before/after");
                Path stop = Files.createTempDirectory(getFilesDir().toPath(), "stop-");
                ProcessBuilder stopped = new ProcessBuilder(lib + "/libproot_candidate.so", "-0", "-l", "--kill-on-exit",
                    "-b", stop + ":/probe", "-w", "/probe", lib + "/libchmodprobe.so", "heartbeat");
                stopped.environment().put("PROOT_NO_SECCOMP", "1");
                stopped.environment().put("PROOT_LOADER", lib + "/libproot_loader.so");
                stopped.environment().put("LD_LIBRARY_PATH", lib);
                stopped.environment().put("PROOT_TMP_DIR", stop.toString());
                stopped.redirectErrorStream(true).redirectOutput(stop.resolve("output.txt").toFile());
                Process tracer = stopped.start();
                try {
                    Path heartbeat = stop.resolve("heartbeat");
                    for (int i = 0; i < 50 && !Files.exists(heartbeat); i++) Thread.sleep(100);
                    String first = Files.readString(heartbeat);
                    Thread.sleep(500);
                    if (first.equals(Files.readString(heartbeat))) throw new Exception("Tracee not advancing");
                    int pid = Integer.parseInt(Files.readString(stop.resolve("tracer.pid")).trim());
                    if (pid <= 1 || android.system.Os.stat("/proc/" + pid).st_uid != android.os.Process.myUid())
                        throw new Exception("Owned tracer UID mismatch");
                    log("candidate tracer pid=" + pid);
                    android.system.Os.kill(pid, android.system.OsConstants.SIGKILL);
                    if (!tracer.waitFor(5, TimeUnit.SECONDS)) throw new Exception("Tracer did not stop");
                    Thread.sleep(300);
                    String last = Files.readString(heartbeat);
                    Thread.sleep(1000);
                    if (!last.equals(Files.readString(heartbeat))) throw new Exception("Tracee survived parent death");
                    log("PASS candidate parent death stops heartbeat");
                } finally {
                    if (tracer.isAlive()) tracer.destroyForcibly();
                }
                log("PASS both app-UID checks");
            } catch (Exception error) { try { log("FAIL " + error); } catch (Exception ignored) {} }
        }, "chmod-probe").start();
    }
}
