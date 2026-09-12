package io.github.gplaider.tinyagent;

import android.app.*;
import android.content.*;
import android.net.Uri;
import android.view.*;
import android.widget.TextView;
import java.nio.file.*;
import java.util.concurrent.TimeUnit;

final class WorkspaceActivityProbe {
    private static String texts(View view) {
        StringBuilder text=new StringBuilder();
        if(view instanceof TextView label)text.append(label.getText()).append(' ');
        if(view instanceof ViewGroup group)for(int i=0;i<group.getChildCount();i++)text.append(texts(group.getChildAt(i)));
        return text.toString();
    }
    static String recreate(Instrumentation instrumentation,boolean failure)throws Exception {
        Context context=instrumentation.getTargetContext();
        Path root=Files.createDirectories(context.getFilesDir().toPath().resolve("linux/workspace"));
        int size=512*1024;Files.write(root.resolve("rotation.bin"),new byte[size]);
        WorkspaceProbeDestination.reset();
        WorkspaceProbeDestination.fail=failure;
        Uri destination=Uri.parse("content://"+context.getPackageName()+".destination/export");
        Instrumentation.ActivityMonitor picker=new Instrumentation.ActivityMonitor(){
            @Override public Instrumentation.ActivityResult onStartActivity(Intent intent) {
                return Intent.ACTION_CREATE_DOCUMENT.equals(intent.getAction())
                        ? new Instrumentation.ActivityResult(Activity.RESULT_OK,new Intent().setData(destination)) : null;
            }
        };
        instrumentation.addMonitor(picker);
        Activity original=null,recreated=null;
        try {
            original=instrumentation.startActivitySync(new Intent(context,InstallerActivity.class)
                    .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK).putExtra("exportPath","rotation.bin"));
            if(!WorkspaceProbeDestination.opened.await(5,TimeUnit.SECONDS))throw new AssertionError("Destination not opened");
            Instrumentation.ActivityMonitor monitor=instrumentation.addMonitor(InstallerActivity.class.getName(),null,false);
            try {
                Activity current=original;instrumentation.runOnMainSync(current::recreate);
                recreated=monitor.waitForActivityWithTimeout(5000);
            }finally{instrumentation.removeMonitor(monitor);}
            if(recreated==null||recreated==original)throw new AssertionError("Activity was not recreated");
            instrumentation.waitForIdleSync();
            WorkspaceProbeDestination.release.countDown();
            if(!WorkspaceProbeDestination.done.await(5,TimeUnit.SECONDS))throw new AssertionError("Copy did not terminate");
            Activity restored=recreated;
            long deadline=android.os.SystemClock.elapsedRealtime()+3000;
            if(failure) {
                if(WorkspaceProbeDestination.error==null)throw new AssertionError("Destination failure not injected");
                String[] shown={""};
                do {
                    instrumentation.runOnMainSync(()->shown[0]=texts(restored.getWindow().getDecorView()));
                    if(shown[0].contains("파일 저장 실패"))break;
                    Thread.sleep(20);
                }while(android.os.SystemClock.elapsedRealtime()<deadline);
                if(!shown[0].contains("파일 저장 실패"))throw new AssertionError("Recreated export lost failure status: "+shown[0]);
                if(restored.isFinishing()||restored.isDestroyed())throw new AssertionError("Failed export silently dismissed");
                if(WorkspaceProbeDestination.opens.get()!=1)throw new AssertionError("Failed export replayed");
                return "PASS actual Activity recreate during output failure, restored screen shows failure, no replay\n";
            }
            if(WorkspaceProbeDestination.error!=null)throw new AssertionError("Destination failed",WorkspaceProbeDestination.error);
            if(WorkspaceProbeDestination.bytes!=size||WorkspaceProbeDestination.opens.get()!=1)throw new AssertionError("Copy lost/replayed");
            while(!restored.isFinishing()&&!restored.isDestroyed()&&android.os.SystemClock.elapsedRealtime()<deadline)Thread.sleep(20);
            if(!restored.isFinishing()&&!restored.isDestroyed()) {
                String[] shown={""};instrumentation.runOnMainSync(()->shown[0]=texts(restored.getWindow().getDecorView()));
                throw new AssertionError("Recreated export stayed open after successful copy: "+shown[0]);
            }
            return "PASS actual Activity recreate during export, exactly one 524288-byte copy, restored screen completes\n";
        }finally {
            WorkspaceProbeDestination.release.countDown();
            instrumentation.removeMonitor(picker);
            Activity first=original,last=recreated;
            instrumentation.runOnMainSync(()->{if(first!=null&&!first.isDestroyed())first.finish();if(last!=null&&!last.isDestroyed())last.finish();});
        }
    }
    static String isolation(Instrumentation instrumentation)throws Exception {
        Context context=instrumentation.getTargetContext();
        Path root=Files.createDirectories(context.getFilesDir().toPath().resolve("linux/workspace"));
        Files.write(root.resolve("failed.bin"),new byte[512*1024]);
        Files.write(root.resolve("success.bin"),new byte[512*1024]);
        Uri destination=Uri.parse("content://"+context.getPackageName()+".destination/export");
        Instrumentation.ActivityMonitor picker=new Instrumentation.ActivityMonitor(){
            @Override public Instrumentation.ActivityResult onStartActivity(Intent intent) {
                return Intent.ACTION_CREATE_DOCUMENT.equals(intent.getAction())
                    ? new Instrumentation.ActivityResult(Activity.RESULT_OK,new Intent().setData(destination)) : null;
            }
        };
        instrumentation.addMonitor(picker);
        Activity failed=null,success=null;
        SharedPreferences installer=context.getSharedPreferences("installer",Context.MODE_PRIVATE);
        installer.edit().putString("status","installer sentinel").commit();
        try {
            WorkspaceProbeDestination.reset();WorkspaceProbeDestination.fail=true;
            failed=instrumentation.startActivitySync(new Intent(context,InstallerActivity.class)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK).putExtra("exportPath","failed.bin"));
            if(!WorkspaceProbeDestination.opened.await(5,TimeUnit.SECONDS))throw new AssertionError("First export did not open");
            WorkspaceProbeDestination.release.countDown();
            if(!WorkspaceProbeDestination.done.await(5,TimeUnit.SECONDS))throw new AssertionError("First export did not fail");
            Activity first=failed;
            String[] shown={""};
            long deadline=android.os.SystemClock.elapsedRealtime()+3000;
            do {
                instrumentation.runOnMainSync(()->shown[0]=texts(first.getWindow().getDecorView()));
                if(shown[0].contains("파일 저장 실패"))break;
                Thread.sleep(20);
            }while(android.os.SystemClock.elapsedRealtime()<deadline);
            if(!shown[0].contains("파일 저장 실패"))throw new AssertionError("Initial failure status missing: "+shown[0]);
            if(!"installer sentinel".equals(installer.getString("status","")))throw new AssertionError("Export changed installer status");
            installer.edit().putString("status","unrelated install update").commit();
            instrumentation.waitForIdleSync();
            instrumentation.runOnMainSync(()->shown[0]=texts(first.getWindow().getDecorView()));
            if(!shown[0].contains("파일 저장 실패"))throw new AssertionError("Installer status replaced export failure");
            WorkspaceProbeDestination.reset();
            Instrumentation.ActivityMonitor monitor=instrumentation.addMonitor(InstallerActivity.class.getName(),null,false);
            try {
                instrumentation.runOnMainSync(()->first.startActivity(new Intent(context,InstallerActivity.class)
                    .putExtra("exportPath","success.bin")));
                success=monitor.waitForActivityWithTimeout(5000);
            }finally{instrumentation.removeMonitor(monitor);}
            if(success==null||success==failed)throw new AssertionError("Expected distinct Activity instances");
            if(!WorkspaceProbeDestination.opened.await(5,TimeUnit.SECONDS))throw new AssertionError("Second export did not open");
            WorkspaceProbeDestination.release.countDown();
            if(!WorkspaceProbeDestination.done.await(5,TimeUnit.SECONDS))throw new AssertionError("Second export did not finish");
            deadline=android.os.SystemClock.elapsedRealtime()+3000;
            while(!success.isFinishing()&&!success.isDestroyed()&&android.os.SystemClock.elapsedRealtime()<deadline)Thread.sleep(20);
            instrumentation.waitForIdleSync();
            instrumentation.runOnMainSync(()->shown[0]=texts(first.getWindow().getDecorView()));
            if(!shown[0].contains("파일 저장 실패")||shown[0].contains("파일 저장 완료"))
                throw new AssertionError("Another export overwrote the failed Activity: "+shown[0]);
            if(!success.isFinishing()&&!success.isDestroyed())throw new AssertionError("Successful export did not close");
            if(WorkspaceProbeDestination.opens.get()!=1||WorkspaceProbeDestination.bytes!=512*1024)
                throw new AssertionError("Second copy replayed or incomplete");
            if(!"unrelated install update".equals(installer.getString("status","")))throw new AssertionError("Successful export changed installer status");
            return "PASS separate export Activities retain their own failure/success status; installer status isolated in both directions\n";
        }finally {
            WorkspaceProbeDestination.release.countDown();instrumentation.removeMonitor(picker);
            Activity first=failed,second=success;
            instrumentation.runOnMainSync(()->{if(first!=null&&!first.isDestroyed())first.finish();if(second!=null&&!second.isDestroyed())second.finish();});
        }
    }

    private static Activity launch(Instrumentation instrumentation,Intent intent)throws Exception {
        Instrumentation.ActivityMonitor monitor=instrumentation.addMonitor(InstallerActivity.class.getName(),null,false);
        try {
            instrumentation.runOnMainSync(()->instrumentation.getTargetContext().startActivity(intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)));
            Activity activity=monitor.waitForActivityWithTimeout(5000);
            if(activity==null)throw new AssertionError("Activity launch timed out");
            instrumentation.waitForIdleSync();
            return activity;
        }finally{instrumentation.removeMonitor(monitor);}
    }
    static String dismiss(Instrumentation instrumentation)throws Exception {
        Context context=instrumentation.getTargetContext();
        Path root=Files.createDirectories(context.getFilesDir().toPath().resolve("linux/workspace"));
        Files.write(root.resolve("closing.bin"),new byte[512*1024]);
        WorkspaceProbeDestination.reset();
        Uri destination=Uri.parse("content://"+context.getPackageName()+".destination/export");
        Instrumentation.ActivityMonitor picker=new Instrumentation.ActivityMonitor(){
            @Override public Instrumentation.ActivityResult onStartActivity(Intent intent) {
                return Intent.ACTION_CREATE_DOCUMENT.equals(intent.getAction())
                    ? new Instrumentation.ActivityResult(Activity.RESULT_OK,new Intent().setData(destination)) : null;
            }
        };
        instrumentation.addMonitor(picker);
        Activity original=null,reopened=null;
        try {
            original=launch(instrumentation,new Intent(context,InstallerActivity.class).putExtra("exportPath","closing.bin"));
            if(!WorkspaceProbeDestination.opened.await(5,TimeUnit.SECONDS))throw new AssertionError("Export not opened");
            Activity closing=original;instrumentation.runOnMainSync(closing::finish);
            long deadline=android.os.SystemClock.elapsedRealtime()+3000;
            while(!closing.isDestroyed()&&android.os.SystemClock.elapsedRealtime()<deadline)Thread.sleep(20);
            if(!closing.isDestroyed())throw new AssertionError("Closed Activity not destroyed");
            reopened=launch(instrumentation,new Intent(context,InstallerActivity.class).putExtra("exportPath","missing.bin"));
            Activity fresh=reopened;
            String[] shown={""};instrumentation.runOnMainSync(()->shown[0]=texts(fresh.getWindow().getDecorView()));
            if(!shown[0].contains("내보내기 실패"))throw new AssertionError("Fresh error screen missing: "+shown[0]);
            WorkspaceProbeDestination.release.countDown();
            if(!WorkspaceProbeDestination.done.await(5,TimeUnit.SECONDS))throw new AssertionError("Dismissed copy did not terminate");
            // Wait for the old worker to finish posting its UI result, without a timing-only assertion.
            var field=InstallerActivity.class.getDeclaredField("worker");field.setAccessible(true);
            if(!((java.util.concurrent.ExecutorService)field.get(closing)).awaitTermination(5,TimeUnit.SECONDS))
                throw new AssertionError("Destroyed Activity worker did not terminate");
            instrumentation.waitForIdleSync();
            instrumentation.runOnMainSync(()->shown[0]=texts(fresh.getWindow().getDecorView()));
            if(fresh.isFinishing()||fresh.isDestroyed()||!shown[0].contains("내보내기 실패")||shown[0].contains("파일 저장 완료"))
                throw new AssertionError("Dismissed export affected reopened screen: "+shown[0]);
            if(WorkspaceProbeDestination.error!=null||WorkspaceProbeDestination.opens.get()!=1||WorkspaceProbeDestination.bytes!=512*1024)
                throw new AssertionError("Dismissed export failed or replayed");
            return "PASS dismiss during copy then reopen: old copy completes once, worker terminates, fresh error screen unaffected\n";
        }finally {
            WorkspaceProbeDestination.release.countDown();instrumentation.removeMonitor(picker);
            Activity first=original,second=reopened;
            instrumentation.runOnMainSync(()->{if(first!=null&&!first.isDestroyed())first.finish();if(second!=null&&!second.isDestroyed())second.finish();});
        }
    }
    private static android.widget.Button button(View view,String text) {
        if(view instanceof android.widget.Button result&&text.contentEquals(result.getText()))return result;
        if(view instanceof ViewGroup group)for(int i=0;i<group.getChildCount();i++){
            var result=button(group.getChildAt(i),text);if(result!=null)return result;
        }
        return null;
    }
    static String statusSwitch(Instrumentation instrumentation)throws Exception {
        Context context=instrumentation.getTargetContext();
        Activity activity=launch(instrumentation,new Intent(context,InstallerActivity.class));
        try {
            String[] failure={""},shown={""};
            instrumentation.runOnMainSync(()->{
                View root=activity.getWindow().getDecorView();
                var install=button(root,"작업공간 APK 설치");var export=button(root,"작업공간 파일 내보내기");
                if(install==null||export==null)throw new AssertionError("Full-screen controls missing");
                // Empty source fails validation before any APK installation or picker is attempted.
                install.performClick();
                failure[0]=context.getSharedPreferences("installer",Context.MODE_PRIVATE).getString("status","");
                if(failure[0].isEmpty())throw new AssertionError("Initial install validation did not fail");
                export.performClick();
                if(!texts(root).contains("내보내기 실패"))throw new AssertionError("Export validation error missing");
                install.performClick();
            });
            instrumentation.waitForIdleSync();
            instrumentation.runOnMainSync(()->shown[0]=texts(activity.getWindow().getDecorView()));
            if(shown[0].contains("내보내기 실패")||!shown[0].contains(failure[0]))
                throw new AssertionError("Repeated installation validation left stale export status: "+shown[0]);
            return "PASS full-screen install/export/install validation switches status even when installer preference value is unchanged\n";
        }finally{instrumentation.runOnMainSync(activity::finish);}
    }

    static String picker(Instrumentation instrumentation,String resultMode)throws Exception {
        Context context=instrumentation.getTargetContext();
        Path root=Files.createDirectories(context.getFilesDir().toPath().resolve("linux/workspace"));
        byte[] payload=new byte[73*1024];new java.util.Random(52819).nextBytes(payload);
        Files.write(root.resolve("picked.bin"),payload);
        WorkspaceProbeDestination.reset();WorkspaceProbePicker.launches=0;
        Uri destination=Uri.parse("content://"+context.getPackageName()+".destination/export");
        Instrumentation.ActivityMonitor redirect=new Instrumentation.ActivityMonitor(){
            @Override public Instrumentation.ActivityResult onStartActivity(Intent intent) {
                if(Intent.ACTION_CREATE_DOCUMENT.equals(intent.getAction()))intent.setClass(context,WorkspaceProbePicker.class);
                return null;
            }
        };
        instrumentation.addMonitor(redirect);
        Instrumentation.ActivityMonitor pickerMonitor=instrumentation.addMonitor(WorkspaceProbePicker.class.getName(),null,false);
        Activity original=null,restored=null;
        WorkspaceProbePicker picker=null;
        try {
            original=launch(instrumentation,new Intent(context,InstallerActivity.class).putExtra("exportPath","picked.bin"));
            picker=(WorkspaceProbePicker)pickerMonitor.waitForActivityWithTimeout(5000);
            if(picker==null)throw new AssertionError("Delayed picker not launched");
            if(WorkspaceProbeDestination.opens.get()!=0)throw new AssertionError("Copy began before selection");
            if(!"picked.bin".equals(picker.getIntent().getStringExtra(Intent.EXTRA_TITLE)))throw new AssertionError("Wrong picker title");
            Instrumentation.ActivityMonitor recreated=instrumentation.addMonitor(InstallerActivity.class.getName(),null,false);
            try {
                Activity first=original;instrumentation.runOnMainSync(first::recreate);
                restored=recreated.waitForActivityWithTimeout(5000);
            }finally{instrumentation.removeMonitor(recreated);}
            if(restored==null||restored==original)throw new AssertionError("Parent not recreated while picker pending");
            instrumentation.waitForIdleSync();
            if(WorkspaceProbePicker.launches!=1||WorkspaceProbeDestination.opens.get()!=0)throw new AssertionError("Pending selection replayed");
            WorkspaceProbePicker pending=picker;
            int code=resultMode.equals("cancel")?Activity.RESULT_CANCELED:Activity.RESULT_OK;
            Intent result=resultMode.equals("save")?new Intent().setData(destination):resultMode.equals("empty")?new Intent():null;
            instrumentation.runOnMainSync(()->pending.deliver(code,result));
            Activity current=restored;
            if(resultMode.equals("save")) {
                if(!WorkspaceProbeDestination.opened.await(5,TimeUnit.SECONDS))throw new AssertionError("Restored selection did not start copy");
                WorkspaceProbeDestination.release.countDown();
                if(!WorkspaceProbeDestination.done.await(5,TimeUnit.SECONDS))throw new AssertionError("Selected copy did not finish");
                StringBuilder expected=new StringBuilder();
                for(byte value:java.security.MessageDigest.getInstance("SHA-256").digest(payload))expected.append(String.format("%02x",value&255));
                if(WorkspaceProbeDestination.error!=null||WorkspaceProbeDestination.opens.get()!=1||WorkspaceProbeDestination.bytes!=payload.length
                    ||!expected.toString().equals(WorkspaceProbeDestination.sha256))throw new AssertionError("Restored selection lost or mixed source contents");
            }
            long deadline=android.os.SystemClock.elapsedRealtime()+3000;
            while(!current.isDestroyed()&&android.os.SystemClock.elapsedRealtime()<deadline)Thread.sleep(20);
            if(!current.isDestroyed())throw new AssertionError("Restored export screen did not close after "+resultMode);
            if(!resultMode.equals("save")&&WorkspaceProbeDestination.opens.get()!=0)throw new AssertionError("Cancelled/invalid result started copy");
            return "PASS delayed picker -> parent recreate -> "+resultMode+": one picker, "+(resultMode.equals("save")?"one SHA-256-verified copy":"no destination opened")+"\n";
        }finally {
            WorkspaceProbeDestination.release.countDown();
            instrumentation.removeMonitor(redirect);instrumentation.removeMonitor(pickerMonitor);
            Activity first=original,last=restored,document=picker;
            instrumentation.runOnMainSync(()->{
                if(document!=null&&!document.isDestroyed())document.finish();
                if(first!=null&&!first.isDestroyed())first.finish();
                if(last!=null&&!last.isDestroyed())last.finish();
            });
        }
    }

}
