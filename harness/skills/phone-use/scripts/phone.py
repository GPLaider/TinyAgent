#!/usr/bin/env python3
"""Operate this TinyAgent phone through its verified Android bridge, from Fedora."""
import argparse
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import shlex
import struct
import runpy
import socket
from concurrent.futures import ThreadPoolExecutor
import sys
import tempfile
import time
import uuid
import xml.etree.ElementTree as ET
import zlib


class Refused(Exception):
    pass


def package_name(value):
    if not value or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z0-9_]+)+", value):
        raise Refused("An explicit Android --package is required")
    return value


def parse_state(window, display, power):
    focus = re.search(r"mCurrentFocus=Window\{[^\n]*?\s([\w.]+)/[\w.$]+", window)
    size = re.findall(r"(?:Physical|Override) size:\s*(\d+)x(\d+)", display)
    rotation = re.search(r"(?:mCurrentRotation|mRotation)=(?:ROTATION_)?(\d+)", window)
    awake = re.search(r"mWakefulness=(\w+)", power)
    ime = re.search(r"Window #\d+ Window\{[^\n]*InputMethod[^\n]*\}(.*?)(?=\n  Window #|\Z)", window, re.S)
    flag = re.search(r"isVisible=(true|false)", ime[1]) if ime else None
    return {"foreground_package": focus[1] if focus else None,
            "display_size": [int(x) for x in size[-1]] if size else None,
            "rotation": int(rotation[1]) if rotation else None,
            "keyboard_visible": flag[1] == "true" if flag else None,
            "wakefulness": awake[1] if awake else None}


def parse_nodes(raw):
    nodes = []
    for i, item in enumerate(ET.fromstring(raw).iter("node")):
        a = item.attrib
        bounds = re.fullmatch(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", a.get("bounds", ""))
        password = a.get("password") == "true"
        nodes.append({"id": f"n{i}", "text": "[REDACTED]" if password else a.get("text", ""),
                      "description": "[REDACTED]" if password else a.get("content-desc", ""),
                      "resource_id": a.get("resource-id", ""), "class": a.get("class", ""),
                      "package": a.get("package", ""),
                      "bounds": [int(v) for v in bounds.groups()] if bounds else None,
                      **{k: a.get(k) == "true" for k in ("enabled", "clickable", "focused", "scrollable", "password")}})
    return nodes


def digest(nodes):
    return hashlib.sha256(json.dumps(nodes, sort_keys=True).encode()).hexdigest()


def image_size(png):
    if png[:8] != b"\x89PNG\r\n\x1a\n" or len(png) < 24:
        raise Refused("Screenshot was not a PNG")
    offset, dimensions, packed, ended = 8, None, bytearray(), False
    while offset + 12 <= len(png):
        length = struct.unpack_from(">I", png, offset)[0]
        kind = png[offset + 4:offset + 8]
        end = offset + 12 + length
        if end > len(png):
            raise Refused("Truncated PNG chunk")
        payload = png[offset + 8:end - 4]
        checksum = struct.unpack_from(">I", png, end - 4)[0]
        if zlib.crc32(kind + payload) != checksum:
            raise Refused("PNG checksum mismatch")
        if dimensions is None:
            if kind != b"IHDR" or length != 13:
                raise Refused("Missing PNG image header")
            width, height, depth, color, compression, filtering, interlace = struct.unpack(">IIBBBBB", payload)
            channels = {0: 1, 2: 3, 4: 2, 6: 4}.get(color)
            if not width or not height or depth != 8 or not channels or compression or filtering or interlace:
                raise Refused("Unsupported screenshot PNG format")
            row = width * channels + 1
            expected = height * row
            if expected > 64 * 1024 * 1024:
                raise Refused("Decoded screenshot exceeds 64 MiB")
            dimensions = [width, height]
        elif kind == b"IHDR":
            raise Refused("Duplicate PNG image header")
        elif kind == b"IDAT":
            packed.extend(payload)
        elif kind == b"IEND":
            ended = length == 0 and end == len(png)
            break
        offset = end
    if not ended or not packed:
        raise Refused("Incomplete PNG screenshot")
    try:
        decoder = zlib.decompressobj()
        pixels = decoder.decompress(packed, expected + 1)
        if (not decoder.eof or decoder.unused_data or decoder.unconsumed_tail or len(pixels) != expected
                or any(pixels[i] > 4 for i in range(0, expected, row))):
            raise Refused("Incomplete or invalid PNG pixel data")
    except zlib.error as exc:
        raise Refused("Invalid PNG compressed pixels") from exc
    return dimensions


def private_dir(root):
    root = Path(root).expanduser().absolute()
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    return Path(tempfile.mkdtemp(prefix="capture-", dir=root))


def save(path, data):
    with path.open("xb") as f:
        os.chmod(path, 0o600)
        f.write(data)


def ascii_input(value):
    if not value or any(ord(c) < 32 or ord(c) > 126 or c == "%" for c in value):
        raise Refused("Only printable ASCII excluding % is supported; use manual entry for Unicode")
    return value.replace(" ", "%s")


def point(xy, size):
    if len(xy) != 2 or not all(isinstance(v, int) and not isinstance(v, bool) for v in xy):
        raise Refused("Coordinates must be integer physical pixels")
    if not (0 <= xy[0] < size[0] and 0 <= xy[1] < size[1]):
        raise Refused("Coordinates outside the captured screen")
    return xy



class UnknownOutcome(Refused):
    """A submitted job may still be running; never replay it automatically."""


class AndroidBridge:
    JOB_SECONDS = 30
    STREAM_SECONDS = 30

    def __init__(self, mode, descriptor=Path("/root/.tinyagent/PACKAGE_SOCKET"), call=None, rejection=()):
        if mode not in ("developer", "root"):
            raise Refused("Phone interaction needs an authorized Developer or Root bridge; Stock has no ADB")
        self.mode, self.descriptor = mode, descriptor
        self.binding = descriptor.read_text().strip()
        if not re.fullmatch(r"tinyagent-android-\d+-\d+", self.binding):
            raise Refused("Invalid live Android bridge descriptor")
        if call is None:
            client = runpy.run_path("/root/.tinyagent/bootstrap/tinyagent-packages.py")
            call = client["request"]
            rejection = client["BridgeResponseError"]
        self.call, self.rejection = call, rejection

    def connected(self):
        if self.descriptor.read_text().strip() != self.binding:
            raise Refused("Android bridge instance changed; remeasure before using old evidence")

    def run(self, command):
        self.connected()
        job = str(uuid.uuid4())
        path = "/android/jobs/" + job
        print("android_job_id=" + job, file=sys.stderr, flush=True)
        try:
            try:
                row = self.call(self.binding, "POST", "/android/jobs",
                                {"id": job, "mode": self.mode, "action": "shell", "cwd": "/", "command": command, "path": ""})
            except self.rejection as exc:
                raise Refused("Android bridge rejected submission of " + job + "; no acceptance confirmed") from exc
            deadline = time.monotonic() + self.JOB_SECONDS
            while True:
                if row.get("id") != job or row.get("mode") != self.mode:
                    raise ValueError("Mismatched Android job reply")
                if row["status"] not in ("queued", "starting", "checking", "running", "cancel_requested"):
                    break
                if time.monotonic() >= deadline:
                    raise TimeoutError()
                time.sleep(0.2)
                row = self.call(self.binding, "GET", path)
        except Refused:
            raise
        except Exception as exc:
            raise UnknownOutcome("Android job " + job + " outcome unknown. Query tinyagent-android.py --id " +
                                 job + " status; do not resubmit") from exc
        if row["status"] == "unknown":
            raise UnknownOutcome("Android job " + job + " outcome unknown; inspect this ID, never replay input")
        if row["status"] != "completed" or row.get("exit_code") != 0:
            raise Refused("Android job " + job + " failed/refused; inspect its status without replaying input")
        if row.get("verified_self") is not True or row.get("execution_uid") != (0 if self.mode == "root" else 2000):
            raise Refused("Android job " + job + " lacks matching self-device and mode proof")
        return row.get("stdout", "")

    def bytes_command(self, command, limit):
        # AndroidJobs stdout is a 32 KiB tail. Binary artifacts need a separate,
        # short-lived authenticated loopback stream, not base64 stuffed into logs.
        token = uuid.uuid4().hex + uuid.uuid4().hex
        remote = "/data/local/tmp/tinyagent-phone-use-" + uuid.uuid4().hex + ".bin"
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
            server.bind(("127.0.0.1", 0))
            server.listen(1)
            server.settimeout(0.2)
            port = server.getsockname()[1]
            script = ("set -e; umask 077; trap " + shlex.quote("rm -f " + remote) + " EXIT; "
                      + "{ " + command + "; } > " + shlex.quote(remote) + "; "
                      + "{ printf '%s\\n' " + shlex.quote(token) + "; cat " + shlex.quote(remote)
                      + "; } | toybox nc -w 10 -W 10 -q 1 127.0.0.1 " + str(port))
            with ThreadPoolExecutor(max_workers=1) as worker:
                future = worker.submit(self.run, script)
                deadline = time.monotonic() + self.STREAM_SECONDS
                while True:
                    try:
                        stream, address = server.accept()
                        break
                    except socket.timeout:
                        if future.done():
                            future.result()
                            raise Refused("Android capture finished without an artifact stream")
                        if time.monotonic() >= deadline:
                            raise Refused("Capture stream timed out; inspect the printed Android job ID")
                with stream:
                    def receive(count):
                        remaining = deadline - time.monotonic()
                        if remaining <= 0:
                            raise Refused("Capture stream deadline exceeded; inspect the printed Android job ID")
                        stream.settimeout(min(10, remaining))
                        return stream.recv(count)

                    header = bytearray()
                    while not header.endswith(b"\n") and len(header) <= 64:
                        chunk = receive(1)
                        if not chunk:
                            break
                        header.extend(chunk)
                    if not hmac.compare_digest(header, (token + "\n").encode()):
                        raise Refused("Capture stream authentication failed")
                    data = bytearray()
                    while True:
                        chunk = receive(min(65536, limit + 1 - len(data)))
                        if not chunk:
                            break
                        data.extend(chunk)
                        if len(data) > limit:
                            raise Refused("Android artifact exceeds its capture limit")
                future.result()
                return bytes(data)


class Phone:
    def __init__(self, mode, package=None, output=".phone-use", bridge=None):
        self.bridge = bridge or AndroidBridge(mode)
        self.binding, self.package, self.output = self.bridge.binding, package, output
        self.connected()

    def connected(self):
        self.bridge.connected()

    def shell(self, *args):
        return self.bridge.run(shlex.join(str(x) for x in args))

    def state(self):
        marker = "PHONEUSE-" + uuid.uuid4().hex
        commands = ["dumpsys window", "wm size", "dumpsys power", "dumpsys window policy"]
        command = ("; printf '\\n" + marker + "\\n'; ").join(commands)
        parts = self.bridge.bytes_command(command, 2 * 1024 * 1024).decode("utf-8", "replace").split("\n" + marker + "\n")
        if len(parts) != 4:
            raise Refused("Incomplete Android state capture")
        window, size, power, policy = parts
        keyguard = {}
        for field in ("showing", "secure"):
            match = re.search(r"^\s+" + field + r"=(true|false)\s*$", policy, re.M)
            keyguard["keyguard_" + field] = match[1] == "true" if match else None
        return {"bridge": self.binding, "mode": self.bridge.mode,
                **parse_state(window, size, power), **keyguard}

    def unlock(self):
        self.connected()
        if self.state()["keyguard_secure"] is not False:
            raise Refused("Secure or unknown keyguard; user must unlock it")
        self.shell("input", "keyevent", "KEYCODE_WAKEUP")
        self.shell("wm", "dismiss-keyguard")
        deadline = time.monotonic() + 5
        while True:
            state = self.state()
            if state["keyguard_showing"] is False and state["wakefulness"] == "Awake":
                return {"plain_lockscreen_dismiss_requested": True, "state": state}
            if time.monotonic() >= deadline:
                raise Refused("Dismiss requested but screen is not ready; inspect state before any further input")
            time.sleep(0.1)

    def guard(self):
        package_name(self.package)
        self.connected()
        state = self.state()
        if (state["foreground_package"] != self.package or state["wakefulness"] != "Awake"
                or state["keyguard_showing"] is not False):
            raise Refused("Selected app is not foreground, awake and unlocked; no input or capture performed")
        return state

    def tree(self):
        remote = f"/data/local/tmp/tinyagent-phone-use-{uuid.uuid4().hex}.xml"
        uncertain = False
        try:
            self.shell("uiautomator", "dump", "--compressed", remote)
            raw = self.bridge.bytes_command(shlex.join(["cat", remote]), 2 * 1024 * 1024)
            return raw, parse_nodes(raw), None
        except UnknownOutcome:
            uncertain = True
            raise
        except (Refused, ET.ParseError):
            return None, [], "UIAutomator unavailable; use screenshot-grounded coordinates"
        finally:
            try:
                if not uncertain:
                    self.shell("rm", "-f", remote)
            except UnknownOutcome:
                raise
            except Refused:
                pass

    def snapshot(self):
        before = self.guard()
        raw, nodes, warning = self.tree()
        png = self.bridge.bytes_command("screencap -p", 16 * 1024 * 1024)
        after = self.guard()
        if before != after:
            raise Refused("Window/display changed during capture; observe again")
        size = image_size(png)
        folder = private_dir(self.output)
        save(folder / "screen.png", png)
        if raw is not None:
            save(folder / "ui.xml", raw)
        result = {"version": 1, "bridge": self.binding, "package": self.package,
                  "captured_at": time.time(), "state": after, "screen_size": size,
                  "screenshot": str(folder / "screen.png"),
                  "screen_digest": hashlib.sha256(png).hexdigest(),
                  "ui_xml": str(folder / "ui.xml") if raw is not None else None,
                  "tree_digest": digest(nodes) if raw is not None else None,
                  "nodes": [n for n in nodes if n["package"] == self.package],
                  "omitted_nodes": sum(n["package"] != self.package for n in nodes),
                  "warning": warning, "snapshot": str(folder / "snapshot.json")}
        save(folder / "snapshot.json", json.dumps(result, ensure_ascii=False, indent=2).encode())
        return result

    def evidence(self, path):
        data = json.loads(Path(path).read_text())
        if data.get("version") != 1 or data.get("bridge") != self.binding or data.get("package") != self.package:
            raise Refused("Snapshot belongs to another bridge/app or unsupported version")
        age = time.time() - data["captured_at"]
        if not 0 <= age <= 120:
            raise Refused("Snapshot is stale; take and inspect a new one")
        if self.guard() != data["state"]:
            raise Refused("App/display state changed; take a new snapshot")
        if data["tree_digest"] is not None:
            raw, nodes, _ = self.tree()
            if raw is None or digest(nodes) != data["tree_digest"]:
                raise Refused("UI tree changed; take and inspect a new snapshot")
        png = self.bridge.bytes_command("screencap -p", 16 * 1024 * 1024)
        if image_size(png) != data["screen_size"]:
            raise Refused("Screen dimensions changed; take a new snapshot")
        if data["tree_digest"] is None and hashlib.sha256(png).hexdigest() != data.get("screen_digest"):
            raise Refused("Screenshot-only screen changed; take and inspect a new snapshot")
        if self.guard() != data["state"]:
            raise Refused("App/display changed while validating evidence; observe again")
        return data

    def act(self, args):
        data = self.evidence(args.snapshot)
        action = args.command
        if action == "tap":
            if args.node:
                node = next((n for n in data["nodes"] if n["id"] == args.node), None)
                if not node or not node["enabled"] or not node["clickable"] or not node["bounds"]:
                    raise Refused("Node missing, disabled, not clickable, or without bounds")
                if node["package"] != self.package:
                    raise Refused("Node is outside the selected app")
                x1, y1, x2, y2 = node["bounds"]
                if x2 <= x1 or y2 <= y1:
                    raise Refused("Node has empty bounds")
                point([x1, y1], data["screen_size"])
                point([x2 - 1, y2 - 1], data["screen_size"])
                xy = [(x1 + x2) // 2, (y1 + y2) // 2]
            else:
                xy = point(args.xy, data["screen_size"])
            command = ("input", "tap", *xy)
        elif action == "swipe":
            start, end = point(args.start, data["screen_size"]), point(args.end, data["screen_size"])
            if not 100 <= args.duration <= 2000:
                raise Refused("Swipe duration must be 100–2000 ms")
            command = ("input", "swipe", *start, *end, args.duration)
        elif action == "key":
            command = ("input", "keyevent", {"back": "KEYCODE_BACK", "enter": "KEYCODE_ENTER", "delete": "KEYCODE_DEL"}[args.key])
        elif action == "text":
            value = ascii_input(args.value)
            focused = [n for n in data["nodes"] if n["focused"]]
            if not focused or any(n["password"] or n["package"] != self.package for n in focused):
                raise Refused("Need an exposed, non-password focused field in the selected app")
            if not any(n["class"].endswith("EditText") for n in focused):
                raise Refused("Focused node is not an exposed editable field; inspect/manual entry")
            command = ("input", "text", value)
        else:
            raise Refused("Unsupported action")
        self.shell(*command)
        try:
            return {"action_dispatched": action, "after": self.snapshot()}
        except Refused as exc:
            return {"action_dispatched": action, "verified": False, "warning": str(exc),
                    "next": "Observe state; do not repeat the action blindly"}

    def launch(self):
        package_name(self.package)
        resolved = self.shell("cmd", "package", "resolve-activity", "--brief", "-a",
                              "android.intent.action.MAIN", "-c", "android.intent.category.LAUNCHER", self.package)
        component = next((line.strip() for line in resolved.splitlines()
                          if re.fullmatch(re.escape(self.package) + r"/[A-Za-z0-9_.$]+", line.strip())), None)
        if not component:
            raise Refused("Selected package has no resolved launcher activity")
        self.shell("am", "start", "-W", "-n", component)
        return {"launch_requested": self.package, "state": self.state(), "next": "Take a snapshot to verify launch"}

    def logs(self, lines):
        package_name(self.package)
        if not 1 <= lines <= 500:
            raise Refused("Log limit must be 1–500 lines")
        pid = self.shell("pidof", self.package).strip()
        if not re.fullmatch(r"\d+", pid):
            raise Refused("No single main app PID; no global log fallback")
        raw = self.bridge.bytes_command(shlex.join(["logcat", "-d", "-t", str(lines), f"--pid={pid}", "-v", "brief"]), 1024 * 1024)
        path = private_dir(self.output) / "app.log"
        save(path, raw)
        return {"bridge": self.binding, "package": self.package, "pid": int(pid), "log": str(path)}


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mode", required=True, choices=["developer", "root"], help="Current authorized Android mode; never auto-escalates")
    p.add_argument("--package")
    p.add_argument("--output", default=".phone-use", help="Artifact root; each capture gets a private subdirectory")
    sub = p.add_subparsers(dest="command", required=True)
    for command in ("state", "snapshot", "launch", "wake", "unlock"):
        sub.add_parser(command)
    log = sub.add_parser("logs")
    log.add_argument("--lines", type=int, default=100)
    for command in ("tap", "swipe", "key", "text"):
        action = sub.add_parser(command)
        action.add_argument("--snapshot", required=True)
        if command == "tap":
            target = action.add_mutually_exclusive_group(required=True)
            target.add_argument("--node")
            target.add_argument("--xy", nargs=2, type=int)
        elif command == "swipe":
            action.add_argument("--start", nargs=2, type=int, required=True)
            action.add_argument("--end", nargs=2, type=int, required=True)
            action.add_argument("--duration", type=int, default=300)
        elif command == "key":
            action.add_argument("key", choices=["back", "enter", "delete"])
        else:
            action.add_argument("value")
    return p


def main():
    args = parser().parse_args()
    try:
        phone = Phone(args.mode, args.package, args.output)
        if args.command in ("state", "snapshot", "launch", "unlock"):
            result = getattr(phone, args.command)()
        elif args.command == "wake":
            phone.shell("input", "keyevent", "KEYCODE_WAKEUP")
            result = phone.state()
        elif args.command == "logs":
            result = phone.logs(args.lines)
        else:
            result = phone.act(args)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (Refused, OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"error": str(exc) if isinstance(exc, Refused) else type(exc).__name__}), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
