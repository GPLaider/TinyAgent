package io.github.gplaider.tinyagent;

import android.content.Context;
import android.content.pm.PackageManager;
import android.util.AtomicFile;
import org.json.JSONObject;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.Base64;
import java.util.List;
import java.util.concurrent.*;

/** Durable Android operations over the existing verified self-ADB connection. */
final class AndroidJobs implements AutoCloseable {
    private final Context context;
    private final File directory;
    private final String protocol;
    // ponytail: bounded FIFO per app; unknown remote outcomes still need inspection.
    private final ExecutorService worker = Executors.newSingleThreadExecutor();
    private final java.util.Map<String,java.util.concurrent.atomic.AtomicBoolean> controls=new java.util.HashMap<>();
    private String current;
    private volatile boolean closed;
    private volatile SelfAdbClient active;

    AndroidJobs(Context context) throws Exception {
        this.context = context.getApplicationContext();
        directory = new File(context.getFilesDir(), "linux/android-jobs");
        Files.createDirectories(directory.toPath());
        try (var input = context.getAssets().open("bootstrap/android-job.sh")) {
            var bytes=new ByteArrayOutputStream();byte[] buffer=new byte[4096];
            for(int count;(count=input.read(buffer))!=-1;)bytes.write(buffer,0,count);
            protocol = Base64.getEncoder().encodeToString(bytes.toByteArray());
        }
        File[] files = directory.listFiles((d,n)->n.endsWith(".json"));
        if (files != null) for (File file : files) {
            JSONObject row = load(file.getName().replace(".json", ""));
            if(row.getString("status").equals("queued")) {
                row.put("status","cancelled").put("error","App stopped before this queued operation started");save(row);
            }
            if (List.of("running", "starting", "checking", "cancel_requested").contains(row.getString("status"))) {
                row.put("status", "unknown").put("error", "App restarted; query this ID to inspect the remote job. Do not resubmit.");
                save(row);
            }
        }
    }
    private File file(String id) throws IOException {
        if (!id.matches("[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")) throw new IOException("Invalid Android job ID");
        return new File(directory, id + ".json");
    }
    private JSONObject load(String id) throws Exception {
        try {return new JSONObject(new String(new AtomicFile(file(id)).readFully(), StandardCharsets.UTF_8));}
        catch(FileNotFoundException error){throw new IOException("Unknown Android job ID: "+id+". The request may have been rejected before acceptance.");}
    }
    private synchronized void save(JSONObject row) throws Exception {
        row.put("updated", System.currentTimeMillis());
        AtomicFile target = new AtomicFile(file(row.getString("id")));
        var output = target.startWrite();
        try { output.write(row.toString().getBytes(StandardCharsets.UTF_8)); target.finishWrite(output); }
        catch (Exception error) { target.failWrite(output); throw error; }
    }
    synchronized JSONObject read(String id) throws Exception {
        return load(id);
    }
    synchronized JSONObject inspect(String id) throws Exception {
        JSONObject row=load(id);
        if (!controls.containsKey(id) && !closed && row.getString("status").equals("unknown") && row.getString("action").equals("shell")) run(row, false);
        return row;
    }
    synchronized JSONObject submit(JSONObject request) throws Exception {
        if (closed) throw new IOException("Android service stopped");
        String id=request.getString("id"), mode=request.getString("mode"), action=request.getString("action");
        file(id);
        if (!List.of("developer", "root").contains(mode)) throw new IOException("Stock has no ADB. Use the existing artifact action for user-approved Stock installation.");
        if (!List.of("shell", "install").contains(action)) throw new IOException("Expected shell or install");
        String command=request.optString("command"), cwd=request.optString("cwd", "/"), path=request.optString("path");
        if (cwd.indexOf('\0')>=0 || !cwd.startsWith("/") || cwd.length()>4096 || command.indexOf('\0')>=0 || command.length()>16384 || (action.equals("shell") && command.isBlank())) throw new IOException("Invalid Android command or cwd");
        JSONObject row=new JSONObject().put("id",id).put("mode",mode).put("action",action).put("command",command).put("cwd",cwd).put("path",path);
        if (file(id).exists()) {
            JSONObject previous=load(id);
            for (String key: List.of("mode","action","command","cwd","path")) if (!previous.getString(key).equals(row.getString(key))) throw new IOException("Job ID belongs to another operation");
            return read(id);
        }
        if (controls.size()>=16) throw new IOException("Android queue full; wait for accepted job IDs");
        row.put("environment","android").put("status","queued").put("stdout","").put("stderr","").put("exit_code",JSONObject.NULL)
            .put("remote_directory","/data/local/tmp/tinyagent-android-"+android.os.Process.myUid()+"-"+(mode.equals("root")?0:2000)+"/"+id);
        save(row); run(row,true);
        return new JSONObject(row.toString());
    }
    private void run(JSONObject row, boolean create) throws Exception {
        String id=row.getString("id");
        var cancelled=new java.util.concurrent.atomic.AtomicBoolean();controls.put(id,cancelled);
        if(!create){row.put("status","checking");save(row);}
        worker.submit(()->{
            boolean root=row.optString("mode").equals("root");
            boolean submitted=!create;
            try (SelfAdbClient connection = new SelfAdbClient(context)) {
                synchronized(AndroidJobs.this){current=id;}
                if(create && cancelled.get()){row.put("status","cancelled");return;}
                row.put("status",create?"starting":"checking");save(row);
                active=connection;
                var proof=connection.inspect(!root && WirelessAdb.selected(context)?0:SelfAdbClient.discoverPort(context),root);
                if (!proof.verifiedSelf) throw new IOException(proof.transcript);
                row.put("verified_self",true).put("execution_uid",root?0:2000); save(row);
                if (create && cancelled.get()) { row.put("status","cancelled"); return; }
                if (row.getString("action").equals("install")) {
                    submitted=true;
                    install(connection,row,root);
                    return;
                }
                if (create) {
                    submitted=true;
                    remote(connection,row,root,"start", encoded(row.getString("command")),encoded(row.getString("cwd")));
                }
                while (true) {
                    if (cancelled.get()) remote(connection,row,root,"cancel");
                    String[] fields=remote(connection,row,root,"status").stdout().split("\n",-1);
                    if (fields.length<4) throw new IOException("Incomplete Android job status");
                    String state=fields[0];
                    if (!List.of("starting","running","completed","cancelled","unknown").contains(state)) throw new IOException("Invalid Android job state");
                    int exit=Integer.parseInt(fields[1]);
                    row.put("status",state).put("exit_code",exit<0?JSONObject.NULL:exit)
                        .put("stdout",new String(Base64.getDecoder().decode(fields[2]),StandardCharsets.UTF_8))
                        .put("stderr",new String(Base64.getDecoder().decode(fields[3]),StandardCharsets.UTF_8))
                        .put("output_limit_bytes_per_stream",32768);
                    if (state.equals("completed") && exit!=0) row.put("status","failed");
                    row.remove("error"); save(row);
                    if (!List.of("starting","running").contains(state)) break;
                    Thread.sleep(1000);
                }
            } catch (Exception error) {
                try {row.put("status",submitted?"unknown":"failed").put("error",error.toString());} catch (Exception ignored) { }
            } finally {
                synchronized(AndroidJobs.this) {
                    try {save(row);} catch (Exception error) {android.util.Log.e("TinyAgentAndroid","Job status save failed",error);}
                    active=null;current=null;controls.remove(id);
                }
            }
        });
    }
    private static String encoded(String value) {return Base64.getEncoder().encodeToString(value.getBytes(StandardCharsets.UTF_8));}
    private AdbShellResult remote(SelfAdbClient connection,JSONObject row,boolean root,String action,String... arguments) throws Exception {
        StringBuilder command=new StringBuilder("printf '%s' ").append(protocol).append(" | base64 -d | /system/bin/sh -s -- ").append(action).append(' ').append(row.getString("remote_directory"));
        for (String argument:arguments) command.append(" '").append(argument).append('\'');
        AdbShellResult result=connection.execute(command.toString(),root);
        if (result.exitCode()!=0) throw new IOException("Android job protocol exit="+result.exitCode()+": "+result.stderr());
        return result;
    }
    private void install(SelfAdbClient connection,JSONObject row,boolean root) throws Exception {
        File workspace=new LocalLinuxRuntime(context).workspace.getCanonicalFile();
        if(row.getString("path").startsWith("/") || row.getString("path").indexOf('\0')>=0)throw new IOException("Use a workspace-relative APK path");
        File source=new File(workspace,row.getString("path")).getCanonicalFile();
        if (!source.toPath().startsWith(workspace.toPath()) || !source.isFile() || !source.getName().endsWith(".apk") || source.length()>1024L*1024*1024) throw new IOException("Expected an APK inside this workspace");
        File staged=File.createTempFile("android-job-", ".apk",context.getCacheDir());
        try {
            try(var input=new FileInputStream(source);var output=new FileOutputStream(staged)) {
                byte[] buffer=new byte[65536];long bytes=0;
                for(int count;(count=input.read(buffer))!=-1;){bytes+=count;if(bytes>1024L*1024*1024)throw new IOException("APK exceeds 1 GiB");output.write(buffer,0,count);}
            }
            var info=context.getPackageManager().getPackageArchiveInfo(staged.toString(),PackageManager.GET_SIGNING_CERTIFICATES);
            if (info==null || info.signingInfo==null) throw new IOException("APK signature metadata unavailable");
            row.put("package",info.packageName).put("version",info.getLongVersionCode()).put("status","running");save(row);
            connection.install(staged,root);
            row.put("status","completed").put("exit_code",0).put("stdout","PackageManager confirmed installation: "+info.packageName);
        } finally {Files.deleteIfExists(staged.toPath());}
    }
    synchronized JSONObject cancel(String id) throws Exception {
        JSONObject row=load(id);
        if (controls.containsKey(id)) {
            controls.get(id).set(true);
            if (id.equals(current) && row.getString("action").equals("install") && active!=null) active.close();
            row.put("status",id.equals(current)?"cancel_requested":"cancelled");save(row);
        } else if (row.getString("action").equals("shell") && row.getString("status").equals("unknown") && !closed) {
            run(row,false);controls.get(id).set(true);
        }
        return row;
    }
    @Override public synchronized void close() {
        closed=true;for(var control:controls.values())control.set(true);
        try {if(current!=null && load(current).getString("action").equals("install") && active!=null)active.close();}
        catch(Exception ignored) { }
        worker.shutdown();
    }
}
