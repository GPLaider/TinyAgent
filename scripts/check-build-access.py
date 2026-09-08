"""Read-only network/tool availability check; no credentials or device mutation."""
import json
import urllib.request

url = 'https://api.github.com/repos/oven-sh/bun/releases/tags/bun-v1.3.14'
try:
    request = urllib.request.Request(url, headers={'User-Agent': 'TinyAgent-build/1'})
    with urllib.request.urlopen(request, timeout=10) as response:
        release = json.load(response)
    assets = [
        {'name': x['name'], 'url': x['browser_download_url'], 'digest': x.get('digest'), 'size': x['size']}
        for x in release['assets'] if x['name'] == 'bun-windows-x64.zip'
    ]
    print(json.dumps({'ok': True, 'tag': release['tag_name'], 'assets': assets}))
except Exception as error:
    print(json.dumps({'ok': False, 'error': str(error)}))
    raise SystemExit(1)
