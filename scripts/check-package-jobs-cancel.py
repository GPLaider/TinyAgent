"""Host regression: compile real PackageJobs with deterministic platform/runtime doubles.

Pass an org.json JSON-java jar. No phone, model call, or package installation.
"""
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
STUBS = {
    'android/content/Context.java': '''package android.content;
public class Context { private final java.io.File root;
 public Context(java.io.File root){this.root=root;} public java.io.File getFilesDir(){return root;} }''',
    'android/util/AtomicFile.java': '''package android.util;
public class AtomicFile { private final java.io.File file;
 public AtomicFile(java.io.File file){this.file=file;}
 public byte[] readFully() throws Exception{return java.nio.file.Files.readAllBytes(file.toPath());}
 public java.io.FileInputStream openRead() throws Exception{return new java.io.FileInputStream(file);}
 public java.io.FileOutputStream startWrite() throws Exception{return new java.io.FileOutputStream(file);}
 public void finishWrite(java.io.FileOutputStream out) throws Exception{out.close();}
 public void failWrite(java.io.FileOutputStream out) throws Exception{out.close();} }''',
    'android/util/Log.java': '''package android.util;
public class Log {public static int e(String tag,String message,Throwable e){throw new AssertionError(message,e);} }''',
    'io/github/gplaider/tinyagent/DnfastRuntime.java': '''package io.github.gplaider.tinyagent;
final class DnfastRuntime {static final String REVISION="test";}''',
    'io/github/gplaider/tinyagent/LocalLinuxRuntime.java': '''package io.github.gplaider.tinyagent;
final class LocalLinuxRuntime {
 static final java.util.concurrent.CountDownLatch started=new java.util.concurrent.CountDownLatch(1),
  cancelled=new java.util.concurrent.CountDownLatch(1), logged=new java.util.concurrent.CountDownLatch(1),
  finish=new java.util.concurrent.CountDownLatch(1);
 LocalLinuxRuntime(android.content.Context context){}
 Integer lastExitCode(){return 0;}
 void cancel(){cancelled.countDown();}
 void runPackages(String action,java.util.function.Consumer<String> lines,String... args) throws Exception {
  started.countDown(); if(!cancelled.await(5,java.util.concurrent.TimeUnit.SECONDS))throw new AssertionError("cancel not forwarded");
  lines.accept("late output after cancel"); logged.countDown();
  if(!finish.await(5,java.util.concurrent.TimeUnit.SECONDS))throw new AssertionError("finish timeout");
  // A successful process exit can race with cancellation; it must not erase the request.
 }
}''',
    'io/github/gplaider/tinyagent/PackageJobsCancelCheck.java': '''package io.github.gplaider.tinyagent;
public class PackageJobsCancelCheck {
 public static void main(String[] args)throws Exception {
  String id=java.util.UUID.randomUUID().toString();
  try(PackageJobs jobs=new PackageJobs(new android.content.Context(new java.io.File(args[0])))){
   var request=new org.json.JSONObject().put("id",id).put("argv",new org.json.JSONArray().put("install").put("git"));
   jobs.submit(request);
   if(!LocalLinuxRuntime.started.await(5,java.util.concurrent.TimeUnit.SECONDS))throw new AssertionError("not started");
   if(!jobs.submit(request).getString("id").equals(id))throw new AssertionError("duplicate request changed identity");
   try{jobs.submit(new org.json.JSONObject(request.toString()).put("argv",new org.json.JSONArray().put("install").put("gcc")));throw new AssertionError("conflicting duplicate accepted");}
   catch(java.io.IOException expected){}
   try{jobs.submit(new org.json.JSONObject(request.toString()).put("id",java.util.UUID.randomUUID().toString()));throw new AssertionError("second writer accepted");}
   catch(java.io.IOException expected){}
   jobs.cancel(id);
   if(!LocalLinuxRuntime.logged.await(5,java.util.concurrent.TimeUnit.SECONDS))throw new AssertionError("no late output");
   if(!jobs.read(id).getString("status").equals("cancel_requested"))throw new AssertionError("late output erased cancellation");
   LocalLinuxRuntime.finish.countDown();
   long deadline=System.nanoTime()+5_000_000_000L;
   while(jobs.read(id).getString("status").equals("cancel_requested")&&System.nanoTime()<deadline)Thread.sleep(10);
   if(!jobs.read(id).getString("status").equals("cancelled"))throw new AssertionError("exit success erased cancellation");
   jobs.close();
   String late=java.util.UUID.randomUUID().toString();
   try{jobs.submit(new org.json.JSONObject(request.toString()).put("id",late));throw new AssertionError("closed service accepted work");}
   catch(java.io.IOException expected){}
   if(new java.io.File(args[0],"linux/package-jobs/"+late+".json").exists())throw new AssertionError("closed service persisted phantom work");
   System.out.println("PASS: idempotency, single writer, cancellation races, closed service rejects without phantom job");
  }finally{LocalLinuxRuntime.finish.countDown();}
 }
}''',
}

jar = pathlib.Path(sys.argv[1]).resolve(strict=True)
with tempfile.TemporaryDirectory(prefix='tinyagent-package-check-') as directory:
    work = pathlib.Path(directory)
    sources = []
    for name, source in STUBS.items():
        path = work / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding='utf-8')
        sources.append(str(path))
    sources.append(str(ROOT / 'app/src/main/java/io/github/gplaider/tinyagent/PackageJobs.java'))
    subprocess.run(['javac', '-encoding', 'UTF-8', '-cp', str(jar), '-d', str(work), *sources], check=True)
    import os
    subprocess.run(['java', '-cp', os.pathsep.join([str(work), str(jar)]),
                    'io.github.gplaider.tinyagent.PackageJobsCancelCheck', str(work / 'data')], check=True, timeout=20)
