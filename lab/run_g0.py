"""Study 1: the G0 feasibility backtest.

For every day with data, per city: which real Kalshi band did the
archived forecast land in, and did that band settle yes. Gates were
committed in SPEC.md before this script ever ran. The walk-forward
bias-corrected columns were added by the spec addendum, and the gate
still judges the raw lead-1 number.

Writes lab/results.json, lab/RESULTS.md, out/gates_status.json.
"""

import datetime
import json
import os

import wx

START = "2024-04-01"
END = "2026-07-20"

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def warm(date_str):
    return 5 <= int(date_str[5:7]) <= 9


def run_city(key, cfg):
    days = wx.by_day(wx.settled_markets(cfg["series"]))
    acis = wx.acis_maxt(cfg["acis"], START, END)
    om = wx.om_forecast_maxes(cfg["lat"], cfg["lon"], cfg["tz"], START, END)

    rows = []
    anomalies = {"no_single_winner": 0, "acis_mismatch": 0}
    for date, mkts in sorted(days.items()):
        if not (START <= date <= END):
            continue
        winners = [m for m in mkts if m.get("result") == "yes"]
        if len(winners) != 1:
            anomalies["no_single_winner"] += 1
            continue
        winner = winners[0]
        actual = acis.get(date)
        fx = om.get(date, {})
        if actual is not None and not wx.band_contains(winner, actual):
            anomalies["acis_mismatch"] += 1
        row = {"date": date, "actual": actual, "warm": warm(date),
               "winner_is_tail": winner.get("floor_strike") is None or winner.get("cap_strike") is None}
        for lead in ("d0", "d1", "d2"):
            v = fx.get(lead)
            row[lead] = v
            pick = wx.pick_band(mkts, None if v is None else round(v))
            row[lead + "_hit"] = None if (v is None) else (pick is not None and pick.get("result") == "yes")
        rows.append(row)

    # walk-forward bias correction: shift by the trailing 30-day mean
    # error, which was fully known the night before. No peeking.
    rows.sort(key=lambda r: r["date"])
    hist = {"d1": [], "d0": []}
    for r in rows:
        mkts = days[r["date"]]
        for lead in ("d1", "d0"):
            v = r[lead]
            r[lead + "c"] = None
            r[lead + "c_hit"] = None
            if v is None or r["actual"] is None:
                continue
            tail = hist[lead][-30:]
            if len(tail) >= 10:
                cv = v + sum(tail) / len(tail)
                r[lead + "c"] = cv
                pick = wx.pick_band(mkts, round(cv))
                r[lead + "c_hit"] = pick is not None and pick.get("result") == "yes"
            hist[lead].append(r["actual"] - v)
    return rows, anomalies


def stats(rows, lead):
    have = [r for r in rows if r.get(lead + "_hit") is not None]
    hits = [r for r in have if r[lead + "_hit"]]
    errs = [abs(r[lead] - r["actual"]) for r in have if r["actual"] is not None and r[lead] is not None]
    return {
        "n": len(have),
        "hit": round(len(hits) / len(have), 4) if have else None,
        "mae": round(sum(errs) / len(errs), 2) if errs else None,
    }


def main():
    all_results = {}
    for key, cfg in wx.CITIES.items():
        rows, anomalies = run_city(key, cfg)
        city = {"series": cfg["series"], "anomalies": anomalies, "days": len(rows)}
        for lead in ("d1", "d0", "d2", "d1c", "d0c"):
            city[lead] = stats(rows, lead)
        biases = [r["actual"] - r["d1"] for r in rows if r["actual"] is not None and r["d1"] is not None]
        city["d1_bias"] = round(sum(biases) / len(biases), 2) if biases else None
        for label, flt in (("warm", lambda r: r["warm"]), ("cold", lambda r: not r["warm"])):
            sub = [r for r in rows if flt(r)]
            city[label + "_d1_hit"] = stats(sub, "d1")["hit"]
            city[label + "_d1c_hit"] = stats(sub, "d1c")["hit"]
        tails = [r for r in rows if r["winner_is_tail"]]
        city["tail_settle_rate"] = round(len(tails) / len(rows), 4) if rows else None
        all_results[key] = city
        print(key, "days", city["days"], "d1", city["d1"]["hit"], "d1c", city["d1c"]["hit"],
              "d0", city["d0"]["hit"], "d0c", city["d0c"]["hit"], "bias", city["d1_bias"], flush=True)

    # G0 gate, exactly as pre-registered in SPEC.md
    pass_a_cities = [k for k, c in all_results.items()
                     if c["d1"]["n"] >= 200 and c["d1"]["hit"] is not None and c["d1"]["hit"] >= 0.47]
    pass_b_cities = [k for k, c in all_results.items()
                     if c["d0"]["hit"] is not None and c["d0"]["hit"] >= 0.55]
    gates = {
        "updated": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "phase": "LAB",
        "g0": {
            "pass_a": {"rule": ">=2 cities with n>=200 and lead-1 hit >= 0.47",
                       "cities": pass_a_cities, "passed": len(pass_a_cities) >= 2},
            "pass_b": {"rule": ">=2 cities lead-0 hit >= 0.55 AND study-2 morning asks <= 60c",
                       "cities": pass_b_cities,
                       "passed": None,
                       "note": "ask condition filled in by run_timing.py"},
            "verdict": "PENDING",
        },
        "evidence_not_gate": {
            "d1_corrected_cities_over_47": [k for k, c in all_results.items()
                                            if c["d1c"]["hit"] is not None and c["d1c"]["hit"] >= 0.47],
        },
    }
    if gates["g0"]["pass_a"]["passed"]:
        gates["g0"]["verdict"] = "PASS_A"

    os.makedirs(os.path.join(ROOT, "out"), exist_ok=True)
    with open(os.path.join(HERE, "results.json"), "w") as f:
        json.dump(all_results, f, indent=1)
    with open(os.path.join(ROOT, "out", "gates_status.json"), "w") as f:
        json.dump(gates, f, indent=1)

    lines = ["# Study 1 results: can the archived forecast find the winning band",
             "",
             "Window: %s to %s. Bands and winners are real settled Kalshi" % (START, END),
             "markets (walked through the events endpoint, which reaches series",
             "birth). Forecasts are the Open-Meteo previous-runs archive at the",
             "settlement station. d1 is the day-before run (what you knew the",
             "night before). d0 is the same-day run and is an UPPER BOUND on",
             "morning-of skill, because afternoon hours use afternoon runs.",
             "d1c and d0c add the walk-forward trailing 30-day bias correction",
             "(causal, known the night before). The G0 gate judges raw d1 only.",
             "",
             "| City | Days | d1 hit | d1c hit | d0 hit | d0c hit | d1 MAE | d1 bias | Tail rate | Warm d1c | Cold d1c |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    order = sorted(all_results.items(), key=lambda kv: -(kv[1]["d1c"]["hit"] or 0))
    for k, c in order:
        lines.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
            k, c["days"],
            c["d1"]["hit"], c["d1c"]["hit"], c["d0"]["hit"], c["d0c"]["hit"],
            c["d1"]["mae"], c["d1_bias"], c["tail_settle_rate"],
            c["warm_d1c_hit"], c["cold_d1c_hit"]))
    lines += ["",
              "G0 pass A (>=2 cities, n>=200, RAW d1 hit >= 0.47): %s, cities: %s" % (
                  gates["g0"]["pass_a"]["passed"], ", ".join(pass_a_cities) or "none"),
              "G0 pass B candidates (d0 hit >= 0.55): %s (ask check lands in TIMING.md)" % (
                  ", ".join(pass_b_cities) or "none"),
              "Corrected d1 at or over 0.47 (evidence for the Phase B model, not a gate): %s" % (
                  ", ".join(gates["evidence_not_gate"]["d1_corrected_cities_over_47"]) or "none"),
              "",
              "Anomaly counts per city (days skipped for not having exactly one",
              "yes band, and days where the yes band disagrees with the ACIS high):",
              ""]
    for k, c in all_results.items():
        lines.append("- %s: %s" % (k, c["anomalies"]))
    with open(os.path.join(HERE, "RESULTS.md"), "w") as f:
        f.write("\n".join(lines) + "\n")
    print("\nwrote lab/results.json, lab/RESULTS.md, out/gates_status.json")


if __name__ == "__main__":
    main()
