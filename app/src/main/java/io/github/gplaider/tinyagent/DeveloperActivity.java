package io.github.gplaider.tinyagent;

import android.app.Activity;
import android.content.*;
import android.os.*;
import android.provider.Settings;
import android.text.InputType;
import android.view.*;
import android.widget.*;

/** Pairing stays in Android Settings; notification input avoids closing its dialog. */
public final class DeveloperActivity extends Activity {
    private TextView status;
    private final Handler refresh = new Handler(Looper.getMainLooper());
    private final Runnable update = new Runnable() {
        public void run() {
            status.setText(getSharedPreferences("connection",0).getString("wirelessStatus","연결 안 됨 · Stock 기능은 바로 사용할 수 있습니다."));
            refresh.postDelayed(this,1000);
        }
    };
    static Intent wirelessSettings(Context context) {
        Intent intent = new Intent("android.settings.WIRELESS_DEBUGGING_SETTINGS");
        if (intent.resolveActivity(context.getPackageManager()) == null) intent = new Intent(Settings.ACTION_APPLICATION_DEVELOPMENT_SETTINGS);
        return intent;
    }
    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        var scroll = new ScrollView(this);
        var body = new LinearLayout(this); body.setOrientation(LinearLayout.VERTICAL);
        int pad = Math.round(24*getResources().getDisplayMetrics().density);
        body.setPadding(pad,pad,pad,pad); scroll.addView(body);
        scroll.setOnApplyWindowInsetsListener((v,insets) -> {
            var bars = insets.getInsets(WindowInsets.Type.systemBars() | WindowInsets.Type.ime());
            v.setPadding(bars.left,bars.top,bars.right,bars.bottom); return insets;
        });
        add(body,"개발자 연결",26);
        status = add(body,"연결 안 됨",16);
        add(body,"1 / 3 · 개발자 옵션",20);
        add(body,"휴대전화 정보에서 빌드 번호를 7번 누르면 개발자 옵션이 열립니다.",15);
        action(body,"개발자 옵션 설정",() -> startActivity(new Intent(
                Settings.Global.getInt(getContentResolver(),Settings.Global.DEVELOPMENT_SETTINGS_ENABLED,0)==1
                        ? Settings.ACTION_APPLICATION_DEVELOPMENT_SETTINGS : Settings.ACTION_DEVICE_INFO_SETTINGS)));
        add(body,"2 / 3 · 무선 디버깅",20);
        add(body,"Wi-Fi에 연결하고 무선 디버깅을 켜세요. PC·Tailscale·기존 ADB 연결은 필요하지 않습니다.",15);
        action(body,"무선 디버깅 열기",() -> startActivity(wirelessSettings(this)));
        add(body,"3 / 3 · 페어링 코드 입력",20);
        add(body,"아래 알림을 켠 뒤 설정에서 ‘페어링 코드로 기기 페어링’을 누르세요. 그 창을 열어 둔 채 알림창의 TinyAgent ‘코드 입력’에 6자리를 입력하세요. 연결은 자동으로 찾습니다.",15);
        action(body,"페어링 알림 켜기",() -> {
            if (Build.VERSION.SDK_INT>=33 && checkSelfPermission(android.Manifest.permission.POST_NOTIFICATIONS)!=getPackageManager().PERMISSION_GRANTED)
                requestPermissions(new String[]{android.Manifest.permission.POST_NOTIFICATIONS},41);
            else startForegroundService(new Intent(this,WirelessPairingService.class));
        });
        add(body,"알림을 쓰지 않으면 분할 화면으로 Android 페어링 창을 유지한 채 아래에 입력하세요.",14);
        var code = new EditText(this); code.setHint("페어링 코드 6자리"); code.setTextSize(18);
        code.setInputType(InputType.TYPE_CLASS_NUMBER | InputType.TYPE_NUMBER_VARIATION_PASSWORD);
        code.setFilters(new android.text.InputFilter[]{new android.text.InputFilter.LengthFilter(6)});
        code.setSingleLine(true); code.setSaveEnabled(false); body.addView(code);
        action(body,"페어링",() -> {
            String value = code.getText().toString(); code.setText("");
            if (!value.matches("[0-9]{6}")) { code.setError("6자리를 입력하세요."); return; }
            startForegroundService(new Intent(this,WirelessPairingService.class).setAction(WirelessPairingService.PAIR).putExtra("code",value));
        });
        action(body,"기존 페어링으로 다시 연결",() -> startForegroundService(new Intent(this,WirelessPairingService.class).setAction(WirelessPairingService.CONNECT)));
        action(body,"Stock으로 돌아가기",() -> {
            stopService(new Intent(this,WirelessPairingService.class));
            getSharedPreferences("connection",0).edit().putString("transport","stock").remove("rootAllowed").putBoolean("rootAvailable",false)
                    .putString("wirelessStatus","Stock · 앱 권한으로 실행합니다. 페어링 키는 다음 연결을 위해 보관합니다.").apply();
            finish();
        });
        setContentView(scroll);
    }
    private TextView add(LinearLayout body,String value,int size) {
        var text = new TextView(this); text.setText(value); text.setTextSize(size);
        text.setTextColor(getColor(R.color.text_primary)); text.setPadding(0,24,0,16); body.addView(text); return text;
    }
    private void action(LinearLayout body,String name,Runnable action) {
        var button = new Button(this); button.setText(name); button.setAllCaps(false);
        button.setMinHeight(Math.round(48*getResources().getDisplayMetrics().density));
        button.setOnClickListener(v->action.run()); body.addView(button,new LinearLayout.LayoutParams(-1,-2));
    }
    @Override public void onRequestPermissionsResult(int request,String[] permissions,int[] results) {
        super.onRequestPermissionsResult(request,permissions,results);
        if (request==41 && results.length>0 && results[0]==android.content.pm.PackageManager.PERMISSION_GRANTED)
            startForegroundService(new Intent(this,WirelessPairingService.class));
    }
    @Override protected void onResume() { super.onResume(); refresh.post(update); }
    @Override protected void onPause() { refresh.removeCallbacks(update); super.onPause(); }
}
