package android.net;
public class Uri {
    private final java.net.URI uri;
    private Uri(String uri) { this.uri=java.net.URI.create(uri); }
    public static Uri parse(String uri) { return new Uri(uri); }
    public String getPath() { return uri.getPath(); }
}
