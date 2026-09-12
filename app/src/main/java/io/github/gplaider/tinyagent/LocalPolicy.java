package io.github.gplaider.tinyagent;

import java.net.URI;
import java.net.URISyntaxException;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/** The single boundary for endpoint, shell path and self-device validation. No Android dependency. */
public final class LocalPolicy {
    public static final String ADB_HOST = "127.0.0.1";
    public static final String BACKEND_ORIGIN = "http://127.0.0.1:4097";
    public static final String RUNTIME_READY = "Fedora 설치 완료. 앱 권한의 로컬 백엔드를 시작했습니다.";
    private static final Pattern UID = Pattern.compile("^uid=([0-9]+)(?:\\(|\\s|$)");

    private LocalPolicy() {}

    public static boolean resumeRuntime(boolean prepared, Boolean wanted, String legacyStatus) {
        return prepared && (wanted != null ? wanted : RUNTIME_READY.equals(legacyStatus));
    }

    public static int port(String input) {
        if (input == null || !input.matches("[0-9]{1,5}")) {
            throw new IllegalArgumentException("포트는 1~65535 사이의 숫자로 입력하세요.");
        }
        int value = Integer.parseInt(input);
        if (value < 1 || value > 65535) {
            throw new IllegalArgumentException("포트는 1~65535 사이의 숫자로 입력하세요.");
        }
        return value;
    }

    public static int listenPort(String addresses) {
        if(addresses==null)return 0;
        for(String address:addresses.trim().split("[;,\\s]+")) {
            if(!address.startsWith("tcp:"))continue;
            try {return port(address.substring(address.lastIndexOf(':')+1));}
            catch(IllegalArgumentException ignored) { }
        }
        return 0;
    }

    public static boolean isBackendUrl(String url) {
        URI uri = uri(url);
        return uri != null && "http".equals(uri.getScheme())
                && ADB_HOST.equals(uri.getHost()) && uri.getPort() == 4097
                && uri.getRawUserInfo() == null;
    }

    public static boolean isBrowserUrl(String url) {
        URI uri = uri(url);
        return uri != null && ("http".equals(uri.getScheme()) || "https".equals(uri.getScheme()))
                && uri.getHost() != null && uri.getRawUserInfo() == null;
    }

    private static URI uri(String url) {
        if (url == null) return null;
        try { return new URI(url); }
        catch (URISyntaxException error) { return null; }
    }

    public static int uid(String idOutput) {
        Matcher matcher = UID.matcher(idOutput == null ? "" : idOutput.trim());
        if (!matcher.find()) throw new IllegalArgumentException("id 결과에서 실행 UID를 확인할 수 없습니다.");
        try { return Integer.parseInt(matcher.group(1)); }
        catch (NumberFormatException error) { throw new IllegalArgumentException("실행 UID 범위가 올바르지 않습니다."); }
    }

    public static String shellPath(String path) {
        // Only a generated app-private path is passed to cat; never accept shell syntax.
        if (path == null || !path.matches("/[A-Za-z0-9_./-]+") || path.contains("/../")
                || path.endsWith("/..")) throw new IllegalArgumentException("진단 파일 경로가 올바르지 않습니다.");
        return path;
    }

    public static void verifyInstallerUid(int verified, int current, boolean root) {
        int expected = root ? 0 : 2000;
        if (verified != expected || current != expected)
            throw new IllegalArgumentException("선택한 설치 권한의 자기 기기 UID 인증이 필요합니다.");
    }

    public static void verifySelf(String device, String ownDevice, String id,
                                  String expectedNonce, String returnedNonce) {
        if (device == null || device.trim().isEmpty() || !device.equals(ownDevice)) {
            throw new IllegalArgumentException("연결 대상의 Android 기기 정보가 이 기기와 다릅니다.");
        }
        if (uid(id) != 0) throw new IllegalArgumentException("root ADB가 필요합니다. 현재 실행 UID가 0이 아닙니다.");
        if (expectedNonce == null || expectedNonce.length() < 32 || returnedNonce == null
                || !MessageDigest.isEqual(expectedNonce.getBytes(StandardCharsets.UTF_8),
                        returnedNonce.getBytes(StandardCharsets.UTF_8))) {
            throw new IllegalArgumentException("이 앱의 비공개 진단 파일 확인 실패. 자기 기기 연결로 인정하지 않습니다.");
        }
    }
}
