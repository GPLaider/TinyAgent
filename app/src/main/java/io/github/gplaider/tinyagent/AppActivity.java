package io.github.gplaider.tinyagent;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.ActivityNotFoundException;
import android.content.Intent;
import android.content.SharedPreferences;
import android.graphics.Insets;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.text.Editable;
import android.text.InputType;
import android.text.TextWatcher;
import android.view.View;
import android.view.WindowInsets;
import android.webkit.CookieManager;
import android.webkit.HttpAuthHandler;
import android.webkit.RenderProcessGoneDetail;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.ScrollView;
import android.widget.Switch;
import android.widget.TextView;
import android.widget.Toast;
import android.window.OnBackInvokedCallback;
import android.window.OnBackInvokedDispatcher;

import org.json.JSONObject;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.Collections;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;

public final class AppActivity extends Activity {
    private final ExecutorService worker = Executors.newSingleThreadExecutor();
    private Object backCallback;
    private SharedPreferences preferences;
    private LinearLayout root;
    private FrameLayout content;
    private ScrollView settings;
    private EditText port;
    private Switch rootAllowed;
    private TextView diagnostics;
    private TextView backendStatus;
    private TextView runtimeStatus;
    private TextView runtimeDetails;
    private SharedPreferences runtimePreferences;
    private final SharedPreferences.OnSharedPreferenceChangeListener runtimeListener = (prefs, key) ->
            runOnUiThread(() -> { if (!isDestroyed() && runtimeStatus != null)
                updateRuntimeStatus(); });
    private ProgressBar progress;
    private Button inspect;
    private Button open;
    private Button settingsButton;
    private WebView webView;
    private EmbeddedWebUi embeddedWebUi;
    private Bundle webState;
    private boolean showingWeb;
    private boolean verifiedSelf;
    private boolean webNeedsReload;
    private Future<?> pending;
    private volatile SelfAdbClient activeClient;
    private volatile HttpURLConnection healthConnection;
    private int operation;
    private String managedPassword;
    private boolean submittedManagedAuth;

    @Override public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        preferences = getSharedPreferences("connection", MODE_PRIVATE);
        runtimePreferences = getSharedPreferences("runtime", MODE_PRIVATE);
        getWindow().setDecorFitsSystemWindows(false);
        buildViews();
        Boolean wanted = runtimePreferences.contains("wanted") ? runtimePreferences.getBoolean("wanted", false) : null;
        boolean resume = LocalPolicy.resumeRuntime(new java.io.File(getFilesDir(), "linux/prepared-v1").isFile(),
                wanted, runtimePreferences.getString("status", ""));
        if (wanted == null) runtimePreferences.edit().putBoolean("wanted", resume).apply();
        if (resume) {
            startForegroundService(new Intent(this, RuntimeSetupService.class));
        }
        if (Build.VERSION.SDK_INT >= 33) {
            backCallback = Api33Back.register(this, this::handleBack);
        }
        if (savedInstanceState != null) {
            webState = savedInstanceState.getBundle("web");
            diagnostics.setText(savedInstanceState.getString("diagnostics", "아직 연결하지 않았습니다."));
            if (savedInstanceState.getBoolean("showingWeb")) checkBackend();
        }
    }

    private void buildViews() {
        root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(getColor(R.color.surface));
        root.setOnApplyWindowInsetsListener((view, insets) -> {
            Insets bars = insets.getInsets(WindowInsets.Type.systemBars() | WindowInsets.Type.displayCutout());
            Insets keyboard = insets.getInsets(WindowInsets.Type.ime());
            view.setPadding(bars.left, bars.top, bars.right, Math.max(bars.bottom, keyboard.bottom));
            // The root already owns system/IME padding; WebView must not apply it a second time.
            return WindowInsets.CONSUMED;
        });
        LinearLayout toolbar = new LinearLayout(this);
        toolbar.setPadding(dp(24), 0, dp(16), 0);
        toolbar.setGravity(android.view.Gravity.CENTER_VERTICAL);
        TextView title = text("TinyAgent", 20);
        title.setTypeface(null, android.graphics.Typeface.BOLD);
        toolbar.addView(title, new LinearLayout.LayoutParams(0, -2, 1));
        settingsButton = button("작업 환경", false);
        settingsButton.setVisibility(View.GONE);
        settingsButton.setOnClickListener(view -> showSettings());
        toolbar.addView(settingsButton, new LinearLayout.LayoutParams(-2, dp(48)));
        root.addView(toolbar, new LinearLayout.LayoutParams(-1, dp(56)));
        content = new FrameLayout(this);
        root.addView(content, new LinearLayout.LayoutParams(-1, 0, 1));
        settings = new ScrollView(this);
        settings.setFillViewport(true);
        LinearLayout body = new LinearLayout(this);
        body.setOrientation(LinearLayout.VERTICAL);
        body.setPadding(dp(24), dp(16), dp(24), dp(24));
        settings.addView(body);
        TextView heading = text("작업 환경", 28);
        heading.setTypeface(null, android.graphics.Typeface.BOLD);
        body.addView(heading);
        body.addView(text("이 폰에서 Android와 Fedora 작업을 실행합니다.", 15));
        section(body, "Android 권한 확장 · 선택 사항");
        rootAllowed = new Switch(this);
        rootAllowed.setText("Root 실행 허용");
        rootAllowed.setContentDescription("Unrestricted root 연결 허용");
        rootAllowed.setTextColor(getColor(R.color.text_primary));
        rootAllowed.setTextSize(16);
        rootAllowed.setMinHeight(dp(48));
        rootAllowed.setSwitchPadding(dp(16));
        rootAllowed.setChecked(preferences.getBoolean("rootAllowed", false));
        body.addView(rootAllowed, new LinearLayout.LayoutParams(-1, -2));
        body.addView(text("Fedora와 대화는 기본 앱 권한으로 실행합니다. Root는 Android 관리 작업에만 사용합니다.", 14));
        LinearLayout advanced = new LinearLayout(this);
        advanced.setOrientation(LinearLayout.VERTICAL);
        fold(body, "고급 연결 설정", advanced);
        advanced.addView(text("활성화된 TCP ADB로 이 폰에 연결합니다. 무선 디버깅 페어링은 아직 지원하지 않습니다.", 14));
        TextView portLabel = text("ADB 포트", 15);
        port = new EditText(this);
        port.setId(View.generateViewId());
        portLabel.setLabelFor(port.getId());
        port.setInputType(InputType.TYPE_CLASS_NUMBER);
        port.setSingleLine(true);
        port.setSelectAllOnFocus(true);
        port.setText(preferences.getString("port", "5555"));
        port.setTextSize(16);
        advanced.addView(portLabel);
        advanced.addView(port, new LinearLayout.LayoutParams(-1, dp(52)));
        inspect = button("이 기기 연결 확인", false);
        inspect.setOnClickListener(view -> {
            if (pending != null && !pending.isDone()) cancelInspection();
            else startInspection(false);
        });
        advanced.addView(inspect);
        progress = new ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal);
        progress.setIndeterminate(true);
        progress.setContentDescription("연결 확인 중");
        progress.setVisibility(View.GONE);
        body.addView(progress, new LinearLayout.LayoutParams(-1, dp(4)));
        diagnostics = text("아직 연결하지 않았습니다.\n처음 연결할 때 Android의 USB 디버깅 허용 창을 확인하세요.", 14);
        diagnostics.setTextIsSelectable(true);
        section(body, "Fedora 환경");
        runtimeStatus = text(runtimePreferences.getString("status", "환경 준비 전"), 14);
        runtimeStatus.setTextIsSelectable(true);
        body.addView(runtimeStatus);
        Button prepare = button("환경 준비하기", true);
        prepare.setContentDescription("Fedora 환경 준비");
        prepare.setOnClickListener(view -> {
            try {
                if (Build.VERSION.SDK_INT >= 33 && checkSelfPermission(android.Manifest.permission.POST_NOTIFICATIONS)
                        != android.content.pm.PackageManager.PERMISSION_GRANTED) {
                    requestPermissions(new String[] {android.Manifest.permission.POST_NOTIFICATIONS}, 1);
                }
                startForegroundService(new Intent(this, RuntimeSetupService.class));
            } catch (IllegalArgumentException error) { port.setError(error.getMessage()); }
        });
        body.addView(prepare);
        LinearLayout details = new LinearLayout(this);
        details.setOrientation(LinearLayout.VERTICAL);
        fold(body, "진단 정보", details);
        details.addView(diagnostics);
        runtimeDetails = text("", 14);
        runtimeDetails.setTextIsSelectable(true);
        details.addView(runtimeDetails);
        updateRuntimeStatus();
        Button stopBackend = button("로컬 백엔드 중단", false);
        stopBackend.setOnClickListener(view -> startService(
                new Intent(this, RuntimeSetupService.class).setAction(RuntimeSetupService.STOP)));
        details.addView(stopBackend);
        Button installApk = button("APK 설치", false);
        installApk.setOnClickListener(view -> startActivity(new Intent(this, InstallerActivity.class)));
        body.addView(installApk);
        backendStatus = text("", 14);
        body.addView(backendStatus);
        View spacer = new View(this);
        body.addView(spacer, new LinearLayout.LayoutParams(1, 0, 1));
        open = button("대화 시작하기", true);
        open.setOnClickListener(view -> checkBackend());
        LinearLayout.LayoutParams openLayout = new LinearLayout.LayoutParams(-1, -2);
        openLayout.topMargin = dp(24);
        body.addView(open, openLayout);
        content.addView(settings, new FrameLayout.LayoutParams(-1, -1));
        port.addTextChangedListener(new TextWatcher() {
            @Override public void beforeTextChanged(CharSequence s, int start, int count, int after) {}
            @Override public void onTextChanged(CharSequence s, int start, int before, int count) { invalidateConnection(); }
            @Override public void afterTextChanged(Editable text) {}
        });
        rootAllowed.setOnCheckedChangeListener((button, checked) -> {
            preferences.edit().putBoolean("rootAllowed", checked).apply();
            invalidateConnection();
        });
        setContentView(root);
        root.requestApplyInsets();
    }

    private void invalidateConnection() {
        verifiedSelf = false;
        open.setEnabled(true);
        diagnostics.setText("연결 설정이 바뀌었습니다. 이 기기 연결을 다시 확인하세요.");
    }

    private void setBusy(boolean busy) {
        port.setEnabled(!busy);
        rootAllowed.setEnabled(!busy);
        progress.setVisibility(busy ? View.VISIBLE : View.GONE);
        inspect.setText(busy ? "연결 확인 중단" : "이 기기 연결 확인");
        open.setText(busy ? "연결 확인 중…" : "대화 시작하기");
        open.setEnabled(!busy);
    }

    private void startInspection(boolean resumeWeb) {
        final int selectedPort;
        try { selectedPort = LocalPolicy.port(port.getText().toString()); }
        catch (IllegalArgumentException error) { port.setError(error.getMessage()); return; }
        preferences.edit().putString("port", Integer.toString(selectedPort)).apply();
        final boolean rootPermission = rootAllowed.isChecked();
        final int request = ++operation;
        verifiedSelf = false;
        setBusy(true);
        diagnostics.setText("이 폰의 ADB 주소 확인 중 · 포트 " + selectedPort + "\n처음 연결하면 Android의 디버깅 허용 창을 확인하세요.");
        backendStatus.setText("기기 연결 확인 중…");
        pending = worker.submit(() -> {
            try (SelfAdbClient client = new SelfAdbClient(getApplicationContext())) {
                activeClient = client;
                SelfAdbClient.Result result = client.inspect(selectedPort, rootPermission);
                runOnUiThread(() -> {
                    if (isDestroyed() || request != operation) return;
                    verifiedSelf = result.verifiedSelf;
                    diagnostics.setText(result.transcript);
                    backendStatus.setText(verifiedSelf ? "자기 기기 연결 확인 완료"
                            : "선택한 Android 권한을 확인하지 못했습니다. 상세 결과는 진단 정보에 있습니다.");
                    setBusy(false);
                    if (resumeWeb && verifiedSelf) checkBackend();
                });
            } catch (Exception error) {
                String detail = error instanceof IOException || error instanceof IllegalArgumentException
                        ? error.getMessage() : error.getClass().getSimpleName();
                runOnUiThread(() -> {
                    if (isDestroyed() || request != operation) return;
                    diagnostics.setText("연결 확인 실패\n" + detail
                            + "\n\nTCP ADB 포트, 디버깅 허용, root adbd 상태를 확인한 뒤 다시 시도하세요.");
                    backendStatus.setText("기기 연결 실패 · 고급 연결 설정과 진단 정보를 확인하세요.");
                    setBusy(false);
                });
            } finally { activeClient = null; }
        });
    }

    private void cancelInspection() {
        operation++;
        if (pending != null) pending.cancel(true);
        SelfAdbClient client = activeClient;
        if (client != null) client.close();
        HttpURLConnection health = healthConnection;
        if (health != null) health.disconnect();
        verifiedSelf = false;
        diagnostics.setText("연결 확인을 중단했습니다. 다시 확인할 수 있습니다.");
        backendStatus.setText("연결 확인을 중단했습니다.");
        setBusy(false);
    }

    private void checkBackend() {
        final int request = ++operation;
        setBusy(true);
        backendStatus.setText("로컬 백엔드 응답 확인 중…");
        pending = worker.submit(() -> {
            HttpURLConnection connection = null;
            try {
                java.io.File auth = new java.io.File(getNoBackupFilesDir(), "stock-backend-auth");
                if (!auth.isFile()) throw new IOException("먼저 앱 내부 환경을 준비하세요.");
                if (auth.isFile() && auth.length() != 64) throw new IOException("로컬 인증 파일 크기 오류");
                managedPassword = auth.isFile() ? new String(java.nio.file.Files.readAllBytes(auth.toPath()), StandardCharsets.US_ASCII) : null;
                if (!managedPassword.matches("[0-9a-f]{64}")) throw new IOException("로컬 인증 파일이 손상됐습니다. 환경 준비를 다시 실행하세요.");
                String encoded = android.util.Base64.encodeToString(("opencode:" + managedPassword)
                        .getBytes(StandardCharsets.US_ASCII), android.util.Base64.NO_WRAP);
                long deadline = android.os.SystemClock.elapsedRealtime() + 60000;
                int code;
                while (true) {
                    if (Thread.currentThread().isInterrupted()) throw new InterruptedException();
                    connection = (HttpURLConnection) new URL(LocalPolicy.BACKEND_ORIGIN + "/global/health").openConnection();
                    healthConnection = connection;
                    connection.setConnectTimeout(3000);
                    connection.setReadTimeout(5000);
                    connection.setInstanceFollowRedirects(false);
                    connection.setRequestProperty("Authorization", "Basic " + encoded);
                    try { code = connection.getResponseCode(); break; }
                    catch (java.net.SocketException | java.net.SocketTimeoutException error) {
                        connection.disconnect();
                        if (!runtimePreferences.getBoolean("wanted", false)
                                || runtimePreferences.getString("status", "").startsWith("환경 준비 실패")
                                || android.os.SystemClock.elapsedRealtime() >= deadline) throw error;
                        Thread.sleep(500);
                    }
                }
                if (code == 401 && managedPassword != null) throw new IOException("로컬 인증 갱신 필요. 환경 준비를 다시 실행하세요.");
                String status;
                if (code == 401) status = "백엔드 인증 필요 (HTTP 401). 사용자 이름과 암호를 입력하세요.";
                else {
                    if (code != 200) throw new IOException("HTTP " + code);
                    JSONObject health = new JSONObject(readHealth(connection.getInputStream()));
                    if (!Boolean.TRUE.equals(health.opt("healthy"))
                            || !(health.opt("version") instanceof String) || health.getString("version").isEmpty()) {
                        throw new IOException("OpenCode health 응답 형식이 올바르지 않습니다.");
                    }
                    status = "대화 연결 준비 완료 · OpenCode " + health.getString("version");
                }
                String result = status;
                runOnUiThread(() -> {
                    if (isDestroyed() || request != operation) return;
                    backendStatus.setText(result);
                    submittedManagedAuth = false;
                    setBusy(false);
                    showWeb();
                });
            } catch (Exception error) {
                String detail = error instanceof IOException ? error.getMessage() : error.getClass().getSimpleName();
                runOnUiThread(() -> {
                    if (isDestroyed() || request != operation) return;
                    backendStatus.setText("로컬 백엔드 확인 실패: " + detail
                            + "\n환경 준비를 눌러 백엔드를 다시 연결한 뒤 확인하세요.");
                    setBusy(false);
                });
            } finally {
                if (connection != null) connection.disconnect();
                healthConnection = null;
            }
        });
    }

    private static String readHealth(InputStream input) throws IOException {
        try (input; ByteArrayOutputStream bytes = new ByteArrayOutputStream()) {
            byte[] buffer = new byte[1024];
            for (int length; (length = input.read(buffer)) != -1;) {
                if (bytes.size() + length > 8192) throw new IOException("health 응답이 너무 큽니다.");
                bytes.write(buffer, 0, length);
            }
            return new String(bytes.toByteArray(), StandardCharsets.UTF_8);
        }
    }

    @SuppressWarnings("deprecation")
    private void createWebView() {
        try { embeddedWebUi = new EmbeddedWebUi(getAssets()); }
        catch (Exception error) { throw new IllegalStateException("Packaged OpenCode GUI missing", error); }
        webView = new WebView(this);
        WebSettings config = webView.getSettings();
        config.setUserAgentString(config.getUserAgentString() + " TinyAgent/0.1");
        config.setJavaScriptEnabled(true);
        config.setDomStorageEnabled(true);
        config.setAllowFileAccess(false);
        config.setAllowContentAccess(false);
        config.setAllowFileAccessFromFileURLs(false);
        config.setAllowUniversalAccessFromFileURLs(false);
        config.setJavaScriptCanOpenWindowsAutomatically(false);
        config.setSupportMultipleWindows(false);
        config.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        CookieManager.getInstance().setAcceptThirdPartyCookies(webView, false);
        webView.setWebViewClient(new WebViewClient() {
            @Override public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                String url = request.getUrl().toString();
                if (LocalPolicy.isBackendUrl(url)) return false;
                if (request.isForMainFrame() && LocalPolicy.isBrowserUrl(url)) {
                    try { startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse(url))); }
                    catch (ActivityNotFoundException error) { Toast.makeText(AppActivity.this, "링크를 열 브라우저가 없습니다.", Toast.LENGTH_SHORT).show(); }
                }
                return true;
            }
            @Override public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest request) {
                if (LocalPolicy.isBackendUrl(request.getUrl().toString())) return embeddedWebUi.intercept(request);
                return new WebResourceResponse("text/plain", "UTF-8", 403, "Forbidden",
                        Collections.emptyMap(), new ByteArrayInputStream(new byte[0]));
            }
            @Override public void onReceivedHttpAuthRequest(WebView view, HttpAuthHandler handler, String host, String realm) {
                if (!LocalPolicy.ADB_HOST.equals(host)) { handler.cancel(); return; }
                if (managedPassword != null) {
                    if (submittedManagedAuth) {
                        handler.cancel();
                        backendStatus.setText("로컬 인증 실패. 환경 준비를 다시 실행하세요.");
                        showSettings();
                    } else {
                        submittedManagedAuth = true;
                        handler.proceed("opencode", managedPassword);
                    }
                    return;
                }
                LinearLayout fields = new LinearLayout(AppActivity.this);
                fields.setOrientation(LinearLayout.VERTICAL);
                fields.setPadding(dp(24), 0, dp(24), 0);
                EditText user = new EditText(AppActivity.this);
                user.setHint("백엔드 사용자 이름");
                user.setSingleLine(true);
                user.setSaveEnabled(false);
                EditText password = new EditText(AppActivity.this);
                password.setHint("백엔드 암호");
                password.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_PASSWORD);
                password.setSaveEnabled(false);
                fields.addView(user);
                fields.addView(password);
                new AlertDialog.Builder(AppActivity.this).setTitle("로컬 OpenCode 인증").setView(fields)
                        .setPositiveButton("연결", (dialog, which) -> handler.proceed(user.getText().toString(), password.getText().toString()))
                        .setNegativeButton("취소", (dialog, which) -> handler.cancel())
                        .setOnCancelListener(dialog -> handler.cancel()).show();
            }
            @Override public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
                if (!request.isForMainFrame()) return;
                webNeedsReload = true;
                backendStatus.setText("웹 화면 연결 실패 (WebView " + error.getErrorCode() + "). 백엔드 상태를 다시 확인하세요.");
                showSettings();
            }
            @Override public boolean onRenderProcessGone(WebView view, RenderProcessGoneDetail detail) {
                content.removeView(view);
                view.destroy();
                webView = null;
                webState = null;
                backendStatus.setText("웹 화면 프로세스가 종료되었습니다. 다시 열면 백엔드에 저장된 세션을 불러옵니다.");
                showSettings();
                return true;
            }
        });
        content.addView(webView, new FrameLayout.LayoutParams(-1, -1));
    }

    private void showWeb() {
        if (webView == null) createWebView();
        showingWeb = true;
        settings.setVisibility(View.GONE);
        settingsButton.setVisibility(View.VISIBLE);
        webView.setVisibility(View.VISIBLE);
        if (webView.getUrl() == null) {
            if (webState == null || webView.restoreState(webState) == null) {
                webView.loadUrl(LocalPolicy.BACKEND_ORIGIN + "/");
            }
            webState = null;
        } else if (webNeedsReload) {
            webNeedsReload = false;
            webView.reload();
        }
    }

    private void showSettings() {
        showingWeb = false;
        if (webView != null) webView.setVisibility(View.GONE);
        settings.setVisibility(View.VISIBLE);
        settingsButton.setVisibility(View.GONE);
    }

    private void handleBack() {
        WindowInsets insets = root.getRootWindowInsets();
        if (insets != null && insets.isVisible(WindowInsets.Type.ime())) {
            getWindow().getInsetsController().hide(WindowInsets.Type.ime());
        } else if (showingWeb && webView != null) {
            // One-way UI event only: no native methods or credentials exposed to JavaScript.
            WebView current = webView;
            current.evaluateJavascript("(() => { for (const selector of ['[data-tinyagent-back]', '[data-tinyagent-close]', '[data-slot=dialog-close-button]']) {"
                    + " const button = Array.from(document.querySelectorAll(selector)).find(e => e.getClientRects().length && !e.disabled);"
                    + " if (button) { button.click(); return true; } } return false; })()", consumed -> {
                if (isDestroyed() || current != webView || !showingWeb || "true".equals(consumed)) return;
                if (current.canGoBack()) current.goBack(); else showSettings();
            });
        } else if (pending != null && !pending.isDone()) {
            cancelInspection();
        } else { finish(); }
    }

    // Android 11/12 fallback; API 33+ registers the native gesture callback in onCreate.
    @android.annotation.SuppressLint("GestureBackNavigation")
    @Override @SuppressWarnings("deprecation") public void onBackPressed() { handleBack(); }

    @Override protected void onSaveInstanceState(Bundle state) {
        super.onSaveInstanceState(state);
        state.putBoolean("showingWeb", showingWeb);
        state.putString("diagnostics", diagnostics.getText().toString());
        Bundle saved = new Bundle();
        if (webView != null && webView.saveState(saved) != null) state.putBundle("web", saved);
        else if (webState != null) state.putBundle("web", webState);
    }

    @Override protected void onPause() {
        runtimePreferences.unregisterOnSharedPreferenceChangeListener(runtimeListener);
        if (webView != null) webView.onPause();
        super.onPause();
    }

    @Override protected void onResume() {
        super.onResume();
        runtimePreferences.registerOnSharedPreferenceChangeListener(runtimeListener);
        updateRuntimeStatus();
        if (webView != null) webView.onResume();
    }

    @Override protected void onDestroy() {
        operation++;
        if (pending != null) pending.cancel(true);
        SelfAdbClient client = activeClient;
        if (client != null) client.close();
        HttpURLConnection health = healthConnection;
        if (health != null) health.disconnect();
        worker.shutdownNow();
        if (Build.VERSION.SDK_INT >= 33 && backCallback != null) Api33Back.unregister(this, backCallback);
        if (webView != null) { content.removeView(webView); webView.destroy(); }
        super.onDestroy();
    }

    private TextView text(String value, int size) {
        TextView view = new TextView(this);
        view.setText(value);
        view.setTextSize(size);
        view.setTextColor(getColor(size < 16 ? R.color.text_secondary : R.color.text_primary));
        view.setIncludeFontPadding(false);
        view.setLineSpacing(dp(3), 1.1f);
        view.setPadding(0, dp(6), 0, dp(6));
        return view;
    }

    private void updateRuntimeStatus() {
        String status = runtimePreferences.getString("status", "환경 준비 전");
        runtimeDetails.setText(status);
        runtimeStatus.setText(status.startsWith("Fedora 설치 완료") && !new java.io.File(getNoBackupFilesDir(), "stock-backend-auth").isFile()
                ? "앱 내부 환경을 준비하세요. 이전 관리자 환경의 파일은 보관되어 있습니다."
                : status.startsWith("Fedora 설치 완료") ? "환경 준비 완료 · 대화를 시작할 수 있습니다."
                : status.startsWith("환경 준비 실패") ? "환경 준비 실패 · 진단 정보에서 원인을 확인하세요."
                : status.startsWith("로컬 백엔드를 중단") ? "중단됨 · 환경 준비하기로 다시 시작합니다."
                : status);
    }

    private Button button(String label, boolean primary) {
        Button button = new Button(this);
        button.setText(label);
        button.setTextSize(16);
        button.setAllCaps(false);
        button.setMinHeight(dp(48));
        button.setMinimumHeight(dp(48));
        button.setPadding(dp(16), dp(12), dp(16), dp(12));
        button.setStateListAnimator(null);
        button.setTextColor(new android.content.res.ColorStateList(
                new int[][] {new int[] {-android.R.attr.state_enabled}, new int[] {}},
                new int[] {getColor(R.color.text_disabled), getColor(primary ? R.color.on_action : R.color.text_primary)}));
        android.graphics.drawable.GradientDrawable background = new android.graphics.drawable.GradientDrawable();
        background.setColor(getColor(primary ? R.color.action : R.color.surface_secondary));
        background.setCornerRadius(dp(12));
        button.setBackground(new android.graphics.drawable.RippleDrawable(
                android.content.res.ColorStateList.valueOf(0x22000000), background, null));
        LinearLayout.LayoutParams layout = new LinearLayout.LayoutParams(-1, -2);
        layout.topMargin = dp(8);
        layout.bottomMargin = dp(8);
        button.setLayoutParams(layout);
        return button;
    }

    private void section(LinearLayout parent, String title) {
        TextView heading = text(title, 18);
        heading.setTypeface(null, android.graphics.Typeface.BOLD);
        LinearLayout.LayoutParams layout = new LinearLayout.LayoutParams(-1, -2);
        layout.topMargin = dp(24);
        layout.bottomMargin = dp(8);
        parent.addView(heading, layout);
    }

    private void fold(LinearLayout parent, String label, LinearLayout panel) {
        Button toggle = button(label + "  ＋", false);
        toggle.setGravity(android.view.Gravity.CENTER_VERTICAL | android.view.Gravity.START);
        toggle.setContentDescription(label);
        toggle.setStateDescription("접힘");
        panel.setVisibility(View.GONE);
        toggle.setOnClickListener(view -> {
            boolean expanded = panel.getVisibility() == View.GONE;
            panel.setVisibility(expanded ? View.VISIBLE : View.GONE);
            toggle.setText(label + (expanded ? "  −" : "  ＋"));
            toggle.setStateDescription(expanded ? "펼쳐짐" : "접힘");
        });
        parent.addView(toggle);
        parent.addView(panel, new LinearLayout.LayoutParams(-1, -2));
    }

    private int dp(int value) { return Math.round(value * getResources().getDisplayMetrics().density); }

    /** Kept in a separately loaded class so Android 11/12 never resolve the API 33 callback interface. */
    @android.annotation.TargetApi(33)
    private static final class Api33Back {
        static Object register(Activity activity, Runnable action) {
            OnBackInvokedCallback callback = action::run;
            activity.getOnBackInvokedDispatcher().registerOnBackInvokedCallback(
                    OnBackInvokedDispatcher.PRIORITY_DEFAULT, callback);
            return callback;
        }
        static void unregister(Activity activity, Object callback) {
            activity.getOnBackInvokedDispatcher().unregisterOnBackInvokedCallback((OnBackInvokedCallback) callback);
        }
    }
}
