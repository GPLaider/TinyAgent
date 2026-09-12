package android.os;
import java.io.*;
import android.system.*;
/** Host API double: actual dup/close/read operations on Linux descriptors. */
public class ParcelFileDescriptor implements Closeable {
    public static boolean failDup;
    private final FileDescriptor fd;
    private boolean closed;
    private ParcelFileDescriptor(FileDescriptor fd) { this.fd = fd; }
    public static ParcelFileDescriptor dup(FileDescriptor fd) throws IOException {
        if (failDup) throw new IOException("injected dup failure");
        try { return new ParcelFileDescriptor(Os.dup(fd)); }
        catch (ErrnoException e) { throw new IOException(e); }
    }
    public FileDescriptor getFileDescriptor() { return fd; }
    public int getFd() { return Os.number(fd); }
    public long getStatSize() {
        try { return Os.size(fd); } catch (ErrnoException error) { return -1; }
    }
    public void close() throws IOException {
        if (closed) return;
        closed = true;
        try { Os.close(fd); } catch (ErrnoException e) { throw new IOException(e); }
    }
    public static class AutoCloseInputStream extends FileInputStream {
        private final ParcelFileDescriptor owner;
        public AutoCloseInputStream(ParcelFileDescriptor owner) { super(owner.fd); this.owner = owner; }
        @Override public void close() throws IOException { owner.close(); }
    }
}
