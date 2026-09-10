package io.github.gplaider.tinyagent;

import java.nio.file.*;
import java.security.MessageDigest;
import java.util.HexFormat;

public final class RuntimeExecutableCheck {
    public static void main(String[] args) throws Exception {
        Path root = Files.createTempDirectory("runtime-update-check-");
        Path installed = root.resolve("opencode"), candidate = root.resolve("candidate");
        Path data = root.resolve("user-data");
        byte[] next = "verified new executable".getBytes();
        String hash = HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(next));
        try {
            Files.writeString(installed, "previous executable");
            Files.writeString(data, "oauth and workspace sentinel");
            Files.writeString(candidate, "corrupt download");
            try {
                RuntimeExecutable.replace(candidate, installed, hash);
                throw new AssertionError("Accepted corrupt binary");
            } catch (java.io.IOException expected) { }
            if (!Files.readString(installed).equals("previous executable")) throw new AssertionError("Lost old binary");
            Files.write(candidate, next);
            RuntimeExecutable.replace(candidate, installed, hash);
            if (!RuntimeExecutable.matches(installed, hash) || Files.exists(candidate)) throw new AssertionError("Replace failed");
            if (!Files.readString(data).equals("oauth and workspace sentinel")) throw new AssertionError("User data changed");
            System.out.println("PASS: corrupt candidate rejected; old binary retained; verified atomic replacement; unrelated data retained");
        } finally {
            Files.deleteIfExists(candidate); Files.deleteIfExists(installed); Files.deleteIfExists(data); Files.delete(root);
        }
    }
}
