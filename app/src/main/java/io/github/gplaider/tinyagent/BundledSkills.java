package io.github.gplaider.tinyagent;

import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;

/** APK-owned skills live beside the fixed harness, never in host Codex's home. */
final class BundledSkills {
    interface Assets { InputStream open(String name) throws IOException; }

    static void install(Path home, Assets assets) throws IOException {
        Path directory = home;
        if (Files.isSymbolicLink(home)) throw new IOException("Skill home must not be a symlink");
        for (String name : new String[] {".tinyagent", "skills", "phone-use", "scripts"}) {
            directory = directory.resolve(name);
            if (Files.isSymbolicLink(directory)) throw new IOException("Bundled skill path must not be a symlink");
            Files.createDirectories(directory);
        }
        // Runtime preparation happens before backend startup. Publish code before its instructions.
        Path root = directory.getParent();
        for (String name : new String[] {"scripts/phone.py", "SKILL.md"}) {
            Path destination = root.resolve(name);
            if (Files.exists(destination, LinkOption.NOFOLLOW_LINKS) && !Files.isRegularFile(destination, LinkOption.NOFOLLOW_LINKS))
                throw new IOException("Bundled skill target must be a regular file");
            Path temporary = Files.createTempFile(destination.getParent(), ".skill-", ".part");
            try (InputStream input = assets.open("skills/phone-use/" + name)) {
                Files.copy(input, temporary, StandardCopyOption.REPLACE_EXISTING);
                Files.move(temporary, destination, StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING);
            } finally {
                Files.deleteIfExists(temporary);
            }
        }
    }
}
