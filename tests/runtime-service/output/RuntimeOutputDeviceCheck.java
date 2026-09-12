package io.github.gplaider.tinyagent;

import android.app.Activity;
import android.app.Instrumentation;
import android.os.Bundle;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.concurrent.*;

/** Production reader and actual Android shell pipes; no runtime replacement. */
public final class RuntimeOutputDeviceCheck extends Instrumentation {
    @Override public void onCreate(Bundle args) { super.onCreate(args); start(); }
    @Override public void onStart() {
        StringBuilder report = new StringBuilder();
        boolean passed = false;
        try {
            for (int round = 1; round <= 3; round++) handshake(round, report);
            passed = true;
        } catch (Throwable error) { report.append("FAIL ").append(error).append('\n'); }
        Bundle result = new Bundle();
        result.putString("stream", report + (passed ? "PASS: Android runtime output; 3 live CR/LF acknowledgment rounds\n" : ""));
        finish(passed ? Activity.RESULT_OK : Activity.RESULT_CANCELED, result);
    }
    private void handshake(int round, StringBuilder report) throws Exception {
        // The shell refuses to emit the next byte until the reader callback ACKs.
        String script = "printf 'ready\\r'; read first; [ \"$first\" = go ] || exit 3; "
                + "printf '\\nsecond\\r'; read second; [ \"$second\" = go ] || exit 4; "
                + "printf 'third'; exit 7";
        Process child = new ProcessBuilder("/system/bin/sh", "-c", script).redirectErrorStream(true).start();
        ExecutorService reader = Executors.newSingleThreadExecutor();
        List<String> lines = new ArrayList<>();
        Future<Integer> result = reader.submit(() -> RuntimeProcessOutput.read(child, line -> {
            lines.add(line);
            if (line.equals("ready") || line.equals("second")) {
                try { child.getOutputStream().write("go\n".getBytes(StandardCharsets.UTF_8)); child.getOutputStream().flush(); }
                catch (IOException error) { throw new UncheckedIOException(error); }
            }
        }, Process::destroy));
        try {
            if (result.get(5, TimeUnit.SECONDS) != 7 || !lines.equals(List.of("ready", "second", "third")))
                throw new AssertionError("CR/LF callback or exit status changed: " + lines);
            if (child.isAlive()) throw new AssertionError("Child remained alive");
            report.append("round=").append(round).append(" PASS immediate CR callback, delayed CRLF, CR/non-LF, EOF and exit 7\n");
        } finally {
            child.destroy();
            child.waitFor(5, TimeUnit.SECONDS);
            reader.shutdownNow();
            if (!reader.awaitTermination(5, TimeUnit.SECONDS)) throw new AssertionError("Reader did not terminate");
        }
    }
}
