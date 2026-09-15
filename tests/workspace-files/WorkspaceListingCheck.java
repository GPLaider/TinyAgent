package io.github.gplaider.tinyagent;

import java.io.IOException;
import java.nio.file.*;
import java.util.Arrays;
import java.util.Set;
import java.util.stream.Collectors;

/** Real filesystem checks; listing does not invoke the Linux-only FD API doubles. */
public final class WorkspaceListingCheck {
    private static int checks;
    interface Action { void run() throws Exception; }
    private static void require(boolean value) {
        if (!value) throw new AssertionError("listing mismatch");
        checks++;
    }
    private static void rejects(Action action) throws Exception {
        try { action.run(); throw new AssertionError("unsafe listing accepted"); }
        catch (IOException expected) { checks++; }
    }
    public static void main(String[] args) throws Exception {
        Path files = Path.of(args[0]).toRealPath();
        WorkspaceFiles workspace = new WorkspaceFiles(files.toFile());
        rejects(() -> workspace.list(""));
        Path root = Files.createDirectories(files.resolve("linux/workspace"));
        Files.createDirectory(root.resolve("empty"));
        Files.writeString(root.resolve("한글 #%.txt"), "hello");
        Files.writeString(root.resolve(".hidden"), "visible");
        Set<String> names = Arrays.stream(workspace.list("")).map(java.io.File::getName).collect(Collectors.toSet());
        require(names.equals(Set.of("empty", "한글 #%.txt", ".hidden")));
        require(workspace.list("empty").length == 0);
        for (String invalid : new String[]{null, "..", "../workspace-other", "missing", "한글 #%.txt", "bad\0path", root.toString()})
            rejects(() -> workspace.list(invalid));
        Path outside = Files.createDirectory(files.resolve("private"));
        Files.writeString(outside.resolve("secret"), "must not list");
        Files.createSymbolicLink(root.resolve("outside"), outside);
        require(Arrays.stream(workspace.list("")).noneMatch(file -> file.getName().equals("outside")));
        rejects(() -> workspace.list("outside"));
        Files.move(root, root.resolveSibling("old-workspace"));
        Files.createSymbolicLink(root, outside);
        rejects(() -> workspace.list(""));
        System.out.println("Workspace listing: " + checks + " checks passed (real files and symlinks)");
    }
}
