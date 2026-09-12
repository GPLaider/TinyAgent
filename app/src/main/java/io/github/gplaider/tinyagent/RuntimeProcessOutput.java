package io.github.gplaider.tinyagent;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.TimeUnit;
import java.util.function.Consumer;

/** Drain an owned process; failed output delivery must not orphan its work. */
final class RuntimeProcessOutput {
    static int read(Process process, Consumer<String> lines, Consumer<Process> stop) throws Exception {
        try {
            try (var reader = new BufferedReader(new InputStreamReader(process.getInputStream(), StandardCharsets.UTF_8))) {
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
