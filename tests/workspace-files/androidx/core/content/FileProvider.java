package androidx.core.content;
import android.content.Context;
import android.net.Uri;
import android.os.ParcelFileDescriptor;
import java.io.FileNotFoundException;
public class FileProvider {
    public Context context;
    public Context getContext() { return context; }
    public ParcelFileDescriptor openFile(Uri uri,String mode) throws FileNotFoundException { throw new AssertionError("unsafe superclass open"); }
    public int delete(Uri uri,String selection,String[] args) { throw new AssertionError("unsafe superclass delete"); }
}
