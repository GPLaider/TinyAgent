package io.github.gplaider.tinyagent;

import android.app.*;
import android.content.*;
import android.os.Bundle;
import android.graphics.BitmapFactory;
import android.widget.*;
import android.webkit.MimeTypeMap;
import androidx.core.content.FileProvider;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.Locale;

/** A selected workspace file, readable URI grants, and explicit user actions. */
public final class ArtifactActivity extends Activity {
    private File file;
    private String relative;
    private String mime;
    @Override public void onCreate(Bundle saved) {
        super.onCreate(saved);
        try {
            relative = getIntent().getStringExtra("path");
            File root = new LocalLinuxRuntime(this).workspace.getCanonicalFile();
            if (relative == null || relative.isEmpty()) throw new IOException("파일 경로가 없습니다.");
            file = new File(root, relative).getCanonicalFile();
            if (!file.toPath().startsWith(root.toPath()) || !file.isFile()) throw new IOException("작업공간 파일을 찾을 수 없습니다.");
            String name = file.getName();
            String ext = name.substring(name.lastIndexOf('.') + 1).toLowerCase(Locale.ROOT);
            mime = MimeTypeMap.getSingleton().getMimeTypeFromExtension(ext);
            if (ext.equals("log") || ext.equals("txt")) mime = "text/plain";
            if (mime == null) mime = "application/octet-stream";
            LinearLayout body = new LinearLayout(this); body.setOrientation(LinearLayout.VERTICAL);
            float density=getResources().getDisplayMetrics().density;
            int pad = (int)(12 * density);
            body.setPadding(pad,pad,pad,pad);
            ScrollView scroll = new ScrollView(this); scroll.addView(body); setContentView(scroll);
            TextView title = new TextView(this); title.setText(name); title.setTextSize(12); title.setAlpha(0.7f); title.setSingleLine(true); title.setEllipsize(android.text.TextUtils.TruncateAt.MIDDLE); body.addView(title);
            LinearLayout actions=new LinearLayout(this); body.addView(actions);
            if (ext.equals("apk")) button(actions,"설치",()->{startActivity(new Intent(this,InstallerActivity.class).putExtra("workspacePath",relative));finish();});
            else if (mime.startsWith("image/")) button(actions,"보기",()->preview(true));
            else if (mime.startsWith("video/")) button(actions,"재생",this::previewVideo);
            else if (mime.startsWith("text/") || mime.equals("application/json") || mime.endsWith("+json")) button(actions,"열기",()->preview(false));
            button(actions,"저장",()->{startActivity(new Intent(this,InstallerActivity.class).putExtra("exportPath",relative));finish();});
            button(actions,"공유",this::share);
            var metrics=getWindowManager().getCurrentWindowMetrics();
            var bars=metrics.getWindowInsets().getInsetsIgnoringVisibility(android.view.WindowInsets.Type.systemBars() | android.view.WindowInsets.Type.displayCutout());
            int width=Math.min((int)(224*density),metrics.getBounds().width()-bars.left-bars.right-2*pad);
            body.measure(android.view.View.MeasureSpec.makeMeasureSpec(width,android.view.View.MeasureSpec.EXACTLY),android.view.View.MeasureSpec.makeMeasureSpec(0,android.view.View.MeasureSpec.UNSPECIFIED));
            var params=getWindow().getAttributes();
            params.gravity=android.view.Gravity.TOP|android.view.Gravity.LEFT;
            params.width=width; params.height=android.view.ViewGroup.LayoutParams.WRAP_CONTENT;
            int availableHeight=metrics.getBounds().height()-bars.top-bars.bottom;
            int tapY=getIntent().getIntExtra("tapY",bars.top)-bars.top;
            int height=body.getMeasuredHeight();
            params.x=Math.max(pad,Math.min(getIntent().getIntExtra("tapX",pad),metrics.getBounds().width()-width-pad-bars.right));
            int below=tapY+pad/2;
            params.y=Math.max(pad,Math.min(below+height<=availableHeight-pad?below:tapY-height-pad/2,availableHeight-height-pad));
            params.dimAmount=0; getWindow().setAttributes(params);
            getWindow().setElevation(12*density);
        } catch (Exception e) { error(e); }
    }
    private void button(LinearLayout body,String label,Runnable action) {
        Button b=new Button(this); b.setText(label); b.setTextSize(16);
        b.setMinWidth(0); b.setMinimumWidth(0); b.setPadding(0,0,0,0);
        android.util.TypedValue ripple=new android.util.TypedValue(); getTheme().resolveAttribute(android.R.attr.selectableItemBackground,ripple,true); b.setBackgroundResource(ripple.resourceId);
        b.setOnClickListener(v->action.run()); body.addView(b,new LinearLayout.LayoutParams(0,(int)(48*getResources().getDisplayMetrics().density),1));
    }
    private void share() {
        try {
            var uri=FileProvider.getUriForFile(this,getPackageName()+".artifacts",file);
            Intent send=new Intent(Intent.ACTION_SEND).setType(mime).putExtra(Intent.EXTRA_STREAM,uri)
                    .addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
            send.setClipData(ClipData.newRawUri(file.getName(),uri));
            startActivity(Intent.createChooser(send,"파일 공유"));
        } catch (Exception e) { error(e); }
    }
    private void previewVideo() {
        try {
            var uri=FileProvider.getUriForFile(this,getPackageName()+".artifacts",file);
            VideoView video=new VideoView(this);
            MediaController controls=new MediaController(this); controls.setAnchorView(video); video.setMediaController(controls);
            var dialog=new AlertDialog.Builder(this).setTitle(file.getName()).setView(video).setPositiveButton("닫기",null).create();
            dialog.setOnDismissListener(d->{controls.hide();video.stopPlayback();});
            video.setOnErrorListener((player,what,extra)->{dialog.dismiss();
                new AlertDialog.Builder(this).setTitle("영상 재생 불가").setMessage("이 기기에서 지원하지 않거나 손상된 영상입니다. 저장·공유로 다른 플레이어에서 열 수 있습니다.").setPositiveButton("확인",null).show();return true;});
            dialog.show();
            dialog.getWindow().setLayout(-1,(int)(getResources().getDisplayMetrics().heightPixels*0.75));
            video.setOnPreparedListener(player->{
                // VideoView attaches controls to its parent during preparation; keep them over the video.
                controls.setAnchorView(video);
                video.start();controls.show(5000);
            });
            video.setVideoURI(uri);
        } catch(Exception e){error(e);}
    }
    private void preview(boolean image) {
        new Thread(()->{
            try {
                if (image) {
                    var bounds=new BitmapFactory.Options(); bounds.inJustDecodeBounds=true;
                    BitmapFactory.decodeFile(file.toString(),bounds);
                    if(bounds.outWidth<=0 || bounds.outHeight<=0) throw new IOException("지원하지 않거나 손상된 이미지입니다.");
                    var options=new BitmapFactory.Options(); options.inSampleSize=1;
                    while(Math.max(bounds.outWidth,bounds.outHeight)/options.inSampleSize>2048) options.inSampleSize*=2;
                    var bitmap=BitmapFactory.decodeFile(file.toString(),options);
                    if(bitmap==null)throw new IOException("이미지를 열 수 없습니다.");
                    runOnUiThread(()->{if(isFinishing()||isDestroyed()){bitmap.recycle();return;}
                        ImageView view=new ImageView(this);view.setImageBitmap(bitmap);view.setAdjustViewBounds(true);
                        new AlertDialog.Builder(this).setTitle(file.getName()).setView(view).setPositiveButton("닫기",null).show();});
                } else {
                    byte[] bytes;
                    try(var input=new FileInputStream(file);var output=new ByteArrayOutputStream()){
                        byte[] buffer=new byte[8192];
                        while(output.size()<262145){int n=input.read(buffer,0,Math.min(buffer.length,262145-output.size()));if(n<0)break;output.write(buffer,0,n);}
                        bytes=output.toByteArray();
                    }
                    String value=new String(bytes,0,Math.min(bytes.length,262144),StandardCharsets.UTF_8)
                            +(bytes.length>262144?"\n\n[미리보기는 앞부분 256 KiB까지 표시합니다. 저장·공유는 전체 파일입니다.]":"");
                    runOnUiThread(()->{if(isFinishing()||isDestroyed())return;
                        TextView text=new TextView(this);text.setText(value);text.setTextIsSelectable(true);text.setTextSize(16);text.setPadding(24,16,24,16);
                        ScrollView scroll=new ScrollView(this);scroll.addView(text);
                        new AlertDialog.Builder(this).setTitle(file.getName()).setView(scroll).setPositiveButton("닫기",null).show();});
                }
            } catch(Exception e){runOnUiThread(()->error(e));}
        },"artifact-preview").start();
    }
    private void error(Exception e){if(!isFinishing()&&!isDestroyed())new AlertDialog.Builder(this).setTitle("파일을 열 수 없습니다").setMessage(e.getMessage()).setPositiveButton("닫기",(d,w)->finish()).show();}
}
