"""Run the production DNS method with deterministic Android doubles; no device edits."""
from pathlib import Path
import argparse
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--android-jar', type=Path)
args = parser.parse_args()
source = (ROOT / 'app/src/main/java/io/github/gplaider/tinyagent/LocalLinuxRuntime.java').read_text(encoding='utf-8')
method = source[source.index('    void refreshDns()'):source.index('    private String password()')]
test = r'''
import java.io.*;
import java.nio.file.*;
import java.nio.charset.StandardCharsets;
import java.net.*;
import java.util.*;
public class DnsCheck {
    static class NetworkCapabilities extends android.net.NetworkCapabilities {
        static final int TRANSPORT_WIFI=1, TRANSPORT_CELLULAR=0, TRANSPORT_ETHERNET=3;
        NetworkCapabilities() { super(false); }
    }
    static class android {
        static class os { static class Build { static class VERSION { static int SDK_INT=36; } } }
        static class net {
            static class LinkProperties {
                List<InetAddress> dns;
                LinkProperties(String ip) throws Exception { dns=ip==null?List.of():List.of(InetAddress.getByName(ip)); }
                List<InetAddress> getDnsServers() { return dns; }
            }
            static class NetworkCapabilities {
                static final int TRANSPORT_VPN=4, NET_CAPABILITY_INTERNET=12, NET_CAPABILITY_VALIDATED=16;
                boolean vpn, validated=true; int transport=1;
                NetworkCapabilities(boolean vpn) { this.vpn=vpn; }
                boolean hasTransport(int t) { return t==TRANSPORT_VPN ? vpn : t==transport; }
                int[] getTransportTypes() { return new int[]{transport}; }
                boolean hasCapability(int c) { return c==NET_CAPABILITY_INTERNET || validated; }
            }
        }
    }
    static class ConnectivityManager {
        Integer active=1;
        Map<Integer,android.net.LinkProperties> links=new LinkedHashMap<>();
        Map<Integer,android.net.NetworkCapabilities> caps=new LinkedHashMap<>();
        Integer getActiveNetwork() { return active; }
        android.net.LinkProperties getLinkProperties(Integer n) { return links.get(n); }
        android.net.NetworkCapabilities getNetworkCapabilities(Integer n) { return caps.get(n); }
        Integer[] getAllNetworks() { return links.keySet().toArray(new Integer[0]); }
        void add(int n,boolean vpn,String dns) throws Exception {
            links.put(n,new android.net.LinkProperties(dns)); caps.put(n,new android.net.NetworkCapabilities(vpn));
        }
    }
    static class Context {
        ConnectivityManager manager=new ConnectivityManager();
        ConnectivityManager getSystemService(Class<?> type) { return manager; }
    }
    Context context=new Context(); File rootfs;
    DnsCheck(Path root) throws Exception { rootfs=root.toFile(); Files.createDirectories(root.resolve("etc")); }
    /* METHOD */
    static void expect(boolean value,String message) { if(!value) throw new AssertionError(message); }
    public static void main(String[] args) throws Exception {
        DnsCheck t=new DnsCheck(Path.of(args[0])); var m=t.context.manager;
        Path path=t.rootfs.toPath().resolve("etc/resolv.conf");
        m.add(1,false,"192.0.2.1"); t.refreshDns();
        expect(Files.readString(path).equals("nameserver 192.0.2.1\noptions timeout:2 attempts:2\n"),"ordinary DNS");
        m.add(1,true,"100.100.100.100"); m.add(2,false,"192.0.2.2"); t.refreshDns();
        expect(Files.readString(path).contains("100.100.100.100"),"VPN DNS wins");
        m.add(1,true,null); m.add(3,false,"192.0.2.3"); m.caps.get(3).transport=0; t.refreshDns();
        expect(Files.readString(path).contains("192.0.2.2"),"VPN Wi-Fi transport excludes cellular");
        Files.delete(path); m.caps.get(3).transport=1; t.refreshDns();
        expect(!Files.exists(path),"ambiguous underlay must not be guessed");
        m.links.remove(3); t.refreshDns(); expect(Files.exists(path),"unique default underlay");
        Files.delete(path); m.caps.get(1).transport=-1; t.refreshDns();
        expect(!Files.exists(path),"unknown underlay transport");
        m.caps.get(1).transport=1; m.caps.get(2).validated=false; t.refreshDns();
        expect(!Files.exists(path),"unvalidated underlay");
        m.caps.get(2).validated=true; android.os.Build.VERSION.SDK_INT=30; t.refreshDns();
        expect(Files.exists(path),"API 30 unique fallback");
        String before=Files.readString(path); m.active=null; t.refreshDns();
        expect(Files.readString(path).equals(before),"offline preserves existing DNS");
        m.active=1; Files.delete(path); Path target=t.rootfs.toPath().resolve("protected");
        Files.writeString(target,"unchanged"); Files.createSymbolicLink(path,target);
        try { t.refreshDns(); throw new AssertionError("symlink accepted"); } catch(IOException expected) { }
        expect(Files.readString(target).equals("unchanged"),"symlink target preserved");
        System.out.println("PASS: 10 production DNS regression checks");
    }
}
'''
with tempfile.TemporaryDirectory(prefix='tinyagent-dns-') as temp:
    path = Path(temp)
    java = path / 'DnsCheck.java'
    java.write_text(test.replace('/* METHOD */', method), encoding='utf-8')
    subprocess.run(['javac', '-encoding', 'UTF-8', str(java)], check=True)
    subprocess.run(['java', '-cp', str(path), 'DnsCheck', str(path / 'root')], check=True)
    if args.android_jar:
        sdk_source = path / 'SdkDnsCheck.java'
        sdk_source.write_text('import android.content.Context; import android.net.ConnectivityManager; import android.net.NetworkCapabilities; '
                             'import java.io.*; import java.util.*; import java.nio.file.*; '
                             'import java.nio.charset.StandardCharsets; '
                             'class SdkDnsCheck { Context context; File rootfs; ' + method + '}', encoding='utf-8')
        subprocess.run(['javac', '-encoding', 'UTF-8', '-cp', str(args.android_jar), str(sdk_source)], check=True)
        print('PASS: production DNS method compiles against Android SDK')
