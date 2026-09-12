package io.github.gplaider.tinyagent;

import android.content.Context;
import android.os.Build;
import android.system.Os;
import io.github.muntashirakon.adb.AbsAdbConnectionManager;
import io.github.muntashirakon.adb.android.AdbMdns;
import java.io.*;
import java.math.BigInteger;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.security.*;
import java.security.cert.Certificate;
import java.security.cert.CertificateFactory;
import java.security.spec.PKCS8EncodedKeySpec;
import java.util.Date;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicReference;
import org.bouncycastle.asn1.x500.X500Name;
import org.bouncycastle.cert.jcajce.JcaX509CertificateConverter;
import org.bouncycastle.cert.jcajce.JcaX509v3CertificateBuilder;
import org.bouncycastle.operator.jcajce.JcaContentSignerBuilder;

/** Local Android wireless debugging only; pairing identity never leaves no_backup. */
final class WirelessAdb extends AbsAdbConnectionManager {
    private final PrivateKey key;
    private final Certificate certificate;
    private final Context context;
    private volatile io.github.muntashirakon.adb.PairingConnectionCtx pendingPair;
    WirelessAdb(Context context) throws Exception {
        this.context = context.getApplicationContext();
        File directory = identity(this.context);
        key = KeyFactory.getInstance("RSA").generatePrivate(new PKCS8EncodedKeySpec(Files.readAllBytes(new File(directory,"key.pk8").toPath())));
        try (var input = new FileInputStream(new File(directory,"certificate.der"))) {
            certificate = CertificateFactory.getInstance("X.509").generateCertificate(input);
        }
        setApi(Build.VERSION.SDK_INT);
        setTimeout(15, TimeUnit.SECONDS);
        setThrowOnUnauthorised(true);
    }
    static boolean selected(Context context) {
        return "wireless".equals(transport(context));
    }
    static String transport(Context context) {
        var prefs = context.getSharedPreferences("connection",0);
        // Preserve an explicitly saved legacy endpoint when updating an older APK.
        return prefs.getString("transport",prefs.getString("port","").isEmpty() ? "stock" : "legacy");
    }
    private static synchronized File identity(Context context) throws Exception {
        File directory = new File(context.getNoBackupFilesDir(),"wireless-adb-identity");
        if (directory.exists()) return directory; // Corruption must fail, never silently replace an authorized key.
        File staged = Files.createTempDirectory(context.getNoBackupFilesDir().toPath(),"wireless-pending-").toFile();
        try {
            Os.chmod(staged.toString(),0700);
            var generator = KeyPairGenerator.getInstance("RSA"); generator.initialize(2048);
            var pair = generator.generateKeyPair();
            long now = System.currentTimeMillis();
            var name = new X500Name("CN=TinyAgent");
            var builder = new JcaX509v3CertificateBuilder(name,new BigInteger(128,new SecureRandom()),
                    new Date(now-86400000L),new Date(now+10L*365*86400000L),name,pair.getPublic());
            byte[] cert = new JcaX509CertificateConverter().getCertificate(builder.build(
                    new JcaContentSignerBuilder("SHA256withRSA").build(pair.getPrivate()))).getEncoded();
            Files.write(new File(staged,"key.pk8").toPath(),pair.getPrivate().getEncoded());
            Files.write(new File(staged,"certificate.der").toPath(),cert);
            Os.chmod(new File(staged,"key.pk8").toString(),0600);
            Os.chmod(new File(staged,"certificate.der").toString(),0600);
            Files.move(staged.toPath(),directory.toPath(),StandardCopyOption.ATOMIC_MOVE);
            return directory;
        } finally {
            Files.deleteIfExists(new File(staged,"key.pk8").toPath());
            Files.deleteIfExists(new File(staged,"certificate.der").toPath());
            Files.deleteIfExists(staged.toPath());
        }
    }
    @Override protected PrivateKey getPrivateKey() { return key; }
    @Override protected Certificate getCertificate() { return certificate; }
    @Override protected String getDeviceName() { return "TinyAgent"; }

    void pairLocal(String code) throws Exception {
        if (!code.matches("[0-9]{6}")) throw new IOException("페어링 코드 6자리를 입력하세요.");
        InetSocketAddress address = discover(AdbMdns.SERVICE_TYPE_TLS_PAIRING);
        try (var client = new io.github.muntashirakon.adb.PairingConnectionCtx(address.getAddress().getHostAddress(),
                address.getPort(),code.getBytes(StandardCharsets.US_ASCII),key,certificate,"TinyAgent")) {
            pendingPair = client; client.start();
        } finally { pendingPair = null; }
    }
    String connectLocal() throws Exception {
        InetSocketAddress address = discover(AdbMdns.SERVICE_TYPE_TLS_CONNECT);
        if (!connect(address.getAddress().getHostAddress(),address.getPort())) throw new IOException("무선 ADB 연결 실패");
        return "local wireless debugging · " + address.getPort();
    }
    private InetSocketAddress discover(String service) throws Exception {
        var found = new AtomicReference<InetSocketAddress>();
        var ready = new CountDownLatch(1);
        var mdns = new AdbMdns(context,service,(host,port) -> {
            try {
                if (host != null && port > 0 && port <= 65535 && NetworkInterface.getByInetAddress(host) != null) {
                    found.compareAndSet(null,new InetSocketAddress(host,port)); ready.countDown();
                }
            } catch (SocketException ignored) { }
        });
        mdns.start();
        try {
            if (!ready.await(25,TimeUnit.SECONDS)) throw new IOException("이 폰의 무선 디버깅을 찾지 못했습니다. Wi-Fi와 무선 디버깅을 확인하고 다시 시도하세요.");
            return found.get();
        } finally { mdns.stop(); }
    }
    String shell(String command) throws Exception {
        var result = execute(command);
        if (result.exitCode() != 0) throw new IOException("ADB 명령 실패 · exit=" + result.exitCode());
        return result.stdout() + result.stderr();
    }
    AdbShellResult execute(String command) throws Exception {
        var connection = getAdbConnection();
        var timer = Executors.newSingleThreadScheduledExecutor();
        timer.schedule(() -> { try { connection.close(); } catch (IOException ignored) { } },60,TimeUnit.SECONDS);
        try (var stream = openStream("shell,v2,raw:" + command)) {
            return AdbShellResult.read(stream.openInputStream());
        } finally { timer.shutdownNow(); }
    }
    void install(File apk) throws Exception {
        var connection = getAdbConnection();
        var timer = Executors.newSingleThreadScheduledExecutor();
        timer.schedule(() -> { try { connection.close(); } catch (IOException ignored) { } },180,TimeUnit.SECONDS);
        try (var stream = openStream("exec:cmd package install -r -S " + apk.length()); var source = new FileInputStream(apk)) {
            var output = stream.openOutputStream();
            byte[] buffer = new byte[65536];
            for (int n; (n=source.read(buffer))!=-1;) output.write(buffer,0,n);
            output.flush();
            var response = new ByteArrayOutputStream();
            var input = stream.openInputStream();
            for (int n; (n=input.read(buffer))!=-1;) {
                if (response.size()+n>8192) throw new IOException("PackageManager 응답 한도 초과");
                response.write(buffer,0,n);
            }
            if (!new String(response.toByteArray(),StandardCharsets.UTF_8).trim().equals("Success")) throw new IOException("PackageManager 설치 성공을 확인하지 못했습니다.");
        } finally { timer.shutdownNow(); }
    }
    @Override public void close() throws IOException {
        if (pendingPair != null) pendingPair.close();
        super.close();
    }
}
