package io.github.gplaider.tinyagent;

import android.app.Activity;
import android.app.Instrumentation;
import android.os.Bundle;
import android.os.SystemClock;
import android.system.Os;
import android.system.OsConstants;
import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.*;
import org.json.*;

/** Real packaged OpenCode; isolated UID/HOME/port; shell API never calls a model. */
public final class BackendLifecycleCheck extends Instrumentation {
    private final StringBuilder report = new StringBuilder();
    private final ExecutorService requests = Executors.newSingleThreadExecutor();
    private LocalLinuxRuntime runtime;
    private Process server;
    private String authorization;
    private int port, checks;
    private String completedMessage;
    private interface Check { boolean ready() throws Exception; }
    @Override public void onCreate(Bundle args) { super.onCreate(args); start(); }
    private void require(boolean value, String message) {
        checks++;
        if (!value) throw new AssertionError(message);
    }
    private void await(Check check, long milliseconds, String message) throws Exception {
        long until = SystemClock.elapsedRealtime() + milliseconds;
        while (!check.ready()) {
            if (SystemClock.elapsedRealtime() > until) throw new AssertionError(message);
            Thread.sleep(50);
        }
        checks++;
    }
    private String request(String path, JSONObject payload, boolean authenticate) throws Exception {
        HttpURLConnection connection = (HttpURLConnection) new URL("http://127.0.0.1:" + port + path).openConnection();
        connection.setConnectTimeout(1000); connection.setReadTimeout(30000);
        connection.setRequestProperty("x-opencode-directory", "/workspace");
        if (authenticate) connection.setRequestProperty("Authorization", authorization);
        try {
            if (payload != null) {
                connection.setRequestMethod("POST"); connection.setDoOutput(true);
                connection.setRequestProperty("Content-Type", "application/json");
                try (OutputStream output = connection.getOutputStream()) { output.write(payload.toString().getBytes(StandardCharsets.UTF_8)); }
            }
            int status = connection.getResponseCode();
            if (!authenticate) return Integer.toString(status);
            try (InputStream input = status >= 400 ? connection.getErrorStream() : connection.getInputStream();
                 ByteArrayOutputStream output = new ByteArrayOutputStream()) {
                if (input != null) {
                    byte[] buffer = new byte[8192];
                    for (int size; (size = input.read(buffer)) != -1;) {
                        if (output.size() + size > 1024 * 1024) throw new IOException("Audit HTTP response too large");
                        output.write(buffer, 0, size);
                    }
                }
                String text = output.toString(StandardCharsets.UTF_8.name());
                if (status != 200) throw new IOException("HTTP " + status + " " + text);
                return text;
            }
        } finally { connection.disconnect(); }
    }
    private JSONObject shell(String command) throws Exception {
        // Explicit bookkeeping model reference avoids default provider lookup.
        return new JSONObject().put("agent", "build").put("command", command)
                .put("model", new JSONObject().put("providerID", "audit").put("modelID", "no-inference"));
    }
    private static int pid(String record) { return Integer.parseInt(record.split("\\R", 2)[0]); }
    private static boolean alive(String record) throws Exception {
        Path path = Paths.get("/proc", Integer.toString(pid(record)), "stat");
        try {
            String stat = Files.readString(path);
            return !stat.substring(stat.lastIndexOf(") ") + 2).startsWith("Z ") && RuntimeProcessIdentity.matches(
                    record, Files.readString(Paths.get("/proc/sys/kernel/random/boot_id")), stat);
        } catch (NoSuchFileException gone) { return false; }
    }
    private void startServer() throws Exception {
        runtime = new LocalLinuxRuntime(getTargetContext());
        runtime.recoverPreviousProcesses(runtime.base);
        // Production startBackend hardcodes the user's port 4097. Build the same
        // guest/start chain here with a dynamically chosen audit-only port.
        ProcessBuilder builder = runtime.guest("/workspace", "/usr/local/bin/opencode", "serve", "--hostname", "127.0.0.1", "--port", Integer.toString(port));
        Map<String, String> env = builder.environment();
        // Password is kept separately from the encoded HTTP header on disk nowhere.
        String userPass = new String(android.util.Base64.decode(authorization.substring(6), android.util.Base64.NO_WRAP), StandardCharsets.UTF_8);
        env.put("OPENCODE_SERVER_PASSWORD", userPass.substring("opencode:".length()));
        env.put("TINYAGENT_PREVIOUS_RUNTIME_STOPPED", "1");
        env.put("OPENCODE_DISABLE_CHANNEL_DB", "1");
        for (String flag : List.of("OPENCODE_DISABLE_AUTOUPDATE", "OPENCODE_DISABLE_MODELS_FETCH", "OPENCODE_DISABLE_DEFAULT_PLUGINS", "OPENCODE_DISABLE_EXTERNAL_SKILLS")) env.put(flag, "true");
        env.put("OPENCODE_CONFIG_CONTENT", "{\"shell\":\"/usr/bin/bash\",\"instructions\":[],\"enabled_providers\":[]}");
        server = runtime.start(builder.redirectOutput(ProcessBuilder.Redirect.appendTo(new File(runtime.base, "backend-audit.log"))));
        await(() -> {
            if (!server.isAlive()) throw new AssertionError("Audit server exited before health: " + server.exitValue());
            try { return new JSONObject(request("/global/health", null, true)).optBoolean("healthy"); }
            catch (IOException error) { return false; }
        }, 60000, "Audit server health timeout");
        require(request("/session", null, false).equals("401"), "Unauthenticated session access accepted");
    }
    private JSONArray messages(String session) throws Exception { return new JSONArray(request("/session/" + session + "/message", null, true)); }
    private static String output(JSONObject state) {
        JSONObject metadata = state.optJSONObject("metadata");
        return state.optString("output") + (metadata == null ? "" : metadata.optString("output"));
    }
    private JSONObject tool(JSONArray messages, String marker) throws Exception {
        for (int i = 0; i < messages.length(); i++) {
            JSONArray parts = messages.getJSONObject(i).getJSONArray("parts");
            for (int j = 0; j < parts.length(); j++) {
                JSONObject part = parts.getJSONObject(j);
                if (part.optString("type").equals("tool") && part.toString().contains(marker)) return part;
            }
        }
        return null;
    }
    private void checkRound(String session, String mode, int round) throws Exception {
        String marker = "AUDIT_PARTIAL_" + mode + "_" + round;
        Path identity = runtime.base.toPath().resolve("shared/child.identity");
        Files.deleteIfExists(identity);
        Future<String> shell = requests.submit(() -> request("/session/" + session + "/shell", shell(
                "/usr/bin/bash /shared/job.sh " + marker), true));
        await(() -> {
            if (shell.isDone()) throw new AssertionError("Shell completed before child marker: " + shell.get());
            return Files.exists(identity);
        }, 20000, "OpenCode shell child missing");
        String record = Files.readString(identity);
        require(alive(record) && Os.stat("/proc/" + pid(record)).st_uid == android.os.Process.myUid(), "Wrong child ownership");
        await(() -> {
            JSONObject part = tool(messages(session), marker);
            return part != null && part.getJSONObject("state").optString("status").equals("running")
                    && output(part.getJSONObject("state")).contains(marker);
        }, 10000, "Running tool/partial output not persisted");
        if (mode.equals("abort")) {
            require(request("/session/" + session + "/abort", new JSONObject(), true).equals("true"), "Abort rejected");
            shell.get(10000, TimeUnit.MILLISECONDS);
        } else {
            if (mode.equals("cancel")) runtime.cancel();
            else {
                var signal = LocalLinuxRuntime.class.getDeclaredMethod("signal", Process.class, int.class);
                signal.setAccessible(true); signal.invoke(runtime, server, OsConstants.SIGKILL);
            }
            require(server.waitFor(5, TimeUnit.SECONDS), "Backend tracer survived stop");
            await(() -> !alive(record), 10000, "Fedora shell child survived tracer stop");
            runtime.forget(server);
            try { shell.get(10000, TimeUnit.MILLISECONDS); }
            catch (ExecutionException expected) { require(expected.getCause() instanceof IOException, "Unexpected request failure"); }
            startServer();
        }
        await(() -> !alive(record), 10000, "Shell child survived operation");
        JSONArray saved = messages(session);
        JSONObject state = tool(saved, marker).getJSONObject("state");
        require(!List.of("pending", "running").contains(state.getString("status")), "Persisted tool still active");
        require(output(state).contains(marker), "Partial output lost");
        require(state.getJSONObject("metadata").optBoolean("interrupted"), "Interrupted command lacks marker");
        if (!mode.equals("abort")) {
            require(state.getString("status").equals("error"), "Recovered tool reported success");
            require(state.getJSONObject("metadata").optBoolean("interrupted") && state.getJSONObject("metadata").optString("recovery").equals("runtime-restarted"), "Missing restart recovery metadata");
        }
        boolean preserved = false;
        for (int i = 0; i < saved.length(); i++) if (saved.getJSONObject(i).getJSONObject("info").getString("id").equals(completedMessage)) {
            require(saved.getJSONObject(i).getJSONObject("info").optJSONObject("error") == null, "Completed history marked aborted");
            JSONObject completed = tool(new JSONArray().put(saved.getJSONObject(i)), "AUDIT_COMPLETED").getJSONObject("state");
            require(completed.optString("status").equals("completed") && completed.optString("output").equals("AUDIT_COMPLETED\nunset"), "Completed tool history changed");
            preserved = true;
        }
        require(preserved, "Completed history missing after restart");
        JSONObject status = new JSONObject(request("/session/status?scope=server", null, true)).optJSONObject(session);
        require(status == null || status.optString("type").equals("idle"), "Session stayed busy");
        report.append(mode).append(" round=").append(round).append(" PASS real shell child death, partial output, terminal state, completed history\n");
    }
    @Override public void onStart() {
        boolean passed = false;
        try {
            runtime = new LocalLinuxRuntime(getTargetContext());
            for (File directory : List.of(runtime.base, runtime.rootfs, runtime.home, runtime.workspace, new File(runtime.base, "shared"), new File(runtime.base, "tmp"), new File(runtime.rootfs, ".l2s"))) Files.createDirectories(directory.toPath());
            try (InputStream input = getTargetContext().getAssets().open("linux-launch.sh")) { Files.copy(input, new File(runtime.base, "launch.sh").toPath()); }
            runtime.unpack("fedora-44-arm64-rootfs.tar.gz.bin", "3a3661a77d5fdb1e4bd10be484142683630c1ffb4c371931d46a42459fd4c125", runtime.rootfs, "Fedora", 5638);
            for (String name : List.of("root", "workspace", "shared", "dev", "proc", "tmp", "usr/local/bin")) Files.createDirectories(new File(runtime.rootfs, name).toPath());
            Files.createFile(new File(runtime.rootfs, "tinyagent-installed.apk").toPath());
            runtime.unpack("opencode-linux-arm64.tar.gz.bin", "b877f7baa8d60611b9a638209c84868e5dea9139c8dec622943d25f29c07f205", new File(runtime.rootfs, "usr/local/bin"), "OpenCode", 1);
            require(RuntimeExecutable.matches(new File(runtime.rootfs, "usr/local/bin/opencode").toPath(), "5e64f096fbc1e7a891d5382d86fc657a7d2b316fe2546a2025a28fb531a1fc6e"), "Wrong OpenCode executable");
            StringBuilder version = new StringBuilder();
            runtime.run(runtime.guest("/workspace", "/usr/local/bin/opencode", "--version"), version::append);
            require(version.toString().contains("1.18.29-tinyagent.12"), "Wrong backend version: " + version);
            report.append("runtime ").append(version).append(" Android UID=").append(android.os.Process.myUid()).append('\n');
            Files.writeString(new File(runtime.base, "shared/job.sh").toPath(), "#!/usr/bin/bash\n{ printf '%s\\n' \"$$\"; cat /proc/sys/kernel/random/boot_id; cat /proc/$$/stat; } > /shared/child.tmp\nmv /shared/child.tmp /shared/child.identity\nprintf '%s\\n' \"$1\"\nexec /usr/bin/sleep 120\n");
            try (ServerSocket socket = new ServerSocket(0, 1, InetAddress.getLoopbackAddress())) { port = socket.getLocalPort(); }
            require(port != 4097, "Audit port collides with production default");
            authorization = "Basic " + android.util.Base64.encodeToString(("opencode:" + UUID.randomUUID() + UUID.randomUUID()).getBytes(StandardCharsets.UTF_8), android.util.Base64.NO_WRAP);
            startServer();
            String session = new JSONObject(request("/session", new JSONObject().put("title", "Isolated lifecycle audit"), true)).getString("id");
            JSONObject completed = new JSONObject(request("/session/" + session + "/shell", shell("printf 'AUDIT_COMPLETED\\n'; printf '%s' \"${TINYAGENT_PREVIOUS_RUNTIME_STOPPED-unset}\""), true));
            completedMessage = completed.getJSONObject("info").getString("id");
            JSONObject state = tool(new JSONArray().put(completed), "AUDIT_COMPLETED").getJSONObject("state");
            require(state.optString("status").equals("completed"), "Initial shell failed");
            require(state.optString("output").contains("AUDIT_COMPLETED\nunset"), "Startup recovery flag leaked to user shell");
            JSONObject failed = new JSONObject(request("/session/" + session + "/shell", shell("printf 'AUDIT_EXIT7\\n'; exit 7"), true));
            JSONObject failedState = tool(new JSONArray().put(failed), "AUDIT_EXIT7").getJSONObject("state");
            require(failedState.getJSONObject("metadata").getInt("exit") == 7 && output(failedState).contains("AUDIT_EXIT7"), "Nonzero command exit/output lost");
            for (String mode : List.of("abort", "cancel", "kill")) for (int round = 1; round <= 2; round++) checkRound(session, mode, round);
            passed = true;
        } catch (Throwable error) {
            report.append("FAIL ").append(error).append('\n');
            try {
                Path log = new File(runtime.base, "backend-audit.log").toPath();
                if (Files.exists(log)) {
                    String tail = Files.readString(log);
                    tail = tail.substring(Math.max(0, tail.length() - 5000));
                    if (authorization != null) {
                        String secret = new String(android.util.Base64.decode(authorization.substring(6), android.util.Base64.NO_WRAP), StandardCharsets.UTF_8).substring("opencode:".length());
                        tail = tail.replace(secret, "[redacted]").replace(authorization, "[redacted]");
                    }
                    report.append("audit-only backend log: ").append(tail).append('\n');
                }
            } catch (Exception ignored) { }
        }
        finally {
            if (runtime != null) {
                try {
                    runtime.cancel();
                    if (server != null) { server.waitFor(5, TimeUnit.SECONDS); runtime.forget(server); }
                    runtime.recoverPreviousProcesses(runtime.base);
                } catch (Exception error) { passed = false; report.append("FAIL cleanup ").append(error).append('\n'); }
            }
            requests.shutdownNow();
        }
        Bundle result = new Bundle();
        result.putString("stream", report + (passed ? "PASS: isolated OpenCode lifecycle; " + checks + " assertions; no model call\n" : ""));
        finish(passed ? Activity.RESULT_OK : Activity.RESULT_CANCELED, result);
    }
}
