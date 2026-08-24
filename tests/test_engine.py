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
        board = [{"ticker": "A", "p_model": 50.0, "ask": 14, "bid": 12}]
        self.assertIsNone(engine.pick_entry(board))

    def test_official_rerun_floor_allows_fifteen_cents(self):
        board = [{"ticker": "A", "p_model": 50.0, "ask": 15, "bid": 13}]
        self.assertEqual(engine.pick_entry(board)["ticker"], "A")

    def test_needs_margin_after_fees(self):
        # G1 d2: entries are judged on the shrunk probability,
        # 0.5 x model + 0.5 x mid. mid 33, fee 2, bar is ask+fee+5=41.
        # p 48: used 40.5, ev 4.5 < 5, no trade
        board = [{"ticker": "A", "p_model": 48.0, "ask": 34, "bid": 32}]
        self.assertIsNone(engine.pick_entry(board))
        # p 49: used 41.0, ev 5, trade
        board = [{"ticker": "A", "p_model": 49.0, "ask": 34, "bid": 32}]
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


class TestG1Adoptions(unittest.TestCase):
    """Engine changes adopted at official G1 and its authorized rerun.
    Rules frozen in SPEC.md addendum 10; numbers in gates_status.json g1."""

    def test_used_prob_is_half_model_half_mid(self):
        # d2: w=0.5 beat w=1.0 on Brier 0.06696 vs 0.08881
        self.assertAlmostEqual(engine.used_prob(80.0, 40, 44), 61.0)

    def test_used_prob_without_quotes_stays_model(self):
        self.assertAlmostEqual(engine.used_prob(80.0, None, 44), 80.0)
        self.assertAlmostEqual(engine.used_prob(80.0, 40, None), 80.0)

    def test_entry_judged_on_shrunk_prob(self):
        # raw p clears the old bar but the blend does not: no trade
        board = [{"ticker": "A", "p_model": 44.0, "ask": 34, "bid": 32}]
        self.assertIsNone(engine.pick_entry(board))

    def test_ride_to_settle_at_95(self):
        # d4: holding beat selling 72500c to 69600c across 13 high sells
        self.assertFalse(engine.should_exit(95, 50.0, 9)[0])
        self.assertFalse(engine.should_exit(97, 50.0, 15)[0])
        self.assertTrue(engine.should_exit(94, 50.0, 15)[0])

    def test_evening_only(self):
        # d6: 36 morning entries net -6606c, morning window closed
        self.assertEqual(engine.entry_leads(20), ["d1"])
        self.assertEqual(engine.entry_leads(9), [])
        self.assertEqual(engine.entry_leads(12), [])

    def test_bench(self):
        # D7 benches persist until G2; the rerun added Austin.
        for c in ("den", "lax", "lv", "aus"):
            self.assertTrue(engine.is_benched(c))
        self.assertFalse(engine.is_benched("sea"))

    def test_rerun_raised_longshot_floor(self):
        self.assertEqual(engine.MIN_ASK, 15)


class TestFillWalk(unittest.TestCase):
    def test_single_level_full_fill(self):
        vwap, filled = engine.fill_walk([(30, 500)], 100)
        self.assertEqual((vwap, filled), (30.0, 100))

    def test_walks_levels_and_averages(self):
        vwap, filled = engine.fill_walk([(30, 60), (32, 100)], 100)
        self.assertEqual(filled, 100)
        self.assertAlmostEqual(vwap, (60 * 30 + 40 * 32) / 100)

    def test_partial_fill_stays_partial(self):
        vwap, filled = engine.fill_walk([(30, 25)], 100)
        self.assertEqual((vwap, filled), (30.0, 25))

    def test_limit_price_refuses_chase(self):
        vwap, filled = engine.fill_walk([(30, 60), (40, 100)], 100, limit_price=35)
        self.assertEqual((vwap, filled), (30.0, 60))

    def test_empty_book(self):
        self.assertEqual(engine.fill_walk([], 100), (None, 0))


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
