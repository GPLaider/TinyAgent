"""Offline regression tests for the APK-bundled phone helper (no ADB/device)."""
import argparse
import importlib.util
import json
from pathlib import Path
import re
import shlex
import socket
import struct
import tempfile
import time
import unittest
import zlib
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("phone", ROOT / "harness/skills/phone-use/scripts/phone.py")
phone = importlib.util.module_from_spec(spec)
spec.loader.exec_module(phone)
PACKAGE = "io.example.qa"
XML = b'<hierarchy><node text="Search" package="io.example.qa" class="android.widget.EditText" bounds="[10,20][90,60]" enabled="true" clickable="true" focused="true" password="false"/></hierarchy>'
def png_chunk(kind, payload):
    return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload))


PNG = (b"\x89PNG\r\n\x1a\n" + png_chunk(b"IHDR", struct.pack(">IIBBBBB", 100, 200, 8, 6, 0, 0, 0))
       + png_chunk(b"IDAT", zlib.compress((b"\0" + b"\x80\x80\x80\xff" * 100) * 200)) + png_chunk(b"IEND", b""))


class FakeBridge:
    binding = "tinyagent-android-10001-1234"
    mode = "developer"

    def __init__(self):
        self.commands = []
        self.package, self.xml, self.png = PACKAGE, XML, PNG
        self.secure, self.showing, self.tree_failure = False, False, None
        self.connected_ok = True

    def connected(self):
        if not self.connected_ok:
            raise phone.Refused("Bridge changed")

    def run(self, command):
        self.commands.append(command)
        args = shlex.split(command)
        if args[0] == "uiautomator" and self.tree_failure:
            raise self.tree_failure("UIAutomator failed")
        if args[:3] == ["cmd", "package", "resolve-activity"]:
            return PACKAGE + "/.Main\n"
        if args[0] == "pidof":
            return "1234"
        return ""

    def bytes_command(self, command, limit):
        self.commands.append(command)
        if command.startswith("dumpsys window"):
            marker = re.search(r"PHONEUSE-[a-f0-9]+", command)[0]
            fields = [f"mCurrentFocus=Window{{abc u0 {self.package}/.Main}}\nmRotation=0\n",
                      "Physical size: 100x200", "mWakefulness=Awake",
                      f"  showing={str(self.showing).lower()}\n  secure={str(self.secure).lower()}\n"]
            return ("\n" + marker + "\n").join(fields).encode()
        if command == "screencap -p":
            return self.png
        if command.startswith("cat "):
            return self.xml
        if command.startswith("logcat "):
            return b"Scoped app log\n"
        raise AssertionError(command)


class PhoneTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.fake = FakeBridge()
        self.phone = phone.Phone("developer", PACKAGE, temp.name, bridge=self.fake)

    def action(self, data, **kwargs):
        values = dict(command="tap", snapshot=data["snapshot"], node="n0", xy=None)
        values.update(kwargs)
        return self.phone.act(argparse.Namespace(**values))

    def test_snapshot_and_tap(self):
        data = self.phone.snapshot()
        self.assertEqual(data["screen_size"], [100, 200])
        self.assertEqual(Path(data["snapshot"]).parent.stat().st_mode & 0o777, 0o700)
        for name in ("snapshot", "screenshot", "ui_xml"):
            self.assertEqual(Path(data[name]).stat().st_mode & 0o777, 0o600)
        after = self.action(data)
        self.assertEqual(self.fake.commands.count("input tap 50 40"), 1)
        self.assertNotEqual(data["snapshot"], after["after"]["snapshot"])

    def test_incomplete_png_never_published_as_snapshot(self):
        invalid_pixels = PNG[:33] + png_chunk(b"IDAT", zlib.compress(b"short")) + png_chunk(b"IEND", b"")
        for malformed in (PNG[:24], PNG[:-12], PNG[:-1], PNG + b"extra", invalid_pixels,
                          PNG[:41] + bytes([PNG[41] ^ 1]) + PNG[42:]):
            self.fake.png = malformed
            with self.assertRaises(phone.Refused):
                self.phone.snapshot()
        self.assertEqual(list(Path(self.phone.output).rglob("snapshot.json")), [])

    def test_wrong_app_or_locked_does_not_capture(self):
        for package, showing in (("io.other.app", False), (PACKAGE, True), (PACKAGE, None)):
            self.fake.package, self.fake.showing = package, showing
            with self.assertRaises(phone.Refused):
                self.phone.snapshot()
        self.assertNotIn("screencap -p", self.fake.commands)

    def test_stale_bridge_mode_app_and_time(self):
        for change in ({"bridge": "tinyagent-android-10002-9999"}, {"package": "io.other.app"},
                       {"captured_at": time.time() - 121}, {"captured_at": time.time() + 100}):
            data = self.phone.snapshot()
            data.update(change)
            Path(data["snapshot"]).write_text(json.dumps(data))
            with self.assertRaises(phone.Refused):
                self.action(data)
        data = self.phone.snapshot()
        self.fake.mode = "root"
        with self.assertRaises(phone.Refused):
            self.action(data)
        self.assertFalse(any(c.startswith("input ") for c in self.fake.commands))

    def test_tree_change_and_screenshot_fallback_change(self):
        data = self.phone.snapshot()
        self.fake.xml = XML.replace(b"Search", b"Changed")
        with self.assertRaises(phone.Refused):
            self.action(data)
        self.fake.tree_failure = phone.Refused
        data = self.phone.snapshot()
        self.assertIsNone(data["tree_digest"])
        self.fake.png += b"changed pixels"
        with self.assertRaises(phone.Refused):
            self.action(data, node=None, xy=[50, 50])

    def test_unknown_dump_no_capture_or_cleanup(self):
        self.fake.tree_failure = phone.UnknownOutcome
        with self.assertRaises(phone.UnknownOutcome):
            self.phone.snapshot()
        self.assertFalse(any(c.startswith(("screencap", "rm ")) for c in self.fake.commands))

    def test_foreign_and_password_nodes(self):
        foreign = XML.replace(b"io.example.qa", b"io.other.app").replace(b"Search", b"PRIVATE")
        self.fake.xml = XML.replace(b"</hierarchy>", foreign.removeprefix(b"<hierarchy>"))
        data = self.phone.snapshot()
        self.assertNotIn("PRIVATE", json.dumps(data))
        self.assertEqual(data["omitted_nodes"], 1)
        with self.assertRaises(phone.Refused):
            self.action(data, node="n1")
        self.fake.xml = XML.replace(b'password="false"', b'password="true"').replace(b"Search", b"SECRET")
        data = self.phone.snapshot()
        self.assertNotIn("SECRET", json.dumps(data))
        with self.assertRaises(phone.Refused):
            self.action(data, command="text", value="hello")

    def test_ascii_text_quoting(self):
        value = "hello ';$(id) & \"x\" `whoami`"
        self.action(self.phone.snapshot(), command="text", value=value)
        self.assertIn(["input", "text", value.replace(" ", "%s")], [shlex.split(c) for c in self.fake.commands])
        for value in ("한글", "%s", "\n", ""):
            with self.assertRaises(phone.Refused):
                phone.ascii_input(value)

    def test_dispatch_not_repeated_when_observation_fails(self):
        data = self.phone.snapshot()
        with patch.object(self.phone, "snapshot", side_effect=phone.Refused("App switched")):
            result = self.action(data)
        self.assertFalse(result["verified"])
        self.assertEqual(self.fake.commands.count("input tap 50 40"), 1)

    def test_bounds_and_duration(self):
        data = self.phone.snapshot()
        for xy in ([-1, 0], [100, 0], [0, 200]):
            with self.assertRaises(phone.Refused):
                self.action(data, node=None, xy=xy)
        with self.assertRaises(phone.Refused):
            self.action(data, command="swipe", start=[1, 1], end=[2, 2], duration=3000)

    def test_launch_logs_unlock(self):
        self.assertEqual(self.phone.launch()["launch_requested"], PACKAGE)
        self.assertEqual(Path(self.phone.logs(20)["log"]).read_bytes(), b"Scoped app log\n")
        self.assertIn("logcat -d -t 20 --pid=1234 -v brief", self.fake.commands)
        self.assertTrue(self.phone.unlock()["plain_lockscreen_dismiss_requested"])
        self.fake.commands.clear()
        for secure in (True, None):
            self.fake.secure = secure
            with self.assertRaises(phone.Refused):
                self.phone.unlock()
        self.assertNotIn("wm dismiss-keyguard", self.fake.commands)


class BridgeTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.descriptor = Path(temp.name) / "PACKAGE_SOCKET"
        self.descriptor.write_text(FakeBridge.binding)
        self.calls = []
        self.statuses, self.uid, self.proof = ["completed"], 2000, True

    def call(self, binding, method, path, payload=None):
        self.calls.append((binding, method, path, payload))
        if payload:
            self.job = payload["id"]
        status = self.statuses.pop(0) if len(self.statuses) > 1 else self.statuses[0]
        return dict(id=self.job, mode="developer", status=status, exit_code=0,
                    verified_self=self.proof, execution_uid=self.uid, stdout="ok")

    def bridge(self, **kwargs):
        return phone.AndroidBridge("developer", self.descriptor, kwargs.pop("call", self.call), **kwargs)

    def test_live_binding_and_no_stock(self):
        bridge = self.bridge()
        self.descriptor.write_text("tinyagent-android-10001-9999")
        with self.assertRaises(phone.Refused):
            bridge.run("input tap 1 2")
        with self.assertRaises(phone.Refused):
            phone.AndroidBridge("stock", self.descriptor, self.call)
        self.assertEqual(self.calls, [])

    def test_single_submission_polling_and_proof(self):
        self.statuses = ["queued", "running", "completed"]
        with patch.object(phone.time, "sleep"):
            self.assertEqual(self.bridge().run("input tap 1 2"), "ok")
        self.assertEqual([x[1] for x in self.calls], ["POST", "GET", "GET"])
        self.assertEqual(self.calls[0][3]["command"], "input tap 1 2")
        for proof, uid in ((False, 2000), (True, 0)):
            self.proof, self.uid = proof, uid
            with self.assertRaises(phone.Refused):
                self.bridge().run("id")

    def test_unknown_no_replay(self):
        def dropped(*args):
            self.calls.append(args)
            raise ConnectionError("lost")
        with self.assertRaises(phone.UnknownOutcome):
            self.bridge(call=dropped).run("input tap 1 2")
        self.assertEqual(len(self.calls), 1)
        self.statuses = ["unknown"]
        with self.assertRaises(phone.UnknownOutcome):
            self.bridge().run("id")

    def test_explicit_rejection_not_unknown(self):
        class Rejection(Exception):
            pass
        def rejected(*args):
            raise Rejection("queue full")
        with self.assertRaises(phone.Refused) as caught:
            self.bridge(call=rejected, rejection=Rejection).run("id")
        self.assertNotIsInstance(caught.exception, phone.UnknownOutcome)

    def test_timeout_and_malformed_status(self):
        self.statuses = ["running"]
        bridge = self.bridge()
        bridge.JOB_SECONDS = 0
        with self.assertRaises(phone.UnknownOutcome):
            bridge.run("id")
        with self.assertRaises(phone.UnknownOutcome):
            self.bridge(call=lambda *a: {"status": "completed"}).run("id")

    def stream(self, payload, wrong_token=False, limit=65536):
        bridge = self.bridge()
        def send(script):
            token = re.search(r"\b[a-f0-9]{64}\b", script)[0]
            port = int(shlex.split(script)[-1])
            with socket.create_connection(("127.0.0.1", port), timeout=2) as client:
                try:
                    client.sendall((("x" * 64 if wrong_token else token) + "\n").encode() + payload)
                except (BrokenPipeError, ConnectionResetError):
                    pass
            return ""
        with patch.object(bridge, "run", side_effect=send):
            return bridge.bytes_command("screencap -p", limit)

    def test_stream_larger_than_android_log_tail(self):
        payload = bytes(range(256)) * 256
        self.assertEqual(self.stream(payload), payload)

    def test_stream_auth_and_size_rejection(self):
        with self.assertRaisesRegex(phone.Refused, "authentication"):
            self.stream(b"private", wrong_token=True)
        with self.assertRaisesRegex(phone.Refused, "limit"):
            self.stream(b"12345", limit=4)

    def test_stream_requires_completed_job(self):
        bridge = self.bridge()
        with patch.object(bridge, "run", side_effect=phone.UnknownOutcome("job uncertain")):
            with self.assertRaises(phone.UnknownOutcome):
                bridge.bytes_command("screencap -p", 100)


if __name__ == "__main__":
    unittest.main()
