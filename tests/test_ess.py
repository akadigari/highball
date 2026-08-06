"""Checks on the ESS receipt math. Run: python3 -m unittest discover tests"""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lab"))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import run_ess  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestBartlett(unittest.TestCase):
    def test_clips_at_n_on_negative_dependence(self):
        # alternating series: rho1 is -5/6, bandwidth-1 vif is 1/6,
        # raw ess explodes past n and must clip to n (matches assay)
        x = [1.0, 2.0, 1.0, 2.0, 1.0, 2.0]
        sweep = run_ess.bartlett_sweep(x)
        self.assertEqual(sweep[0]["bandwidth"], 1)
        self.assertEqual(sweep[0]["ess"], 6.0)

    def test_discounts_positive_dependence(self):
        # a smooth trend with every value repeated: heavy clustering,
        # the worst-bandwidth ess must fall far below raw n
        x = []
        for v in (5.0, 5.5, 6.0, 7.0, 8.0, 4.0, 3.0, 2.0):
            x += [v, v]
        worst = min(s["ess"] for s in run_ess.bartlett_sweep(x))
        self.assertLess(worst, 0.5 * len(x))

    def test_receipt_written_from_ledger(self):
        out = run_ess.main()
        path = os.path.join(ROOT, "lab", "ess_g1.json")
        self.assertTrue(os.path.exists(path))
        d = json.load(open(path))
        self.assertEqual(d["n"], out["n"])
        self.assertGreater(d["n"], 0)
        self.assertGreater(d["ess_min"], 0)
        self.assertLessEqual(d["ess_max"], d["n"])


if __name__ == "__main__":
    unittest.main()
