"""The timing-robustness check, adopted from the old ProjectQuant lab.

Its +17.8% weather "edge" flipped to -27.6% when the same bets were
re-priced at a different hour: the profit was stale thin quotes, not
skill. Rule adopted here: no price-based claim stands unless its sign
survives re-pricing at other hours.

Takes the replay's exact entries and re-prices each at three other
hours (17:00 and 22:00 the night before, 09:00 morning of). Same
band, same settlement, only the entry price moves.

Writes lab/robustness.json and lab/ROBUSTNESS.md.
"""

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

HOURS = {"eve17": (-1, 17), "eve20": (-1, 20), "eve22": (-1, 22), "morn9": (0, 9)}


def main():
    replay = json.load(open(os.path.join(HERE, "replay.json")))
    out = {h: {"n": 0, "pnl_taker": 0, "pnl_maker": 0, "asks": []} for h in HOURS}
    for e in replay["entries"]:
        key = e["city"]
        cfg = wx.CITIES[key]
        date = e["date"]
        try:
            cs = wx.candles(cfg["series"], e["ticker"],
                            local_ts(date, 0, cfg["tz"], -1),
                            local_ts(date, 23, cfg["tz"]) + 7200)
        except RuntimeError:
            continue
        for name, (off, hh) in HOURS.items():
            ask = quote_at(cs, local_ts(date, hh, cfg["tz"], off), "yes_ask")
            if ask is None or not (0 < ask < 99):
                continue
            taker, maker = engine.entry_pnl(ask, e["won"])
            out[name]["n"] += 1
            out[name]["pnl_taker"] += taker
            out[name]["pnl_maker"] += maker
            out[name]["asks"].append(ask)

    lines = ["# Timing robustness: the same bets, re-priced at other hours",
             "",
             "The old lab's rule, now this desk's rule: an edge that changes",
             "sign when you change the measurement hour is an artifact. These",
             "are the replay's exact entries with only the entry hour moved.",
             "",
             "| Entry hour | N priced | Avg ask | Taker P&L | Maker P&L |",
             "|---|---|---|---|---|"]
    for name in ("eve17", "eve20", "eve22", "morn9"):
        r = out[name]
        avg = round(sum(r["asks"]) / len(r["asks"]), 1) if r["asks"] else None
        lines.append("| %s | %s | %s | %s | %s |" % (
            name, r["n"], avg, r["pnl_taker"], r["pnl_maker"]))
        r["avg_ask"] = avg
        del r["asks"]
    signs = {n: (out[n]["pnl_taker"] > 0) for n in HOURS if out[n]["n"] >= 30}
    stable = len(set(signs.values())) == 1 if signs else False
    verdict = ("SIGN STABLE across hours" if stable else
               "SIGN FLIPS across hours: treat the replay number as an artifact until G1 forward data rules")
    lines += ["", "Verdict: " + verdict, ""]
    out["verdict"] = verdict
    with open(os.path.join(HERE, "robustness.json"), "w") as f:
        json.dump(out, f, indent=1)
    with open(os.path.join(HERE, "ROBUSTNESS.md"), "w") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines[6:]))


if __name__ == "__main__":
    main()
