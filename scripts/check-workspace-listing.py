"""Run the production directory listing on a real temporary filesystem with JDK 17."""
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/workspace-files"
sources = list((FIXTURE / "android/system").glob("*.java"))
sources += [FIXTURE / "android/os/ParcelFileDescriptor.java", FIXTURE / "WorkspaceListingCheck.java",
            ROOT / "app/src/main/java/io/github/gplaider/tinyagent/WorkspaceFiles.java"]
with tempfile.TemporaryDirectory(prefix="tinyagent-listing-") as directory:
    subprocess.run([shutil.which("javac"), "-encoding", "UTF-8", "-d", directory, *map(str, sources)],
                   check=True, timeout=30)
    subprocess.run([shutil.which("java"), "-cp", directory,
                    "io.github.gplaider.tinyagent.WorkspaceListingCheck", directory], check=True, timeout=30)
