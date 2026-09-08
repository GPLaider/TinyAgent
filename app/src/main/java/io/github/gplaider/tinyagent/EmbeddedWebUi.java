package io.github.gplaider.tinyagent;

import android.content.res.AssetManager;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import org.json.JSONObject;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.Map;

/** Versioned official GUI assets only; API requests still reach the phone backend. */
final class EmbeddedWebUi {
    private final AssetManager assets;
    private final JSONObject files;
    private final String csp;

    EmbeddedWebUi(AssetManager assets) throws Exception {
        this.assets = assets;
        try (var input = assets.open("web-ui-manifest.json")) {
            var bytes = new java.io.ByteArrayOutputStream();
            byte[] buffer = new byte[8192];
            for (int size; (size = input.read(buffer)) != -1;) {
                if (bytes.size() + size > 1024 * 1024) throw new IOException("UI manifest too large");
                bytes.write(buffer, 0, size);
            }
            JSONObject manifest = new JSONObject(bytes.toString(StandardCharsets.UTF_8.name()));
            files = manifest.getJSONObject("files");
            csp = manifest.getString("csp");
        }
    }

    WebResourceResponse intercept(WebResourceRequest request) {
        if (!"GET".equals(request.getMethod())) return null;
        String path = request.getUrl().getPath();
        if (path == null) return null;
        if (request.isForMainFrame()) path = "/index.html";
        String mime = files.optString(path, "");
        if (mime.isEmpty()) return null;
        try {
            return new WebResourceResponse(mime, "UTF-8", 200, "OK",
                    Map.of("Content-Security-Policy", csp, "Cache-Control", "no-cache", "X-Content-Type-Options", "nosniff"),
                    assets.open("web-ui" + path));
        } catch (IOException error) {
            return new WebResourceResponse("text/plain", "UTF-8", 500, "Missing packaged UI",
                    Map.of(), new java.io.ByteArrayInputStream(new byte[0]));
        }
    }
}
