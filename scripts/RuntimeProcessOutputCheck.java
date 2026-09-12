package io.github.gplaider.tinyagent;

import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.atomic.AtomicBoolean;

public class RuntimeProcessOutputCheck {
    public static void main(String[] args) throws Exception {
        if (args.length > 0) {
            System.out.println("한글 output"); System.out.flush();
            if (args[0].equals("wait")) Thread.sleep(60000);
            System.exit(args[0].equals("failure") ? 7 : 0);
        }
        for (String mode : List.of("success", "failure")) {
            Process child = child(mode);
            var output = new ArrayList<String>();
            int code = RuntimeProcessOutput.read(child, output::add, Process::destroy);
            if (code != (mode.equals("success") ? 0 : 7) || !output.equals(List.of("한글 output")))
                throw new AssertionError("Output or exit code changed");
        }
        Process child = child("wait");
        var stopped = new AtomicBoolean();
        try {
            RuntimeProcessOutput.read(child, line -> {throw new IllegalStateException("storage failed");},
                    process -> {stopped.set(true);process.destroy();});
            throw new AssertionError("Output failure swallowed");
        } catch (IllegalStateException expected) {
            if (!expected.getMessage().equals("storage failed") || !stopped.get() || child.isAlive())
                throw new AssertionError("Output failure left child alive", expected);
        } finally {child.destroyForcibly();}
        System.out.println("PASS: UTF-8, exit 0/7, callback failure terminates actual child before returning");
    }
    private static Process child(String mode) throws Exception {
        return new ProcessBuilder(Path.of(System.getProperty("java.home"), "bin", "java").toString(),
                "-Dfile.encoding=UTF-8", "-cp", System.getProperty("java.class.path"),
                RuntimeProcessOutputCheck.class.getName(), mode).redirectErrorStream(true).start();
    }
}
