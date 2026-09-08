package io.github.gplaider.tinyagent;

import android.content.Context;
import android.net.LocalServerSocket;
import android.net.LocalSocket;
import android.os.Build;
import org.json.JSONObject;
import java.io.*;
import java.nio.charset.StandardCharsets;

/** Read-only Android facts for the Fedora agent. Kernel peer UID is the boundary. */
final class AndroidDiagnosticsBridge implements AutoCloseable {
    private final Context context;
    private final LocalServerSocket server;
    private volatile LocalSocket client;
    private volatile SelfAdbClient adb;
    private volatile boolean closed;
    static String socketName() { return "tinyagent-android-" + android.os.Process.myUid() + "-" + android.os.Process.myPid(); }

    AndroidDiagnosticsBridge(Context context) throws IOException {
        this.context = context.getApplicationContext();
        server = new LocalServerSocket(socketName());
        new Thread(this::serve, "tinyagent-android-diagnostics").start();
    }

    private void serve() {
        // ponytail: serialize short read-only diagnostics; no command/job scheduler here.
        while (!closed) {
            try (LocalSocket accepted = server.accept()) {
                client = accepted;
                accepted.setSoTimeout(5000);
                if (accepted.getPeerCredentials().getUid() != android.os.Process.myUid()) continue;
                InputStream input = accepted.getInputStream();
                String first = line(input);
                int bytes = first.length();
                for (String header; !(header = line(input)).isEmpty();) {
                    bytes += header.length();
                    if (bytes > 4096) throw new IOException("Request headers too large");
                }
                String[] request = first.split(" ");
                if (request.length != 3 || !request[0].equals("GET")) { reply(accepted, 400, new JSONObject().put("error", "GET required")); continue; }
                String mode = switch (request[1]) {
                    case "/inspect/stock" -> "stock";
                    case "/inspect/developer" -> "developer";
                    case "/inspect/root" -> "root";
                    default -> "";
                };
                if (mode.isEmpty()) { reply(accepted, 404, new JSONObject().put("error", "Unknown diagnostic")); continue; }
                try { reply(accepted, 200, inspect(mode)); }
                catch (Exception error) { reply(accepted, 409, new JSONObject().put("error", error.getMessage()).put("mode", mode)); }
            } catch (Exception error) {
                if (!closed) android.util.Log.w("TinyAgentAndroid", error.getClass().getSimpleName());
            } finally { client = null; }
        }
    }

    private JSONObject inspect(String mode) throws Exception {
        var prefs = context.getSharedPreferences("connection", Context.MODE_PRIVATE);
        JSONObject result = new JSONObject().put("environment", "android").put("mode", mode)
                .put("measured_at", java.time.Instant.now().toString()).put("device", Build.DEVICE)
                .put("model", Build.MODEL).put("android_version", Build.VERSION.RELEASE)
                .put("sdk", Build.VERSION.SDK_INT).put("app_uid", android.os.Process.myUid())
                .put("root_selected", prefs.getBoolean("rootAllowed", false))
                .put("selected_transport", WirelessAdb.transport(context));
        if (mode.equals("stock")) return result.put("execution_uid", android.os.Process.myUid())
                .put("serial", JSONObject.NULL).put("authority", "app-sandbox");
        boolean root = mode.equals("root");
        if (!root && "stock".equals(WirelessAdb.transport(context)))
            throw new IOException("Stock 모드입니다. Developer 연결 설정에서 권한을 연결하세요.");
        if (root && !prefs.getBoolean("rootAllowed", false)) throw new IOException("Root 실행이 허용되지 않았습니다.");
        try (SelfAdbClient connection = new SelfAdbClient(context)) {
            adb = connection;
            if (closed) throw new IOException("진단 중단");
            SelfAdbClient.Result proof = connection.inspect(!root && WirelessAdb.selected(context) ? 0 : LocalPolicy.port(prefs.getString("port", "")), root);
            if (!proof.verifiedSelf) throw new IOException(proof.transcript);
            return result.put("verified_self", true).put("execution_uid", root ? 0 : 2000).put("transcript", proof.transcript);
        } finally { adb = null; }
    }

    private static String line(InputStream input) throws IOException {
        ByteArrayOutputStream output = new ByteArrayOutputStream();
        int bytes = 0;
        for (int value; (value = input.read()) != '\n';) {
            if (value < 0 || ++bytes > 1024) throw new IOException("Invalid request line");
            if (value != '\r') output.write(value);
        }
        return output.toString(StandardCharsets.US_ASCII.name());
    }

    private static void reply(LocalSocket socket, int code, JSONObject result) throws IOException {
        byte[] body = (result.toString() + "\n").getBytes(StandardCharsets.UTF_8);
        OutputStream output = socket.getOutputStream();
        output.write(("HTTP/1.1 " + code + " Result\r\nContent-Type: application/json; charset=utf-8\r\nContent-Length: "
                + body.length + "\r\nConnection: close\r\n\r\n").getBytes(StandardCharsets.US_ASCII));
        output.write(body); output.flush();
    }

    @Override public void close() {
        closed = true;
        try { server.close(); } catch (IOException ignored) { }
        LocalSocket active = client;
        if (active != null) try { active.close(); } catch (IOException ignored) { }
        SelfAdbClient connection = adb;
        if (connection != null) connection.close();
    }
}
