package io.github.gplaider.tinyagent;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.security.MessageDigest;
import java.util.*;
import org.json.JSONObject;

/** Every request enters through the app-owned native launcher before PRoot. */
final class DnfastRuntime {
    static final String REVISION = "1449710f35e1079c5999a3d6cc41800d4b432a4d";
    static final String CLI = "eb33f7c1326623cf3cc642095c6c1c065ead4aad457b57a79bda1a2167b6084a";
    static final String EXECUTOR = "14910c774700c88d6280b9ade9dc5facbc9d6bf07a9b17926b2446c6a6a5fd89";
    static final String OVERLAY = "9f55a462f0bec5c872cd4bd59bb0a436aa6f576b5098fb9240a94b93a2a58326";

    static void prepare(LocalLinuxRuntime runtime) throws Exception {
        synchronized (DnfastRuntime.class) { prepareLocked(runtime); }
    }
    private static void prepareLocked(LocalLinuxRuntime runtime) throws Exception {
        byte[] data;
        try (var input=runtime.context.getAssets().open("dnfast-manifest.json"); var output=new ByteArrayOutputStream()) {
            byte[] buffer=new byte[8192];
            for(int count;(count=input.read(buffer))!=-1;)output.write(buffer,0,count);
            data=output.toByteArray();
        }
        if (!hex(MessageDigest.getInstance("SHA-256").digest(data)).equals("ec8599eb4b44266abbbcafa0952a67d29d96d4ff5572566ad403c0c425492699"))
            throw new IOException("dnfast manifest hash mismatch");
        JSONObject files=new JSONObject(new String(data,StandardCharsets.UTF_8)).getJSONObject("files");
        Path cli=runtime.rootfs.toPath().resolve("usr/bin/dnfast");
        var checkpoint = new android.util.AtomicFile(new File(runtime.base, "dnfast-upgrade-1449710"));
        boolean upgraded = false;
        if (!Files.exists(cli)) runtime.unpack("dnfast-root-overlay.tar.gz.bin",OVERLAY,runtime.rootfs,"dnfast",files.length());
        else if (!RuntimeExecutable.matches(cli, CLI)
                || !RuntimeExecutable.matches(runtime.rootfs.toPath().resolve("usr/libexec/dnfast-executor"), EXECUTOR)) {
            if (!new File(runtime.rootfs, "usr/bin/python3").isFile())
                throw new IOException("dnfast 업데이트에 기존 Fedora Python이 필요합니다. 기존 환경은 보존했습니다.");
            for (String name : List.of("upgrade-dnfast-empty.py", "upgrade-dnfast-checked.py")) {
                try (var input = runtime.context.getAssets().open("bootstrap/" + name)) {
                    Files.copy(input, new File(runtime.home, name).toPath(), StandardCopyOption.REPLACE_EXISTING);
                }
            }
            String oldCli = "ada035264f62bba6e321df3a95d194d7ffa1ba9ec795a3c223c4a5726ecda67a";
            String oldExecutor = "56f09485e5d442f40fa9e9268404407e55e41c20c79d5da41a2a09980b86ea5d";
            String checked = null;
            try { checked = new String(checkpoint.readFully(), StandardCharsets.US_ASCII); }
            catch (FileNotFoundException missing) { /* First publication attempt. */ }
            if (RuntimeExecutable.matches(cli, oldCli)
                    && RuntimeExecutable.matches(runtime.rootfs.toPath().resolve("usr/libexec/dnfast-executor"), oldExecutor))
                checked = null; // No partial publication: validate current state again rather than trust a stale receipt.
            if (checked != null || RuntimeExecutable.matches(cli, oldCli)) {
                if (checked == null) {
                    StringBuilder state = new StringBuilder();
                    runtime.run(runtime.guest("/workspace", "/usr/bin/python3", "/root/upgrade-dnfast-checked.py",
                            "/tinyagent-installed.apk", "snapshot"), line -> { if (line.matches("[0-9a-f]{64}")) state.append(line); });
                    checked = state.toString();
                    if (!checked.matches("[0-9a-f]{64}")) throw new IOException("Invalid package state snapshot");
                    StringBuilder result = new StringBuilder();
                    runtime.run(command(runtime, oldCli, oldExecutor, new String[]{"app-runtime", "check"}),
                            line -> { if (line.startsWith("{") && line.contains("dnfast.cli.v1")) { result.setLength(0); result.append(line); } });
                    DnfastResult.require("upgrade-check", 0, result.toString());
                    var output = checkpoint.startWrite();
                    try { output.write(checked.getBytes(StandardCharsets.US_ASCII)); checkpoint.finishWrite(output); }
                    catch (Exception error) { checkpoint.failWrite(output); throw error; }
                }
                if (!checked.matches("[0-9a-f]{64}")) throw new IOException("Invalid preserved package checkpoint");
                runtime.run(runtime.guest("/workspace", "/usr/bin/python3", "/root/upgrade-dnfast-checked.py",
                        "/tinyagent-installed.apk", checked));
            } else {
                runtime.run(runtime.guest("/workspace", "/usr/bin/python3", "/root/upgrade-dnfast-empty.py", "/tinyagent-installed.apk"));
            }
            upgraded = true;
        }
        if (upgraded || checkpoint.getBaseFile().exists()) {
            runtime.runPackages("check", line -> {}, "app-runtime", "check");
            runtime.runPackages("migrate", line -> {}, "app-runtime", "migrate");
            runtime.runPackages("verify", line -> {}, "app-runtime", "check");
            checkpoint.delete();
        }
        for (var names=files.keys();names.hasNext();) {
            String name=names.next();
            Path path=runtime.rootfs.toPath().resolve(name).normalize();
            if (!path.startsWith(runtime.rootfs.toPath()) || !RuntimeExecutable.matches(path,files.getString(name)))
                throw new IOException("dnfast input differs: "+name+"; preserve existing runtime for recovery");
        }
    }

    static ProcessBuilder command(LocalLinuxRuntime runtime,String... operation) throws Exception {
        return command(runtime, CLI, EXECUTOR, operation);
    }
    private static ProcessBuilder command(LocalLinuxRuntime runtime, String cliHash, String executorHash, String[] operation) throws Exception {
        if (!RuntimeExecutable.matches(new File(runtime.rootfs,"usr/bin/dnfast").toPath(),cliHash)
                || !RuntimeExecutable.matches(new File(runtime.rootfs,"usr/libexec/dnfast-executor").toPath(),executorHash))
            throw new IOException("dnfast executable identity mismatch");
        var args=new ArrayList<>(List.of("/usr/bin/dnfast","--app-proot")); args.addAll(List.of(operation));
        ProcessBuilder builder=runtime.guest("/workspace",args.toArray(new String[0]));
        var proot=new ArrayList<>(builder.command());
        // Existing request-stage trace omits credentials and feeds durable package progress.
        proot.add(proot.indexOf("/usr/bin/dnfast"),"DNFAST_REFRESH_TRACE=1");
        String binds=String.join("\0",proot.subList(1,proot.indexOf("/usr/bin/env")));
        String nativeDir=runtime.context.getApplicationInfo().nativeLibraryDir;
        String runtimeHash=hex(MessageDigest.getInstance("SHA-256").digest(Files.readAllBytes(Paths.get(nativeDir,"libproot.so"))));
        String bindsHash=hex(MessageDigest.getInstance("SHA-256").digest(binds.getBytes(StandardCharsets.UTF_8)));
        var launch=new ArrayList<>(List.of(nativeDir+"/libdnfastlaunch.so",runtime.rootfs.getCanonicalPath(),
                Integer.toString(android.os.Process.myUid()),runtimeHash,bindsHash,cliHash,executorHash,"--"));
        launch.addAll(proot); return builder.command(launch);
    }
    // Cache only successful planning publication. Native binding/journal checks remain authoritative.
    static String planningIdentity(LocalLinuxRuntime runtime) throws Exception {
        Path rootId = runtime.rootfs.toPath().resolve(".tinyagent-root-id");
        if (!Files.exists(rootId, LinkOption.NOFOLLOW_LINKS)) return null;
        if (Files.isSymbolicLink(rootId)) throw new IOException("Invalid dnfast root identity");
        String id = new String(Files.readAllBytes(rootId), StandardCharsets.US_ASCII);
        if (!id.matches("[0-9a-f]{64}")) throw new IOException("Invalid dnfast root identity");
        List<String> argv = command(runtime, "repo", "refresh").command();
        // Launcher prefix contains canonical root, UID, runtime, bind, CLI and executor hashes.
        String identity = "app-proot-v1\0schema=1\0" + id + "\0" + android.system.Os.getgid()
                + "\0" + String.join("\0", argv.subList(0, argv.indexOf("--")));
        return hex(MessageDigest.getInstance("SHA-256").digest(identity.getBytes(StandardCharsets.UTF_8)));
    }
    static boolean planningCurrent(LocalLinuxRuntime runtime) throws Exception {
        String identity = planningIdentity(runtime);
        var marker = new android.util.AtomicFile(new File(runtime.base, "dnfast-planning-binding"));
        try { return identity != null && identity.equals(new String(marker.readFully(), StandardCharsets.US_ASCII)); }
        catch (FileNotFoundException missing) { return false; }
    }
    static void rememberPlanning(LocalLinuxRuntime runtime, String before) throws Exception {
        String after = planningIdentity(runtime);
        if (before == null || !before.equals(after)) return;
        var marker = new android.util.AtomicFile(new File(runtime.base, "dnfast-planning-binding"));
        var output = marker.startWrite();
        try { output.write(after.getBytes(StandardCharsets.US_ASCII)); marker.finishWrite(output); }
        catch (Exception error) { marker.failWrite(output); throw error; }
    }
    private static String hex(byte[] bytes) {
        StringBuilder out=new StringBuilder();for(byte b:bytes)out.append(String.format("%02x",b&255));return out.toString();
    }
}
