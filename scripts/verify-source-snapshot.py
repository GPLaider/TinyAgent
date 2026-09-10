"""Check exported source bytes against their snapshot; this does not prove build reproducibility."""
import hashlib
import json
from pathlib import Path
import sys
import zipfile

with zipfile.ZipFile(Path(sys.argv[1])) as archive:
    snapshot = json.loads(archive.read('TinyAgent/SOURCE-SNAPSHOT.json'))
    for name, expected in snapshot['files_sha256'].items():
        assert not Path(name).is_absolute() and '..' not in Path(name).parts
        data = archive.read('TinyAgent/'+name)
        assert hashlib.sha256(data).hexdigest() == expected, name
    print(json.dumps(dict(files=len(snapshot['files_sha256']), apk_sha256=snapshot['apk_sha256'], passed=True)))
