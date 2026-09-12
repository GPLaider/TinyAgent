"""Compile the complete production service with deterministic host Android doubles.

No methods are reimplemented or extracted. Only imports and the enclosing class
declaration are adapted to nest the service beside test doubles. This verifies
service request ordering, not real Binder, Handler, wakelock or PRoot behavior.
"""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    home = os.environ.get("JAVA_HOME")
    javac = Path(home) / "bin/javac" if home else Path(shutil.which("javac") or "/missing-javac")
    if not javac.is_file():
        raise SystemExit("JDK missing: set JAVA_HOME or put javac on PATH")
    source = (ROOT / "app/src/main/java/io/github/gplaider/tinyagent/RuntimeSetupService.java").read_text()
    source = "\n".join(line for line in source.splitlines()
                       if not line.startswith(("package ", "import ")))
    source = source.replace("public final class RuntimeSetupService", "public static final class RuntimeSetupService")
    template = (ROOT / "tests/runtime-service/RuntimeServiceCheck.template").read_text()
    with tempfile.TemporaryDirectory(prefix="tinyagent-service-") as directory:
        target = Path(directory) / "RuntimeServiceCheck.java"
        target.write_text(template.replace("/* PRODUCTION_SERVICE */", source))
        subprocess.run([str(javac), "-encoding", "UTF-8", str(target)], check=True, timeout=30)
        subprocess.run([str(javac.parent / "java"), "-cp", directory, "RuntimeServiceCheck"], check=True, timeout=30)


if __name__ == "__main__":
    main()
