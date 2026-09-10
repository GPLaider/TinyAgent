"""Serve one exact source bundle on host loopback, then exit; never serves a directory."""
import argparse
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import shutil
import time

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('bundle', type=Path)
parser.add_argument('--port', type=int, default=18551)
args = parser.parse_args()
assert args.bundle.is_file() and args.bundle.suffix == '.bundle'
assert 1024 <= args.port <= 65535
served = False

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass
    def do_GET(self):
        global served
        if self.path != '/source.bundle':
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header('Content-Length', str(args.bundle.stat().st_size))
        self.send_header('Content-Type', 'application/octet-stream')
        self.end_headers()
        with args.bundle.open('rb') as stream:
            shutil.copyfileobj(stream, self.wfile)
        self.wfile.flush()
        served = True

with HTTPServer(('127.0.0.1', args.port), Handler) as server:
    server.timeout = 1
    deadline = time.monotonic() + 300
    print('Source-only loopback transfer ready', flush=True)
    while not served and time.monotonic() < deadline:
        server.handle_request()
assert served, 'Source was not transferred before the observation deadline'
print('Source transferred; server closed', flush=True)
