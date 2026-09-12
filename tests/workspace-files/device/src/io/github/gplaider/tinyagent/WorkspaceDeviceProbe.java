package io.github.gplaider.tinyagent;

import android.app.Activity;
import android.app.Instrumentation;
import android.content.Context;
import android.content.Intent;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.media.MediaMetadataRetriever;
import android.net.Uri;
import android.os.Bundle;
import android.os.ParcelFileDescriptor;
import android.system.Os;
import android.system.OsConstants;
import androidx.core.content.FileProvider;
import java.io.*;
import java.nio.*;
import java.nio.file.*;

/** Isolated test APK: the production helper/provider run under real Android UIDs. */
public final class WorkspaceDeviceProbe extends Instrumentation {
    private static final String OWNER="io.github.gplaider.tinyagent.workspaceprobe";
    private static final Uri SHARED=Uri.parse("content://"+OWNER+".artifacts/workspace/shared.txt");
    private final StringBuilder report=new StringBuilder();
    private Bundle args;
    interface Checked { void run() throws Exception; }
    private void require(boolean okay,String label) {
        if(!okay)throw new AssertionError(label);
        report.append("PASS ").append(label).append('\n');
    }
    private void reject(String label,Checked checked)throws Exception {
        try {checked.run();throw new AssertionError(label+" accepted");}
        catch(IOException|SecurityException expected){report.append("PASS ").append(label).append('\n');}
    }
    private static Path write(Path path,String value)throws IOException {
        return Files.write(path,value.getBytes(java.nio.charset.StandardCharsets.UTF_8));
    }
    private String text(InputStream input)throws Exception {
        try(input){return new String(input.readAllBytes(),java.nio.charset.StandardCharsets.UTF_8);}
    }
    @Override public void onCreate(Bundle arguments){super.onCreate(arguments);args=arguments;start();}
    @Override public void onStart(){
        Bundle result=new Bundle();
        try {
            Context context=getTargetContext();
            require(android.os.Process.myUid()>=10000,"app UID="+android.os.Process.myUid());
            String mode=args.getString("mode","owner");
            if(mode.startsWith("death-"))death(context,mode);
            else if(mode.equals("owner"))owner(context);
            else if(mode.equals("activity-recreate"))report.append(WorkspaceActivityProbe.recreate(this,false));
            else if(mode.equals("activity-recreate-failure"))report.append(WorkspaceActivityProbe.recreate(this,true));
            else if(mode.startsWith("activity-picker-"))report.append(WorkspaceActivityProbe.picker(this,mode.substring("activity-picker-".length())));
            else if(mode.equals("activity-dismiss"))report.append(WorkspaceActivityProbe.dismiss(this));
            else if(mode.equals("activity-status-switch"))report.append(WorkspaceActivityProbe.statusSwitch(this));
            else if(mode.equals("activity-isolation"))report.append(WorkspaceActivityProbe.isolation(this));
            else if(mode.equals("client-denied"))reject("ungranted/revoked cross-UID read",()->text(context.getContentResolver().openInputStream(SHARED)));
            else if(mode.equals("client-granted")) {
                Uri control=Uri.parse("content://"+OWNER+".control");
                context.getContentResolver().call(control,"grant",null,null);
                require(text(context.getContentResolver().openInputStream(SHARED)).equals("SHARED"),"granted cross-UID Binder read");
                reject("read grant cannot write",()->{try(var ignored=context.getContentResolver().openFileDescriptor(SHARED,"w")) {}});
                Uri other=Uri.parse("content://"+OWNER+".artifacts/workspace/private.txt");
                reject("read grant limited to selected URI",()->text(context.getContentResolver().openInputStream(other)));
                context.getContentResolver().call(control,"revoke",null,null);
                reject("revoked grant denied in same client process",()->text(context.getContentResolver().openInputStream(SHARED)));
            } else throw new IllegalArgumentException(mode);
            result.putString("stream",report+"PASS mode="+mode+"\n");finish(-1,result);
        } catch(Throwable failure){result.putString("stream",report+"FAIL "+android.util.Log.getStackTraceString(failure));finish(1,result);}
    }
    private Bundle deathCall(Context context,String method,String arg)throws Exception {
        try(var client=context.getContentResolver().acquireUnstableContentProviderClient(Uri.parse("content://"+OWNER+".death"))){
            if(client==null)throw new AssertionError("Death control missing");
            return client.call(method,arg,null);
        }
    }
    private void death(Context context,String mode)throws Exception {
        require(context.getPackageName().equals(OWNER+".client"),"external client controls isolated owner death");
        if(mode.startsWith("death-picker-")){deathPicker(context,mode.substring("death-picker-".length()));return;}
        String phase=args.getString("phase","running");
        if(mode.equals("death-prepare")){
            deathCall(context,"prepare",null);
            context.startActivity(new Intent().setClassName(OWNER,"io.github.gplaider.tinyagent.WorkspaceDeathEntry").addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));
            Bundle snapshot;
            long deadline=android.os.SystemClock.elapsedRealtime()+5000;
            do{snapshot=deathCall(context,"snapshot",null);if(snapshot.getInt("opens")==1)break;Thread.sleep(20);}
            while(android.os.SystemClock.elapsedRealtime()<deadline);
            require(snapshot.getInt("opens")==1&&snapshot.getString("text","").contains("파일 저장 중"),"copy blocked before process death");
            if(phase.equals("completed-before-save"))deathComplete(context);
            deathCall(context,"background",null);deadline=android.os.SystemClock.elapsedRealtime()+5000;
            do{snapshot=deathCall(context,"snapshot",null);if(snapshot.getBoolean("saved")&&snapshot.getBoolean("stopped"))break;Thread.sleep(20);}
            while(android.os.SystemClock.elapsedRealtime()<deadline);
            require(snapshot.getBoolean("saved")&&snapshot.getBoolean("stopped"),"Android saved and stopped original task");
            if(phase.equals("completed-after-save"))deathComplete(context);
            report.append("DEATH_TARGET pid=").append(snapshot.getInt("pid")).append(" task=").append(snapshot.getInt("task")).append('\n');
        }else if(mode.equals("death-restore")){
            context.startActivity(new Intent().setClassName(OWNER,"io.github.gplaider.tinyagent.WorkspaceDeathEntry").addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));
            Bundle snapshot;
            long deadline=android.os.SystemClock.elapsedRealtime()+5000;
            do{snapshot=deathCall(context,"snapshot",null);if(snapshot.getBoolean("restored")&&!snapshot.getBoolean("stopped"))break;Thread.sleep(20);}
            while(android.os.SystemClock.elapsedRealtime()<deadline);
            require(snapshot.getBoolean("restored"),"Android delivered saved Bundle after main process restart");
            require(snapshot.getInt("pid")!=Integer.parseInt(args.getString("oldpid")),"new owner PID");
            require(snapshot.getInt("task")==Integer.parseInt(args.getString("task")),"same Android task restored");
            require(snapshot.getInt("opens")==0,"dead export not replayed");
            String text=snapshot.getString("text","");report.append("RESTORED_UI ").append(text).append('\n');
            if(phase.equals("completed-before-save"))
                require(text.contains("파일 저장 완료")&&!text.contains("결과를 확인할 수 없습니다"),"saved completed result survives process death");
            else require(text.contains("결과를 확인할 수 없습니다")&&!text.contains("파일 저장 중")&&!text.contains("파일 저장 완료"),"unconfirmed export result is reported truthfully");
            report.append("PASS death phase=").append(phase).append('\n');
            deathFinish(context);
        }else throw new IllegalArgumentException(mode);
    }
    private void deathPicker(Context context,String resultMode)throws Exception {
        var monitor=addMonitor(WorkspaceDeathPicker.class.getName(),null,false);
        WorkspaceDeathPicker picker=null;
        try {
            deathCall(context,"prepare-picker",null);
            context.startActivity(new Intent().setClassName(OWNER,"io.github.gplaider.tinyagent.WorkspaceDeathEntry").addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));
            picker=(WorkspaceDeathPicker)monitor.waitForActivityWithTimeout(5000);
            require(picker!=null,"paired-client picker is open");
            Bundle before;long deadline=android.os.SystemClock.elapsedRealtime()+5000;
            do{before=deathCall(context,"snapshot",null);if(before.getBoolean("saved")&&before.getBoolean("stopped"))break;Thread.sleep(20);}
            while(android.os.SystemClock.elapsedRealtime()<deadline);
            require(before.getBoolean("saved")&&before.getBoolean("stopped")&&before.getInt("opens")==0,"pending owner saved/stopped without copying");
            int oldPid=before.getInt("pid"),task=before.getInt("task");
            deathCall(context,"die",Integer.toString(oldPid));
            boolean dead=false;deadline=android.os.SystemClock.elapsedRealtime()+5000;
            do {
                try{android.system.Os.kill(oldPid,0);}
                catch(android.system.ErrnoException error){
                    if(error.errno==android.system.OsConstants.ESRCH){dead=true;break;}
                    if(error.errno!=android.system.OsConstants.EPERM)throw error;
                }
                Thread.sleep(20);
            }while(android.os.SystemClock.elapsedRealtime()<deadline);
            require(dead,"pending owner process death confirmed by ESRCH");
            WorkspaceDeathPicker pending=picker;
            Intent result=resultMode.equals("save")?new Intent().setData(Uri.parse("content://"+OWNER+".destination/export"))
                :resultMode.equals("empty")?new Intent():null;
            runOnMainSync(()->pending.deliver(resultMode.equals("cancel")?Activity.RESULT_CANCELED:Activity.RESULT_OK,result));
            Bundle after;deadline=android.os.SystemClock.elapsedRealtime()+5000;
            do{after=deathCall(context,"snapshot",null);if(after.getBoolean("restored")&&!after.getBoolean("stopped"))break;Thread.sleep(20);}
            while(android.os.SystemClock.elapsedRealtime()<deadline);
            require(after.getBoolean("restored")&&after.getInt("pid")!=oldPid&&after.getInt("task")==task,"picker result restored same task with OS Bundle and new PID");
            if(resultMode.equals("save")){
                deathComplete(context);deadline=android.os.SystemClock.elapsedRealtime()+5000;
                do{after=deathCall(context,"snapshot",null);if(after.getString("sha256")!=null)break;Thread.sleep(20);}
                while(android.os.SystemClock.elapsedRealtime()<deadline);
                StringBuilder expected=new StringBuilder();
                byte[] payload=new byte[512*1024];new java.util.Random(80755).nextBytes(payload);
                for(byte value:java.security.MessageDigest.getInstance("SHA-256").digest(payload))expected.append(String.format("%02x",value&255));
                require(after.getInt("opens")==1&&after.getLong("bytes")==512*1024&&expected.toString().equals(after.getString("sha256")),"pending source survives death and copies once with matching SHA-256");
            }else {
                require(after.getInt("opens")==0&&after.getString("text","").contains("내보내기를 취소"),"cancelled/invalid result after death opens no output");
            }
            report.append("PENDING_DEATH oldpid=").append(oldPid).append(" newpid=").append(after.getInt("pid")).append(" task=").append(task).append(" result=").append(resultMode).append('\n');
            deathFinish(context);
        }finally{
            removeMonitor(monitor);WorkspaceDeathPicker pending=picker;
            if(pending!=null)runOnMainSync(()->{if(!pending.isDestroyed())pending.finish();});
        }
    }
    private void deathFinish(Context context)throws Exception {
        deathCall(context,"finish",null);Bundle snapshot;
        long deadline=android.os.SystemClock.elapsedRealtime()+5000;
        do{snapshot=deathCall(context,"snapshot",null);if(!snapshot.getBoolean("hasActivity"))break;Thread.sleep(20);}
        while(android.os.SystemClock.elapsedRealtime()<deadline);
        require(!snapshot.getBoolean("hasActivity"),"probe task removed and Activity destruction confirmed");
    }
    private void deathComplete(Context context)throws Exception {
        deathCall(context,"release",null);Bundle snapshot;
        long deadline=android.os.SystemClock.elapsedRealtime()+5000;
        do{snapshot=deathCall(context,"snapshot",null);if(snapshot.getString("text","").contains("파일 저장 완료"))break;Thread.sleep(20);}
        while(android.os.SystemClock.elapsedRealtime()<deadline);
        require(snapshot.getString("text","").contains("파일 저장 완료"),"copy completed before killing owner");
    }
    private int providerPid(Context context) {
        for(var process:context.getSystemService(android.app.ActivityManager.class).getRunningAppProcesses())
            if(process.processName.equals(OWNER+":files")&&process.uid==android.os.Process.myUid())return process.pid;
        throw new AssertionError("Owned provider process missing");
    }
    private int fdCount(int pid) {
        String[] descriptors=new File("/proc/"+pid+"/fd").list();
        if(descriptors==null)throw new AssertionError("Cannot inspect owned process FD count");
        return descriptors.length;
    }
    private void owner(Context context)throws Exception {
        require(context.getPackageName().equals(OWNER),"owner package");
        Path files=context.getFilesDir().toPath();
        Path root=Files.createDirectories(files.resolve("linux/workspace"));
        Path good=write(root.resolve("shared.txt"),"SHARED");
        write(root.resolve("private.txt"),"UNGRANTED");
        Path secret=write(files.resolve("outside.txt"),"PRIVATE");
        WorkspaceFiles workspace=new WorkspaceFiles(context.getFilesDir());
        report.append("filesDir=").append(files).append(" canonical=").append(files.toFile().getCanonicalPath()).append('\n');
        try(var descriptor=workspace.open("shared.txt")) {
            report.append("fdTarget=").append(Os.readlink("/proc/self/fd/"+descriptor.getFd())).append('\n');
            require((Os.fcntlInt(descriptor.getFileDescriptor(),OsConstants.F_GETFD,0)&OsConstants.FD_CLOEXEC)!=0,"CLOEXEC");
            require(text(new ParcelFileDescriptor.AutoCloseInputStream(descriptor)).equals("SHARED"),"returned FD survives original close");
        }
        for(String value:new String[]{null,"","/shared.txt","../outside.txt","shared.txt\0tail","."})
            reject("malformed path "+value,()->{try(var ignored=workspace.open(value)) {}});
        Path link=root.resolve("link");Files.deleteIfExists(link);Files.createSymbolicLink(link,secret);
        reject("outside symlink",()->{try(var ignored=workspace.open("link")) {}});
        Path denied=write(root.resolve("denied.txt"),"DENIED");Os.chmod(denied.toString(),0);
        try{reject("mode 000 permission denial",()->{try(var ignored=workspace.open("denied.txt")) {}});}
        finally{Os.chmod(denied.toString(),0600);}
        Path fifo=root.resolve("fifo");Files.deleteIfExists(fifo);Os.mkfifo(fifo.toString(),0600);
        reject("FIFO rejected",()->{try(var ignored=workspace.open("fifo")) {}});
        Path held=write(root.resolve("held.txt"),"ORIGINAL");
        try(var input=workspace.input("held.txt")) {
            Files.delete(held);write(held,"REPLACEMENT");
            require(text(input).equals("ORIGINAL"),"FD pins opened inode after unlink");
        }
        Path named=write(root.resolve("한글 + # 😀.txt"),"UNICODE");
        Uri encoded=FileProvider.getUriForFile(context,OWNER+".artifacts",named.toFile());
        require(text(context.getContentResolver().openInputStream(encoded)).equals("UNICODE"),"production FileProvider URI plus Binder Unicode read");
        reject("owner provider write rejected",()->{try(var ignored=context.getContentResolver().openFileDescriptor(SHARED,"w")) {}});
        // Warm remote provider/parcel code before measuring local descriptor stability.
        text(context.getContentResolver().openInputStream(SHARED));
        int before=fdCount(android.os.Process.myPid());
        int serverPid=providerPid(context), serverBefore=fdCount(serverPid);
        for(int i=0;i<300;i++) {
            text(workspace.input("shared.txt"));
            text(context.getContentResolver().openInputStream(SHARED));
            try{workspace.open("link");throw new AssertionError("outside link");}catch(IOException expected){}
        }
        int after=fdCount(android.os.Process.myPid()), serverAfter=fdCount(serverPid);
        require(before==after,"300 local/Binder/denial FD cycles "+before+" -> "+after);
        require(serverBefore==serverAfter,"300 remote provider FD cycles "+serverBefore+" -> "+serverAfter);
        Path image=root.resolve("image.png");Bitmap bitmap=Bitmap.createBitmap(32,24,Bitmap.Config.ARGB_8888);
        try(var output=Files.newOutputStream(image)){require(bitmap.compress(Bitmap.CompressFormat.PNG,100,output),"PNG fixture");}finally{bitmap.recycle();}
        try(var fd=workspace.open("image.png")) {
            BitmapFactory.Options bounds=new BitmapFactory.Options();bounds.inJustDecodeBounds=true;
            BitmapFactory.decodeFileDescriptor(fd.getFileDescriptor(),null,bounds);
            Bitmap decoded=BitmapFactory.decodeFileDescriptor(fd.getFileDescriptor());
            require(bounds.outWidth==32&&bounds.outHeight==24&&decoded!=null&&decoded.getWidth()==32,"same FD bounds and bitmap decode");
            decoded.recycle();
        }
        // Small generated PCM WAV verifies a real media consumer accepting a Binder PFD.
        Path wave=root.resolve("tone.wav");int bytes=16000;
        ByteBuffer wav=ByteBuffer.allocate(44+bytes).order(ByteOrder.LITTLE_ENDIAN);
        wav.put("RIFF".getBytes()).putInt(36+bytes).put("WAVEfmt ".getBytes()).putInt(16).putShort((short)1).putShort((short)1);
        wav.putInt(8000).putInt(16000).putShort((short)2).putShort((short)16).put("data".getBytes()).putInt(bytes);
        Files.write(wave,wav.array());
        Uri media=FileProvider.getUriForFile(context,OWNER+".artifacts",wave.toFile());
        try(MediaMetadataRetriever reader=new MediaMetadataRetriever()) {
            reader.setDataSource(context,media);
            require("1000".equals(reader.extractMetadata(MediaMetadataRetriever.METADATA_KEY_DURATION)),"media reads Binder URI duration=1000ms");
        }
        Path changing=write(root.resolve("changing.txt"),"ORIGINAL");
        try(var descriptor=workspace.open("changing.txt");
            var input=new ParcelFileDescriptor.AutoCloseInputStream(descriptor)) {
            long expected=descriptor.getStatSize();
            require(expected==8,"Android FD snapshot size");
            write(changing,"");
            reject("copy detects truncated source",()->WorkspaceCopy.copy(input,new ByteArrayOutputStream(),expected));
        }
        write(changing,"A");
        try(var descriptor=workspace.open("changing.txt");
            var input=new ParcelFileDescriptor.AutoCloseInputStream(descriptor)) {
            long expected=descriptor.getStatSize();
            ByteArrayOutputStream copied=new ByteArrayOutputStream();
            OutputStream growing=new OutputStream(){
                public void write(int value)throws IOException {
                    copied.write(value);
                    Files.write(changing,new byte[]{'B'},StandardOpenOption.APPEND);
                }
            };
            reject("copy detects growing source",()->WorkspaceCopy.copy(input,growing,expected));
            require(copied.size()==1,"copy stops at initial Android FD size");
        }
        ParcelFileDescriptor detached;
        // A stable ContentResolver lease lets Android kill its consumer when the
        // provider dies. Detach the FD and release the unstable Binder client first.
        try(var client=context.getContentResolver().acquireUnstableContentProviderClient(SHARED);
            var remote=client.openFile(SHARED,"r")) {
            detached=ParcelFileDescriptor.dup(remote.getFileDescriptor());
        }
        try(var heldInput=new ParcelFileDescriptor.AutoCloseInputStream(detached)) {
            int pid=providerPid(context);
            require(pid>1&&pid!=android.os.Process.myPid(),"separate provider process identified");
            android.os.Process.killProcess(pid);
            boolean gone=false;
            long deadline=android.os.SystemClock.elapsedRealtime()+3000;
            while(android.os.SystemClock.elapsedRealtime()<deadline) {
                try {Os.kill(pid,0);}
                catch(android.system.ErrnoException error) {
                    if(error.errno!=OsConstants.ESRCH)throw error;
                    gone=true;break;
                }
                Thread.sleep(20);
            }
            require(gone,"provider process death confirmed by ESRCH");
            require(text(heldInput).equals("SHARED"),"detached FD survives confirmed provider process death");
        }
    }
}
