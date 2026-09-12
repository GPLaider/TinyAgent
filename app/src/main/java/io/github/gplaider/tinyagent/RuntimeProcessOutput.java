package io.github.gplaider.tinyagent;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.TimeUnit;
import java.util.function.Consumer;

/** Drain an owned process; failed output delivery must not orphan its work. */
final class RuntimeProcessOutput {
    static final int MAX_LINE_CHARS = 1024 * 1024;

    private static final class LineReader extends BufferedReader {
        private boolean skipLf;
        LineReader(InputStream input) { super(new InputStreamReader(input, StandardCharsets.UTF_8)); }
        @Override public String readLine() throws IOException {
            StringBuilder line = new StringBuilder();
            for (int value; (value = read()) != -1;) {
                if (skipLf) {
                    skipLf = false;
                    if (value == '\n') continue;
                }
                if (value == '\n') return line.toString();
                if (value == '\r') {
                    // Deliver CR immediately. Its optional LF is consumed by the
                    // next call, so a child can wait for this line's callback.
                    skipLf = true;
                    return line.toString();
                }
                if (line.length() == MAX_LINE_CHARS)
                    throw new IOException("Process output line exceeds " + MAX_LINE_CHARS + " characters");
                line.append((char) value);
            }
            return line.length() == 0 ? null : line.toString();
        }
    }

    static int read(Process process, Consumer<String> lines, Consumer<Process> stop) throws Exception {
        try {
            try (var reader = new LineReader(process.getInputStream())) {
                for (String line; (line = reader.readLine()) != null;) lines.accept(line);
            }
            return process.waitFor();
        } catch (Exception error) {
            try {
                if (process.isAlive()) {
                    stop.accept(process);
                    if (!process.waitFor(5, TimeUnit.SECONDS))
                        throw new IOException("Owned process termination not confirmed");
                }
            } catch (Exception cleanup) { error.addSuppressed(cleanup); }
            throw error;
        }
    }
}
