package io.github.gplaider.tinyagent;

public final class RuntimeProcessIdentityCheck {
    static String stat(String pid, String ticks) {
        return pid + " (name with ) spaces) S " + "0 ".repeat(18) + ticks + " 0\n";
    }
    public static void main(String[] args) {
        String current = stat("1234", "98765");
        String record = "1234\nboot-one\n" + current;
        if (!RuntimeProcessIdentity.matches(record, "boot-one\n", current)) throw new AssertionError("Same execution rejected");
        if (RuntimeProcessIdentity.matches(record, "boot-two", current)) throw new AssertionError("Reboot accepted");
        if (RuntimeProcessIdentity.matches(record, "boot-one", stat("1234", "98766"))) throw new AssertionError("Reused PID accepted");
        if (RuntimeProcessIdentity.matches(record, "boot-one", stat("1235", "98765"))) throw new AssertionError("Different PID accepted");
        if (RuntimeProcessIdentity.matches("1234", "boot-one", current)) throw new AssertionError("Legacy PID trusted");
        try { RuntimeProcessIdentity.startTicks("malformed"); throw new AssertionError("Malformed stat accepted"); }
        catch (IllegalArgumentException expected) { }
        System.out.println("PASS: execution identity, reboot, PID reuse, different PID, legacy and malformed records");
    }
}
