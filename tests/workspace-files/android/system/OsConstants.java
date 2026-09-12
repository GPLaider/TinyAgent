package android.system;
public class OsConstants {
    public static final int O_RDONLY=0, O_NONBLOCK=2048, O_NOFOLLOW=131072, O_CLOEXEC=524288;
    public static final int F_GETFD=1, F_SETFD=2, FD_CLOEXEC=1;
    public static boolean S_ISREG(int mode) { return (mode & 0170000) == 0100000; }
}
