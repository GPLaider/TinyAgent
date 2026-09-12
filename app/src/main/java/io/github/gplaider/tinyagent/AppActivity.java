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
import android.widget.ImageView;
import android.widget.RadioButton;
import android.widget.RadioGroup;
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
    private final SharedPreferences.OnSharedPreferenceChangeListener connectionListener = (prefs, key) -> {
        if ("wirelessStatus".equals(key) || "transport".equals(key))
            runOnUiThread(this::updateConnectionStatus);
    };
    private LinearLayout root;
    private FrameLayout content;
    private ScrollView settings;
    private LinearLayout connecting;
    private TextView rootStatus;
    private final ExecutorService accessWorker = Executors.newSingleThreadExecutor();
    private Future<?> accessProbe;
    private volatile SelfAdbClient rootProbeClient;
    private TextView diagnostics;
    private TextView backendStatus;
    private TextView runtimeStatus;
    private TextView runtimeDetails;
    private Button prepare;
    private LinearLayout preparation;
    private TextView preparationLabel;
    private ProgressBar preparationBar;
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
        }
        if (resume && (savedInstanceState == null || savedInstanceState.getBoolean("showingWeb"))) {
            settings.setVisibility(View.GONE);
            connecting.setVisibility(View.VISIBLE);
            settingsButton.setVisibility(View.VISIBLE);
            checkBackend();
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
        ImageView logo = new ImageView(this);
        logo.setImageResource(R.mipmap.ic_launcher);
        logo.setImportantForAccessibility(View.IMPORTANT_FOR_ACCESSIBILITY_NO);
        LinearLayout.LayoutParams logoLayout = new LinearLayout.LayoutParams(dp(32), dp(32));
        logoLayout.setMarginEnd(dp(10));
        toolbar.addView(logo, logoLayout);
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
        Button developer = button("Developer 연결 설정", false);
        developer.setOnClickListener(v -> startActivity(new Intent(this, DeveloperActivity.class)));
        body.addView(developer);
        rootStatus = text("기기 관리 기능 확인 중…", 15);
        body.addView(rootStatus);
        body.addView(text("Fedora와 대화는 기본 앱 권한으로 실행합니다. Root는 Android 관리 작업에만 사용합니다.", 14));
        inspect = button("기기 관리 기능 다시 확인", false);
        inspect.setOnClickListener(view -> detectRootAccess());
        body.addView(inspect);
        progress = new ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal);
        progress.setIndeterminate(true);
        progress.setContentDescription("연결 확인 중");
        progress.setVisibility(View.GONE);
        body.addView(progress, new LinearLayout.LayoutParams(-1, dp(4)));
        diagnostics = text("이 화면에서 연결을 아직 확인하지 않았습니다.\nAndroid 권한이 필요한 작업은 Developer 연결 설정에서 확인하세요. Fedora와 대화는 ADB 없이 사용할 수 있습니다.", 14);
        diagnostics.setTextIsSelectable(true);
        section(body, "Fedora 환경");
        body.addView(text("패키지 관리자 · 최초 준비 전에 선택", 16));
        RadioGroup managers = new RadioGroup(this);
        managers.setOrientation(LinearLayout.HORIZONTAL);
        RadioButton dnfast = new RadioButton(this);
        dnfast.setId(View.generateViewId()); dnfast.setText("dnfast");
        RadioButton dnf5 = new RadioButton(this);
        dnf5.setId(View.generateViewId()); dnf5.setText("dnf5");
        managers.addView(dnfast); managers.addView(dnf5);
        try { managers.check(PackageManagerChoice.read(this).equals("dnf5") ? dnf5.getId() : dnfast.getId()); }
        catch (IOException error) { Toast.makeText(this, error.getMessage(), Toast.LENGTH_LONG).show(); }
        boolean managerLocked = PackageManagerChoice.locked(this);
        dnfast.setEnabled(!managerLocked); dnf5.setEnabled(!managerLocked);
        boolean[] updatingManager = {false};
        managers.setOnCheckedChangeListener((group, checked) -> {
            if (updatingManager[0]) return;
            try { PackageManagerChoice.select(this, checked == dnf5.getId() ? "dnf5" : "dnfast"); }
            catch (IOException error) { Toast.makeText(this, error.getMessage(), Toast.LENGTH_LONG).show(); }
            finally {
                updatingManager[0] = true;
                try { group.check(PackageManagerChoice.read(this).equals("dnf5") ? dnf5.getId() : dnfast.getId()); }
                catch (IOException error) { dnfast.setEnabled(false); dnf5.setEnabled(false); }
                finally { updatingManager[0] = false; }
            }
        });
        body.addView(managers);
        body.addView(text("준비를 시작하면 이 Fedora 환경에 고정됩니다. 앱 업데이트 후에도 유지됩니다.", 13));
        runtimeStatus = text(runtimePreferences.getString("status", "환경 준비 전"), 14);
        runtimeStatus.setTextIsSelectable(true);
        body.addView(runtimeStatus);
        prepare = button("환경 준비하기", true);
        prepare.setContentDescription("Fedora 환경 준비");
        prepare.setOnClickListener(view -> {
            dnfast.setEnabled(false); dnf5.setEnabled(false);
            prepare.setEnabled(false);
            prepare.setVisibility(View.GONE);
            preparation.setVisibility(View.VISIBLE);
            preparationLabel.setText("환경 준비 시작 중…");
            try {
                if (Build.VERSION.SDK_INT >= 33 && checkSelfPermission(android.Manifest.permission.POST_NOTIFICATIONS)
                        != android.content.pm.PackageManager.PERMISSION_GRANTED) {
                    requestPermissions(new String[] {android.Manifest.permission.POST_NOTIFICATIONS}, 1);
                }
                startForegroundService(new Intent(this, RuntimeSetupService.class));
            } catch (RuntimeException error) {
                dnfast.setEnabled(!PackageManagerChoice.locked(this)); dnf5.setEnabled(!PackageManagerChoice.locked(this));
                preparation.setVisibility(View.GONE);
                prepare.setVisibility(View.VISIBLE); prepare.setEnabled(true);
                runtimeStatus.setText("환경 준비 시작 실패 · " + error.getClass().getSimpleName());
            }
        });
        FrameLayout preparationSlot = new FrameLayout(this);
        preparationSlot.addView(prepare, new FrameLayout.LayoutParams(-1, -2));
        preparation = new LinearLayout(this);
        preparation.setOrientation(LinearLayout.VERTICAL);
        preparation.setPadding(dp(16), dp(12), dp(16), dp(12));
        preparation.setMinimumHeight(dp(48));
        preparationLabel = text("환경 준비 중…", 15);
        preparationLabel.setAccessibilityLiveRegion(View.ACCESSIBILITY_LIVE_REGION_POLITE);
        preparation.addView(preparationLabel);
        preparationBar = new ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal);
        preparationBar.setIndeterminate(true);
        preparationBar.setContentDescription("환경 준비 진행 중");
        preparation.addView(preparationBar, new LinearLayout.LayoutParams(-1, dp(6)));
        preparation.setVisibility(View.GONE);
        preparationSlot.addView(preparation, new FrameLayout.LayoutParams(-1, -2));
        body.addView(preparationSlot);
        LinearLayout details = new LinearLayout(this);
        details.setOrientation(LinearLayout.VERTICAL);
        fold(body, "진단 정보", details);
        details.addView(text("Android 권한 확장 · ADB 연결 진단", 16));
        details.addView(diagnostics);
        details.addView(text("Fedora · 앱 내부 실행환경 진단", 16));
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
        connecting = new LinearLayout(this);
        connecting.setOrientation(LinearLayout.VERTICAL);
        connecting.setGravity(android.view.Gravity.CENTER);
        connecting.setPadding(dp(24), dp(24), dp(24), dp(24));
        connecting.addView(new ProgressBar(this), new LinearLayout.LayoutParams(dp(36), dp(36)));
        connecting.addView(text("대화에 다시 연결하는 중…", 18));
        connecting.setVisibility(View.GONE);
        content.addView(connecting, new FrameLayout.LayoutParams(-1, -1));
        setContentView(root);
        root.requestApplyInsets();
    }

    private void invalidateConnection() {
        verifiedSelf = false;
        open.setEnabled(true);
        diagnostics.setText("연결 설정이 바뀌었습니다. 이 기기 연결을 다시 확인하세요.");
    }

    private void updateConnectionStatus() {
        if (isDestroyed() || diagnostics == null) return;
        String transport = WirelessAdb.transport(this);
        if ("wireless".equals(transport)) {
            diagnostics.setText(preferences.getString("wirelessStatus", "무선 ADB 연결 확인 전")
                    + "\n\n최근 연결 결과입니다. Android 작업마다 연결·권한을 다시 확인합니다.");
        } else if ("stock".equals(transport)) {
            diagnostics.setText("Stock · ADB를 사용하지 않습니다.\nFedora 준비와 대화는 앱 권한으로 실행합니다.");
        }
    }

    private void setBusy(boolean busy) {
        progress.setVisibility(busy ? View.VISIBLE : View.GONE);
        open.setText(busy ? "연결 확인 중…" : "대화 시작하기");
        open.setEnabled(!busy);
    }

    private void detectRootAccess() {
        if (accessProbe != null && !accessProbe.isDone()) return;
        rootStatus.setText("기기 관리 기능 확인 중…");
        accessProbe = accessWorker.submit(() -> {
            boolean available = false;
            try (SelfAdbClient client = new SelfAdbClient(getApplicationContext())) {
                rootProbeClient = client;
                int detected = SelfAdbClient.discoverPort(this);
                if (detected != 0 || WirelessAdb.selected(this)) available = client.inspect(detected, true).verifiedSelf;
            } catch (Exception ignored) { }
            finally { rootProbeClient = null; }
            final boolean measured = available;
            preferences.edit().putBoolean("rootAvailable", measured).putLong("rootMeasuredAt", System.currentTimeMillis()).apply();
            runOnUiThread(() -> {
                if (isDestroyed()) return;
                rootStatus.setText(measured ? "Root 기기 관리 사용 가능 · 자기 기기 UID 0 확인"
                        : "기본 기능 사용 가능 · Root 연결은 감지되지 않았습니다.");
            });
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
        updateConnectionStatus();
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
                    connecting.setVisibility(View.GONE);
                    showSettings();
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
            @Override public void onPageFinished(WebView view, String url) {
                if (!LocalPolicy.isBackendUrl(url)) return;
                // OpenCode marks Markdown links target=_blank; route local file actions in this WebView.
                view.evaluateJavascript("(() => { if(window.__tinyagentFiles) return; window.__tinyagentFiles=true;"
                        + "document.addEventListener('click', e => { const a=e.target.closest?.('a[href]'); if(!a) return;"
                        + "const u=new URL(a.href,location.href); if(u.origin!==location.origin || !['/tinyagent/file','/tinyagent/export'].includes(u.pathname)) return;"
                        + "const r=a.getBoundingClientRect(); u.searchParams.set('tapX',String((e.detail?e.clientX:r.left)/innerWidth));"
                        + "u.searchParams.set('tapY',String((e.detail?e.clientY:r.bottom)/innerHeight));"
                        + "e.preventDefault(); e.stopImmediatePropagation(); location.assign(u.href); },true); })()", null);
            }
            @Override public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                String url = request.getUrl().toString();
                if (request.isForMainFrame() && LocalPolicy.isBackendUrl(view.getUrl())
                        && LocalPolicy.isBackendUrl(url) && "/tinyagent/project/create".equals(request.getUrl().getPath())) {
                    createProjectFolder(view);
                    return true;
                }
                if (request.isForMainFrame() && LocalPolicy.isBackendUrl(view.getUrl())
                        && LocalPolicy.isBackendUrl(url) && "/tinyagent/file".equals(request.getUrl().getPath())) {
                    int[] point = new int[2]; view.getLocationOnScreen(point);
                    try {
                        float x=Float.parseFloat(request.getUrl().getQueryParameter("tapX"));
                        float y=Float.parseFloat(request.getUrl().getQueryParameter("tapY"));
                        if (Float.isFinite(x) && Float.isFinite(y)) {
                            point[0] += (int)(Math.max(0,Math.min(1,x))*view.getWidth());
                            point[1] += (int)(Math.max(0,Math.min(1,y))*view.getHeight());
                        }
                    } catch (Exception ignored) { /* Older links anchor at the conversation's top edge. */ }
                    startActivity(new Intent(AppActivity.this, ArtifactActivity.class)
                            .putExtra("path", request.getUrl().getQueryParameter("path"))
                            .putExtra("tapX",point[0]).putExtra("tapY",point[1]));
                    return true;
                }
                if (request.isForMainFrame() && LocalPolicy.isBackendUrl(view.getUrl())
                        && LocalPolicy.isBackendUrl(url) && "/tinyagent/export".equals(request.getUrl().getPath())) {
                    startActivity(new Intent(AppActivity.this, InstallerActivity.class)
                            .putExtra("exportPath", request.getUrl().getQueryParameter("path")));
                    return true;
                }
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

    private void createProjectFolder(WebView source) {
        EditText name = new EditText(this);
        name.setSingleLine(true);
        name.setHint("폴더 이름");
        name.setPadding(dp(20), dp(16), dp(20), dp(16));
        AlertDialog dialog = new AlertDialog.Builder(this).setTitle("새 프로젝트 폴더")
                .setMessage("/workspace 안에 새 폴더를 만들고 프로젝트로 엽니다.")
                .setView(name).setNegativeButton("취소", null).setPositiveButton("만들고 열기", null).create();
        dialog.setOnShowListener(ignored -> dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(button -> {
            String value = name.getText().toString().trim();
            if (value.isEmpty() || value.length() > 120 || value.equals(".") || value.equals("..")
                    || value.indexOf('/') >= 0 || value.indexOf('\\') >= 0 || value.chars().anyMatch(Character::isISOControl)) {
                name.setError("경로 구분자 없이 폴더 이름을 입력하세요.");
                return;
            }
            try {
                java.io.File workspace = new java.io.File(getFilesDir(), "linux/workspace").getCanonicalFile();
                if (!workspace.toPath().startsWith(getFilesDir().getCanonicalFile().toPath())) throw new IOException("작업공간 경로 확인 필요");
                java.nio.file.Files.createDirectory(new java.io.File(workspace, value).toPath());
                String event = "window.dispatchEvent(new CustomEvent('tinyagent:project-created',{detail:{path:"
                        + JSONObject.quote("/workspace/" + value) + "}}))";
                if (source == webView && LocalPolicy.isBackendUrl(source.getUrl())) source.evaluateJavascript(event, null);
                dialog.dismiss();
            } catch (java.nio.file.FileAlreadyExistsException error) { name.setError("같은 이름의 폴더가 이미 있습니다."); }
            catch (Exception error) { name.setError("폴더를 만들지 못했습니다. 실행 환경과 저장 공간을 확인하세요."); }
        }));
        dialog.show();
    }

    private void showWeb() {
        connecting.setVisibility(View.GONE);
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
        if (connecting.getVisibility() == View.VISIBLE) cancelInspection();
        connecting.setVisibility(View.GONE);
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
        } else if (connecting.getVisibility() == View.VISIBLE) {
            showSettings();
        } else if (pending != null && !pending.isDone()) {
            cancelInspection();
        } else { finish(); }
    }

    // Android 11/12 fallback; API 33+ registers the native gesture callback in onCreate.
    @android.annotation.SuppressLint("GestureBackNavigation")
    @Override @SuppressWarnings("deprecation") public void onBackPressed() { handleBack(); }

    @Override protected void onSaveInstanceState(Bundle state) {
        super.onSaveInstanceState(state);
        state.putBoolean("showingWeb", showingWeb || connecting.getVisibility() == View.VISIBLE);
        state.putString("diagnostics", diagnostics.getText().toString());
        Bundle saved = new Bundle();
        if (webView != null && webView.saveState(saved) != null) state.putBundle("web", saved);
        else if (webState != null) state.putBundle("web", webState);
    }

    @Override protected void onPause() {
        preferences.unregisterOnSharedPreferenceChangeListener(connectionListener);
        runtimePreferences.unregisterOnSharedPreferenceChangeListener(runtimeListener);
        if (webView != null) webView.onPause();
        super.onPause();
    }

    @Override protected void onResume() {
        super.onResume();
        preferences.registerOnSharedPreferenceChangeListener(connectionListener);
        updateConnectionStatus();
        detectRootAccess();
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
        if (rootProbeClient != null) rootProbeClient.close();
        accessWorker.shutdownNow();
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
        boolean preparing = RuntimeSetupService.preparing;
        prepare.setEnabled(!preparing);
        prepare.setVisibility(preparing ? View.GONE : View.VISIBLE);
        preparation.setVisibility(preparing ? View.VISIBLE : View.GONE);
        preparationLabel.setText(runtimePreferences.getString("progressDetail", status));
        int percent = runtimePreferences.getInt("percent", -1);
        preparationBar.setIndeterminate(percent < 0);
        preparationBar.setProgress(Math.max(0, percent));
        if (LocalPolicy.RUNTIME_READY.equals(status) && backendStatus != null) backendStatus.setText("");
        prepare.setText(status.startsWith("환경 준비 실패") ? "환경 준비 다시 시도" : "환경 준비하기");
        String previousExit = runtimePreferences.getString("previousProcessExit", "");
        runtimeDetails.setText(status + (previousExit.isEmpty() ? "" : "\n\n" + previousExit));
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
