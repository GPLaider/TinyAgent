"""Collect verified public upstream artifacts; never unpack or install them.

Run from the project: python scripts/collect_upstream.py
Check parser/error guards: python scripts/collect_upstream.py --self-check
"""
from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import re
import shutil
import subprocess
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts"
FEDORA_BASE = "https://dl.fedoraproject.org/pub/fedora/linux/releases/44/Container/aarch64/images/"
FEDORA_NAME = "Fedora-Container-Base-Generic-Minimal-44-1.7.aarch64.oci.tar.xz"
CHECKSUM_NAME = "Fedora-Container-44-1.7-aarch64-CHECKSUM"
FEDORA_SHA256 = "2c00fc0e7890a5bfecbd243561e5a2d07d2661667e1b897eab549b83f6b1db9a"
FEDORA_FINGERPRINT = "36F612DCF27F7D1A48A835E4DBFCF71C6D9F90A6"
GITHUB_API = "https://api.github.com/repos/anomalyco/opencode/releases/tags/v1.18.29"
OPENCODE_NAME = "opencode-linux-arm64.tar.gz"
MAX_BYTES = 1024 * 1024 * 1024


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class IncompleteDownload(RuntimeError):
    pass


def download(url: str, name: str, expected: str | None = None, *, refresh: bool = False) -> dict:
    for attempt in range(3):
        try:
            return _download_once(url, name, expected, refresh=refresh)
        except (IncompleteDownload, urllib.error.URLError, http.client.HTTPException, TimeoutError):
            if attempt == 2:
                raise
            print(f'Transfer interrupted; retry {attempt+2}/3: {name}', flush=True)
            time.sleep(attempt+1)
    raise AssertionError('Unreachable')


def _download_once(url: str, name: str, expected: str | None = None, *, refresh: bool = False) -> dict:
    target = OUT / name
    if target.exists() and not refresh:
        actual = sha256(target)
        if expected and actual != expected:
            raise RuntimeError(f"Existing artifact checksum mismatch: {name}")
        print(f"reuse {name}: {target.stat().st_size} bytes", flush=True)
        return {"file": name, "url": url, "sha256": actual, "bytes": target.stat().st_size, "reused": True}
    request = urllib.request.Request(url, headers={"User-Agent": "TinyAgent-upstream-collector/1", "Accept": "application/vnd.github+json" if "api.github.com" in url else "*/*"})
    part = OUT / (name + ".part")
    received = 0
    last_report = time.monotonic()
    with urllib.request.urlopen(request, timeout=60) as response, part.open("wb") as destination:
        if not response.url.startswith("https://"):
            raise RuntimeError("Refusing a non-HTTPS download redirect")
        size = int(response.headers.get("Content-Length", "0"))
        if size > MAX_BYTES:
            raise RuntimeError("Artifact exceeds 1 GiB safety bound")
        final_url = response.url
        while chunk := response.read(1024 * 1024):
            received += len(chunk)
            if received > MAX_BYTES:
                raise RuntimeError("Artifact exceeds 1 GiB safety bound")
            destination.write(chunk)
            if time.monotonic() - last_report > 10:
                percent = f" {received * 100 / size:.0f}%" if size else ""
                print(f"download {name}: {received // 1048576} MiB{percent}", flush=True)
                last_report = time.monotonic()
        if size and received != size:
            raise IncompleteDownload(f"Incomplete download: {name}: {received}/{size}")
    actual = sha256(part)
    if expected and actual != expected:
        raise RuntimeError(f"Downloaded artifact checksum mismatch: {name}")
    part.replace(target)
    print(f"downloaded {name}: {received} bytes", flush=True)
    return {"file": name, "url": url, "final_url": final_url, "sha256": actual, "bytes": received, "reused": False}


def checksum_for(text: str, filename: str) -> str:
    matches = re.findall(r"^SHA256 \(" + re.escape(filename) + r"\) = ([0-9a-f]{64})$", text, flags=re.MULTILINE)
    if len(matches) != 1:
        raise RuntimeError(f"Expected one signed SHA256 entry for {filename}")
    return matches[0]


def validate_signature(status: str) -> None:
    signatures = [line.split()[2:] for line in status.splitlines() if line.startswith("[GNUPG:] VALIDSIG ")]
    if not any(len(fields) >= 9 and (fields[0] == FEDORA_FINGERPRINT or (len(fields) == 10 and fields[9] == FEDORA_FINGERPRINT)) for fields in signatures):
        raise RuntimeError("CHECKSUM has no valid signature from the pinned Fedora 44 key")
    if any(f"[GNUPG:] {failure}" in status for failure in ("BADSIG", "ERRSIG", "REVKEYSIG", "EXPKEYSIG", "EXPSIG")):
        raise RuntimeError("GPG reports an invalid/expired/revoked CHECKSUM signature")


def gpg_command() -> list[str]:
    home = OUT / "public-gpg-home"
    home.mkdir(exist_ok=True)
    candidates = [shutil.which("gpgv"), "C:/Program Files/Git/usr/bin/gpgv.exe", "C:/Program Files (x86)/GnuPG/bin/gpgv.exe"]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return [candidate, "--homedir", "./public-gpg-home", "--keyring", "./fedora.gpg", "--status-fd", "1", CHECKSUM_NAME]
    raise RuntimeError("No native gpgv found. Probe WSL through wsl_safe.py before adding a verified fallback.")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    report = OUT / "upstream-verification.md"
    report.write_text("# TinyAgent upstream artifact verification\n\nStatus: collecting. No current verification result yet.\n", encoding="utf-8")
    manifest = {"purpose": "Verified upstream source artifacts; not a TinyAgent release", "started_utc": datetime.now(timezone.utc).isoformat(), "artifacts": [], "status": "collecting"}
    try:
        for url, name in ((FEDORA_BASE + CHECKSUM_NAME, CHECKSUM_NAME), ("https://fedoraproject.org/fedora.gpg", "fedora.gpg"), ("https://fedoraproject.org/fedora.pgp", "fedora.pgp")):
            manifest["artifacts"].append(download(url, name))
        command = gpg_command()
        result = subprocess.run(command, cwd=OUT, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60, shell=False)
        log = "cwd=" + str(OUT) + "\n$ " + subprocess.list2cmdline(command) + "\nexit=" + str(result.returncode) + "\n" + result.stdout + result.stderr
        (OUT / "fedora-signature-verification.log").write_text(log, encoding="utf-8")
        if result.returncode:
            raise RuntimeError(f"Fedora CHECKSUM signature failed, gpgv exit={result.returncode}; see verification log")
        validate_signature(result.stdout)
        expected = checksum_for((OUT / CHECKSUM_NAME).read_text(encoding="utf-8"), FEDORA_NAME)
        if expected != FEDORA_SHA256:
            raise RuntimeError("Signed CHECKSUM differs from pinned official Fedora website digest")
        print(f"Fedora CHECKSUM signature verified: {FEDORA_FINGERPRINT}", flush=True)
        manifest["fedora_signature"] = {"verified": True, "pinned_primary_fingerprint": FEDORA_FINGERPRINT, "log": "fedora-signature-verification.log", "verifier": command[0], "exit_code": result.returncode}
        manifest["artifacts"].append(download(FEDORA_BASE + FEDORA_NAME, FEDORA_NAME, expected))
        # Local API metadata is not an independent source of artifact provenance.
        metadata = download(GITHUB_API, "opencode-v1.18.29-release-api.json", refresh=True)
        manifest["artifacts"].append(metadata)
        release = json.loads((OUT / metadata["file"]).read_text(encoding="utf-8"))
        if release.get("tag_name") != "v1.18.29" or release.get("draft") or release.get("prerelease"):
            raise RuntimeError("Unexpected OpenCode release identity/status")
        matches = [item for item in release["assets"] if item["name"] == OPENCODE_NAME]
        if len(matches) != 1:
            raise RuntimeError("Expected exactly one OpenCode Linux ARM64 asset")
        asset = matches[0]
        digest = asset.get("digest", "")
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
            raise RuntimeError("GitHub release API does not provide the required SHA256 digest")
        expected_url = "https://github.com/anomalyco/opencode/releases/download/v1.18.29/" + OPENCODE_NAME
        if asset["browser_download_url"] != expected_url:
            raise RuntimeError("Unexpected OpenCode asset URL")
        manifest["opencode_release"] = {"tag": release["tag_name"], "id": release["id"], "published_at": release["published_at"], "asset_id": asset["id"], "api_digest": digest, "verification_scope": "GitHub public release API digest over HTTPS; not a release-signature or attestation verification"}
        artifact = download(expected_url, OPENCODE_NAME, digest.split(":", 1)[1])
        if artifact["bytes"] != asset["size"]:
            raise RuntimeError("OpenCode asset size mismatch")
        manifest["artifacts"].append(artifact)
        manifest["status"] = "verified"
        manifest["completed_utc"] = datetime.now(timezone.utc).isoformat()
    except Exception as error:
        manifest["status"] = "failed"
        manifest["error"] = str(error)
        raise
    finally:
        (OUT / "upstream-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if manifest["status"] != "verified":
            report.write_text("# TinyAgent upstream artifact verification\n\nStatus: failed.\n\n" + manifest.get("error", "Verification incomplete") + "\n", encoding="utf-8")
    lines = ["# TinyAgent upstream artifact verification", "", "Status: verified. Source collection only; no extraction, installation or device changes.", "", f"Fedora 44 CHECKSUM signature: valid, pinned primary key {FEDORA_FINGERPRINT}.", "OpenCode archive: matches public GitHub release API SHA256 and size; attestation/signature not checked.", "", "| File | Bytes | SHA256 |", "|---|---:|---|"]
    lines.extend(f"| {item['file']} | {item['bytes']} | {item['sha256']} |" for item in manifest["artifacts"])
    lines += ["", "Reproduce: `python scripts/collect_upstream.py`", "Parser guard check: `python scripts/collect_upstream.py --self-check`", "Details: `upstream-manifest.json`, `fedora-signature-verification.log`.", ""]
    (OUT / "upstream-verification.md").write_text("\n".join(lines), encoding="utf-8")
    print("Verified both upstream archives; manifest and report written.", flush=True)


def self_check() -> None:
    from unittest.mock import patch
    with patch(__name__+'._download_once', side_effect=[IncompleteDownload('truncated'), {'verified': True}]) as transfer, patch(__name__+'.time.sleep'):
        assert download('https://example.invalid/', 'probe') == {'verified': True}
        assert transfer.call_count == 2
    with patch(__name__+'._download_once', side_effect=RuntimeError('checksum mismatch')) as transfer:
        try:
            download('https://example.invalid/', 'probe')
        except RuntimeError:
            pass
        else:
            raise AssertionError('Integrity failure accepted')
        assert transfer.call_count == 1
    assert checksum_for("SHA256 (a.tar) = " + "a" * 64, "a.tar") == "a" * 64
    for invalid in ("", "SHA256 (other.tar) = " + "a" * 64, ("SHA256 (a.tar) = " + "a" * 64 + "\n") * 2):
        try:
            checksum_for(invalid, "a.tar")
        except RuntimeError:
            pass
        else:
            raise AssertionError("Unmatched checksum accepted")
    valid = "[GNUPG:] VALIDSIG " + FEDORA_FINGERPRINT + " 2026-04-24 0 0 4 0 1 10 01 " + FEDORA_FINGERPRINT
    validate_signature(valid)
    for invalid in (
        valid.replace(FEDORA_FINGERPRINT, "A" * 40),
        "[GNUPG:] VALIDSIG " + FEDORA_FINGERPRINT,
        *(valid + "\n[GNUPG:] " + reason for reason in ("BADSIG", "ERRSIG", "REVKEYSIG", "EXPKEYSIG", "EXPSIG")),
    ):
        try:
            validate_signature(invalid)
        except RuntimeError:
            pass
        else:
            raise AssertionError("Untrusted signature accepted")
    print("Parser/signature guards passed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-check", action="store_true")
    parser.add_argument("--output", type=Path, default=OUT, help="Artifact directory")
    options = parser.parse_args()
    OUT = options.output.resolve()
    try:
        self_check() if options.self_check else main()
    except Exception as error:
        print(f"STOP: {error}", file=sys.stderr, flush=True)
        raise SystemExit(1)
