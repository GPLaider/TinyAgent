"""Compile the real manager choice against small Android storage doubles."""
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    'android/content/Context.java': '''package android.content;
public class Context {
 public static final int MODE_PRIVATE=0;
 final java.io.File root;
 public final Preferences preferences=new Preferences();
 public Context(java.io.File root){this.root=root;}
 public java.io.File getFilesDir(){return root;}
 public Preferences getSharedPreferences(String name,int mode){return preferences;}
 public static class Preferences {
  public String value="dnfast";
  public String getString(String key,String fallback){return value;}
  public Preferences edit(){return this;}
  public Preferences putString(String key,String value){this.value=value;return this;}
  public boolean commit(){return true;}
 }
}''',
    'android/util/AtomicFile.java': '''package android.util;
public class AtomicFile {
 final java.io.File file;
 public AtomicFile(java.io.File file){this.file=file;}
 public byte[] readFully()throws java.io.IOException{return java.nio.file.Files.readAllBytes(file.toPath());}
 public java.io.FileOutputStream startWrite()throws java.io.IOException{return new java.io.FileOutputStream(file);}
 public void finishWrite(java.io.FileOutputStream out)throws java.io.IOException{out.close();}
 public void failWrite(java.io.FileOutputStream out){try{out.close();}catch(Exception ignored){}}
}''',
    'io/github/gplaider/tinyagent/ChoiceCheck.java': '''package io.github.gplaider.tinyagent;
import java.nio.file.*;
import java.util.*;
public class ChoiceCheck {
 static int count;
 static void check(boolean value){count++;if(!value)throw new AssertionError("check "+count);}
 public static void main(String[] argv)throws Exception{
  var root=Path.of(argv[0]);
  var fresh=new android.content.Context(root.resolve("fresh").toFile());
  check(PackageManagerChoice.read(fresh).equals("dnfast"));
  check(!PackageManagerChoice.locked(fresh));
  PackageManagerChoice.select(fresh,"dnf5");
  check(PackageManagerChoice.freeze(fresh).equals("dnf5"));
  check(PackageManagerChoice.locked(fresh));
  fresh.preferences.value="dnfast";
  check(PackageManagerChoice.read(fresh).equals("dnf5"));
  check(PackageManagerChoice.freeze(fresh).equals("dnf5"));
  try{PackageManagerChoice.select(fresh,"dnfast");throw new AssertionError("changed frozen root");}
  catch(java.io.IOException expected){count++;}
  var old=new android.content.Context(root.resolve("existing").toFile());
  Files.createDirectories(old.getFilesDir().toPath().resolve("linux"));
  Files.writeString(old.getFilesDir().toPath().resolve("linux/prepared-v1"),"fedora=44");
  old.preferences.value="dnf5";
  check(PackageManagerChoice.freeze(old).equals("dnfast"));
  check(PackageManagerChoice.dnf5Command("refresh").equals(List.of("/usr/bin/dnf5","--refresh","makecache")));
  check(PackageManagerChoice.dnf5Command("check").equals(List.of("/usr/bin/dnf5","check")));
  check(PackageManagerChoice.dnf5Command("install","install","--assumeyes","git").equals(List.of("/usr/bin/dnf5","install","--assumeyes","git")));
  for(String action:List.of("recover","migrate","remove")){
   try{PackageManagerChoice.dnf5Command(action);throw new AssertionError("unsupported action");}
   catch(java.io.IOException expected){count++;}
  }
  for(String invalid:Arrays.asList(null,"","microdnf","dnf5\\n")){
   try{PackageManagerChoice.validate(invalid);throw new AssertionError("invalid manager");}
   catch(java.io.IOException expected){count++;}
  }
  Files.writeString(fresh.getFilesDir().toPath().resolve("linux/package-manager"),"invalid");
  try{PackageManagerChoice.read(fresh);throw new AssertionError("corruption ignored");}
  catch(java.io.IOException expected){count++;}
  System.out.println("PASS "+count+" assertions: frozen selection, legacy roots, dispatch and corrupt state");
 }
}''',
}
java = Path(os.environ['JAVA_HOME']) / 'bin' if os.environ.get('JAVA_HOME') else Path('/usr/bin')
with tempfile.TemporaryDirectory(prefix='tinyagent-manager-') as directory:
    work = Path(directory)
    for name, source in SOURCES.items():
        file = work/name
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(source)
    files = list(work.rglob('*.java')) + [ROOT/'app/src/main/java/io/github/gplaider/tinyagent/PackageManagerChoice.java']
    subprocess.run([str(java/'javac'), '-d', str(work/'classes'), *map(str, files)], check=True)
    subprocess.run([str(java/'java'), '-cp', str(work/'classes'), 'io.github.gplaider.tinyagent.ChoiceCheck', str(work/'data')], check=True)
