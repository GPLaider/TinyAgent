"""Exercise production attachment result handling without an Android device."""
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
JAVA = ROOT / "app/src/main/java/io/github/gplaider/tinyagent"
source = (JAVA / "AppActivity.java").read_text(encoding="utf-8")
start = source.index("    @Override protected void onActivityResult(")
end = source.index("    private void showSettings()", start)
template = (ROOT / "tests/workspace-files/AttachmentResultCheck.template").read_text(encoding="utf-8")
with tempfile.TemporaryDirectory(prefix="tinyagent-attachment-") as directory:
    target = Path(directory) / "AttachmentResultCheck.java"
    target.write_text(template.replace("/* PRODUCTION_METHODS */", source[start:end]), encoding="utf-8")
    subprocess.run([shutil.which("javac"), "-encoding", "UTF-8", "-d", directory,
                    str(target), str(JAVA / "LocalPolicy.java")], check=True, timeout=30)
    subprocess.run([shutil.which("java"), "-cp", directory,
                    "io.github.gplaider.tinyagent.AttachmentResultCheck"], check=True, timeout=30)
