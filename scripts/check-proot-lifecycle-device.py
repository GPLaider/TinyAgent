"""Run the production runtime/PRoot/Fedora in an isolated, disposable Android app.

Requires JAVA_HOME, ANDROID_HOME, adb and host-native Android build tools.
Never replaces an installed package or reads another app's workspace/credentials.
"""
import argparse
import hashlib
import json
import os
import re
from pathlib import Path
import subprocess
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "io.github.gplaider.tinyagent.prootaudit"


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--serial", required=True)
    parser.add_argument("--build-tools", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--backend", action="store_true", help="Run isolated shipped OpenCode shell/restart checks instead of the PRoot-only suite")
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
    scope = "production guest/start/stop/recover with shipped OpenCode on a separate port; no model or package transaction" if args.backend else "production Java runtime, packaged PRoot and pinned Fedora; no OpenCode/model or package transaction"
    check = "BackendLifecycleCheck" if args.backend else "PRootLifecycleCheck"
    success = "PASS: isolated OpenCode lifecycle" if args.backend else "PASS: real PRoot/Fedora lifecycle"
    evidence = {"device": args.serial, "package": PACKAGE, "scope": scope, "passed": False}
    try:
        evidence["android_release"] = adb("shell", "getprop", "ro.build.version.release").strip()
        evidence["sdk"] = adb("shell", "getprop", "ro.build.version.sdk").strip()
        evidence["existing_debug_pid_before"] = adb("shell", "pidof", "io.github.gplaider.tinyagent.debug").strip()
        native = ROOT / "app/src/main/jniLibs/arm64-v8a"
        native_names = ["libproot.so", "libproot_loader.so", "libtalloc.so", "libandroid-shmem.so"]
        metadata = json.loads((ROOT / "runtime/proot-fchmodat2-2.json").read_text())
        evidence["native_sha256"] = {name: digest(native / name) for name in native_names}
        assert evidence["native_sha256"] == metadata["outputs"] | metadata["dependencies"], "PRoot native bytes differ from pinned source build"
        assets = ROOT / "app/src/main/assets"
        fedora = assets / "fedora-44-arm64-rootfs.tar.gz.bin"
        evidence["fedora_sha256"] = digest(fedora)
        assert evidence["fedora_sha256"] == "3a3661a77d5fdb1e4bd10be484142683630c1ffb4c371931d46a42459fd4c125"
        with tempfile.TemporaryDirectory(prefix="tinyagent-proot-device-") as directory:
            build = Path(directory)
            classes = build / "classes"; classes.mkdir()
            fixture = ROOT / "tests/proot-lifecycle"
            evidence["fixture_sha256"] = {p.name: digest(p) for p in fixture.glob("*") if p.is_file()}
            production = ROOT / "app/src/main/java/io/github/gplaider/tinyagent"
            names = ["LocalLinuxRuntime", "LocalPolicy", "RuntimeProcessIdentity", "RuntimeProcessOutput", "RuntimeExecutable", "DnfastRuntime", "DnfastResult", "BundledSkills"]
            evidence["source_sha256"] = {name: digest(production / (name + ".java")) for name in names}
            run(jdk / "bin/javac", "-source", "17", "-target", "17", "-encoding", "UTF-8", "-classpath", android, "-d", classes,
                *[production / (name + ".java") for name in names], *fixture.glob("*.java"))
            run(jdk / "bin/java", "-cp", args.build_tools / "lib/d8.jar", "com.android.tools.r8.D8", "--lib", android,
                "--min-api", "30", "--output", build, *classes.rglob("*.class"))
            run(args.build_tools / "aapt2", "link", "--manifest", fixture / "AndroidManifest.xml", "-I", android, "-o", build / "unsigned.apk")
            with zipfile.ZipFile(build / "unsigned.apk", "a") as apk:
                apk.write(build / "classes.dex", "classes.dex", compress_type=zipfile.ZIP_DEFLATED)
                apk.write(assets / "linux-launch.sh", "assets/linux-launch.sh", compress_type=zipfile.ZIP_DEFLATED)
                apk.write(fedora, "assets/" + fedora.name, compress_type=zipfile.ZIP_STORED)
                if args.backend:
                    backend = assets / "opencode-linux-arm64.tar.gz.bin"
                    evidence["backend_archive_sha256"] = digest(backend)
                    assert evidence["backend_archive_sha256"] == json.loads((ROOT / "runtime/opencode-snapshot-12.json").read_text())["archive_sha256"]
                    apk.write(backend, "assets/" + backend.name, compress_type=zipfile.ZIP_STORED)
                for name in native_names:
                    apk.write(native / name, "lib/arm64-v8a/" + name, compress_type=zipfile.ZIP_DEFLATED)
            run(args.build_tools / "zipalign", "-f", "4", build / "unsigned.apk", build / "aligned.apk")
            run(jdk / "bin/keytool", "-genkeypair", "-keystore", build / "test.jks", "-storepass", "android", "-keypass", "android",
                "-alias", "test", "-keyalg", "RSA", "-validity", "1", "-dname", "CN=Temporary PRoot audit", "-noprompt")
            run(jdk / "bin/java", "-jar", args.build_tools / "lib/apksigner.jar", "sign", "--ks", build / "test.jks",
                "--ks-pass", "pass:android", "--out", build / "audit.apk", build / "aligned.apk")
            evidence["apk_sha256"] = digest(build / "audit.apk")
            run(jdk / "bin/keytool", "-exportcert", "-keystore", build / "test.jks",
                "-storepass", "android", "-alias", "test", "-file", build / "test.der")
            evidence["expected_test_signer_sha256"] = digest(build / "test.der")
            evidence["signer_verification"] = run(jdk / "bin/java", "-jar", args.build_tools / "lib/apksigner.jar",
                "verify", "--print-certs", build / "audit.apk")
            assert set(re.findall(r"certificate SHA-256 digest: ([0-9a-f]{64})", evidence["signer_verification"])) == {evidence["expected_test_signer_sha256"]}
            adb("install", "--no-streaming", build / "audit.apk")
            installed = True
            report = adb("shell", "am", "instrument", "-w", PACKAGE + "/io.github.gplaider.tinyagent." + check, timeout=420 if args.backend else 180)
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
