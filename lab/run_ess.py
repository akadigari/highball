"""Effective sample size receipt for the training tape.

A pure-python mirror of assay/ess.py's Bartlett-taper sweep, the
fleet's reference implementation for the effective-n rule. Kept
dependency-free so the keyless Actions runner can write the receipt.
Reads the settled taker P&L series from data/ledger.csv in time
order, writes lab/ess_g1.json. Deterministic, no network.

Usage: python3 lab/run_ess.py
"""

import csv
import datetime
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

BARTLETT_LADDER = (1, 2, 3, 5, 8, 13, 21, 34)


def autocorrelations(x, max_lag):
    n = len(x)
    mean = sum(x) / n
    c = [v - mean for v in x]
    denom = sum(v * v for v in c)
    out = []
    for lag in range(1, max_lag + 1):
        out.append(sum(c[i] * c[i + lag] for i in range(n - lag)) / denom)
    return out


def bartlett_sweep(x):
    """Per-bandwidth variance inflation and effective n, assay's rules:
    a non-positive vif means pathological negative dependence, which is
    never evidence of less independence, so the ess clips at n."""
    n = len(x)
    bandwidths = [k for k in BARTLETT_LADDER if k <= n // 3]
    rho = autocorrelations(x, max(bandwidths))
    sweep = []
    for b in bandwidths:
        vif = 1.0 + 2.0 * sum((1.0 - lag / (b + 1.0)) * rho[lag - 1]
                              for lag in range(1, b + 1))
        ess = min(n / vif, float(n)) if vif > 0 else float(n)
        sweep.append({"bandwidth": b, "vif": round(vif, 6),
                      "ess": round(ess, 2)})
    return sweep


def settled_pnl():
    rows = list(csv.DictReader(open(os.path.join(ROOT, "data", "ledger.csv"))))
    pnl = [(r["ts"], float(r["pnl_taker_c"])) for r in rows if r["pnl_taker_c"]]
    pnl.sort()
    return [v for _, v in pnl]


def main():
    x = settled_pnl()
    sweep = bartlett_sweep(x)
    esses = [s["ess"] for s in sweep]
    n = len(x)
    receipt = {
        "what": "effective n of the settled taker P&L series, Bartlett ladder",
        "reference": "assay/ess.py, the fleet effective-n rule",
        "written": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "n": n,
        "ess_min": min(esses), "ess_max": max(esses),
        "ratio_min": round(min(esses) / n, 3), "ratio_max": round(max(esses) / n, 3),
        "sweep": sweep,
    }
    with open(os.path.join(HERE, "ess_g1.json"), "w") as f:
        json.dump(receipt, f, indent=1)
    print(json.dumps(receipt, indent=1))
    return receipt


if __name__ == "__main__":
    main()
