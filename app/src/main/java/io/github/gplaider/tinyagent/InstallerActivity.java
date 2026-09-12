package io.github.gplaider.tinyagent;

import android.app.*;
import android.content.*;
import android.content.pm.*;
import android.net.Uri;
import android.os.Bundle;
import android.provider.Settings;
import android.widget.*;
import java.io.*;
import java.nio.file.*;
import java.util.concurrent.*;

/** One selected APK, one explicitly selected authority; never escalates on failure. */
public final class InstallerActivity extends Activity {
    private final ExecutorService worker = Executors.newSingleThreadExecutor();
    private SharedPreferences state;
    private TextView status;
    private Spinner route;
    private EditText path;
    private boolean quick, quickExport, started;
    private String openedConfirmation = "";
    private String pendingExport;
    // Retained only across configuration changes; exports do not share installer preferences.
    private static final class ExportState {
        String text;
        boolean complete;
        int activeCopies;
        Runnable observer;
    }
    private ExportState exportState;
    private final Runnable exportObserver = this::refresh;
    private static final java.util.concurrent.atomic.AtomicBoolean BUSY = new java.util.concurrent.atomic.AtomicBoolean();
    private final SharedPreferences.OnSharedPreferenceChangeListener listener = (p, k) -> runOnUiThread(this::refresh);
    @Override public void onCreate(Bundle saved) {
        boolean popup = getIntent().hasExtra("workspacePath") || getIntent().hasExtra("exportPath");
        if (popup) setTheme(R.style.ArtifactPopup);
        super.onCreate(saved);
        pendingExport = saved == null ? null : saved.getString("pendingExport");
        exportState = (ExportState) getLastNonConfigurationInstance();
        if (exportState == null) {
            exportState = new ExportState();
            if (saved != null) {
                exportState.text = saved.getString("exportStatus");
                exportState.complete = saved.getBoolean("exportComplete");
                if (saved.getBoolean("exportRunning")) {
                    exportState.text = "파일 저장 결과를 확인할 수 없습니다. 저장이 중단됐거나 대상에 일부 파일만 남았을 수 있습니다. 대상 파일을 확인하세요.";
                    exportState.complete = false;
                }
            }
        }
        exportState.observer = exportObserver;
        state = getSharedPreferences("installer", MODE_PRIVATE);
        quick = popup;
        quickExport = getIntent().hasExtra("exportPath");
        if (quick) {
            LinearLayout body=new LinearLayout(this); body.setOrientation(LinearLayout.VERTICAL);
            int pad=(int)(20*getResources().getDisplayMetrics().density); body.setPadding(pad,pad,pad,pad);
            TextView title=new TextView(this); title.setText(quickExport?"파일 저장":"APK 설치"); title.setTextSize(18); body.addView(title);
            String selectedPath=getIntent().getStringExtra(quickExport?"exportPath":"workspacePath");
            TextView filename=new TextView(this); filename.setText(selectedPath == null ? "" : new File(selectedPath).getName()); filename.setSingleLine(true); filename.setEllipsize(android.text.TextUtils.TruncateAt.MIDDLE); filename.setTextSize(14); body.addView(filename);
            status=new TextView(this); status.setText(quickExport?"저장 위치를 선택하세요.":"Android 설치 준비 중…"); status.setTextSize(14); status.setPadding(0,pad/2,0,pad/2); body.addView(status);
            button(body,"닫기",this::finish); setContentView(body);
            route=new Spinner(this); route.setAdapter(new ArrayAdapter<>(this,android.R.layout.simple_spinner_dropdown_item,new String[]{"Stock","Developer","Root","ROM"}));
            route.setSelection(Math.max(0,Math.min(3,state.getInt("route",0))));
            path=new EditText(this); path.setText(selectedPath);
            state.registerOnSharedPreferenceChangeListener(listener);
            started=saved!=null && saved.getBoolean("started");
            if(saved!=null) openedConfirmation=saved.getString("openedConfirmation","");
            if(saved==null) { if(quickExport) exportWorkspace(); else stageWorkspace(selectedPath); }
            else refresh();
            return;
        }
        LinearLayout body = new LinearLayout(this); body.setOrientation(LinearLayout.VERTICAL);
        int pad = (int) (24 * getResources().getDisplayMetrics().density); body.setPadding(pad, pad, pad, pad);
        if (!popup) body.setOnApplyWindowInsetsListener((view, insets) -> {
            var bars = insets.getInsets(android.view.WindowInsets.Type.systemBars() | android.view.WindowInsets.Type.displayCutout() | android.view.WindowInsets.Type.ime());
            view.setPadding(pad + bars.left, pad + bars.top, pad + bars.right, pad + bars.bottom);
            return android.view.WindowInsets.CONSUMED;
        });
        ScrollView scroll = new ScrollView(this); scroll.addView(body); setContentView(scroll);
        TextView title = new TextView(this); title.setText("APK 설치"); title.setTextSize(26); body.addView(title);
        status = new TextView(this); status.setTextSize(16); status.setTextIsSelectable(true); body.addView(status);
        route = new Spinner(this);
        route.setAdapter(new ArrayAdapter<>(this, android.R.layout.simple_spinner_dropdown_item,
                new String[]{"Stock · Android 승인", "Developer · self-ADB", "Root · self root-ADB", "ROM · INSTALL_PACKAGES 권한"}));
        route.setSelection(Math.max(0, Math.min(3, state.getInt("route", 0))));
        body.addView(route);
        path = new EditText(this); path.setSingleLine(true); path.setHint("Fedora /workspace/ 아래 APK 상대 경로"); body.addView(path);
        button(body, "작업공간 APK 설치", () -> stageWorkspace(path.getText().toString()));
        button(body, "작업공간 파일 내보내기", this::exportWorkspace);
        button(body, "파일에서 APK 선택", () -> startActivityForResult(new Intent(Intent.ACTION_OPEN_DOCUMENT)
                .addCategory(Intent.CATEGORY_OPENABLE).setType("application/vnd.android.package-archive"), 10));
        button(body, "이 앱의 설치 허용 설정", () -> startActivity(new Intent(Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES,
                Uri.parse("package:" + getPackageName()))));
        button(body, "Android 승인 화면 열기", () -> {
            try {
                String value = state.getString("confirmation", "");
                if (value.isEmpty()) throw new IOException("현재 승인 대기 중인 설치가 없습니다.");
                startActivity(Intent.parseUri(value, Intent.URI_INTENT_SCHEME | Intent.URI_ALLOW_UNSAFE));
            } catch (Exception error) { message(error.getMessage()); }
        });
        button(body, "닫기", this::finish);
        state.registerOnSharedPreferenceChangeListener(listener); refresh();
        if (saved == null && getIntent().hasExtra("workspacePath")) path.setText(getIntent().getStringExtra("workspacePath"));
        if (saved == null && getIntent().hasExtra("exportPath")) {
            path.setText(getIntent().getStringExtra("exportPath"));
            exportWorkspace();
        }
    }
    private void button(LinearLayout body, String text, Runnable action) {
        Button button = new Button(this); button.setText(text); button.setTextSize(16);
        button.setMinHeight((int)(48 * getResources().getDisplayMetrics().density));
        button.setOnClickListener(v -> action.run()); body.addView(button);
    }
    private void refresh() {
        if (quickExport || exportState.text != null) {
            if (status != null) status.setText(exportState.text == null ? "저장 위치를 선택하세요." : exportState.text);
            if (quickExport && exportState.complete && !isFinishing()) {
                Toast.makeText(this,"파일을 저장했습니다.",Toast.LENGTH_SHORT).show(); finish();
            }
            return;
        }
        if (quick && !started) return;
        if (status != null) status.setText(state.getString("status", "설치할 APK와 실행 권한을 선택하세요."));
        if (!quick || quickExport || isFinishing()) return;
        String confirmation=state.getString("confirmation","");
        if (!confirmation.isEmpty() && !confirmation.equals(openedConfirmation)) {
            try { openedConfirmation=confirmation; startActivity(Intent.parseUri(confirmation,Intent.URI_INTENT_SCHEME|Intent.URI_ALLOW_UNSAFE)); }
            catch(Exception error){ status.setText("Android 설치 화면을 열 수 없습니다: "+error.getMessage()); }
        }
        int code=state.getInt("code",-2);
        if(code==PackageInstaller.STATUS_SUCCESS || code==PackageInstaller.STATUS_FAILURE_ABORTED) {
            Toast.makeText(this,code==0?"설치 완료":"설치를 취소했습니다.",Toast.LENGTH_SHORT).show(); finish();
        }
    }
    private void message(String value) {
        runOnUiThread(() -> { exportState.text = null; exportState.complete = false; if(status!=null) status.setText(value); });
        state.edit().putString("status", value).apply();
    }
    private void exportMessage(String value, boolean complete) {
        ExportState current = exportState;
        runOnUiThread(() -> {
            current.text = value;
            current.complete = complete;
            if (current.observer != null) current.observer.run();
        });
    }
    private void exportResult(String value, boolean complete) {
        ExportState current = exportState;
        runOnUiThread(() -> {
            current.activeCopies--;
            exportMessage(value, complete);
        });
    }
    @Override public Object onRetainNonConfigurationInstance() { return exportState; }
    @Override protected void onSaveInstanceState(Bundle out) { out.putBoolean("exportRunning",exportState.activeCopies > 0); out.putString("exportStatus",exportState.text); out.putBoolean("exportComplete",exportState.complete); out.putString("pendingExport",pendingExport); out.putBoolean("started",started); out.putString("openedConfirmation",openedConfirmation); super.onSaveInstanceState(out); }
    private void stageWorkspace(String relative) {
        try {
            workspaceFile(relative);
            submit(() -> new WorkspaceFiles(getFilesDir()).input(relative));
        } catch (Exception error) { message(error.getMessage()); }
    }
    private File workspaceFile(String relative) throws IOException {
        return new WorkspaceFiles(getFilesDir()).resolve(relative);
    }
    private void exportWorkspace() {
        try {
            if (pendingExport != null) throw new IOException("기존 저장 위치 선택을 먼저 완료하거나 취소하세요.");
            String relative = path.getText().toString();
            File input = workspaceFile(relative);
            startActivityForResult(new Intent(Intent.ACTION_CREATE_DOCUMENT)
                    .addCategory(Intent.CATEGORY_OPENABLE)
                    .setType(input.getName().endsWith(".apk") ? "application/vnd.android.package-archive" : "application/octet-stream")
                    .putExtra(Intent.EXTRA_TITLE, input.getName()), 20);
            pendingExport = relative;
        } catch (Exception error) { exportMessage("내보내기 실패: " + error.getMessage(), false); }
    }
    @Override protected void onActivityResult(int request, int result, Intent data) {
        super.onActivityResult(request, result, data);
        if(request==30 && quick) {
            if(getPackageManager().canRequestPackageInstalls()) stageWorkspace(path.getText().toString());
            else finish();
        }
        if (request == 10 && result == RESULT_OK && data != null && data.getData() != null) {
            Uri uri = data.getData(); submit(() -> getContentResolver().openInputStream(uri));
        }
        if (request == 20) {
            String relative = pendingExport;
            pendingExport = null;
            if (result != RESULT_OK || data == null || data.getData() == null) {
                if(quick) finish(); else exportMessage("내보내기를 취소했습니다.", false); return;
            }
            if (relative == null) { exportMessage("저장할 파일 선택 정보가 없습니다. 다시 선택하세요.", false); return; }
            Uri uri = data.getData();
            started = true; // Retained in saved state so recreated export UI observes the result.
            exportMessage("선택한 위치로 파일 저장 중…", false);
            exportState.activeCopies++;
            worker.submit(() -> {
                try {
                  long total = 0;
                  try (var descriptor = new WorkspaceFiles(getFilesDir()).open(relative);
                       InputStream input = new android.os.ParcelFileDescriptor.AutoCloseInputStream(descriptor)) {
                    long expectedSize = descriptor.getStatSize();
                    if (expectedSize < 0) throw new IOException("원본 파일 크기를 확인할 수 없습니다.");
                    try (OutputStream output = getContentResolver().openOutputStream(uri, "wt")) {
                      if (output == null) throw new IOException("저장할 위치를 열 수 없습니다.");
                      total = WorkspaceCopy.copy(input, output, expectedSize);
                      output.flush();
                    }
                  }
                    exportResult("파일 저장 완료 · " + total + " bytes · Android 파일 앱에서 선택한 위치를 확인하세요.", true);
                } catch (Exception error) { exportResult("파일 저장 실패: " + error.getMessage() + " · 대상에 일부 파일이 남았을 수 있습니다.", false); }
            });
        }
    }
    private interface Source { InputStream open() throws IOException; }
    private void submit(Source source) {
        if (BUSY.get()) { message("설치 요청 처리 중입니다."); return; }
        int previous = state.getInt("session", -1);
        if (previous >= 0 && state.getInt("code", -2) < 0
                && getPackageManager().getPackageInstaller().getSessionInfo(previous) != null) {
            message("기존 Android 설치 결과를 기다리는 중입니다. 승인 대기라면 승인 화면을 열어 완료하거나 취소하세요."); return;
        }
        if (!state.getString("confirmation", "").isEmpty()) { message("기존 Android 설치 승인을 먼저 완료하거나 취소하세요."); return; }
        int selected = route.getSelectedItemPosition();
        if (selected == 0 && android.os.Build.VERSION.SDK_INT < 31
                && checkSelfPermission("android.permission.INSTALL_PACKAGES") == PackageManager.PERMISSION_GRANTED) {
            message("Android 11의 특권 앱에서는 승인 강제 기능을 지원하지 않습니다. 설치 경로를 명시적으로 다시 선택하세요."); return;
        }
        if (selected == 0 && !getPackageManager().canRequestPackageInstalls()) {
            if(quick) { startActivityForResult(new Intent(Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES,Uri.parse("package:"+getPackageName())),30); return; }
            message("‘이 앱의 설치 허용 설정’에서 허용한 뒤 APK를 다시 선택하세요."); return;
        }
        var connection = getSharedPreferences("connection", MODE_PRIVATE);
        if (selected == 1 && "stock".equals(WirelessAdb.transport(this))) {
            message("Stock 모드입니다. Developer 연결 설정에서 먼저 권한을 연결하세요."); return;
        }
        final int port = 0; // Discover on the worker, then verify the actual device and UID.
        if (selected == 3 && checkSelfPermission("android.permission.INSTALL_PACKAGES") != PackageManager.PERMISSION_GRANTED) {
            message("이 APK에는 INSTALL_PACKAGES 권한이 없습니다. ROM 통합·실제 권한 부여가 필요합니다."); return;
        }
        if (!BUSY.compareAndSet(false, true)) return;
        started=true;
        state.edit().putInt("code",-2).apply();
        message("APK 검증·설치 요청 중…");
        worker.submit(() -> {
            File staged = null;
            try {
                staged = File.createTempFile("install-", ".apk", getCacheDir());
                try (InputStream input = source.open(); OutputStream output = new FileOutputStream(staged)) {
                    if (input == null) throw new IOException("APK를 열 수 없습니다.");
                    byte[] buffer = new byte[65536]; long total = 0;
                    for (int n; (n = input.read(buffer)) != -1;) {
                        total += n; if (total > 1024L * 1024 * 1024) throw new IOException("APK 최대 크기 1 GiB 초과");
                        output.write(buffer, 0, n);
                    }
                }
                PackageInfo info = getPackageManager().getPackageArchiveInfo(staged.toString(), PackageManager.GET_SIGNING_CERTIFICATES);
                if (info == null || info.signingInfo == null) throw new IOException("유효한 서명 APK가 아닙니다.");
                state.edit().putString("package", info.packageName).putLong("version", info.getLongVersionCode())
                        .putInt("route", selected).putInt("code", -2).putLong("updated", System.currentTimeMillis()).commit();
                if (selected == 1 || selected == 2) {
                    try (SelfAdbClient adb = new SelfAdbClient(this)) {
                        adb.inspect(port, selected == 2);
                        adb.install(staged, selected == 2);
                    }
                    state.edit().putInt("code", 0).putLong("updated", System.currentTimeMillis())
                            .putString("status", "설치 완료 · " + info.packageName + " · version=" + info.getLongVersionCode()).commit();
                } else installSession(staged, info, selected == 3);
            } catch (Exception error) { state.edit().putInt("code", 1).putString("status", "설치 실패: " + error.getMessage()).commit(); }
            finally { if (staged != null) staged.delete(); BUSY.set(false); }
        });
    }
    private void installSession(File apk, PackageInfo info, boolean privileged) throws Exception {
        PackageInstaller installer = getPackageManager().getPackageInstaller();
        var params = new PackageInstaller.SessionParams(PackageInstaller.SessionParams.MODE_FULL_INSTALL);
        params.setAppPackageName(info.packageName); params.setSize(apk.length());
        if (android.os.Build.VERSION.SDK_INT >= 31)
            params.setRequireUserAction(privileged ? PackageInstaller.SessionParams.USER_ACTION_NOT_REQUIRED : PackageInstaller.SessionParams.USER_ACTION_REQUIRED);
        int id = installer.createSession(params);
        state.edit().putInt("session", id).putString("status", "Android 설치 결과 대기 · session=" + id).commit();
        try (var session = installer.openSession(id); var input = new FileInputStream(apk)) {
            try (var output = session.openWrite("base.apk", 0, apk.length())) {
                byte[] buffer = new byte[65536];
                for (int n; (n = input.read(buffer)) != -1;) output.write(buffer, 0, n);
                session.fsync(output);
            }
            Intent result = new Intent(this, InstallResultReceiver.class).setAction(getPackageName() + ".INSTALL_RESULT." + id);
            session.commit(PendingIntent.getBroadcast(this, id, result, PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_MUTABLE).getIntentSender());
        } catch (Exception error) { installer.abandonSession(id); throw error; }
    }
    @Override protected void onDestroy() { state.unregisterOnSharedPreferenceChangeListener(listener); if (exportState.observer == exportObserver) exportState.observer = null; worker.shutdown(); super.onDestroy(); }
}
