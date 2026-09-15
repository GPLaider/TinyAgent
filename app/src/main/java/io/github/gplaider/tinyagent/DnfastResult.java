package io.github.gplaider.tinyagent;

import java.io.IOException;
import java.util.HashSet;
import org.json.JSONArray;
import org.json.JSONObject;

/** Validate the CLI result as well as the owning process exit status. */
final class DnfastResult {
    private static final String PLAN_EXPIRED = "proposal is not a current canonical solver plan: canonical document failed: invalid plan: plan expired";

    static JSONObject require(String action, int processExit, String output) throws Exception {
        JSONObject terminal = terminal(output);
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
            case "check", "verify", "upgrade-check", "recover", "migrate" -> command.equals("app-runtime") && status.equals("planned");
            default -> false;
        };
        if (!valid) throw new IOException("Unexpected dnfast result for " + action);
        if (action.equals("verify") || action.equals("upgrade-check")) {
            if (!(terminal.opt("message") instanceof String)) throw new IOException("Missing package journal states");
            JSONArray states = new JSONArray(terminal.getString("message"));
            HashSet<String> ids = new HashSet<>();
            for (int i = 0; i < states.length(); i++) {
                JSONArray row = states.getJSONArray(i);
                if (row.length() != 3 || !(row.opt(0) instanceof String)
                        || row.getString(0).isBlank() || !ids.add(row.getString(0))
                        || !(row.opt(1) instanceof String)
                        || !(row.opt(2) instanceof Boolean)) throw new IOException("Invalid package journal state");
                String state = row.getString(1);
                if (!state.equals("reconciled") && !(action.equals("upgrade-check") && state.equals("prepared")))
                    throw new IOException("패키지 작업 복구가 필요합니다. 기존 실행환경과 기록을 보존했습니다: " + state);
            }
        }
        return terminal;
    }

    static boolean planExpired(String output) {
        try {
            JSONObject terminal = terminal(output);
            JSONArray errors = terminal == null ? null : terminal.optJSONArray("errors");
            if (terminal == null || !"apply".equals(terminal.optString("command"))
                    || !"failed".equals(terminal.optString("status"))
                    || !(terminal.opt("exit_code") instanceof Number)
                    || ((Number) terminal.opt("exit_code")).doubleValue() != 1
                    || !PLAN_EXPIRED.equals(terminal.optString("message"))
                    || errors == null || errors.length() != 1 || !(errors.opt(0) instanceof JSONObject)) return false;
            JSONObject error = errors.getJSONObject(0);
            return "runtime_failure".equals(error.optString("code"))
                    && PLAN_EXPIRED.equals(error.optString("message"));
        } catch (Exception invalid) { return false; }
    }

    private static JSONObject terminal(String output) throws IOException {
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
        return terminal;
    }
}
