package android.system;
import java.io.FileDescriptor;
public class Os {
    static { System.loadLibrary("workspace_test"); }
    public static Runnable beforeOpen;
    public static boolean failReadlink, failStat, failFcntl;
    public static int fcntlInt(FileDescriptor fd, int cmd, int arg) throws ErrnoException {
        if (failFcntl) throw new ErrnoException("fcntl", 13);
        return fcntlNative(fd, cmd, arg);
    }
    private static native int fcntlNative(FileDescriptor fd, int cmd, int arg) throws ErrnoException;
    public static FileDescriptor open(String path, int flags, int mode) throws ErrnoException {
        Runnable hook = beforeOpen; beforeOpen = null;
        if (hook != null) hook.run();
        return openNative(path, flags, mode);
    }
    private static native FileDescriptor openNative(String path, int flags, int mode) throws ErrnoException;
    public static StructStat fstat(FileDescriptor fd) throws ErrnoException {
        if (failStat) throw new ErrnoException("fstat", 13);
        return new StructStat(statNative(fd));
    }
    public static String readlink(String path) throws ErrnoException {
        if (failReadlink) throw new ErrnoException("readlink", 13);
        return readlinkNative(path);
    }
    public static native int number(FileDescriptor fd);
    public static native long size(FileDescriptor fd) throws ErrnoException;
    public static native FileDescriptor dup(FileDescriptor fd) throws ErrnoException;
    public static native void close(FileDescriptor fd) throws ErrnoException;
    private static native int statNative(FileDescriptor fd) throws ErrnoException;
    private static native String readlinkNative(String path) throws ErrnoException;
}
