"""Build the AI's beliefs from history: error tables plus the training log.

For every city and lead, walk the joined ACIS + forecast history in
date order, apply the causal 30-day bias correction, and record the
distribution of what the official high actually did relative to the
corrected forecast. That distribution IS the model: it turns any
forecast into a probability for every band.

Writes model/error_tables.json and model/history.csv. Pass a cutoff
date to build a past version of the beliefs (used by the replay to
prove there is no lookahead).

Usage: python3 build_tables.py [--cutoff YYYY-MM-DD] [--out DIR]
"""

import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "lab"))
import wx  # noqa: E402

START = "2024-04-01"
END = "2026-07-20"
CLIP = 9          # errors are clipped into [-CLIP, CLIP]
SMOOTH = 0.5      # Laplace smoothing so no band ever gets probability zero
TRAIL = 30        # bias window, same as the lab
MIN_BIAS_N = 10


def season(date):
    return "warm" if 5 <= int(date[5:7]) <= 9 else "cold"


def build(cutoff=None):
    tables = {}
    history = []
    for key, cfg in wx.CITIES.items():
        acis = wx.acis_maxt(cfg["acis"], START, END)
        om = wx.om_forecast_maxes(cfg["lat"], cfg["lon"], cfg["tz"], START, END)
        tables[key] = {}
        for lead in ("d1", "d0"):
            pairs = []
            for date in sorted(om):
                if cutoff and date >= cutoff:
                    continue
                a, f = acis.get(date), om[date].get(lead)
                if a is not None and f is not None and START <= date <= END:
                    pairs.append((date, f, a))
            counts = {"warm": {}, "cold": {}}
            ns = {"warm": 0, "cold": 0}
            raw_hist = []
            for date, f, a in pairs:
                history.append((date, key, lead, round(f, 2), a))
                tail = raw_hist[-TRAIL:]
                if len(tail) >= MIN_BIAS_N:
                    corrected = f + sum(tail) / len(tail)
                    e = max(-CLIP, min(CLIP, a - round(corrected)))
                    s = season(date)
                    counts[s][e] = counts[s].get(e, 0) + 1
                    ns[s] += 1
                raw_hist.append(a - f)
            tables[key][lead] = {}
            for s in ("warm", "cold"):
                total = ns[s] + SMOOTH * (2 * CLIP + 1)
                tables[key][lead][s] = {
                    "n": ns[s],
                    "p": {str(e): round((counts[s].get(e, 0) + SMOOTH) / total, 6)
                          for e in range(-CLIP, CLIP + 1)},
                }
        print(key, "d1 warm n", tables[key]["d1"]["warm"]["n"],
              "cold n", tables[key]["d1"]["cold"]["n"], flush=True)
    return tables, sorted(history)


def main():
    cutoff = None
    outdir = HERE
    args = sys.argv[1:]
    while args:
        a = args.pop(0)
        if a == "--cutoff":
            cutoff = args.pop(0)
        elif a == "--out":
            outdir = args.pop(0)
    tables, history = build(cutoff)
    os.makedirs(outdir, exist_ok=True)
    meta = {"built_through": cutoff or END, "start": START, "clip": CLIP,
            "smooth": SMOOTH, "trail": TRAIL}
    with open(os.path.join(outdir, "error_tables.json"), "w") as f:
        json.dump({"meta": meta, "cities": tables}, f, indent=1)
    with open(os.path.join(outdir, "history.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "city", "lead", "forecast", "actual"])
        w.writerows(history)
    print("wrote error_tables.json + history.csv (%d rows) in %s" % (len(history), outdir))


if __name__ == "__main__":
    main()
