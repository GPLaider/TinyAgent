package io.github.gplaider.tinyagent;

import android.content.ContentProvider;
import android.content.ContentValues;
import android.content.Intent;
import android.database.Cursor;
import android.net.Uri;
import android.os.Bundle;

/** Test-only, signature-protected control; never part of TinyAgent's application. */
public final class WorkspaceProbeControl extends ContentProvider {
    private static final String OWNER="io.github.gplaider.tinyagent.workspaceprobe";
    @Override public boolean onCreate(){return true;}
    @Override public Bundle call(String method,String arg,Bundle extras) {
        if(!getContext().getPackageName().equals(OWNER)||!(OWNER+".client").equals(getCallingPackage()))
            throw new SecurityException("Expected the paired probe client");
        Uri uri=Uri.parse("content://"+OWNER+".artifacts/workspace/shared.txt");
        if(method.equals("grant"))getContext().grantUriPermission(OWNER+".client",uri,Intent.FLAG_GRANT_READ_URI_PERMISSION);
        else if(method.equals("revoke"))getContext().revokeUriPermission(uri,Intent.FLAG_GRANT_READ_URI_PERMISSION);
        else throw new IllegalArgumentException(method);
        return Bundle.EMPTY;
    }
    @Override public Cursor query(Uri uri,String[] projection,String selection,String[] args,String order){throw new UnsupportedOperationException();}
    @Override public String getType(Uri uri){return null;}
    @Override public Uri insert(Uri uri,ContentValues values){throw new UnsupportedOperationException();}
    @Override public int update(Uri uri,ContentValues values,String selection,String[] args){throw new UnsupportedOperationException();}
    @Override public int delete(Uri uri,String selection,String[] args){throw new UnsupportedOperationException();}
}
