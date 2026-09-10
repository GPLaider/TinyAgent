package io.github.gplaider.tinyagent;

import java.io.IOException;
import org.json.JSONObject;

/** Validate the CLI result as well as the owning process exit status. */
final class DnfastResult {
    static JSONObject require(String action, int processExit, String output) throws Exception {
        JSONObject terminal = null;
        for (String line : output.split("\\n")) {
            if (!line.startsWith("{")) continue;
            JSONObject value;
            try { value = new JSONObject(line); }
            catch (org.json.JSONException error) {
                if (line.contains("dnfast.cli.v1")) throw new IOException("Truncated dnfast terminal result", error);
                continue;
            }
            if ("dnfast.cli.v1".equals(value.optString("schema"))) terminal = value;
        }
        if (processExit != 0 || terminal == null || !(terminal.opt("exit_code") instanceof Number)
                || ((Number) terminal.opt("exit_code")).doubleValue() != 0 || terminal.optJSONArray("errors") == null
                || terminal.getJSONArray("errors").length() != 0)
            throw new IOException("Missing or unsuccessful dnfast terminal result");
        String command = terminal.optString("command"), status = terminal.optString("status");
        boolean unchanged = command.equals("install") && status.equals("planned")
                && terminal.optString("message").equals("no changes; requested state is already satisfied")
                && terminal.optJSONArray("actions") != null && terminal.getJSONArray("actions").length() == 0;
        boolean valid = switch (action) {
            case "install" -> unchanged || command.equals("apply") && status.equals("applied");
            case "plan" -> unchanged || command.equals("install") && status.equals("aborted");
            case "refresh" -> command.equals("repo") && status.equals("planned");
            case "check", "verify", "recover" -> command.equals("app-runtime") && status.equals("planned");
            default -> false;
        };
        if (!valid) throw new IOException("Unexpected dnfast result for " + action);
        return terminal;
    }
}
