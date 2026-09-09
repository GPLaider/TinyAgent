"""Transfer one APK to the explicitly selected Tailscale peer, then close."""
import argparse
import http.server
from pathlib import Path
import shutil

p = argparse.ArgumentParser()
p.add_argument('apk', type=Path)
p.add_argument('bind')
p.add_argument('peer')
args = p.parse_args()
assert args.apk.is_file() and args.apk.suffix == '.apk'
class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.client_address[0] != args.peer or self.path != '/artifact.apk':
            self.send_error(403)
            return
        self.send_response(200)
        self.send_header('Content-Length', str(args.apk.stat().st_size))
        self.end_headers()
        with args.apk.open('rb') as source:
            shutil.copyfileobj(source, self.wfile)
        self.server.delivered = True
server = http.server.HTTPServer((args.bind, 14285), Handler)
server.timeout = 60
server.delivered = False
try:
    server.handle_request()
    assert server.delivered, 'APK was not delivered'
finally:
    server.server_close()
