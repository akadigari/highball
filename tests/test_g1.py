"""Checks on the G1 courtroom's math. Run: python3 -m unittest discover tests"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lab"))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import run_g1  # noqa: E402


class TestBrier(unittest.TestCase):
    def test_perfect_and_worst(self):
        rows = [(1.0, 0.5, True), (0.0, 0.5, False)]
        self.assertAlmostEqual(run_g1.brier(rows, 1.0), 0.0)
        rows = [(0.0, 0.5, True), (1.0, 0.5, False)]
        self.assertAlmostEqual(run_g1.brier(rows, 1.0), 1.0)

    def test_shrink_moves_toward_market(self):
        # model says 0.9, market says 0.5, outcome no: shrinking helps
        rows = [(0.9, 0.5, False)]
        self.assertLess(run_g1.brier(rows, 0.5), run_g1.brier(rows, 1.0))

    def test_w_zero_is_market(self):
        rows = [(0.9, 0.6, True)]
        self.assertAlmostEqual(run_g1.brier(rows, 0.0), (0.6 - 1.0) ** 2)


class TestMeter(unittest.TestCase):
    def test_win_and_loss_at_95(self):
        # fee at 95c is ceil(7*.95*.05) = 1
        self.assertEqual(run_g1.meter_pnl(95, True), 4)
        self.assertEqual(run_g1.meter_pnl(95, False), -96)


class TestNotes(unittest.TestCase):
    def test_hold_note(self):
        self.assertEqual(run_g1.parse_hold_note("hold_would_be 6200"), 6200)
        self.assertIsNone(run_g1.parse_hold_note("held"))
        self.assertIsNone(run_g1.parse_hold_note(None))


class TestBuckets(unittest.TestCase):
    def test_run_families(self):
        self.assertEqual(run_g1.bucket_of("2026-07-24T00:40:27+00:00"), "eve")
        self.assertEqual(run_g1.bucket_of("2026-07-24T03:46:26+00:00"), "eve")
        self.assertEqual(run_g1.bucket_of("2026-07-24T14:44:22+00:00"), "morn")
        self.assertEqual(run_g1.bucket_of("2026-07-24T17:35:00+00:00"), "aft")


if __name__ == "__main__":
    unittest.main()
