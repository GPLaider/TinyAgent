package io.github.gplaider.tinyagent;

import java.io.*;
import java.nio.charset.StandardCharsets;

/** Bounded shell-v2 result; EOF is not a successful exit. */
record AdbShellResult(String stdout, String stderr, int exitCode) {
    static AdbShellResult read(InputStream source) throws IOException {
        var input = new DataInputStream(source);
        var stdout = new ByteArrayOutputStream();
        var stderr = new ByteArrayOutputStream();
        while (true) {
            int kind = input.readUnsignedByte();
            int length = Integer.reverseBytes(input.readInt());
            if (length < 0 || length > 1024 * 1024 || stdout.size() + stderr.size() + length > 1024 * 1024)
                throw new IOException("ADB 출력 한도 초과");
            if (kind == 3) {
                if (length != 1) throw new IOException("잘못된 ADB 종료 프레임");
                return new AdbShellResult(new String(stdout.toByteArray(), StandardCharsets.UTF_8),
                        new String(stderr.toByteArray(), StandardCharsets.UTF_8), input.readUnsignedByte());
            }
            if (kind != 1 && kind != 2) throw new IOException("예상하지 못한 ADB shell frame");
            byte[] bytes = new byte[length]; input.readFully(bytes);
            (kind == 1 ? stdout : stderr).write(bytes);
        }
    }
}
