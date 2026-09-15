"""Execute the production Java package lifecycle with a deterministic CLI double."""
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
source = (root / 'app/src/main/java/io/github/gplaider/tinyagent/LocalLinuxRuntime.java').read_text(encoding='utf-8')
methods = source[source.index('    void runPackages('):source.index('    void run(ProcessBuilder builder)')]
harness = r'''
import java.util.*;
import java.io.IOException;
import java.util.function.Consumer;
class LocalLinuxRuntime {
    static List<String> calls = new ArrayList<>();
    static String fail = "";
    Object context;
    ProcessBuilder guest(String cwd, String... command) { return new ProcessBuilder(command); }
    void run(ProcessBuilder command, Consumer<String> lines) throws Exception {
        String action = command.command().get(0);
        calls.add(action);
        if ((fail.equals("expired") || fail.equals("expired-once")) && action.equals("install")) {
            lines.accept("{\"schema\":\"dnfast.cli.v1\",\"expired\":true}");
            if (fail.equals("expired") || Collections.frequency(calls, "install") == 1) throw new IOException("plan expired");
        }
        if (fail.equals(action)) throw new Exception("native refusal");
        lines.accept("{dnfast.cli.v1}");
    }
METHODS
    static void check(boolean current, String failure, List<String> expected) throws Exception {
        calls.clear(); fail = failure; DnfastRuntime.current = current;
        boolean shouldFail = !failure.isEmpty() && !failure.equals("expired-once");
        try {
            new LocalLinuxRuntime().runPackages("install", line -> {}, "install", "git");
            if (shouldFail) throw new AssertionError("Failure hidden");
        } catch (Exception e) {
            if (!shouldFail) throw e;
        }
        if (!calls.equals(expected)) throw new AssertionError(calls.toString());
        if (!current && !failure.isEmpty() && DnfastRuntime.current) throw new AssertionError("Failed refresh cached");
    }
    public static void main(String[] args) throws Exception {
        check(true, "", List.of("install"));
        check(false, "", List.of("check", "migrate", "check", "refresh", "install"));
        check(false, "check", List.of("check"));
        check(false, "migrate", List.of("check", "migrate"));
        check(false, "refresh", List.of("check", "migrate", "check", "refresh"));
        check(false, "terminal", List.of("check"));
        check(false, "terminal:refresh", List.of("check", "migrate", "check", "refresh"));
        check(true, "install", List.of("install"));
        check(true, "expired-once", List.of("install", "refresh", "install"));
        check(true, "expired", List.of("install", "refresh", "install"));
        System.out.println("PASS: binding changes replan; only expired plans retry once; other failures stop");
    }
}
class PackageManagerChoice {
    static String read(Object context) { return "dnfast"; }
    static List<String> dnf5Command(String action, String... operation) { return List.of(operation); }
}
class DnfastRuntime {
    static boolean current;
    static boolean planningCurrent(LocalLinuxRuntime r) { return current; }
    static String planningIdentity(LocalLinuxRuntime r) { return "binding"; }
    static void rememberPlanning(LocalLinuxRuntime r, String before) { current = true; }
    static ProcessBuilder command(LocalLinuxRuntime r, String... op) {
        return new ProcessBuilder(op[0].equals("app-runtime") ? op[1] : op[0].equals("repo") ? "refresh" : op[0]);
    }
}
class DnfastResult {
    static boolean planExpired(String output) { return output.contains("\"expired\":true"); }
    static void require(String action, int exit, String output) throws Exception {
        if (LocalLinuxRuntime.fail.equals("terminal") || LocalLinuxRuntime.fail.equals("terminal:" + action))
            throw new Exception("invalid terminal");
    }
}
'''.replace('METHODS', methods)
with tempfile.TemporaryDirectory(prefix='tinyagent-package-planning-') as directory:
    file = Path(directory) / 'LocalLinuxRuntime.java'
    file.write_text(harness, encoding='utf-8')
    subprocess.run(['javac', '-encoding', 'UTF-8', '-d', directory, str(file)], check=True)
    subprocess.run(['java', '-cp', directory, 'LocalLinuxRuntime'], check=True)
