"""Accuracy tests for the decision core. Run: python3 -m unittest discover tests"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import engine  # noqa: E402


def flat_table(clip=9):
    n = 2 * clip + 1
    return {"p": {str(e): 1.0 / n for e in range(-clip, clip + 1)}}


def spiky_table():
    # 60% exactly right, 15% each side one degree off, 5% two low, 5% two high
    return {"p": {"0": 0.6, "-1": 0.15, "1": 0.15, "-2": 0.05, "2": 0.05}}


class TestFees(unittest.TestCase):
    def test_known_values(self):
        # ceil(7 * p * (1-p)) in cents
        self.assertEqual(engine.taker_fee_cents(50), 2)   # 1.75 -> 2
        self.assertEqual(engine.taker_fee_cents(45), 2)   # 1.7325 -> 2
        self.assertEqual(engine.taker_fee_cents(26), 2)   # 1.3468 -> 2
        self.assertEqual(engine.taker_fee_cents(10), 1)   # 0.63 -> 1
        self.assertEqual(engine.taker_fee_cents(85), 1)   # 0.8925 -> 1
        self.assertEqual(engine.taker_fee_cents(99), 1)   # 0.0693 -> 1


class TestBias(unittest.TestCase):
    def test_needs_minimum_sample(self):
        self.assertEqual(engine.bias([2.0] * 9), 0.0)
        self.assertAlmostEqual(engine.bias([2.0] * 10), 2.0)

    def test_trailing_window(self):
        errs = [10.0] * 100 + [1.0] * 30
        self.assertAlmostEqual(engine.bias(errs), 1.0)


class TestBandProb(unittest.TestCase):
    def test_board_sums_to_one(self):
        t = flat_table()
        f = 80.0
        bands = [{"lo": None, "hi": 77}, {"lo": 77, "hi": 78},
                 {"lo": 79, "hi": 80}, {"lo": 81, "hi": 82},
                 {"lo": 83, "hi": 84}, {"lo": 84, "hi": None}]
        total = sum(engine.band_prob(t, f, b["lo"], b["hi"]) for b in bands)
        self.assertAlmostEqual(total, 1.0, places=6)

    def test_spike_lands_in_own_band(self):
        t = spiky_table()
        # forecast 84, band 83-84 holds e in {-1, 0}: 0.15 + 0.6
        self.assertAlmostEqual(engine.band_prob(t, 84.0, 83, 84), 0.75)
        # band 85-86 holds e in {1, 2}: 0.15 + 0.05
        self.assertAlmostEqual(engine.band_prob(t, 84.0, 85, 86), 0.20)

    def test_tails(self):
        t = spiky_table()
        # or-above with floor 85: high > 85 means e >= 2
        self.assertAlmostEqual(engine.band_prob(t, 84.0, 85, None), 0.05)
        # or-below with cap 83: high < 83 means e <= -2
        self.assertAlmostEqual(engine.band_prob(t, 84.0, None, 83), 0.05)


class TestEntry(unittest.TestCase):
    def test_longshot_filter_blocks_cheap_bands(self):
        board = [{"ticker": "A", "p_model": 30.0, "ask": 8, "bid": 6}]
        self.assertIsNone(engine.pick_entry(board))

    def test_needs_margin_after_fees(self):
        # p 40, ask 34, fee 2: ev 4 < 5, no trade
        board = [{"ticker": "A", "p_model": 40.0, "ask": 34, "bid": 32}]
        self.assertIsNone(engine.pick_entry(board))
        # p 41, ask 34, fee 2: ev 5, trade
        board = [{"ticker": "A", "p_model": 41.0, "ask": 34, "bid": 32}]
        self.assertEqual(engine.pick_entry(board)["ticker"], "A")

    def test_picks_best_ev(self):
        board = [{"ticker": "A", "p_model": 45.0, "ask": 35, "bid": 33},
                 {"ticker": "B", "p_model": 60.0, "ask": 40, "bid": 38}]
        self.assertEqual(engine.pick_entry(board)["ticker"], "B")


class TestExit(unittest.TestCase):
    def test_edge_gone(self):
        yes, why = engine.should_exit(66, 60.0, 15)
        self.assertTrue(yes)
        self.assertEqual(why, "edge_gone")

    def test_hold_when_model_agrees(self):
        yes, _ = engine.should_exit(70, 80.0, 15)
        self.assertFalse(yes)

    def test_harvest_only_early(self):
        self.assertTrue(engine.should_exit(92, 95.0, 9)[0])
        self.assertFalse(engine.should_exit(92, 95.0, 14)[0])


class TestPnl(unittest.TestCase):
    def test_hold_win_and_loss(self):
        taker, maker = engine.entry_pnl(53, True)
        self.assertEqual((taker, maker), (100 - 53 - 2, 100 - 53))
        taker, maker = engine.entry_pnl(53, False)
        self.assertEqual((taker, maker), (-55, -53))

    def test_sell(self):
        taker, maker = engine.sell_pnl(40, 86)
        self.assertEqual(taker, 86 - 40 - 2 - 1)
        self.assertEqual(maker, 46)


if __name__ == "__main__":
    unittest.main()
