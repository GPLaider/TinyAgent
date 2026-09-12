"""Offline controls for comparison admission; no package manager is executed."""
import importlib.util
import json
from pathlib import Path
import statistics
import unittest

spec=importlib.util.spec_from_file_location('package_compare',Path(__file__).with_name('compare.py'))
compare=importlib.util.module_from_spec(spec)
spec.loader.exec_module(compare)


def row(trial,seconds=1.0,exit=0,tool='dnfast',workload='help'):
    return dict(trial=trial,seconds=seconds,exit=exit,tool=tool,workload=workload,
                maxrssKiB=1000+trial,output='fixture')


def summarize(rows):
    return compare.summarize(rows,['help'],['dnfast'])[0]


class ComparisonTests(unittest.TestCase):
    def test_fast_failures_cannot_win(self):
        rows=[row(i,0.01,1) for i in range(1,5)]+[row(5,1.1),row(6,1.3)]
        self.assertEqual(statistics.median(r['seconds'] for r in rows),0.01)
        result=summarize(rows)
        self.assertEqual((result['status'],result['failedRuns'],result['successfulRuns']),('failed',4,2))
        self.assertIsNone(result['medianSeconds'])
        self.assertIsNone(result['medianRssKiB'])
        self.assertEqual(result['exits'],[0,1])
        self.assertIsNone(json.loads(json.dumps(result))['medianSeconds'])

    def test_complete_success_excludes_warmup(self):
        result=summarize([row(0,999,1)]+[row(i,float(i)) for i in range(1,7)])
        self.assertEqual(result['status'],'passed')
        self.assertEqual(result['medianSeconds'],3.5)
        self.assertEqual(result['medianRssKiB'],1003.5)
        self.assertEqual(result['warmupExits'],[1])

    def test_signal_failure_is_failure(self):
        result=summarize([row(i) for i in range(1,6)]+[row(6,0.001,-15)])
        self.assertEqual(result['status'],'failed')
        self.assertIsNone(result['medianSeconds'])
        self.assertIn(-15,result['exits'])

    def test_all_failed(self):
        result=summarize([row(i,0.001,1) for i in range(1,7)])
        self.assertEqual(result['successfulRuns'],0)
        self.assertIsNone(result['medianSeconds'])

    def test_missing_or_duplicate_trials_are_incomplete(self):
        for rows in [[],[row(0)],[row(i) for i in range(1,6)],
                     [row(1) for _ in range(6)],
                     [row(i) for i in range(2,8)],
                     [row(i) for i in range(1,8)]]:
            with self.subTest(rows=rows):
                result=summarize(rows)
                self.assertEqual(result['status'],'incomplete')
                self.assertIsNone(result['medianSeconds'])

    def test_cells_are_independent_and_raw_evidence_preserved(self):
        rows=[row(i,float(i)) for i in range(1,7)]
        rows += [row(i,0.001,1,tool='dnf5') for i in range(1,7)]
        rows += [row(i,20.0,workload='repo-list') for i in range(1,7)]
        original=json.dumps(rows,sort_keys=True)
        result=compare.summarize(rows,['help','repo-list'],['dnfast','dnf5'])
        self.assertEqual([r['status'] for r in result],['passed','failed','passed','incomplete'])
        self.assertEqual([r['medianSeconds'] for r in result],[3.5,None,20.0,None])
        self.assertEqual(json.dumps(rows,sort_keys=True),original)


if __name__=='__main__':
    unittest.main(verbosity=2)
