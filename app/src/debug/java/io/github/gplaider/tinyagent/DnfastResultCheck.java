package io.github.gplaider.tinyagent;

import java.io.IOException;
import org.json.JSONArray;
import org.json.JSONObject;

final class DnfastResultCheck {
    static void run() throws Exception {
        JSONObject value = new JSONObject().put("schema", "dnfast.cli.v1").put("exit_code", 0)
                .put("command", "install").put("status", "planned")
                .put("message", "no changes; requested state is already satisfied")
                .put("actions", new JSONArray()).put("errors", new JSONArray());
        DnfastResult.require("install", 0, value.toString());
        DnfastResult.require("plan", 0, value.toString());
        reject("install", 1, value.toString());
        reject("refresh", 0, value.toString());
        reject("install", 0, value.toString() + "\n{\"schema\":\"dnfast.cli.v1\"");
        reject("install", 0, "trace only");
        reject("install", 0, new JSONObject(value.toString()).put("exit_code", "0").toString());
        reject("install", 0, new JSONObject(value.toString()).put("exit_code", 0.1).toString());
        reject("install", 0, new JSONObject(value.toString()).put("message", "not installed").toString());
        reject("install", 0, new JSONObject(value.toString()).put("errors", new JSONArray().put("failure")).toString());
        reject("install", 0, new JSONObject(value.toString()).put("actions", new JSONArray().put("pending")).toString());
        value.put("command", "apply").put("status", "applied");
        DnfastResult.require("install", 0, value.toString());
        value.put("command", "install").put("status", "aborted");
        DnfastResult.require("plan", 0, value.toString());
        value.put("command", "repo").put("status", "planned");
        DnfastResult.require("refresh", 0, value.toString());
        value.put("command", "app-runtime");
        for (String action : new String[]{"check", "recover", "verify"}) DnfastResult.require(action, 0, value.toString());
    }
    private static void reject(String action, int exit, String output) throws Exception {
        try { DnfastResult.require(action, exit, output); }
        catch (IOException expected) { return; }
        throw new AssertionError("Invalid terminal result accepted");
    }
}
