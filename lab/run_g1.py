"""The G1 courtroom. Written and committed before the evidence existed.

Applies the decision rules frozen in SPEC.md addendum 10 to whatever
the desk has recorded so far. Preview mode any day; official mode
(writes decisions into out/gates_status.json) only once 14 or more
snapshot days exist, or with --force.

Usage: python3 lab/run_g1.py [--official] [--force]
"""

import csv
import datetime
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)

import wx  # noqa: E402
import engine  # noqa: E402

MIN_DAYS = 14
GRID = [1.0, 0.8, 0.7, 0.6, 0.5]
MIN_SHRINK_GAIN = 0.02


def bucket_of(ts):
    """Which run family a snapshot timestamp belongs to, by UTC hour."""
    h = int(ts[11:13])
    if h in (0, 1, 2):
        return "eve"
    if h in (3, 4, 5):
        return "eve"
    if h in (13, 14):
        return "morn"
    return "aft"


def brier(rows, w):
    """rows: (p_model 0..1, mid 0..1, won bool). Lower is better."""
    if not rows:
        return None
    s = 0.0
    for p, mid, won in rows:
        used = w * p + (1 - w) * mid
        s += (used - (1.0 if won else 0.0)) ** 2
    return s / len(rows)


def meter_pnl(ask_cents, won):
    """Addendum 9 afternoon meter: buy at ask, taker fee, hold."""
    fee = engine.taker_fee_cents(ask_cents)
    return (100 - ask_cents - fee) if won else (-ask_cents - fee)


def parse_hold_note(note):
    """'hold_would_be 6200' -> 6200, else None."""
    if note and note.startswith("hold_would_be "):
        try:
            return int(note.split()[1])
        except ValueError:
            return None
    return None


def load_ledger():
    path = os.path.join(ROOT, "data", "ledger.csv")
    if not os.path.exists(path):
        return []
    return list(csv.DictReader(open(path)))


def entries_from_ledger(rows):
    """One record per position with its realized outcome, if settled."""
    by_key = {}
    for r in rows:
        by_key.setdefault((r["city"], r["event_date"], r["ticker"]), []).append(r)
    out = []
    for (city, date, ticker), rs in by_key.items():
        opens = [r for r in rs if r["action"] == "OPEN"]
        sells = [r for r in rs if r["action"] == "SELL"]
        settles = [r for r in rs if r["action"] == "SETTLE"]
        if not opens:
            continue
        o = opens[0]
        e = {"city": city, "date": date, "ticker": ticker,
             "lead": (o.get("note") or "").split()[0],
             "fill": float(o.get("fill_vwap_c") or o.get("price_c") or 0),
             "settled": bool(sells or settles), "pnl": None, "clv": None,
             "sold": bool(sells), "sell_price": None, "hold_would_be": None}
        if settles:
            s = settles[0]
            e["clv"] = float(s["clv_c"]) if s.get("clv_c") else None
            e["hold_would_be"] = parse_hold_note(s.get("note"))
            if s.get("pnl_taker_c"):
                e["pnl"] = float(s["pnl_taker_c"])
        if sells:
            sl = sells[0]
            e["sell_price"] = float(sl.get("price_c") or 0)
            if sl.get("pnl_taker_c"):
                e["pnl"] = float(sl["pnl_taker_c"])
        if e["pnl"] is None:
            e["settled"] = False
        out.append(e)
    return out


def truth_for(cities_needed):
    """city -> {date: set of winning tickers} from settled markets."""
    truth = {}
    for key in cities_needed:
        cfg = wx.CITIES[key]
        days = wx.by_day(wx.settled_markets(cfg["series"]))
        truth[key] = {d: {m["ticker"] for m in ms if m.get("result") == "yes"}
                      for d, ms in days.items()}
    return truth


def snapshot_bands(truth):
    """Every stamped band whose outcome is now known."""
    out = []
    for path in sorted(glob.glob(os.path.join(ROOT, "data", "snapshots", "*.jsonl"))):
        for line in open(path):
            try:
                row = json.loads(line)
            except ValueError:
                continue
            city = row.get("city")
            for date, board in (row.get("boards") or {}).items():
                winners = truth.get(city, {}).get(date)
                if not winners:
                    continue
                for b in board:
                    p, bid, ask = b.get("p"), b.get("bid"), b.get("ask")
                    if p is None or bid is None or ask is None or not (0 < ask < 100):
                        continue
                    out.append({"city": city, "date": date,
                                "bucket": bucket_of(row.get("ts", "")),
                                "ticker": b.get("ticker"),
                                "p": p / 100.0, "mid": (bid + ask) / 200.0,
                                "ask": ask,
                                "won": b.get("ticker") in winners})
    return out


def main():
    official = "--official" in sys.argv
    force = "--force" in sys.argv
    snap_days = len(glob.glob(os.path.join(ROOT, "data", "snapshots", "*.jsonl")))
    mode = "OFFICIAL" if (official and (snap_days >= MIN_DAYS or force)) else "PREVIEW"

    ledger = load_ledger()
    entries = entries_from_ledger(ledger)
    settled = [e for e in entries if e["settled"]]
    cities_needed = sorted({e["city"] for e in entries} | set(wx.CITIES))
    truth = truth_for(cities_needed)
    bands = snapshot_bands(truth)
    eve_bands = [(b["p"], b["mid"], b["won"]) for b in bands if b["bucket"] == "eve"]

    D = {}

    # D1 counted clock
    per_city = {}
    for e in settled:
        c = per_city.setdefault(e["city"], {"n": 0, "pnl": 0.0, "clv": [], "neg": False})
        c["n"] += 1
        c["pnl"] += e["pnl"]
        if e["clv"] is not None:
            c["clv"].append(e["clv"])
    qual = [k for k, v in per_city.items() if v["n"] >= 5 and v["pnl"] > 0]
    D["d1_counted_clock"] = {"rule": ">=3 cities with >=5 settled entries and positive net taker P&L",
                             "qualifying_cities": qual, "passed": len(qual) >= 3,
                             "per_city": {k: {"n": v["n"], "pnl_c": round(v["pnl"])} for k, v in per_city.items()}}

    # D2 shrink grid
    scores = {str(w): (round(brier(eve_bands, w), 5) if eve_bands else None) for w in GRID}
    d2 = {"rule": "adopt best w only if >=2% relative Brier gain vs w=1.0",
          "n_bands": len(eve_bands), "scores": scores, "adopted_w": 1.0}
    if eve_bands:
        base = brier(eve_bands, 1.0)
        best_w = min(GRID, key=lambda w: brier(eve_bands, w))
        if best_w != 1.0 and brier(eve_bands, best_w) <= base * (1 - MIN_SHRINK_GAIN):
            d2["adopted_w"] = best_w
    D["d2_shrink"] = d2

    # D3 honesty override: adopted model vs market mid
    if eve_bands:
        model_b = brier(eve_bands, D["d2_shrink"]["adopted_w"])
        market_b = brier(eve_bands, 0.0)
        D["d3_honesty"] = {"rule": "no counted clock if adopted model Brier worse than market mid",
                           "model_brier": round(model_b, 5), "market_brier": round(market_b, 5),
                           "override_fired": model_b > market_b}
        if D["d3_honesty"]["override_fired"]:
            D["d1_counted_clock"]["passed"] = False
    else:
        D["d3_honesty"] = {"rule": "insufficient bands", "override_fired": None}

    # D4 exit exemption at 95c+
    hi_sells = [e for e in settled if e["sold"] and e["sell_price"] is not None
                and e["sell_price"] >= 95 and e["hold_would_be"] is not None]
    sell_total = sum(e["pnl"] for e in hi_sells)
    hold_total = sum(e["hold_would_be"] for e in hi_sells)
    D["d4_exit_95"] = {"rule": "ride bids >=95c if holding beat selling, min 5",
                       "n": len(hi_sells), "sell_total_c": round(sell_total),
                       "hold_total_c": round(hold_total),
                       "adopt_ride": len(hi_sells) >= 5 and hold_total > sell_total}

    # D5 floor
    cheap = [e for e in settled if e["fill"] < 15]
    D["d5_floor"] = {"rule": "raise floor to 15c if sub-15c entries net negative, min 10",
                     "n": len(cheap), "pnl_c": round(sum(e["pnl"] for e in cheap)),
                     "raise_floor": len(cheap) >= 10 and sum(e["pnl"] for e in cheap) < 0}

    # D6 mornings
    d0e = [e for e in settled if e["lead"] == "d0"]
    D["d6_mornings"] = {"rule": "close morning window if d0 entries net negative, min 8",
                        "n": len(d0e), "pnl_c": round(sum(e["pnl"] for e in d0e)),
                        "close_mornings": len(d0e) >= 8 and sum(e["pnl"] for e in d0e) < 0}

    # D7 bench
    benched = []
    for k, v in per_city.items():
        mean_clv = (sum(v["clv"]) / len(v["clv"])) if v["clv"] else None
        if v["n"] >= 6 and v["pnl"] < 0 and mean_clv is not None and mean_clv < 0:
            benched.append(k)
    D["d7_bench"] = {"rule": "bench city: >=6 settled, negative P&L, negative mean CLV",
                     "benched": benched}

    # D8 afternoon meter
    aft = [b for b in bands if b["bucket"] == "aft" and 90 <= b["ask"] <= 99]
    meter_total = sum(meter_pnl(b["ask"], b["won"]) for b in aft)
    D["d8_afternoon_meter"] = {"rule": "report always; armable only if positive with n>=50, owner call",
                               "n": len(aft), "pnl_c_per_contract_sum": round(meter_total),
                               "armable": len(aft) >= 50 and meter_total > 0}

    # D9 maker route report. bid = 2*mid - ask, so spread = 2*(ask - mid).
    sp = [2 * (b["ask"] - b["mid"] * 100) for b in bands if b["bucket"] == "eve"]
    fee_delta = sum(float(r["pnl_maker_c"]) - float(r["pnl_taker_c"])
                    for r in ledger
                    if r.get("pnl_maker_c") and r.get("pnl_taker_c"))
    D["d9_maker"] = {"rule": "report only",
                     "n": len(sp),
                     "avg_spread_c": round(sum(sp) / len(sp), 2) if sp else None,
                     "fee_delta_c": round(fee_delta, 1)}

    verdict = {
        "mode": mode, "snapshot_days": snap_days, "min_days": MIN_DAYS,
        "ran": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "settled_entries": len(settled),
        "decisions": D,
        "passed": bool(D["d1_counted_clock"]["passed"]),
    }

    lines = ["# G1: the pre-registered checkpoint",
             "",
             "Mode: %s (%d of %d snapshot days). Rules frozen in SPEC.md" % (mode, snap_days, MIN_DAYS),
             "addendum 10 before the window filled. Status quo holds wherever",
             "minimum sample sizes are not met.",
             ""]
    for k, v in D.items():
        lines.append("## " + k)
        lines.append("")
        lines.append("```json")
        lines.append(json.dumps(v, indent=1))
        lines.append("```")
        lines.append("")
    lines.append("Counted clock: %s" % ("STARTS" if verdict["passed"] else "does not start yet"))
    with open(os.path.join(HERE, "G1.md"), "w") as f:
        f.write("\n".join(lines) + "\n")

    if mode == "OFFICIAL":
        gpath = os.path.join(ROOT, "out", "gates_status.json")
        gates = json.load(open(gpath))
        gates["g1"] = verdict
        with open(gpath, "w") as f:
            json.dump(gates, f, indent=1)
    print(json.dumps(verdict, indent=1))
    print("\nwrote lab/G1.md" + (" and updated out/gates_status.json" if mode == "OFFICIAL" else " (preview only)"))


if __name__ == "__main__":
    main()
