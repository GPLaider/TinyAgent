package io.github.gplaider.tinyagent;

import android.content.Context;
import android.util.AtomicFile;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.*;
import java.util.concurrent.*;
import org.json.*;

/** One package writer per app; the native launcher also locks the Fedora root. */
final class PackageJobs implements AutoCloseable {
    private final Context context;
    private final File directory;
    private final ExecutorService worker=Executors.newSingleThreadExecutor();
    private LocalLinuxRuntime running;
    private String current;
    private JSONObject currentRow;
    private boolean cancelRequested;
    PackageJobs(Context context) throws Exception {
        this.context=context;
        directory=new File(context.getFilesDir(),"linux/package-jobs"); Files.createDirectories(directory.toPath());
        File[] files=directory.listFiles((d,n)->n.endsWith(".json"));
        if(files!=null)for(File file:files){
            JSONObject row=read(file.getName().replace(".json",""));
            if(List.of("running","cancel_requested").contains(row.getString("status"))) {
                row.put("status","interrupted").put("error","Runtime restarted; inspect app-runtime check/recover before another transaction");save(row);
            }
        }
    }
    private File file(String id) throws IOException {
        if(!id.matches("[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"))throw new IOException("Invalid request ID");
        return new File(directory,id+".json");
    }
    synchronized JSONObject read(String id) throws Exception {
        return new JSONObject(new String(new AtomicFile(file(id)).readFully(),StandardCharsets.UTF_8));
    }
    private synchronized void save(JSONObject row) throws Exception {
        row.put("updated",System.currentTimeMillis());
        AtomicFile file=new AtomicFile(file(row.getString("id")));var out=file.startWrite();
        try {out.write(row.toString().getBytes(StandardCharsets.UTF_8));file.finishWrite(out);}
        catch(Exception e){file.failWrite(out);throw e;}
    }
    synchronized JSONObject submit(JSONObject request) throws Exception {
        if(worker.isShutdown())throw new IOException("Package service stopped");
        String id=request.getString("id");file(id);
        JSONArray array=request.getJSONArray("argv");
        if(array.length()<1||array.length()>128)throw new IOException("Invalid package arguments");
        List<String> args=new ArrayList<>();
        for(int i=0;i<array.length();i++){
            String value=array.getString(i);
            if(value.isBlank()||value.length()>4096||value.indexOf('\0')>=0)throw new IOException("Invalid package argument");
            args.add(value);
        }
        String action;
        if(args.get(0).equals("install"))action="install";
        else if(args.equals(List.of("repo","refresh")))action="refresh";
        else if(args.equals(List.of("app-runtime","check")))action="check";
        else if(args.equals(List.of("app-runtime","recover")))action="recover";
        else if(args.equals(List.of("app-runtime","migrate")))action="migrate";
        else throw new IOException("Supported: install, repo refresh, app-runtime check/recover/migrate");
        if(file(id).exists()){
            JSONObject previous=read(id);
            if(!previous.getJSONArray("argv").toString().equals(array.toString()))throw new IOException("Request ID already used for another command");
            return previous;
        }
        if(current!=null)throw new IOException("Package task running: "+current);
        JSONObject row=new JSONObject().put("id",id).put("argv",array).put("environment","fedora-local")
                .put("cwd","/workspace").put("manager","dnfast").put("revision",DnfastRuntime.REVISION)
                .put("status","running").put("output","").put("output_truncated",false).put("exit_code",JSONObject.NULL);
        save(row);current=id;currentRow=row;cancelRequested=false;running=new LocalLinuxRuntime(context);
        LocalLinuxRuntime runtime=running;
        worker.submit(()->{
            try {
                runtime.runPackages(action,line->{
                    synchronized(PackageJobs.this){try{
                        String output=row.optString("output")+line+"\n";
                        if(output.length()>16384){output=output.substring(output.length()-16384);row.put("output_truncated",true);}
                        row.put("output",output);save(row);
                    }catch(Exception e){throw new IllegalStateException(e);}}
                },args.toArray(new String[0]));
                synchronized(PackageJobs.this){row.put("status",cancelRequested?"cancelled":"completed").put("exit_code",0);}
            }catch(Exception e){synchronized(PackageJobs.this){try{row.put("status",cancelRequested?"cancelled":"failed").put("error",e.toString());}catch(JSONException ignored){}}}
            finally {synchronized(PackageJobs.this){try{
                Integer exit=runtime.lastExitCode();
                row.put("exit_code",exit==null?JSONObject.NULL:exit);save(row);
            }catch(Exception e){android.util.Log.e("TinyAgentPackages","Task status save failed",e);}running=null;current=null;currentRow=null;}}
        });
        return new JSONObject(row.toString());
    }
    synchronized JSONObject cancel(String id) throws Exception {
        JSONObject row=read(id);
        if(id.equals(current)&&running!=null){
            cancelRequested=true;row=currentRow;row.put("status","cancel_requested");
            try {save(row);} finally {running.cancel();}
        }
        return new JSONObject(row.toString());
    }
    @Override public synchronized void close(){
        try {if(current!=null)cancel(current);}
        catch(Exception e){android.util.Log.e("TinyAgentPackages","Cancellation status save failed",e);}
        finally {worker.shutdown();}
    }
}
