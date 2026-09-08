"""Offline synthetic regression checks. No real downloads or GPG verification.

Only tests unsigned metadata cache trust and stale success Markdown.
Run: python scripts/test-collector.py --log evidence/collector-before.log
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
from pathlib import Path
import runpy
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

MODULE = runpy.run_path(str(Path(__file__).with_name("collect_upstream.py")), run_name="collector_test")
GLOBALS = MODULE["main"].__globals__
NOTICE = "OFFLINE SYNTHETIC FIXTURES ONLY: no network, no external GPG, no upstream verification claim."


class CollectorRegression(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix="tinyagent-collector-test-")
        self.addCleanup(directory.cleanup)
        self.out = Path(directory.name)
        fedora = b"synthetic Fedora prerequisite, not a real rootfs"
        opencode = b"synthetic arbitrary bytes, not downloaded from GitHub"
        fedora_hash = hashlib.sha256(fedora).hexdigest()
        (self.out / MODULE["FEDORA_NAME"]).write_bytes(fedora)
        (self.out / MODULE["CHECKSUM_NAME"]).write_text(
            "SHA256 (" + MODULE["FEDORA_NAME"] + ") = " + fedora_hash,
            encoding="utf-8",
        )
        for name in ("fedora.gpg", "fedora.pgp"):
            (self.out / name).write_bytes(b"synthetic public key fixture")
        (self.out / MODULE["OPENCODE_NAME"]).write_bytes(opencode)
        self.metadata = json.dumps({
            "tag_name": "v1.18.29", "draft": False, "prerelease": False,
            "id": 1, "published_at": "2026-09-04T23:47:00Z",
            "assets": [{
                "id": 1, "name": MODULE["OPENCODE_NAME"], "size": len(opencode),
                "digest": "sha256:" + hashlib.sha256(opencode).hexdigest(),
                "browser_download_url": "https://github.com/anomalyco/opencode/releases/download/v1.18.29/" + MODULE["OPENCODE_NAME"],
            }],
        }).encode()
        (self.out / "opencode-v1.18.29-release-api.json").write_bytes(self.metadata)
        # Fedora signature verification is a prerequisite fixture, not under test.
        status = "[GNUPG:] VALIDSIG " + MODULE["FEDORA_FINGERPRINT"] + " 2026-04-24 0 0 4 0 1 10 01 " + MODULE["FEDORA_FINGERPRINT"]
        self.enterContext(patch.dict(GLOBALS, {
            "OUT": self.out, "FEDORA_SHA256": fedora_hash,
            "gpg_command": lambda: ["synthetic-gpgv-never-executed"],
        }))
        self.enterContext(patch.object(MODULE["subprocess"], "run", return_value=SimpleNamespace(returncode=0, stdout=status, stderr="")))
        self.enterContext(contextlib.redirect_stdout(io.StringIO()))

    def fake_metadata_response(self, request, **kwargs):
        self.assertEqual(request.full_url, MODULE["GITHUB_API"])
        response = io.BytesIO(self.metadata)
        response.url = MODULE["GITHUB_API"]
        response.headers = {"Content-Length": str(len(self.metadata))}
        return response

    def test_unsigned_cached_metadata_cannot_pass_offline(self):
        with patch.object(MODULE["urllib"].request, "urlopen", side_effect=RuntimeError("offline fixture: HTTPS metadata unavailable")) as request:
            with self.assertRaisesRegex(RuntimeError, "HTTPS metadata unavailable"):
                MODULE["main"]()
        self.assertEqual(request.call_count, 1)
        self.assertEqual(json.loads((self.out / "upstream-manifest.json").read_text())["status"], "failed")

    def test_failed_recheck_replaces_success_markdown(self):
        with patch.object(MODULE["urllib"].request, "urlopen", side_effect=self.fake_metadata_response):
            MODULE["main"]()
            report = self.out / "upstream-verification.md"
            self.assertIn("Status: verified", report.read_text())
            (self.out / MODULE["OPENCODE_NAME"]).write_bytes(b"modified synthetic archive")
            with self.assertRaisesRegex(RuntimeError, "checksum mismatch"):
                MODULE["main"]()
        self.assertEqual(json.loads((self.out / "upstream-manifest.json").read_text())["status"], "failed")
        self.assertNotIn("Status: verified", report.read_text())
        self.assertIn("Status: failed", report.read_text())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", type=Path)
    options = parser.parse_args()
    output = io.StringIO()
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(CollectorRegression)
    result = unittest.TextTestRunner(stream=output, verbosity=2).run(suite)
    transcript = NOTICE + "\n" + output.getvalue()
    print(transcript, end="")
    if options.log:
        options.log.parent.mkdir(parents=True, exist_ok=True)
        options.log.write_text(transcript, encoding="utf-8")
    raise SystemExit(0 if result.wasSuccessful() else 1)
