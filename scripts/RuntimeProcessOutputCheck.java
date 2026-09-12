package io.github.gplaider.tinyagent;

import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.*;

public class RuntimeProcessOutputCheck {
    public static void main(String[] args) throws Exception {
        if (args.length > 0) {
            if (args[0].equals("cr-handshake")) {
                var input = new java.io.BufferedReader(new java.io.InputStreamReader(System.in, java.nio.charset.StandardCharsets.UTF_8));
                System.out.print("ready\r"); System.out.flush();
                if (!"go".equals(input.readLine())) throw new AssertionError("First acknowledgment missing");
                // Delayed LF belongs to the preceding CR; the next lone CR must
                // also be delivered before this child will produce more output.
                System.out.print("\nsecond\r"); System.out.flush();
                if (!"go".equals(input.readLine())) throw new AssertionError("Second acknowledgment missing");
                System.out.print("third");
                return;
            }
            if (args[0].equals("oversized")) {
                for (int i = 0; i < 2048; i++) System.out.print("x".repeat(1024));
                System.out.flush();
                Thread.sleep(60000);
                return;
            }
            if (args[0].equals("lines")) {
                System.out.print("한글\r\n\rsecond\nfinal");
                return;
            }
            if (args[0].equals("boundary")) {
                System.out.print("x".repeat(RuntimeProcessOutput.MAX_LINE_CHARS) + "\n");
                return;
            }
            System.out.println("한글 output"); System.out.flush();
            if (args[0].equals("wait")) Thread.sleep(60000);
            System.exit(args[0].equals("failure") ? 7 : 0);
        }
        for (String mode : List.of("success", "failure")) {
            Process child = child(mode);
            var output = new ArrayList<String>();
            int code = RuntimeProcessOutput.read(child, output::add, Process::destroy);
            if (code != (mode.equals("success") ? 0 : 7) || !output.equals(List.of("한글 output")))
                throw new AssertionError("Output or exit code changed");
        }
        Process child = child("wait");
        var stopped = new AtomicBoolean();
        try {
            RuntimeProcessOutput.read(child, line -> {throw new IllegalStateException("storage failed");},
                    process -> {stopped.set(true);process.destroy();});
            throw new AssertionError("Output failure swallowed");
        } catch (IllegalStateException expected) {
            if (!expected.getMessage().equals("storage failed") || !stopped.get() || child.isAlive())
                throw new AssertionError("Output failure left child alive", expected);
        } finally {child.destroyForcibly();}
        var lines = new ArrayList<String>();
        if (RuntimeProcessOutput.read(child("lines"), lines::add, Process::destroy) != 0
                || !lines.equals(List.of("한글", "", "second", "final")))
            throw new AssertionError("CR/LF or unterminated final line changed");
        carriageReturnHandshake();
        var boundary = new ArrayList<String>();
        RuntimeProcessOutput.read(child("boundary"), boundary::add, Process::destroy);
        if (boundary.size() != 1 || boundary.get(0).length() != RuntimeProcessOutput.MAX_LINE_CHARS)
            throw new AssertionError("Valid boundary line rejected");
        Process oversized = child("oversized");
        try {
            RuntimeProcessOutput.read(oversized, line -> {throw new AssertionError("Oversized line delivered");}, Process::destroy);
            throw new AssertionError("Unbounded output accepted");
        } catch (java.io.IOException expected) {
            if (!expected.getMessage().startsWith("Process output line exceeds") || oversized.isAlive())
                throw new AssertionError("Oversized output left child alive", expected);
        } finally {oversized.destroyForcibly();}
        System.out.println("PASS: UTF-8, exit 0/7, callback cleanup, CR/LF/EOF, live CR acknowledgment handshake, line boundary and oversized live-child cleanup");
    }
    private static void carriageReturnHandshake() throws Exception {
        Process process = child("cr-handshake");
        ExecutorService reader = Executors.newSingleThreadExecutor();
        var lines = new ArrayList<String>();
        Future<Integer> result = reader.submit(() -> RuntimeProcessOutput.read(process, line -> {
            lines.add(line);
            if (line.equals("ready") || line.equals("second")) {
                try { process.getOutputStream().write("go\n".getBytes(java.nio.charset.StandardCharsets.UTF_8)); process.getOutputStream().flush(); }
                catch (java.io.IOException error) { throw new java.io.UncheckedIOException(error); }
            }
        }, Process::destroy));
        try {
            if (result.get(5, TimeUnit.SECONDS) != 0 || !lines.equals(List.of("ready", "second", "third")))
                throw new AssertionError("CR handshake changed line or exit semantics: " + lines);
        } catch (TimeoutException timeout) {
            throw new AssertionError("CR line delivery waited for another byte; child and callback deadlocked", timeout);
        } finally {
            process.destroyForcibly();
            process.waitFor(5, TimeUnit.SECONDS);
            reader.shutdownNow();
            if (!reader.awaitTermination(5, TimeUnit.SECONDS)) throw new AssertionError("Handshake reader did not stop");
        }
    }
    private static Process child(String mode) throws Exception {
        return new ProcessBuilder(Path.of(System.getProperty("java.home"), "bin", "java").toString(),
                "-Dfile.encoding=UTF-8", "-cp", System.getProperty("java.class.path"),
                RuntimeProcessOutputCheck.class.getName(), mode).redirectErrorStream(true).start();
    }
}
