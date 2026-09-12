package io.github.gplaider.tinyagent;

import android.content.Context;
import android.util.AtomicFile;
import java.io.File;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.ArrayList;
import java.util.List;

/** A Fedora root keeps its selected package manager across retries and app updates. */
final class PackageManagerChoice {
    private static File marker(Context context) { return new File(context.getFilesDir(), "linux/package-manager"); }
    static boolean locked(Context context) {
        return marker(context).exists() || new File(context.getFilesDir(), "linux/prepared-v1").exists();
    }
    static String validate(String value) throws IOException {
        if (!"dnfast".equals(value) && !"dnf5".equals(value)) throw new IOException("Unknown Fedora package manager");
        return value;
    }
    static synchronized String read(Context context) throws IOException {
        File file = marker(context);
        if (file.exists()) return validate(new String(new AtomicFile(file).readFully(), StandardCharsets.UTF_8).trim());
        // Existing roots predate this choice and have always used dnfast.
        if (new File(context.getFilesDir(), "linux/prepared-v1").exists()) return "dnfast";
        return validate(context.getSharedPreferences("runtime", Context.MODE_PRIVATE).getString("packageManager", "dnfast"));
    }
    static synchronized void select(Context context, String value) throws IOException {
        validate(value);
        if (locked(context)) throw new IOException("이미 준비를 시작한 Fedora 환경의 패키지 관리자는 변경할 수 없습니다.");
        if (!context.getSharedPreferences("runtime", Context.MODE_PRIVATE).edit().putString("packageManager", value).commit())
            throw new IOException("패키지 관리자 설정 저장 실패");
    }
    static synchronized String freeze(Context context) throws IOException {
        String value = read(context);
        File file = marker(context);
        if (!file.exists()) {
            Files.createDirectories(file.getParentFile().toPath());
            AtomicFile atomic = new AtomicFile(file);
            var output = atomic.startWrite();
            try { output.write(value.getBytes(StandardCharsets.UTF_8)); atomic.finishWrite(output); }
            catch (IOException error) { atomic.failWrite(output); throw error; }
        }
        return value;
    }
    static List<String> dnf5Command(String action, String... operation) throws IOException {
        if (List.of("check", "verify").contains(action)) return List.of("/usr/bin/dnf5", "check");
        if (action.equals("refresh")) return List.of("/usr/bin/dnf5", "--refresh", "makecache");
        if (!action.equals("install") || operation.length < 2 || !operation[0].equals("install"))
            throw new IOException("dnf5 supports install, repo refresh and check; dnfast journal recovery/migration is not applicable.");
        var args = new ArrayList<>(List.of("/usr/bin/dnf5"));
        args.addAll(List.of(operation));
        return args;
    }
}
