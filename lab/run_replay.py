"""The held-out replay: proof the desk AI works end to end.

Beliefs frozen at the cutoff (built by model/build_tables.py --cutoff),
then every evening from the cutoff to the end date the engine sees the
real board (every band's candle ask at 20:00 local the night before),
prices it with what it knew at the time, and trades the registered
rules. Settlements grade it. No lookahead anywhere: the distribution
tables predate every trade, and the bias term only uses settlements
that were already public that evening.

Writes lab/replay.json and lab/REPLAY.md.
"""

import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)

import wx  # noqa: E402
import engine  # noqa: E402
from run_timing import local_ts, quote_at  # noqa: E402

CITY_KEYS = ["nyc", "lv", "chi"]
FROM = "2026-06-15"
TO = "2026-07-20"
TABLES = os.path.join(HERE, "replay_model", "error_tables.json")


def load_bias_source():
    """City -> chronological (date, error) list for lead d1, full span.
    The replay slices it per trade date, so it stays causal."""
    out = {}
    with open(os.path.join(ROOT, "model", "history.csv")) as f:
        for r in csv.DictReader(f):
            if r["lead"] != "d1":
                continue
            out.setdefault(r["city"], []).append(
                (r["date"], int(r["actual"]) - float(r["forecast"])))
    for k in out:
        out[k].sort()
    return out


def main():
    tables = json.load(open(TABLES))
    assert tables["meta"]["built_through"] <= FROM, "lookahead in tables"
    bias_src = load_bias_source()

    results = {}
    rows_out = []
    for key in CITY_KEYS:
        cfg = wx.CITIES[key]
        days = wx.by_day(wx.settled_markets(cfg["series"]))
        om = wx.om_forecast_maxes(cfg["lat"], cfg["lon"], cfg["tz"], "2024-04-01", TO)
        entries = []
        candidates = 0
        for date in sorted(days):
            if not (FROM <= date <= TO):
                continue
            mkts = days[date]
            winners = [m for m in mkts if m.get("result") == "yes"]
            f_raw = (om.get(date) or {}).get("d1")
            if len(winners) != 1 or f_raw is None:
                continue
            candidates += 1
            errs = [e for d, e in bias_src.get(key, []) if d < date]
            f_corr = f_raw + engine.bias(errs)
            t_eve = local_ts(date, 20, cfg["tz"], -1)
            board = []
            for m in mkts:
                try:
                    cs = wx.candles(cfg["series"], m["ticker"],
                                    local_ts(date, 0, cfg["tz"], -1),
                                    local_ts(date, 23, cfg["tz"]) + 7200)
                except RuntimeError:
                    continue
                board.append({
                    "ticker": m["ticker"],
                    "lo": m.get("floor_strike"), "hi": m.get("cap_strike"),
                    "ask": quote_at(cs, t_eve, "yes_ask"),
                    "bid": quote_at(cs, t_eve, "yes_bid"),
                    "won": m.get("result") == "yes",
                })
            table = tables["cities"][key]["d1"][engine.season(date)]
            priced = engine.price_board(table, f_corr, board)
            pick = engine.pick_entry(priced)
            if pick is None:
                continue
            won = pick["won"]
            taker, maker = engine.entry_pnl(pick["ask"], won)
            entries.append({"date": date, "ticker": pick["ticker"],
                            "ask": pick["ask"], "p_model": pick["p_model"],
                            "ev": pick["ev"], "won": won,
                            "pnl_taker": taker, "pnl_maker": maker})
            print(key, date, pick["ticker"], "ask", pick["ask"],
                  "p", pick["p_model"], "won" if won else "lost", flush=True)
        n = len(entries)
        wins = sum(1 for e in entries if e["won"])
        results[key] = {
            "candidates": candidates,
            "entries": n,
            "win_rate": round(wins / n, 3) if n else None,
            "avg_ask": round(sum(e["ask"] for e in entries) / n, 1) if n else None,
            "avg_p_model": round(sum(e["p_model"] for e in entries) / n, 1) if n else None,
            "pnl_taker_total": sum(e["pnl_taker"] for e in entries),
            "pnl_maker_total": sum(e["pnl_maker"] for e in entries),
        }
        rows_out += [dict(e, city=key) for e in entries]

    with open(os.path.join(HERE, "replay.json"), "w") as f:
        json.dump({"config": {"cities": CITY_KEYS, "from": FROM, "to": TO,
                              "tables_built_through": tables["meta"]["built_through"]},
                   "cities": results, "entries": rows_out}, f, indent=1)

    lines = ["# The held-out replay",
             "",
             "Beliefs frozen at %s, replayed %s to %s on real full-board" % (
                 tables["meta"]["built_through"], FROM, TO),
             "candle asks at 20:00 local the night before. The engine only",
             "traded when its registered rules fired. Per contract, cents.",
             "",
             "| City | Nights | Entries | Win rate | Avg ask | Avg model P | Taker P&L | Maker P&L |",
             "|---|---|---|---|---|---|---|---|"]
    for k, r in results.items():
        lines.append("| %s | %s | %s | %s | %s | %s | %s | %s |" % (
            k, r["candidates"], r["entries"], r["win_rate"], r["avg_ask"],
            r["avg_p_model"], r["pnl_taker_total"], r["pnl_maker_total"]))
    lines += ["",
              "Reading: if avg model P is close to the realized win rate, the",
              "beliefs are calibrated out of sample. If taker P&L is positive,",
              "the whole loop (forecast, bias, pricing, entry rule, fees)",
              "makes money on days the tables never saw. Small samples stay",
              "small; the verdict clock still starts at G1 per the spec.",
              ""]
    with open(os.path.join(HERE, "REPLAY.md"), "w") as f:
        f.write("\n".join(lines) + "\n")
    print("\nwrote lab/replay.json, lab/REPLAY.md")


if __name__ == "__main__":
    main()
