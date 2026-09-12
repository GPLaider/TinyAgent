"""Build/run/remove a separate Android lifecycle test app; never replace TinyAgent.

Requires JAVA_HOME, ANDROID_HOME and --build-tools for host-native aapt2/zipalign.
The test compiles the actual service and uses real Android framework services,
but replaces Fedora/ADB with a test runtime that only owns sleep children.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "io.github.gplaider.tinyagent.runtimeaudit"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--serial", required=True)
    parser.add_argument("--build-tools", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--output-only", action="store_true", help="Check production output reader with live Android shell children")
    args = parser.parse_args()
    jdk, sdk = Path(os.environ["JAVA_HOME"]), Path(os.environ["ANDROID_HOME"])
    android = sdk / "platforms/android-36/android.jar"
    logs = []
    def run(*command, timeout=60):
        result = subprocess.run(list(map(str, command)), capture_output=True, text=True, timeout=timeout)
        logs.append(result.stdout + result.stderr)
        if result.returncode:
            raise RuntimeError(logs[-1])
        return result.stdout
    def adb(*command, **options):
        return run("adb", "-s", args.serial, *command, **options)
    if "package:" + PACKAGE in adb("shell", "pm", "list", "packages", PACKAGE).splitlines():
        raise SystemExit("Audit package already exists; refusing to replace or remove it")
    installed = False
    scope = "production output reader with real Android shell; no service/PRoot/model" if args.output_only else "real Android service, sleep-backed runtime; no PRoot/agent test"
    check = "RuntimeOutputDeviceCheck" if args.output_only else "RuntimeServiceDeviceCheck"
    success = "PASS: Android runtime output" if args.output_only else "PASS: Android runtime-service lifecycle"
    evidence = {"device": args.serial, "package": PACKAGE, "scope": scope, "passed": False}
    try:
        evidence["android_release"] = adb("shell", "getprop", "ro.build.version.release").strip()
        evidence["sdk"] = adb("shell", "getprop", "ro.build.version.sdk").strip()
        evidence["existing_debug_pid_before"] = adb("shell", "pidof", "io.github.gplaider.tinyagent.debug").strip()
        with tempfile.TemporaryDirectory(prefix="tinyagent-service-device-") as directory:
            build = Path(directory)
            classes = build / "classes"; classes.mkdir()
            fixture = ROOT / "tests/runtime-service" / ("output" if args.output_only else "device")
            production = ROOT / "app/src/main/java/io/github/gplaider/tinyagent"
            names = ["RuntimeProcessOutput"] if args.output_only else ["RuntimeSetupService", "LocalPolicy"]
            evidence["source_sha256"] = {name: hashlib.sha256((production / (name + ".java")).read_bytes()).hexdigest() for name in names}
            if not args.output_only:
                evidence["service_sha256"] = evidence["source_sha256"]["RuntimeSetupService"]
            evidence["fixture_sha256"] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in fixture.glob("*") if p.is_file()}
            run(jdk / "bin/javac", "-source", "17", "-target", "17", "-encoding", "UTF-8", "-classpath", android, "-d", classes,
                *[production / (name + ".java") for name in names], *fixture.glob("*.java"))
            run(jdk / "bin/java", "-cp", args.build_tools / "lib/d8.jar", "com.android.tools.r8.D8", "--lib", android,
                "--min-api", "30", "--output", build, *classes.rglob("*.class"))
            run(args.build_tools / "aapt2", "link", "--manifest", fixture / "AndroidManifest.xml", "-I", android, "-o", build / "unsigned.apk")
            with zipfile.ZipFile(build / "unsigned.apk", "a", compression=zipfile.ZIP_DEFLATED) as apk:
                apk.write(build / "classes.dex", "classes.dex")
            run(args.build_tools / "zipalign", "-f", "4", build / "unsigned.apk", build / "aligned.apk")
            run(jdk / "bin/keytool", "-genkeypair", "-keystore", build / "test.jks", "-storepass", "android", "-keypass", "android",
                "-alias", "test", "-keyalg", "RSA", "-validity", "1", "-dname", "CN=Temporary runtime audit", "-noprompt")
            run(jdk / "bin/java", "-jar", args.build_tools / "lib/apksigner.jar", "sign", "--ks", build / "test.jks",
                "--ks-pass", "pass:android", "--out", build / "audit.apk", build / "aligned.apk")
            evidence["apk_sha256"] = hashlib.sha256((build / "audit.apk").read_bytes()).hexdigest()
            adb("install", "--no-streaming", build / "audit.apk")
            installed = True
            report = adb("shell", "am", "instrument", "-w", PACKAGE + "/io.github.gplaider.tinyagent." + check, timeout=90)
            evidence["instrumentation"] = report
            if success not in report or "FAIL" in report:
                raise RuntimeError(report)
            evidence["passed"] = True
    finally:
        if installed:
            evidence["uninstall"] = adb("uninstall", PACKAGE).strip()
        evidence["existing_debug_pid_after"] = adb("shell", "pidof", "io.github.gplaider.tinyagent.debug").strip()
        evidence["build_and_test_log"] = "\n".join(logs)
        args.result.parent.mkdir(parents=True, exist_ok=True)
        args.result.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: v for k, v in evidence.items() if k != "build_and_test_log"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
