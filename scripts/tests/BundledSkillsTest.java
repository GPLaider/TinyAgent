package io.github.gplaider.tinyagent;

import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Comparator;

/** Run with javac/java; no Android SDK or device needed. */
public final class BundledSkillsTest {
    private static void check(boolean value) {
        if (!value) throw new AssertionError();
    }
    private static void refused(Path home) throws Exception {
        try {
            BundledSkills.install(home, name -> new ByteArrayInputStream(name.getBytes(StandardCharsets.UTF_8)));
            throw new AssertionError("Expected installation to refuse unsafe path");
        } catch (IOException expected) { }
    }
    public static void main(String[] args) throws Exception {
        Path temporary = Files.createTempDirectory("bundled-skills-test-");
        try {
            Path home = Files.createDirectory(temporary.resolve("home"));
            Path user = home.resolve(".config/opencode/skills/user/SKILL.md");
            Files.createDirectories(user.getParent());
            Files.writeString(user, "user owned");
            BundledSkills.install(home, name -> new ByteArrayInputStream(name.getBytes(StandardCharsets.UTF_8)));
            Path root = home.resolve(".tinyagent/skills/phone-use");
            check(Files.readString(root.resolve("SKILL.md")).equals("skills/phone-use/SKILL.md"));
            check(Files.readString(root.resolve("scripts/phone.py")).equals("skills/phone-use/scripts/phone.py"));
            BundledSkills.install(home, name -> new ByteArrayInputStream(("updated " + name).getBytes(StandardCharsets.UTF_8)));
            check(Files.readString(root.resolve("SKILL.md")).startsWith("updated "));
            check(Files.readString(user).equals("user owned"));
            try {
                BundledSkills.install(home, name -> { throw new IOException("missing asset"); });
                throw new AssertionError("Missing assets must fail preparation");
            } catch (IOException expected) { }
            try (var files = Files.walk(root)) {
                check(files.noneMatch(p -> p.toString().endsWith(".part")));
            }
            check(Files.readString(root.resolve("SKILL.md")).startsWith("updated "));
            Files.delete(root.resolve("SKILL.md"));
            Files.createSymbolicLink(root.resolve("SKILL.md"), user);
            refused(home);
            check(Files.readString(user).equals("user owned"));
            for (String conflict : new String[] {".tinyagent", ".tinyagent/skills", ".tinyagent/skills/phone-use", ".tinyagent/skills/phone-use/scripts"}) {
                Path another = Files.createTempDirectory(temporary, "home-");
                Path path = another.resolve(conflict);
                Files.createDirectories(path.getParent());
                Files.createSymbolicLink(path, home);
                refused(another);
            }
            Path link = temporary.resolve("linked-home");
            Files.createSymbolicLink(link, home);
            refused(link);
            System.out.println("PASS: install, update, user skill preservation, failure cleanup, target and directory symlink refusal");
        } finally {
            try (var paths = Files.walk(temporary)) {
                for (Path path : paths.sorted(Comparator.reverseOrder()).toList()) Files.delete(path);
            }
        }
    }
}
