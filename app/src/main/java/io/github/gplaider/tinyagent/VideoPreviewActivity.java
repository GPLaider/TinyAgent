package io.github.gplaider.tinyagent;

import android.app.Activity;
import android.app.AlertDialog;
import android.os.Bundle;
import android.view.Gravity;
import android.view.WindowInsets;
import android.widget.*;
import androidx.core.content.FileProvider;
import java.io.File;
import java.io.IOException;

/** Playback and controls share one native window; no floating controller intercepts close. */
public final class VideoPreviewActivity extends Activity {
    private VideoView video;
    private SeekBar seek;
    private Button play;
    private TextView elapsed;
    private boolean seeking;
    private int position;
    private boolean resumePlayback=true, prepared, foreground;
    private final Runnable progress=new Runnable(){public void run(){
        if(!prepared||!foreground)return;
        int duration=Math.max(1,video.getDuration()), current=video.getCurrentPosition();
        if(!seeking)seek.setProgress((int)(1000L*current/duration));
        elapsed.setText(String.format(java.util.Locale.ROOT,"%d:%02d / %d:%02d",current/60000,current/1000%60,duration/60000,duration/1000%60));
        play.setText(video.isPlaying()?"일시정지":"재생");
        video.postDelayed(this,500);
    }};

    @Override public void onCreate(Bundle saved) {
        super.onCreate(saved);
        if(saved!=null){position=saved.getInt("position");resumePlayback=saved.getBoolean("playing");}
        try {
            String relative=getIntent().getStringExtra("path");
            File root=new LocalLinuxRuntime(this).workspace.getCanonicalFile();
            if(relative==null||relative.isEmpty())throw new IOException("파일 경로가 없습니다.");
            File file=new File(root,relative).getCanonicalFile();
            if(!file.toPath().startsWith(root.toPath())||!file.isFile())throw new IOException("작업공간 파일을 찾을 수 없습니다.");
            LinearLayout body=new LinearLayout(this);body.setOrientation(LinearLayout.VERTICAL);
            body.setOnApplyWindowInsetsListener((view,insets)->{
                var bars=insets.getInsets(WindowInsets.Type.systemBars()|WindowInsets.Type.displayCutout());
                view.setPadding(bars.left,bars.top,bars.right,bars.bottom);return insets;
            });
            LinearLayout header=new LinearLayout(this);header.setGravity(Gravity.CENTER_VERTICAL);
            TextView title=new TextView(this);title.setText(file.getName());title.setTextSize(18);
            title.setSingleLine(true);title.setEllipsize(android.text.TextUtils.TruncateAt.MIDDLE);
            int dp=(int)(getResources().getDisplayMetrics().density*16);
            title.setPadding(dp,0,dp,0);header.addView(title,new LinearLayout.LayoutParams(0,-2,1));
            Button close=new Button(this);close.setText("닫기");close.setMinHeight(dp*3);close.setOnClickListener(v->finish());header.addView(close);
            body.addView(header);
            FrameLayout frame=new FrameLayout(this);frame.setBackgroundColor(android.graphics.Color.BLACK);
            body.addView(frame,new LinearLayout.LayoutParams(-1,0,1));
            video=new VideoView(this);frame.addView(video,new FrameLayout.LayoutParams(-1,-1,Gravity.CENTER));
            LinearLayout controls=new LinearLayout(this);controls.setGravity(Gravity.CENTER_VERTICAL);
            Button back=new Button(this);back.setText("−10초");back.setContentDescription("10초 뒤로");back.setOnClickListener(v->video.seekTo(Math.max(0,video.getCurrentPosition()-10000)));controls.addView(back);
            play=new Button(this);play.setText("재생");play.setOnClickListener(v->{if(video.isPlaying())video.pause();else video.start();video.removeCallbacks(progress);video.post(progress);});controls.addView(play);
            Button next=new Button(this);next.setText("+10초");next.setContentDescription("10초 앞으로");next.setOnClickListener(v->video.seekTo(Math.min(video.getDuration(),video.getCurrentPosition()+10000)));controls.addView(next);
            body.addView(controls);
            seek=new SeekBar(this);seek.setMax(1000);seek.setContentDescription("영상 재생 위치");seek.setMinimumHeight(dp*3);body.addView(seek);
            elapsed=new TextView(this);elapsed.setGravity(Gravity.CENTER);body.addView(elapsed);
            seek.setOnSeekBarChangeListener(new SeekBar.OnSeekBarChangeListener(){
                public void onStartTrackingTouch(SeekBar bar){seeking=true;}
                public void onStopTrackingTouch(SeekBar bar){seeking=false;}
                public void onProgressChanged(SeekBar bar,int value,boolean user){if(user&&prepared)video.seekTo((int)((long)video.getDuration()*value/1000));}
            });
            setContentView(body);
            video.setOnPreparedListener(player->{prepared=true;video.seekTo(position);if(foreground){if(resumePlayback)video.start();video.removeCallbacks(progress);video.post(progress);}});
            video.setOnCompletionListener(player->resumePlayback=false);
            video.setOnErrorListener((player,what,extra)->{prepared=false;video.removeCallbacks(progress);
                new AlertDialog.Builder(this).setTitle("영상 재생 불가").setMessage("이 기기에서 지원하지 않거나 손상된 영상입니다. 저장·공유로 다른 플레이어에서 열 수 있습니다.").setPositiveButton("닫기",(d,w)->finish()).setOnCancelListener(d->finish()).show();return true;});
            video.setVideoURI(FileProvider.getUriForFile(this,getPackageName()+".artifacts",file));
        } catch(Exception e){new AlertDialog.Builder(this).setTitle("파일을 열 수 없습니다").setMessage(e.getMessage()).setPositiveButton("닫기",(d,w)->finish()).setOnCancelListener(d->finish()).show();}
    }
    @Override protected void onPause(){if(prepared){resumePlayback=video.isPlaying();position=video.getCurrentPosition();video.pause();}foreground=false;if(video!=null)video.removeCallbacks(progress);super.onPause();}
    @Override protected void onResume(){super.onResume();foreground=true;if(prepared){if(resumePlayback)video.start();video.removeCallbacks(progress);video.post(progress);}}
    @Override protected void onSaveInstanceState(Bundle out){super.onSaveInstanceState(out);out.putInt("position",prepared?video.getCurrentPosition():position);out.putBoolean("playing",prepared&&foreground?video.isPlaying():resumePlayback);}
    @Override protected void onDestroy(){if(video!=null){video.removeCallbacks(progress);video.stopPlayback();}super.onDestroy();}
}
