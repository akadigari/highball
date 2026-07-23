"""The live desk loop. Cron calls this a few times a day.

Each run, per city: snapshot the real board and the live forecasts,
let the engine decide entries and exits by the registered rules,
settle yesterday, and append a training observation for every new
settlement. Everything is appended to committed files; the ledger is
the receipt and the training tape at once.

Sim only. This process never sends an order anywhere. It reads public
market data and writes files.
"""

import csv
import datetime
import json
import os
import sys
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "lab"))
sys.path.insert(0, HERE)
import wx  # noqa: E402
import engine  # noqa: E402

DATA = os.path.join(HERE, "data")
OUT = os.path.join(HERE, "out")
SNAPDIR = os.path.join(DATA, "snapshots")
LEDGER = os.path.join(DATA, "ledger.csv")
POSITIONS = os.path.join(DATA, "positions.json")
FLOG = os.path.join(DATA, "forecast_log.csv")
HISTORY = os.path.join(HERE, "model", "history.csv")
TABLES = os.path.join(HERE, "model", "error_tables.json")

LEDGER_COLS = ["ts", "city", "event_date", "ticker", "action", "price_c",
               "fill_vwap_c", "filled_qty", "qty", "fee_c", "p_model",
               "ev_c", "pnl_taker_c", "pnl_maker_c", "clv_c",
               "phase_label", "note"]


def last_seen_quote(ticker):
    """The last snapshot mid for a ticker, for closing-line grading."""
    try:
        files = sorted(os.listdir(SNAPDIR), reverse=True)[:3]
    except OSError:
        return None
    for fn in files:
        best = None
        with open(os.path.join(SNAPDIR, fn)) as f:
            for line in f:
                try:
                    row = json.loads(line)
                except ValueError:
                    continue
                for board in (row.get("boards") or {}).values():
                    for b in board:
                        if b.get("ticker") == ticker:
                            bid, ask = b.get("bid"), b.get("ask")
                            if bid is not None and ask is not None:
                                best = (bid + ask) / 2
                            elif ask is not None:
                                best = ask
        if best is not None:
            return round(best, 1)
    return None


def utcnow():
    return datetime.datetime.now(datetime.timezone.utc)


def qcents(m, field):
    """Kalshi quote in cents from either dollar strings or int cents."""
    d = m.get(field + "_dollars")
    if d is not None:
        return round(float(d) * 100)
    v = m.get(field)
    return int(v) if v is not None else None


def climate_day_max(hourly, date, tz):
    """Daily max over the CLI climate day. CLI uses local STANDARD time,
    so during daylight saving the day runs 01:00 to 00:59 local."""
    z = ZoneInfo(tz)
    noon = datetime.datetime.fromisoformat(date + "T12:00").replace(tzinfo=z)
    dst = bool(noon.dst())
    lo = date + ("T01:00" if dst else "T00:00")
    d2 = (datetime.date.fromisoformat(date) + datetime.timedelta(days=1)).isoformat()
    hi = (d2 + "T00:59") if dst else (date + "T23:59")
    vals = [v for t, v in hourly if lo <= t <= hi and v is not None]
    return max(vals) if vals else None


def live_forecasts(cfg, today, tomorrow):
    url = ("https://api.open-meteo.com/v1/forecast?latitude=%s&longitude=%s"
           "&hourly=temperature_2m&forecast_days=3&past_days=1"
           "&temperature_unit=fahrenheit&timezone=%s"
           % (cfg["lat"], cfg["lon"], cfg["tz"].replace("/", "%2F")))
    d = wx.fetch(url, fresh=True)
    h = d.get("hourly", {})
    hourly = list(zip(h.get("time", []), h.get("temperature_2m", [])))
    return (climate_day_max(hourly, today, cfg["tz"]),
            climate_day_max(hourly, tomorrow, cfg["tz"]))


def load_positions():
    if os.path.exists(POSITIONS):
        return json.load(open(POSITIONS))
    return []


def save_positions(ps):
    os.makedirs(DATA, exist_ok=True)
    with open(POSITIONS, "w") as f:
        json.dump(ps, f, indent=1)


def append_ledger(row):
    os.makedirs(DATA, exist_ok=True)
    new = not os.path.exists(LEDGER)
    with open(LEDGER, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=LEDGER_COLS)
        if new:
            w.writeheader()
        w.writerow(row)


def phase_label():
    try:
        g = json.load(open(os.path.join(OUT, "gates_status.json")))
        if (g.get("g1") or {}).get("passed"):
            return "counted"
    except Exception:
        pass
    return "training"


def bias_errors(city, lead):
    errs = []
    if os.path.exists(HISTORY):
        with open(HISTORY) as f:
            for r in csv.DictReader(f):
                if r["city"] == city and r["lead"] == lead:
                    errs.append((r["date"], int(r["actual"]) - float(r["forecast"])))
    errs.sort()
    return [e for _, e in errs]


def log_forecast(city, target_date, lead, value):
    """Keep the freshest forecast per (city, date, lead); settle trains on it."""
    rows = []
    if os.path.exists(FLOG):
        rows = [r for r in csv.DictReader(open(FLOG))
                if not (r["city"] == city and r["date"] == target_date and r["lead"] == lead)]
    rows.append({"city": city, "date": target_date, "lead": lead,
                 "forecast": round(value, 2), "ts": utcnow().isoformat(timespec="seconds")})
    with open(FLOG, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["city", "date", "lead", "forecast", "ts"])
        w.writeheader()
        w.writerows(rows)


def train_append(city, date, lead, forecast, actual):
    """One settlement becomes one training observation, once."""
    with open(HISTORY) as f:
        for r in csv.DictReader(f):
            if r["city"] == city and r["date"] == date and r["lead"] == lead:
                return False
    with open(HISTORY, "a", newline="") as f:
        csv.writer(f).writerow([date, city, lead, round(forecast, 2), actual])
    return True


def main():
    now = utcnow()
    tables = json.load(open(TABLES))["cities"]
    positions = load_positions()
    label = phase_label()
    os.makedirs(SNAPDIR, exist_ok=True)
    snap_path = os.path.join(SNAPDIR, now.date().isoformat() + ".jsonl")
    snap_f = open(snap_path, "a")
    opened = closed = settled = trained = 0

    for key, cfg in wx.CITIES.items():
        z = ZoneInfo(cfg["tz"])
        local = now.astimezone(z)
        today = local.date().isoformat()
        tomorrow = (local.date() + datetime.timedelta(days=1)).isoformat()

        try:
            mkts = wx.fetch(wx.BASE + "/markets?series_ticker=%s&status=open&limit=100"
                            % cfg["series"], fresh=True).get("markets", [])
            f_today, f_tomorrow = live_forecasts(cfg, today, tomorrow)
        except RuntimeError as e:
            print(key, "fetch failed:", e, flush=True)
            continue

        boards = {}
        for m in mkts:
            d = wx.ticker_date(m.get("ticker", ""))
            if d in (today, tomorrow):
                boards.setdefault(d, []).append({
                    "ticker": m["ticker"],
                    "lo": m.get("floor_strike"), "hi": m.get("cap_strike"),
                    "bid": qcents(m, "yes_bid"), "ask": qcents(m, "yes_ask")})
        # stamp the model's probability on every band it can price, so
        # snapshots carry everything a Brier score needs at G1
        for target, lead, f_raw in ((today, "d0", f_today), (tomorrow, "d1", f_tomorrow)):
            if f_raw is None or not boards.get(target):
                continue
            f_corr = f_raw + engine.bias(bias_errors(key, lead))
            table = tables[key][lead][engine.season(target)]
            for b in boards[target]:
                b["p"] = round(engine.band_prob(table, f_corr, b.get("lo"), b.get("hi")) * 100, 1)
        snap_f.write(json.dumps({
            "ts": now.isoformat(timespec="seconds"), "city": key,
            "f_today": f_today, "f_tomorrow": f_tomorrow,
            "boards": boards}) + "\n")
        if f_today is not None:
            log_forecast(key, today, "d0", f_today)
        if f_tomorrow is not None:
            log_forecast(key, tomorrow, "d1", f_tomorrow)

        # entries: evening window trades tomorrow, morning window today
        windows = []
        if 19 <= local.hour < 22 and f_tomorrow is not None:
            windows.append((tomorrow, "d1", f_tomorrow))
        if 8 <= local.hour < 10 and f_today is not None:
            windows.append((today, "d0", f_today))
        for target, lead, f_raw in windows:
            if any(p["city"] == key and p["event_date"] == target for p in positions):
                continue
            board = boards.get(target) or []
            if not board:
                continue
            f_corr = f_raw + engine.bias(bias_errors(key, lead))
            table = tables[key][lead][engine.season(target)]
            pick = engine.pick_entry(engine.price_board(table, f_corr, board))
            if pick is None:
                continue
            # fill against the real book, partial fills stay partial
            try:
                ob = wx.orderbook(pick["ticker"])
                vwap, filled = engine.fill_walk(
                    ob["asks"], engine.QTY,
                    limit_price=pick["ask"] + engine.SLIPPAGE_CAP)
                fill_note = lead
            except RuntimeError:
                vwap, filled = float(pick["ask"]), engine.QTY
                fill_note = lead + " book_unavailable_top_fill"
            if filled == 0:
                continue
            fill_c = round(vwap)
            fee = engine.taker_fee_cents(fill_c)
            positions.append({"city": key, "event_date": target,
                              "ticker": pick["ticker"], "ask": pick["ask"],
                              "vwap": fill_c, "qty": filled,
                              "p_model": pick["p_model"],
                              "lead": lead, "status": "open",
                              "ts_open": now.isoformat(timespec="seconds")})
            append_ledger({"ts": now.isoformat(timespec="seconds"), "city": key,
                           "event_date": target, "ticker": pick["ticker"],
                           "action": "OPEN", "price_c": pick["ask"],
                           "fill_vwap_c": vwap, "filled_qty": filled,
                           "qty": engine.QTY, "fee_c": fee,
                           "p_model": pick["p_model"], "ev_c": pick["ev"],
                           "pnl_taker_c": "", "pnl_maker_c": "", "clv_c": "",
                           "phase_label": label, "note": fill_note})
            opened += 1

        # exits on open positions in this city
        by_ticker = {m["ticker"]: m for m in mkts}
        for p in positions:
            if p["city"] != key or p["status"] != "open":
                continue
            m = by_ticker.get(p["ticker"])
            if m is None:
                continue
            bid = qcents(m, "yes_bid")
            f_now = f_today if p["event_date"] == today else f_tomorrow
            lead_now = "d0" if p["event_date"] == today else "d1"
            if f_now is None:
                continue
            f_corr = f_now + engine.bias(bias_errors(key, lead_now))
            table = tables[key][lead_now][engine.season(p["event_date"])]
            p_now = engine.band_prob(table, f_corr, m.get("floor_strike"),
                                     m.get("cap_strike")) * 100
            go, why = engine.should_exit(bid, p_now, local.hour)
            if go:
                try:
                    ob = wx.orderbook(p["ticker"])
                    svwap, sfilled = engine.fill_walk(
                        ob["bids"], p["qty"],
                        limit_price=None)
                except RuntimeError:
                    svwap, sfilled = float(bid), p["qty"]
                if sfilled == 0:
                    continue
                sell_c = round(svwap)
                entry_c = p.get("vwap", p["ask"])
                taker, maker = engine.sell_pnl(entry_c, sell_c)
                p["status"] = "sold"
                p["sell_bid"] = sell_c
                p["sold_qty"] = sfilled
                append_ledger({"ts": now.isoformat(timespec="seconds"), "city": key,
                               "event_date": p["event_date"], "ticker": p["ticker"],
                               "action": "SELL", "price_c": bid,
                               "fill_vwap_c": svwap, "filled_qty": sfilled,
                               "qty": p["qty"],
                               "fee_c": engine.taker_fee_cents(sell_c),
                               "p_model": round(p_now, 1), "ev_c": "",
                               "pnl_taker_c": taker * sfilled,
                               "pnl_maker_c": maker * sfilled, "clv_c": "",
                               "phase_label": label, "note": why})
                closed += 1

    # settle everything whose day is over, then learn from it
    done = []
    acis_cache = {}
    for p in positions:
        key = p["city"]
        cfg = wx.CITIES[key]
        local_today = now.astimezone(ZoneInfo(cfg["tz"])).date().isoformat()
        if p["event_date"] >= local_today:
            continue
        try:
            sm = wx.fetch(wx.BASE + "/markets?series_ticker=%s&status=settled&limit=100"
                          % cfg["series"], fresh=True).get("markets", [])
        except RuntimeError:
            continue
        row = next((m for m in sm if m["ticker"] == p["ticker"]), None)
        if row is None or row.get("result") not in ("yes", "no"):
            continue
        won = row["result"] == "yes"
        entry_c = p.get("vwap", p["ask"])
        taker, maker = engine.entry_pnl(entry_c, won)
        close_mid = last_seen_quote(p["ticker"])
        clv = round(close_mid - entry_c, 1) if close_mid is not None else ""
        if p["status"] == "sold":
            note = "hold_would_be %d" % (taker * p["qty"])
            pnl_t = pnl_m = ""
        else:
            note = "held"
            pnl_t, pnl_m = taker * p["qty"], maker * p["qty"]
        append_ledger({"ts": now.isoformat(timespec="seconds"), "city": key,
                       "event_date": p["event_date"], "ticker": p["ticker"],
                       "action": "SETTLE", "price_c": 100 if won else 0,
                       "fill_vwap_c": entry_c, "filled_qty": p["qty"],
                       "qty": p["qty"], "fee_c": 0, "p_model": p["p_model"],
                       "ev_c": "", "pnl_taker_c": pnl_t, "pnl_maker_c": pnl_m,
                       "clv_c": clv, "phase_label": label, "note": note})
        settled += 1
        done.append(p)
    for p in done:
        positions.remove(p)

    # training: every past forecast that now has an official high
    if os.path.exists(FLOG):
        for r in list(csv.DictReader(open(FLOG))):
            key = r["city"]
            cfg = wx.CITIES[key]
            local_today = now.astimezone(ZoneInfo(cfg["tz"])).date().isoformat()
            if r["date"] >= local_today:
                continue
            if key not in acis_cache:
                try:
                    end = now.date().isoformat()
                    start = (now.date() - datetime.timedelta(days=7)).isoformat()
                    acis_cache[key] = wx.fetch(
                        "https://data.rcc-acis.org/StnData",
                        post_json={"sid": cfg["acis"], "sdate": start,
                                   "edate": end, "elems": "maxt"}, fresh=True)
                    acis_cache[key] = {row[0]: int(row[1])
                                       for row in acis_cache[key].get("data", [])
                                       if row[1] not in ("M", "T")}
                except RuntimeError:
                    acis_cache[key] = {}
            actual = acis_cache[key].get(r["date"])
            if actual is not None:
                if train_append(key, r["date"], r["lead"], float(r["forecast"]), actual):
                    trained += 1

    snap_f.close()
    save_positions(positions)
    os.makedirs(OUT, exist_ok=True)
    ledger_rows = 0
    if os.path.exists(LEDGER):
        ledger_rows = sum(1 for _ in open(LEDGER)) - 1
    with open(os.path.join(OUT, "heartbeat.json"), "w") as f:
        json.dump({"ts": now.isoformat(timespec="seconds"),
                   "opened": opened, "closed": closed, "settled": settled,
                   "trained": trained, "open_positions": len(positions),
                   "ledger_rows": ledger_rows,
                   "snapshot_days": len(os.listdir(SNAPDIR))}, f, indent=1)
    try:
        g = json.load(open(os.path.join(OUT, "gates_status.json")))
        g["phase"] = "S"
        g["snapshot_days"] = len(os.listdir(SNAPDIR))
        with open(os.path.join(OUT, "gates_status.json"), "w") as f:
            json.dump(g, f, indent=1)
    except Exception:
        pass
    print("run done: opened %d, closed %d, settled %d, trained %d, open now %d"
          % (opened, closed, settled, trained, len(positions)))


if __name__ == "__main__":
    main()
