package io.github.gplaider.tinyagent;

import android.os.ParcelFileDescriptor;
import android.system.Os;
import android.system.OsConstants;
import java.io.*;
import java.nio.file.*;
import java.nio.file.attribute.PosixFilePermissions;

public class WorkspaceFilesCheck {
    interface Checked { void run() throws Exception; }
    static int cases;
    static void require(boolean ok, String message) { if (!ok) throw new AssertionError(message); }
    static void rejected(String name, Checked action) throws Exception {
        try { action.run(); throw new AssertionError(name + " accepted"); }
        catch (IOException expected) { cases++; }
    }
    static long descriptors() throws IOException {
        try (var list = Files.list(Path.of("/proc/self/fd"))) { return list.count(); }
    }
    static void replace(Path file, Path target) {
        try { Files.delete(file); Files.createSymbolicLink(file, target); }
        catch (IOException e) { throw new UncheckedIOException(e); }
    }
    public static void main(String[] args) throws Exception {
        Path fixture = Path.of(args[0]);
        Path files = Files.createDirectory(fixture.resolve("files"));
        Path root = Files.createDirectories(files.resolve("linux/workspace"));
        Path outside = Files.createDirectory(files.resolve("private"));
        Path secret = Files.writeString(outside.resolve("secret.txt"), "PRIVATE");
        Path good = Files.writeString(root.resolve("good.txt"), "PUBLIC");
        WorkspaceFiles workspace = new WorkspaceFiles(files.toFile());
        for (String path : new String[]{null,"","/good.txt","../private/secret.txt","../../private/secret.txt","good.txt\0tail",".","missing"})
            rejected("malformed " + path, () -> { try (var fd = workspace.open(path)) {} });
        Files.createSymbolicLink(root.resolve("outside"), secret);
        rejected("outside symlink", () -> workspace.open("outside"));
        Files.createSymbolicLink(root.resolve("inside"), good);
        try (var input = workspace.input("inside")) { require(new String(input.readAllBytes()).equals("PUBLIC"), "inside symlink"); }
        cases++;
        Path sibling = Files.createDirectory(files.resolve("linux/workspace-other"));
        Files.writeString(sibling.resolve("secret.txt"), "SIBLING");
        rejected("prefix sibling", () -> workspace.open("../workspace-other/secret.txt"));

        // Demonstrate the old canonical-check-then-open actually discloses the replacement.
        Path race = Files.writeString(root.resolve("race.txt"), "PUBLIC");
        File oldChecked = race.toFile().getCanonicalFile();
        require(oldChecked.isFile() && oldChecked.toPath().startsWith(root), "old validation");
        replace(race, secret);
        try (var input = new FileInputStream(oldChecked)) {
            require(new String(input.readAllBytes()).equals("PRIVATE"), "baseline race not reproduced");
        }
        Files.delete(race); Files.writeString(race, "PUBLIC");
        Os.beforeOpen = () -> replace(race, secret);
        rejected("leaf swapped after validation", () -> workspace.open("race.txt"));
        Files.delete(race);
        Path folder = Files.createDirectory(root.resolve("folder"));
        Files.writeString(folder.resolve("secret.txt"), "PUBLIC");
        Os.beforeOpen = () -> {
            try { Files.move(folder, root.resolve("old-folder")); Files.createSymbolicLink(folder, outside); }
            catch (IOException e) { throw new UncheckedIOException(e); }
        };
        rejected("parent swapped after validation", () -> workspace.open("folder/secret.txt"));
        Files.delete(folder);

        Path fifo = Files.writeString(root.resolve("fifo"), "PUBLIC");
        Os.beforeOpen = () -> {
            try {
                Files.delete(fifo);
                require(new ProcessBuilder("mkfifo", fifo.toString()).start().waitFor() == 0, "mkfifo");
            } catch (Exception e) { throw new RuntimeException(e); }
        };
        long start = System.nanoTime();
        rejected("FIFO swap", () -> workspace.open("fifo"));
        require(System.nanoTime() - start < 2_000_000_000L, "FIFO open blocked");
        rejected("existing FIFO", () -> workspace.open("fifo"));
        Files.delete(fifo);

        Path denied = Files.writeString(root.resolve("denied"), "PRIVATE");
        Files.setPosixFilePermissions(denied, PosixFilePermissions.fromString("---------"));
        try { rejected("permission denial", () -> workspace.open("denied")); }
        finally { Files.setPosixFilePermissions(denied, PosixFilePermissions.fromString("rw-------")); }
        try (var held = workspace.input("good.txt")) {
            Files.delete(good); Files.writeString(good, "REPLACED");
            require(new String(held.readAllBytes()).equals("PUBLIC"), "FD closed early or reopened by path");
        }
        cases++;
        Os.beforeOpen = () -> { try { Files.delete(good); } catch (IOException e) { throw new UncheckedIOException(e); } };
        rejected("disappearing file", () -> workspace.open("good.txt"));
        Files.writeString(good, "PUBLIC");

        // Warm up lazy JDK initialization before asserting stable native descriptor counts.
        try (var fd = workspace.open("good.txt")) {
            require((Os.fcntlInt(fd.getFileDescriptor(), OsConstants.F_GETFD, 0) & OsConstants.FD_CLOEXEC) != 0,
                    "returned descriptor inherited across exec");
        }
        cases++;
        try (var input = workspace.input("good.txt")) { input.readAllBytes(); }
        long before = descriptors();
        for (int i=0; i<500; i++) {
            try (var input = workspace.input("good.txt")) { require(input.read() == 'P', "read after original FD closed"); }
            Os.failReadlink = true;
            try { rejected("proc permission failure", () -> workspace.open("good.txt")); }
            finally { Os.failReadlink = false; }
            Os.failStat = true;
            try { rejected("fstat failure", () -> workspace.open("good.txt")); }
            finally { Os.failStat = false; }
            ParcelFileDescriptor.failDup = true;
            try { rejected("dup failure", () -> workspace.open("good.txt")); }
            finally { ParcelFileDescriptor.failDup = false; }
            Os.failFcntl = true;
            try { rejected("fcntl failure", () -> workspace.open("good.txt")); }
            finally { Os.failFcntl = false; }
        }
        require(descriptors() == before, "native FD leak: " + before + " -> " + descriptors());
        cases++;
        WorkspaceFileProvider provider = new WorkspaceFileProvider();
        provider.context = new android.content.Context(files.toFile());
        for (String mode : new String[]{"w","rw","rwt","wa",null})
            rejected("provider write " + mode, () -> provider.openFile(android.net.Uri.parse("content://app.artifacts/workspace/good.txt"), mode));
        for (String path : new String[]{"/other/good.txt","/workspace/../private/secret.txt","/workspace/%2Fgood.txt","/workspace/good.txt%00tail"})
            rejected("provider malformed path", () -> provider.openFile(android.net.Uri.parse("content://app.artifacts" + path), "r"));
        Path encoded = Files.writeString(root.resolve("space + # %.txt"), "ENCODED");
        try (var fd = provider.openFile(android.net.Uri.parse("content://app.artifacts/workspace/space%20%2B%20%23%20%25.txt"), "r");
             var input = new ParcelFileDescriptor.AutoCloseInputStream(fd)) {
            require(new String(input.readAllBytes()).equals("ENCODED"), "URI decode");
        }
        cases++;
        try { provider.delete(android.net.Uri.parse("content://app.artifacts/workspace/good.txt"), null, null); throw new AssertionError("provider delete"); }
        catch (SecurityException expected) { cases++; }
        Os.beforeOpen = () -> replace(encoded, secret);
        rejected("provider race", () -> provider.openFile(android.net.Uri.parse("content://app.artifacts/workspace/space%20%2B%20%23%20%25.txt"), "r"));
        Path originalRoot = root.resolveSibling("workspace-saved");
        Files.move(root, originalRoot); Files.createSymbolicLink(root, outside);
        rejected("workspace root replaced", () -> workspace.open("secret.txt"));
        Files.delete(root); Files.move(originalRoot, root);
        Path linux = files.resolve("linux");
        Files.move(linux, files.resolve("linux-saved")); Files.createSymbolicLink(linux, files.resolve("linux-saved"));
        rejected("workspace ancestor symlink", () -> workspace.open("good.txt"));
        System.out.println("PASS: " + cases + " assertions; baseline disclosure reproduced; leaf/parent/FIFO races, malformed paths, permission failures, FD ownership and 500 leak cycles");
    }
}
