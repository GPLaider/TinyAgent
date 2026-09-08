package io.github.gplaider.tinyagent;

/** Run with javac/java; no Android SDK, dependency resolution, device or test framework needed. */
public final class LocalPolicyCheck {
    private static int checks;
    public static void main(String[] args) {
        require(LocalPolicy.resumeRuntime(true, null, LocalPolicy.RUNTIME_READY));
        require(!LocalPolicy.resumeRuntime(false, null, LocalPolicy.RUNTIME_READY));
        require(!LocalPolicy.resumeRuntime(true, null, "로컬 백엔드를 중단했습니다."));
        require(!LocalPolicy.resumeRuntime(true, null, null));
        require(!LocalPolicy.resumeRuntime(true, false, LocalPolicy.RUNTIME_READY));
        require(LocalPolicy.resumeRuntime(true, true, "환경 준비 실패"));
        require(!LocalPolicy.resumeRuntime(false, true, LocalPolicy.RUNTIME_READY));
        require(LocalPolicy.port("5555") == 5555);
        require(LocalPolicy.port("1") == 1);
        require(LocalPolicy.port("65535") == 65535);
        for (String bad : new String[] {null, "", "0", "65536", "9999999999", "-1", "+5555", "5555\n", " 5555", "5555;id", "127.0.0.1:5555", "５５５５"}) {
            rejects(() -> LocalPolicy.port(bad));
        }
        for (String good : new String[] {LocalPolicy.BACKEND_ORIGIN, LocalPolicy.BACKEND_ORIGIN + "/", LocalPolicy.BACKEND_ORIGIN + "/session/a?x=1#end"}) {
            require(LocalPolicy.isBackendUrl(good));
        }
        for (String bad : new String[] {null, "", "file:///etc/passwd", "content://x", "javascript:alert(1)", "data:text/html,x", "https://127.0.0.1:4096", "http://127.0.0.1", "http://localhost:4096", "http://127.0.0.2:4096", "http://127.0.0.1.:4096", "http://[::1]:4096", "http://127.0.0.1:4096.evil/", "http://127.0.0.1:4096@evil/", "http://evil@127.0.0.1:4096/", "http://127.0.0.1:4096\\@evil/", "http://127.0.0.1:4096\n"}) {
            require(!LocalPolicy.isBackendUrl(bad));
        }
        require(LocalPolicy.isBrowserUrl("https://opencode.ai/docs"));
        require(!LocalPolicy.isBackendUrl("http://127.0.0.1:4096"));
        for (String bad : new String[]{"http://evil@127.0.0.1:4097", "http://127.0.0.1:4097@evil/", "http://localhost:4097"})
            require(!LocalPolicy.isBackendUrl(bad));
        LocalPolicy.verifyInstallerUid(2000, 2000, false);
        LocalPolicy.verifyInstallerUid(0, 0, true);
        for (int verified : new int[]{-1, 0, 2000, 10225}) {
            for (int current : new int[]{-1, 0, 2000, 10225}) {
                if (verified != 2000 || current != 2000) rejects(() -> LocalPolicy.verifyInstallerUid(verified, current, false));
                if (verified != 0 || current != 0) rejects(() -> LocalPolicy.verifyInstallerUid(verified, current, true));
            }
        }
        require(!LocalPolicy.isBrowserUrl("intent://x"));
        require(!LocalPolicy.isBrowserUrl("https://token@example.com"));
        require(LocalPolicy.uid("uid=0(root) gid=0(root)\n") == 0);
        require(LocalPolicy.uid("uid=2000(shell) gid=2000(shell)") == 2000);
        for (String bad : new String[] {null, "root", "uid=-1(root)", "uid=0evil", "prefix uid=0(root)", "uid=999999999999(root)"}) rejects(() -> LocalPolicy.uid(bad));
        String path = "/data/user/0/io.github.gplaider.tinyagent/no_backup/self-probe-1.txt";
        require(LocalPolicy.shellPath(path).equals(path));
        for (String bad : new String[] {null, "relative", "/tmp/a;id", "/tmp/a b", "/tmp/../x", "/tmp/a\n"}) rejects(() -> LocalPolicy.shellPath(bad));
        String nonce = "fbd275af-f597-4312-829f-5479d1be2d0d";
        LocalPolicy.verifySelf("lyriq", "lyriq", "uid=0(root)", nonce, nonce);
        checks++;
        rejects(() -> LocalPolicy.verifySelf("other", "lyriq", "uid=0(root)", nonce, nonce));
        rejects(() -> LocalPolicy.verifySelf("lyriq", "lyriq", "uid=2000(shell)", nonce, nonce));
        rejects(() -> LocalPolicy.verifySelf("lyriq", "lyriq", "uid=0(root)", nonce, "different"));
        rejects(() -> LocalPolicy.verifySelf("lyriq", "lyriq", "uid=0(root)", "", ""));
        System.out.println("LocalPolicyCheck: " + checks + " checks passed");
    }
    private static void require(boolean value) {
        checks++;
        if (!value) throw new AssertionError("check " + checks);
    }
    private static void rejects(Runnable work) {
        checks++;
        try { work.run(); }
        catch (IllegalArgumentException expected) { return; }
        throw new AssertionError("check " + checks + ": invalid input accepted");
    }
}
