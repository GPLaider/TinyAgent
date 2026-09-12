"""Offline output/admission/deadline tests; no RPM or phone actions."""
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('host_cli', Path(__file__).with_name('benchmark-host-cli.py'))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class HostCliTests(unittest.TestCase):
    def test_dnfast_terminal_record_required(self):
        record = dict(schema='dnfast.cli.v1', command='cli', exit_code=0, errors=[],
                      message='Usage: dnfast\nCommands:')
        self.assertTrue(module.valid_help('dnfast', json.dumps(record)))
        for damaged in ['Usage: dnfast\nCommands:', '[]',
                        json.dumps(dict(record, exit_code=1)),
                        json.dumps(dict(record, errors=['failure'])),
                        json.dumps(dict(record, command='install')),
                        json.dumps(dict(record, message=None))]:
            self.assertFalse(module.valid_help('dnfast', damaged))

    def test_dnf5_usage_required(self):
        self.assertTrue(module.valid_help('dnf5', 'Usage: dnf5\nCommands:'))
        self.assertFalse(module.valid_help('dnf5', 'dnf5 library load error'))

    def test_failed_or_incomplete_cells_have_no_time(self):
        rows = [dict(tool='dnfast', trial=i, seconds=1.0, exit=0, timeout=False, valid_help=True)
                for i in range(1, 4)]
        self.assertEqual(module.summarize(rows, 3)[0]['median_seconds'], 1.0)
        self.assertEqual(module.summarize(rows, 3)[1]['status'], 'incomplete')
        for field, value in [('exit', 1), ('timeout', True), ('valid_help', False)]:
            changed = [dict(row) for row in rows]
            changed[0][field] = value
            result = module.summarize(changed, 3)[0]
            self.assertEqual(result['status'], 'failed')
            self.assertIsNone(result['median_seconds'])
        self.assertEqual(module.summarize([rows[0]] * 3, 3)[0]['status'], 'incomplete')

    def test_child_exit_and_timeout_are_reaped(self):
        with tempfile.TemporaryDirectory() as home:
            env = {'PATH': '/usr/bin:/bin', 'HOME': home}
            row, output = module.measure([sys.executable, '-c', 'print("fixture")'], home, env, 2)
            self.assertEqual(row['exit'], 0)
            self.assertFalse(row['timeout'])
            self.assertEqual(output.strip(), 'fixture')
            row, _ = module.measure([sys.executable, '-c', 'import time; time.sleep(5)'], home, env, 0.05)
            self.assertTrue(row['timeout'])
            self.assertEqual(row['exit'], -9)
            self.assertLess(row['seconds'], 2)
            with self.assertRaises(ChildProcessError):
                os.waitpid(-1, os.WNOHANG)


if __name__ == '__main__':
    unittest.main(verbosity=2)
