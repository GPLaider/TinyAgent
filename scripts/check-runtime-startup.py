"""Exercise production startup ownership with real host children, without an Android device.

Extract the unchanged start/cancel/forget methods; adapt the shell path and
SIGKILL constant to the host. stop/signal are host doubles; no PRoot death claim.
Requires Java 17 on PATH. Temporary files and children belong to this test.
"""
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
JAVA = ROOT / "app/src/main/java/io/github/gplaider/tinyagent"
source = (JAVA / "LocalLinuxRuntime.java").read_text()
start = source[source.index("    synchronized Process start("):source.index("    void stop(Process")]
forget = source[source.index("    void forget(Process"):source.index("    private static String readText(")]
start = start.replace('"/system/bin/sh"', '"/bin/sh"')
start = start.replace('android.system.OsConstants.SIGKILL', '9')
fixture = r'''
import java.io.*;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.*;

public class StartupCheck {
    final File base;
    final Map<Process, File> pids = new ConcurrentHashMap<>();
    boolean cancelled;
    StartupCheck(Path base) { this.base = base.toFile(); }
    void stop(Process process) { process.destroyForcibly(); }
    void signal(Process process, int signal) {
        if (signal != 9) throw new AssertionError("Expected force-stop signal");
        process.destroyForcibly();
    }
    void script(String text) throws Exception { Files.writeString(base.toPath().resolve("launch.sh"), text); }
    void empty() throws Exception {
        if (!pids.isEmpty()) throw new AssertionError("Failed start retained process ownership");
        try (var files = Files.list(base.toPath())) {
            if (files.anyMatch(p -> p.getFileName().toString().endsWith(".pid")))
                throw new AssertionError("Failed start retained PID record");
        }
    }
    public static void main(String[] args) throws Exception {
        Path directory = Path.of(args[0]);
        StartupCheck runtime = new StartupCheck(directory);
        try {
        runtime.script("printf '%s\\n' \"$$\" > \"$1\"\nshift\nexec \"$@\"\n");
        Process normal = runtime.start(new ProcessBuilder("/bin/sh", "-c", "exit 7"));
        if (normal.waitFor() != 7) throw new AssertionError("Normal exit changed");
        runtime.forget(normal); runtime.empty();

        // Hold the launcher before its handshake without spawning grandchildren.
        runtime.script("while :; do :; done\n");
        AtomicReference<Throwable> failure = new AtomicReference<>();
        Thread starter = new Thread(() -> {
            try { runtime.start(new ProcessBuilder("unused")); }
            catch (Throwable error) { failure.set(error); }
        });
        starter.start();
        long deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(3);
        while (runtime.pids.isEmpty() && System.nanoTime() < deadline) Thread.sleep(1);
        Process interrupted = runtime.pids.keySet().stream().findFirst().orElseThrow();
        starter.interrupt(); starter.join(7000);
        if (starter.isAlive() || !(failure.get() instanceof InterruptedException) || interrupted.isAlive())
            throw new AssertionError("Interrupted start leaked its actual child", failure.get());
        runtime.empty();

        AtomicReference<Process> timedOut = new AtomicReference<>();
        Thread observer = new Thread(() -> {
            long until = System.nanoTime() + TimeUnit.SECONDS.toNanos(3);
            while (System.nanoTime() < until) {
                for (Process process : runtime.pids.keySet()) { timedOut.set(process); return; }
                Thread.yield();
            }
        });
        observer.start();
        try { runtime.start(new ProcessBuilder("unused")); throw new AssertionError("Missing handshake accepted"); }
        catch (IOException expected) { }
        observer.join(4000);
        if (timedOut.get() == null || timedOut.get().isAlive()) throw new AssertionError("Handshake timeout leaked child");
        runtime.empty();

        // ProcessBuilder.start failure must remove the pre-created record.
        try {
            runtime.start(new ProcessBuilder("unused").directory(directory.resolve("missing").toFile()));
            throw new AssertionError("Invalid cwd accepted");
        } catch (IOException expected) { }
        runtime.empty();
        runtime.cancel();
        try { runtime.start(new ProcessBuilder("unused")); throw new AssertionError("Cancelled runtime started"); }
        catch (InterruptedException expected) { }
        runtime.empty();
        System.out.println("PASS: exit status, startup interrupt, missing handshake, launch failure, cancelled launch; no owned child/PID leaks");
        } finally {
            for (Process process : runtime.pids.keySet()) {
                process.destroyForcibly();
                process.waitFor(5, TimeUnit.SECONDS);
            }
        }
    }
'''

with tempfile.TemporaryDirectory(prefix="tinyagent-startup-") as directory:
    temp = Path(directory)
    java = temp / "StartupCheck.java"
    java.write_text(fixture + start + forget + "}\n")
    subprocess.run(["javac", "-encoding", "UTF-8", str(java)], check=True)
    subprocess.run(["java", "-cp", directory, "StartupCheck", directory], check=True, timeout=25)

# The Android service publishes ownership before queuing any work. STOP thus
# cancels the same runtime even before prepare starts, which rejects cancellation.
service = (JAVA / "RuntimeSetupService.java").read_text()
assert service.index("runtime = new LocalLinuxRuntime(this);") < service.index("worker.submit(() ->")
prepare = source[source.index("    void prepare("):source.index("        this.measured = reporter;")]
assert "if (cancelled) throw new InterruptedException" in prepare
print("PASS: service publishes runtime before dispatch and prepare rejects pre-start cancellation (source invariant)")
