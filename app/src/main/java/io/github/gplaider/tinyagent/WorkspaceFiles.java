package io.github.gplaider.tinyagent;

import android.os.ParcelFileDescriptor;
import android.system.ErrnoException;
import android.system.Os;
import android.system.OsConstants;
import java.io.*;
import java.nio.file.*;

/** Workspace reads validate the opened inode, not just a path checked earlier. */
final class WorkspaceFiles {
    private final File root;

    WorkspaceFiles(File filesDir) throws IOException {
        root = new File(filesDir.getCanonicalFile(), "linux/workspace");
    }

    File resolve(String relative) throws IOException {
        if (relative == null || relative.isEmpty() || relative.indexOf('\0') >= 0
                || new File(relative).isAbsolute())
            throw new IOException("작업공간 안의 상대 파일 경로를 지정하세요.");
        // Android may alias filesDir itself, but a replaced linux/workspace must not
        // redefine the boundary to include another private directory.
        if (!root.equals(root.getCanonicalFile()) || !root.isDirectory())
            throw new IOException("작업공간 경로가 없거나 변경되었습니다.");
        File file = new File(root, relative).getCanonicalFile();
        if (!inside(file.toPath()) || !file.isFile())
            throw new IOException("작업공간 안의 일반 파일을 지정하세요.");
        return file;
    }

    private boolean inside(Path path) {
        return !path.equals(root.toPath()) && path.startsWith(root.toPath());
    }

    ParcelFileDescriptor open(String relative) throws IOException {
        File file = resolve(relative);
        FileDescriptor raw = null;
        ParcelFileDescriptor owned = null;
        try {
            // NONBLOCK prevents a regular file replaced by a FIFO from hanging open.
            raw = Os.open(file.toString(), OsConstants.O_RDONLY | OsConstants.O_CLOEXEC
                    | OsConstants.O_NOFOLLOW | OsConstants.O_NONBLOCK, 0);
            owned = ParcelFileDescriptor.dup(raw);
            // dup need not retain the original descriptor's close-on-exec flag.
            Os.fcntlInt(owned.getFileDescriptor(), OsConstants.F_SETFD, OsConstants.FD_CLOEXEC);
            if (!OsConstants.S_ISREG(Os.fstat(owned.getFileDescriptor()).st_mode))
                throw new IOException("작업공간 안의 일반 파일을 지정하세요.");
            // Also catches a parent directory swapped to a symlink between resolve/open.
            Path actual = Paths.get(Os.readlink("/proc/self/fd/" + owned.getFd()));
            if (!inside(actual) || !actual.equals(file.toPath()))
                throw new IOException("파일을 여는 동안 작업공간 경로가 변경되었습니다.");
            ParcelFileDescriptor result = owned;
            owned = null;
            return result;
        } catch (ErrnoException error) {
            throw new IOException("작업공간 파일을 열 수 없습니다: " + error.getMessage(), error);
        } finally {
            // dup transfers ownership to the returned PFD; the original is always ours.
            if (raw != null) try { Os.close(raw); } catch (ErrnoException ignored) { }
            if (owned != null) owned.close();
        }
    }

    InputStream input(String relative) throws IOException {
        return new ParcelFileDescriptor.AutoCloseInputStream(open(relative));
    }
}
