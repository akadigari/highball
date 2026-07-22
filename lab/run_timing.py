"""Study 2: timing and exit, on real candle prices.

NYC, Denver, Miami, trailing days where candles exist. Buys the
day-before forecast band at three entry times, holds or sells into
strength, all after taker fees. Also the longshot table: what the
eventual winner cost the night before.

Writes lab/timing.json, lab/TIMING.md, updates out/gates_status.json.
"""

import datetime
import json
import os
from zoneinfo import ZoneInfo

import wx

CITY_KEYS = ["nyc", "den", "mia"]
LOOKBACK_DAYS = 65
START = "2024-04-01"
END = "2026-07-20"

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def local_ts(date_str, hour, tz, day_offset=0):
    d = datetime.date.fromisoformat(date_str) + datetime.timedelta(days=day_offset)
    return int(datetime.datetime(d.year, d.month, d.day, hour, 0,
                                 tzinfo=ZoneInfo(tz)).timestamp())


def quote_at(cs, ts, side):
    """Close quote of the candle for the hour ending at or just after ts."""
    for k in cs:
        if k.get("end_period_ts", 0) >= ts:
            q = k.get(side) or {}
            return wx.cents(q.get("close_dollars"))
    return None


def first_touch(cs, after_ts, before_ts, level):
    """First hour whose bid closes at or above level, else None."""
    for k in cs:
        t = k.get("end_period_ts", 0)
        if after_ts < t <= before_ts:
            bid = wx.cents((k.get("yes_bid") or {}).get("close_dollars"))
            if bid is not None and bid >= level:
                return bid
    return None


def main():
    out = {}
    for key in CITY_KEYS:
        cfg = wx.CITIES[key]
        days = wx.by_day(wx.settled_markets(cfg["series"]))
        om = wx.om_forecast_maxes(cfg["lat"], cfg["lon"], cfg["tz"], START, END)
        dates = sorted(d for d in days if START <= d <= END)[-LOOKBACK_DAYS:]

        entries = {"eve20": [], "morn9": [], "noon12": []}
        longshot = []
        for date in dates:
            mkts = days[date]
            winners = [m for m in mkts if m.get("result") == "yes"]
            if len(winners) != 1:
                continue
            winner = winners[0]
            f = (om.get(date) or {}).get("d1")
            band = wx.pick_band(mkts, None if f is None else round(f))
            if band is None:
                continue
            t_open = local_ts(date, 0, cfg["tz"], -1)
            t_end = local_ts(date, 23, cfg["tz"])
            cs = wx.candles(cfg["series"], band["ticker"], t_open, t_end + 7200)
            won = band.get("result") == "yes"

            for name, (off, hh) in {"eve20": (-1, 20), "morn9": (0, 9), "noon12": (0, 12)}.items():
                ts = local_ts(date, hh, cfg["tz"], off)
                ask = quote_at(cs, ts, "yes_ask")
                if ask is None or ask >= 99 or ask <= 0:
                    continue
                fee = wx.taker_fee_cents(ask)
                hold = (100 - ask - fee) if won else (-ask - fee)
                touch = first_touch(cs, ts, local_ts(date, 23, cfg["tz"]), 85)
                if touch is not None:
                    sell = touch - ask - fee - wx.taker_fee_cents(touch)
                else:
                    sell = hold
                entries[name].append({"date": date, "ask": ask, "won": won,
                                      "hold": hold, "sell85": sell})

            # what did the eventual winner cost the night before
            wcs = cs if winner["ticker"] == band["ticker"] else wx.candles(
                cfg["series"], winner["ticker"], t_open, t_end + 7200)
            wask = quote_at(wcs, local_ts(date, 20, cfg["tz"], -1), "yes_ask")
            if wask is not None and 0 < wask < 100:
                longshot.append(wask)
            print(key, date, "band", band.get("yes_sub_title"), "won" if won else "lost", flush=True)

        city = {"n_days": len(dates)}
        for name, rows in entries.items():
            n = len(rows)
            city[name] = {
                "n": n,
                "avg_ask": round(sum(r["ask"] for r in rows) / n, 1) if n else None,
                "win_rate": round(sum(1 for r in rows if r["won"]) / n, 3) if n else None,
                "hold_pnl_per_contract": round(sum(r["hold"] for r in rows) / n, 2) if n else None,
                "sell85_pnl_per_contract": round(sum(r["sell85"] for r in rows) / n, 2) if n else None,
            }
        ls = sorted(longshot)
        city["winner_ask_eve"] = {
            "n": len(ls),
            "median": ls[len(ls) // 2] if ls else None,
            "pct_le_15c": round(sum(1 for x in ls if x <= 15) / len(ls), 3) if ls else None,
            "pct_le_25c": round(sum(1 for x in ls if x <= 25) / len(ls), 3) if ls else None,
        }
        out[key] = city
        print(key, json.dumps(city, indent=1), flush=True)

    with open(os.path.join(HERE, "timing.json"), "w") as f:
        json.dump(out, f, indent=1)

    # fill in the ask half of G0 pass B
    gpath = os.path.join(ROOT, "out", "gates_status.json")
    gates = json.load(open(gpath))
    morn_asks = [c["morn9"]["avg_ask"] for c in out.values() if c["morn9"]["avg_ask"] is not None]
    ask_ok = bool(morn_asks) and (sum(morn_asks) / len(morn_asks)) <= 60
    b = gates["g0"]["pass_b"]
    b["avg_morning_ask"] = round(sum(morn_asks) / len(morn_asks), 1) if morn_asks else None
    b["passed"] = bool(b["cities"] and len(b["cities"]) >= 2 and ask_ok)
    if gates["g0"]["verdict"] == "PENDING":
        gates["g0"]["verdict"] = "PASS_B" if b["passed"] else "FAIL"
    with open(gpath, "w") as f:
        json.dump(gates, f, indent=1)

    lines = ["# Study 2: timing and exit on real prices",
             "",
             "Buy the day-before forecast band, after taker fees, per contract,",
             "in cents. sell85 exits the first hour the bid closes at 85 or",
             "better on settlement day, otherwise it rides to settlement.",
             ""]
    for k, c in out.items():
        lines.append("## " + k)
        lines.append("")
        lines.append("| Entry | N | Avg ask | Win rate | Hold P&L | Sell-85 P&L |")
        lines.append("|---|---|---|---|---|---|")
        for name in ("eve20", "morn9", "noon12"):
            e = c[name]
            lines.append("| %s | %s | %s | %s | %s | %s |" % (
                name, e["n"], e["avg_ask"], e["win_rate"],
                e["hold_pnl_per_contract"], e["sell85_pnl_per_contract"]))
        w = c["winner_ask_eve"]
        lines.append("")
        lines.append("Winner's ask at 20:00 the night before: median %sc, %s%% at 15c or less, %s%% at 25c or less (n=%s)." % (
            w["median"],
            None if w["pct_le_15c"] is None else round(w["pct_le_15c"] * 100, 1),
            None if w["pct_le_25c"] is None else round(w["pct_le_25c"] * 100, 1),
            w["n"]))
        lines.append("")
    with open(os.path.join(HERE, "TIMING.md"), "w") as f:
        f.write("\n".join(lines) + "\n")
    print("wrote lab/timing.json, lab/TIMING.md, updated out/gates_status.json")


if __name__ == "__main__":
    main()
