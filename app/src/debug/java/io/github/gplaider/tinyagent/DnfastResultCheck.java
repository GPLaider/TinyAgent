package io.github.gplaider.tinyagent;

import java.io.IOException;
import org.json.JSONArray;
import org.json.JSONObject;

final class DnfastResultCheck {
    public static void main(String[] args) {
        try { run(); System.out.println("PASS: dnfast terminal result validation"); }
        catch (Throwable failure) { failure.printStackTrace(); System.exit(1); }
    }
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
        for (String action : new String[]{"check", "recover", "migrate"}) {
            DnfastResult.require(action, 0, value.toString());
            reject(action, 1, value.toString());
            reject(action, 0, new JSONObject(value.toString()).put("errors", new JSONArray().put("pending transaction")).toString());
        }
        value.put("message", "[]");
        DnfastResult.require("verify", 0, value.toString());
        for (String action : new String[]{"verify", "upgrade-check"}) {
            value.put("message", "[[\"old-success\",\"reconciled\",false],[\"old-failure\",\"reconciled\",false]]");
            DnfastResult.require(action, 0, value.toString());
            for (String state : new String[]{"started", "rpm_result", "unknown"}) {
                value.put("message", "[[\"pending\",\"" + state + "\",true]]");
                reject(action, 0, value.toString());
            }
            value.put("message", "[[\"same\",\"reconciled\",false],[\"same\",\"reconciled\",true]]");
            reject(action, 0, value.toString());
        }
        value.put("message", "[[\"prepared\",\"prepared\",false]]");
        DnfastResult.require("upgrade-check", 0, value.toString());
        reject("verify", 0, value.toString());
        for (String malformed : new String[]{"not-json", "{}", "[[\"id\",\"reconciled\",\"false\"]]", "[[\"id\",0,false]]"}) {
            value.put("message", malformed);
            reject("verify", 0, value.toString());
        }
    }
    private static void reject(String action, int exit, String output) throws Exception {
        try { DnfastResult.require(action, exit, output); }
        catch (IOException expected) { return; }
        catch (org.json.JSONException expected) { return; }
        throw new AssertionError("Invalid terminal result accepted");
    }
}
