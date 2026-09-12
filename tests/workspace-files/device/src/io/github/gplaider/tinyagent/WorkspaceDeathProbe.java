package io.github.gplaider.tinyagent;

import android.app.*;
import android.content.*;
import android.database.Cursor;
import android.net.Uri;
import android.os.*;
import android.view.*;
import android.widget.TextView;
import java.nio.file.*;
import java.util.concurrent.*;

/** Test-only process-death control and lifecycle observation, excluded from production. */
public final class WorkspaceDeathProbe extends Application implements Application.ActivityLifecycleCallbacks {
    private static final String OWNER="io.github.gplaider.tinyagent.workspaceprobe";
    private static InstallerActivity current;
    private static boolean preparing,pendingPicker,restored,saved,stopped;
    @Override public void onCreate(){super.onCreate();registerActivityLifecycleCallbacks(this);}
    public void onActivityCreated(Activity activity,Bundle state){
        if(activity instanceof InstallerActivity installer){current=installer;restored=state!=null;saved=false;stopped=false;}
    }
    public void onActivityResumed(Activity activity){
        if(activity==current&&preparing){
            preparing=false;
            try {
                var field=InstallerActivity.class.getDeclaredField("pendingExport");field.setAccessible(true);field.set(current,"death.bin");
                if(pendingPicker)current.startActivityForResult(new Intent().setClassName(OWNER+".client","io.github.gplaider.tinyagent.WorkspaceDeathPicker"),20);
                else current.onActivityResult(20,Activity.RESULT_OK,new Intent().setData(Uri.parse("content://"+OWNER+".destination/export")));
            }catch(Exception error){throw new AssertionError(error);}
        }
        if(activity==current)stopped=false;
    }
    public void onActivitySaveInstanceState(Activity activity,Bundle state){if(activity==current)saved=true;}
    public void onActivityStopped(Activity activity){if(activity==current)stopped=true;}
    public void onActivityDestroyed(Activity activity){if(activity==current)current=null;}
    public void onActivityStarted(Activity activity){}
    public void onActivityPaused(Activity activity){}
    private static String text(View view){
        StringBuilder out=new StringBuilder();if(view instanceof TextView label)out.append(label.getText()).append(' ');
        if(view instanceof ViewGroup group)for(int i=0;i<group.getChildCount();i++)out.append(text(group.getChildAt(i)));
        return out.toString();
    }
    public static final class Control extends ContentProvider {
        public boolean onCreate(){return true;}
        @Override public Bundle call(String method,String arg,Bundle extras){
            if(!OWNER.equals(getContext().getPackageName())||!(OWNER+".client").equals(getCallingPackage()))throw new SecurityException("Paired probe only");
            var result=new java.util.concurrent.atomic.AtomicReference<Bundle>();
            var failure=new java.util.concurrent.atomic.AtomicReference<Throwable>();
            CountDownLatch done=new CountDownLatch(1);
            new Handler(Looper.getMainLooper()).post(()->{
                try{result.set(action(method,arg));}catch(Throwable error){failure.set(error);}finally{done.countDown();}
            });
            try{if(!done.await(5,TimeUnit.SECONDS))throw new IllegalStateException("Control main-thread timeout");}
            catch(InterruptedException error){Thread.currentThread().interrupt();throw new IllegalStateException(error);}
            if(failure.get()!=null)throw new IllegalStateException(failure.get());
            return result.get();
        }
        private Bundle action(String method,String arg)throws Exception {
            if(method.equals("prepare")||method.equals("prepare-picker")){
                if(current!=null)throw new IllegalStateException("Unexpected existing Activity");
                Path root=Files.createDirectories(getContext().getFilesDir().toPath().resolve("linux/workspace"));
                byte[] payload=new byte[512*1024];
                if(method.equals("prepare-picker"))new java.util.Random(80755).nextBytes(payload);
                Files.write(root.resolve("death.bin"),payload);
                WorkspaceProbeDestination.reset();preparing=true;pendingPicker=method.equals("prepare-picker");
            }else if(method.equals("die")){
                int pid=android.os.Process.myPid();
                if(!saved||!stopped||current==null||pid!=Integer.parseInt(arg))throw new IllegalStateException("Expected stopped owner PID");
                new Handler(Looper.getMainLooper()).postDelayed(()->android.os.Process.killProcess(pid),300);
            }else if(method.equals("release")){
                WorkspaceProbeDestination.release.countDown();
            }else if(method.equals("background")){
                if(current==null||!current.moveTaskToBack(true))throw new IllegalStateException("Could not background probe task");
            }else if(method.equals("finish")){
                if(current!=null)current.finishAndRemoveTask();
            }else if(!method.equals("snapshot"))throw new IllegalArgumentException(method);
            Bundle out=new Bundle();out.putBoolean("hasActivity",current!=null);out.putInt("pid",android.os.Process.myPid());out.putBoolean("saved",saved);out.putBoolean("stopped",stopped);
            out.putBoolean("restored",restored);out.putInt("opens",WorkspaceProbeDestination.opens.get());out.putLong("bytes",WorkspaceProbeDestination.bytes);out.putString("sha256",WorkspaceProbeDestination.sha256);
            if(current!=null){out.putInt("task",current.getTaskId());out.putString("text",text(current.getWindow().getDecorView()));}
            return out;
        }
        public Cursor query(Uri uri,String[] projection,String selection,String[] args,String order){throw new UnsupportedOperationException();}
        public String getType(Uri uri){return null;}
        public Uri insert(Uri uri,ContentValues values){throw new UnsupportedOperationException();}
        public int update(Uri uri,ContentValues values,String selection,String[] args){throw new UnsupportedOperationException();}
        public int delete(Uri uri,String selection,String[] args){throw new UnsupportedOperationException();}
    }
}
