package io.github.gplaider.tinyagent;

import java.io.IOException;
import java.nio.file.*;
import java.security.*;

/** Verify before replacing the executable; never overwrite a running inode in place. */
final class RuntimeExecutable {
    static boolean matches(Path file, String expected) throws Exception {
        if (!Files.isRegularFile(file, LinkOption.NOFOLLOW_LINKS)) return false;
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        try (var input = Files.newInputStream(file)) {
            byte[] buffer = new byte[65536];
            for (int n; (n = input.read(buffer)) != -1;) digest.update(buffer, 0, n);
        }
        StringBuilder actual = new StringBuilder();
        for (byte value : digest.digest()) actual.append(String.format("%02x", value & 255));
        return actual.toString().equals(expected);
    }

    static void replace(Path candidate, Path target, String expected) throws Exception {
        if (!matches(candidate, expected)) throw new IOException("OpenCode 실행 파일 SHA256 불일치");
        if (!candidate.toFile().setExecutable(true, true)) throw new IOException("OpenCode 실행 권한 설정 실패");
        // No copy fallback: a failed atomic move must leave the previous backend intact.
        Files.move(candidate, target, StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING);
    }
}
