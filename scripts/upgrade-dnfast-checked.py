"""43b0928 publication after native validation of an unchanged state snapshot.

The caller holds the app's package mutex and has stopped the previous backend.
This helper does not interpret, recover, remove or rewrite package journals.
"""
import importlib.util
from pathlib import Path
import sys

spec = importlib.util.spec_from_file_location('upgrade', Path(__file__).with_name('upgrade-dnfast-empty.py'))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.OLD = {
    'usr/bin/dnfast': 'ada035264f62bba6e321df3a95d194d7ffa1ba9ec795a3c223c4a5726ecda67a',
    'usr/libexec/dnfast-executor': '56f09485e5d442f40fa9e9268404407e55e41c20c79d5da41a2a09980b86ea5d',
}
module.BACKUP = '43b0928-to-1449710'
if __name__ == '__main__':
    module.upgrade(Path('/'), Path(sys.argv[1]), sys.argv[2])
