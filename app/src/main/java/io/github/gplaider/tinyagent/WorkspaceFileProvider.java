package io.github.gplaider.tinyagent;

import android.net.Uri;
import android.os.ParcelFileDescriptor;
import androidx.core.content.FileProvider;
import java.io.*;

/** Read-only artifact grants use the same checked FD as native workspace reads. */
public final class WorkspaceFileProvider extends FileProvider {
    @Override public ParcelFileDescriptor openFile(Uri uri, String mode) throws FileNotFoundException {
        if (!"r".equals(mode)) throw new FileNotFoundException("작업공간 공유는 읽기 전용입니다.");
        String path = uri.getPath();
        if (path == null || !path.startsWith("/workspace/"))
            throw new FileNotFoundException("작업공간 파일 경로가 아닙니다.");
        try {
            return new WorkspaceFiles(getContext().getFilesDir()).open(path.substring("/workspace/".length()));
        } catch (IOException error) {
            FileNotFoundException missing = new FileNotFoundException(error.getMessage());
            missing.initCause(error);
            throw missing;
        }
    }

    @Override public int delete(Uri uri, String selection, String[] selectionArgs) {
        throw new SecurityException("작업공간 공유는 읽기 전용입니다.");
    }
}
