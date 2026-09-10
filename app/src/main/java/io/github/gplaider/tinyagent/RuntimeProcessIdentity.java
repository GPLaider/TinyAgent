package io.github.gplaider.tinyagent;

/** PID reuse must never turn recovery into a signal to another process. */
final class RuntimeProcessIdentity {
    static String startTicks(String stat) {
        int end = stat.lastIndexOf(") ");
        if (end < 0) throw new IllegalArgumentException("Invalid process stat");
        String[] fields = stat.substring(end + 2).trim().split("\\s+");
        if (fields.length < 20 || !fields[19].matches("[0-9]+"))
            throw new IllegalArgumentException("Missing process start time");
        return fields[19];
    }
    static boolean matches(String record, String boot, String stat) {
        String[] lines = record.split("\\R", 3);
        return lines.length == 3 && lines[0].matches("[0-9]+")
                && lines[1].equals(boot.trim()) && stat.startsWith(lines[0] + " (")
                && lines[2].startsWith(lines[0] + " (")
                && startTicks(lines[2]).equals(startTicks(stat));
    }
}
