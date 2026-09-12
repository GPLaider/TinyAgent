package io.github.gplaider.tinyagent;

import android.content.*;
import android.database.Cursor;
import android.net.Uri;
import android.os.ParcelFileDescriptor;
import java.io.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicInteger;

/** Controlled destination for real Activity rotation tests, only in probe APKs. */
public final class WorkspaceProbeDestination extends ContentProvider {
    static CountDownLatch opened=new CountDownLatch(1), release=new CountDownLatch(1), done=new CountDownLatch(1);
    static final AtomicInteger opens=new AtomicInteger();
    static volatile long bytes;
    static volatile String sha256;
    static volatile boolean fail;
    static volatile Throwable error;
    static void reset(){opened=new CountDownLatch(1);release=new CountDownLatch(1);done=new CountDownLatch(1);opens.set(0);bytes=0;sha256=null;error=null;fail=false;}
    public boolean onCreate(){return true;}
    @Override public ParcelFileDescriptor openFile(Uri uri,String mode)throws FileNotFoundException {
        try {
            ParcelFileDescriptor[] pipe=ParcelFileDescriptor.createReliablePipe();
            opens.incrementAndGet();
            new Thread(()->{
                try(var input=new ParcelFileDescriptor.AutoCloseInputStream(pipe[0])) {
                    if(!release.await(10,TimeUnit.SECONDS))throw new IOException("Probe destination timed out");
                    if(fail){pipe[0].closeWithError("injected destination failure");throw new IOException("injected destination failure");}
                    var digest=java.security.MessageDigest.getInstance("SHA-256");
                    byte[] buffer=new byte[8192];for(int count;(count=input.read(buffer))!=-1;){bytes+=count;digest.update(buffer,0,count);}
                    StringBuilder hex=new StringBuilder();for(byte value:digest.digest())hex.append(String.format("%02x",value&255));
                    sha256=hex.toString();
                }catch(Throwable failure){error=failure;}finally{done.countDown();}
            },"probe-destination").start();
            opened.countDown();
            return pipe[1];
        }catch(IOException error){throw new FileNotFoundException(error.toString());}
    }
    public String getType(Uri uri){return "application/octet-stream";}
    public Cursor query(Uri uri,String[] projection,String selection,String[] args,String order){return null;}
    public Uri insert(Uri uri,ContentValues values){throw new UnsupportedOperationException();}
    public int update(Uri uri,ContentValues values,String selection,String[] args){throw new UnsupportedOperationException();}
    public int delete(Uri uri,String selection,String[] args){throw new UnsupportedOperationException();}
}
