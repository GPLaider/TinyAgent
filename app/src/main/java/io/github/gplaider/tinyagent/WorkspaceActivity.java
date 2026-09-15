package io.github.gplaider.tinyagent;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Intent;
import android.os.Bundle;
import android.view.View;
import android.view.WindowInsets;
import android.widget.*;
import androidx.core.content.FileProvider;
import java.io.File;
import java.io.IOException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Comparator;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/** Native browsing and explicit file selection within the agent workspace. */
public final class WorkspaceActivity extends Activity {
    private final ExecutorService worker = Executors.newSingleThreadExecutor();
    private String directory = "";
    private int generation;
    private TextView path;
    private TextView status;
    private ListView list;
    private Button up;
    private Object backCallback;
    private final ArrayList<File> entries = new ArrayList<>();

    @Override public void onCreate(Bundle saved) {
        super.onCreate(saved);
        directory = saved != null ? saved.getString("directory", "")
                : getSharedPreferences("workspace-browser", MODE_PRIVATE).getString("directory", "");
        getWindow().setDecorFitsSystemWindows(false);
        LinearLayout body = new LinearLayout(this);
        body.setOrientation(LinearLayout.VERTICAL);
        body.setBackgroundColor(getColor(R.color.surface));
        int padding = (int)(16 * getResources().getDisplayMetrics().density);
        body.setOnApplyWindowInsetsListener((view, insets) -> {
            var bars = insets.getInsets(WindowInsets.Type.systemBars() | WindowInsets.Type.displayCutout());
            view.setPadding(bars.left + padding, bars.top, bars.right + padding, bars.bottom);
            return WindowInsets.CONSUMED;
        });
        LinearLayout toolbar = new LinearLayout(this);
        Button close = new Button(this); close.setText("닫기"); close.setOnClickListener(v -> finish());
        toolbar.addView(close);
        up = new Button(this); up.setText("상위 폴더"); up.setOnClickListener(v -> parent());
        toolbar.addView(up);
        Button refresh = new Button(this); refresh.setText("새로고침"); refresh.setOnClickListener(v -> load());
        toolbar.addView(refresh);
        body.addView(toolbar);
        TextView heading = new TextView(this);
        heading.setText(getIntent().getBooleanExtra("pick", false) ? "첨부할 파일 선택" : "작업 파일");
        heading.setTextSize(24); heading.setTextColor(getColor(R.color.text_primary));
        heading.setPadding(0, padding, 0, padding / 2);
        body.addView(heading);
        path = new TextView(this); path.setTextSize(18); path.setTextIsSelectable(true); body.addView(path);
        status = new TextView(this); status.setAccessibilityLiveRegion(View.ACCESSIBILITY_LIVE_REGION_POLITE);
        body.addView(status);
        list = new ListView(this); body.addView(list, new LinearLayout.LayoutParams(-1, 0, 1));
        list.setOnItemClickListener((parent, view, position, id) -> select(entries.get(position), view));
        setContentView(body);
        if (android.os.Build.VERSION.SDK_INT >= 33) backCallback = Api33Back.register(this, this::back);
        load();
    }

    private void load() {
        int request = ++generation;
        String requested = directory;
        path.setText("/workspace" + (directory.isEmpty() ? "" : "/" + directory));
        up.setEnabled(!directory.isEmpty());
        list.setEnabled(false);
        status.setText("파일 목록을 불러오는 중…");
        worker.execute(() -> {
            try {
                File[] found = new WorkspaceFiles(getFilesDir()).list(requested);
                Arrays.sort(found, Comparator.comparing((File file) -> !file.isDirectory())
                        .thenComparing(File::getName, String.CASE_INSENSITIVE_ORDER));
                ArrayList<String> labels = new ArrayList<>();
                for (File file : found) labels.add((file.isDirectory() ? "폴더 · " : "파일 · ") + file.getName());
                runOnUiThread(() -> {
                    if (isDestroyed() || isFinishing() || request != generation) return;
                    entries.clear(); entries.addAll(Arrays.asList(found));
                    list.setAdapter(new ArrayAdapter<>(this, android.R.layout.simple_list_item_1, labels));
                    list.setEnabled(true);
                    getSharedPreferences("workspace-browser", MODE_PRIVATE).edit().putString("directory", requested).apply();
                    status.setText(found.length == 0 ? "아직 파일이 없습니다. 대화에서 만든 작업 파일이 여기에 표시됩니다."
                            : getIntent().getBooleanExtra("pick", false) ? "이미지·PDF·텍스트 중 하나를 선택하세요. 최대 32 MiB. 이미지·PDF는 지원 모델이 필요합니다."
                            : "파일을 누르면 열기·저장·공유할 수 있습니다.");
                });
            } catch (IOException error) {
                runOnUiThread(() -> {
                    if (isDestroyed() || isFinishing() || request != generation) return;
                    entries.clear(); list.setAdapter(null);
                    status.setText(directory.isEmpty() ? error.getMessage() : "폴더를 열 수 없습니다. 상위 폴더로 이동하거나 새로고침하세요.");
                });
            }
        });
    }

    private void select(File file, View row) {
        String relative = directory.isEmpty() ? file.getName() : directory + "/" + file.getName();
        if (file.isDirectory()) { directory = relative; load(); return; }
        try {
            WorkspaceFiles files = new WorkspaceFiles(getFilesDir());
            File selected = files.resolve(relative);
            if (!getIntent().getBooleanExtra("pick", false)) {
                int[] point = new int[2]; row.getLocationOnScreen(point);
                startActivity(new Intent(this, ArtifactActivity.class).putExtra("path", relative)
                        .putExtra("tapX", point[0]).putExtra("tapY", point[1] + row.getHeight()));
                return;
            }
            try (var descriptor = files.open(relative)) {
                if (descriptor.getStatSize() > 32L * 1024 * 1024)
                    throw new IOException("첨부 파일은 32 MiB 이하로 선택하세요.");
            }
            var uri = FileProvider.getUriForFile(this, getPackageName() + ".artifacts", selected);
            setResult(RESULT_OK, new Intent().setData(uri));
            finish();
        } catch (Exception error) {
            new AlertDialog.Builder(this).setTitle("파일 선택 실패").setMessage(error.getMessage())
                    .setPositiveButton("닫기", null).show();
        }
    }

    private void parent() {
        int slash = directory.lastIndexOf('/');
        directory = slash < 0 ? "" : directory.substring(0, slash);
        load();
    }

    private void back() {
        if (directory.isEmpty()) finish();
        else parent();
    }

    @android.annotation.SuppressLint("GestureBackNavigation")
    @Override @SuppressWarnings("deprecation") public void onBackPressed() { back(); }

    @Override protected void onSaveInstanceState(Bundle state) {
        super.onSaveInstanceState(state); state.putString("directory", directory);
    }

    @Override protected void onDestroy() {
        if (android.os.Build.VERSION.SDK_INT >= 33 && backCallback != null) Api33Back.unregister(this, backCallback);
        generation++; worker.shutdownNow(); super.onDestroy();
    }

    @android.annotation.TargetApi(33)
    private static final class Api33Back {
        static Object register(Activity activity, Runnable action) {
            android.window.OnBackInvokedCallback callback = action::run;
            activity.getOnBackInvokedDispatcher().registerOnBackInvokedCallback(
                    android.window.OnBackInvokedDispatcher.PRIORITY_DEFAULT, callback);
            return callback;
        }
        static void unregister(Activity activity, Object callback) {
            activity.getOnBackInvokedDispatcher().unregisterOnBackInvokedCallback((android.window.OnBackInvokedCallback) callback);
        }
    }
}
