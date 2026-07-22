"""Shared helpers for the vane lab. Keyless public data only.

All network work goes through curl because the framework python on this
machine has no SSL certificates wired up. Every fetch is cached on disk
so reruns are free and the numbers stay reproducible.
"""

import datetime
import hashlib
import json
import math
import os
import subprocess
import time

BASE = "https://api.elections.kalshi.com/trade-api/v2"
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")

# Verified live on 2026-07-22. Settlement station comes from each
# market's rules text. Austin is Bergstrom now, not Camp Mabry.
CITIES = {
    "nyc":  {"series": "KXHIGHNY",    "acis": "KNYC", "lat": 40.779,  "lon": -73.969,  "tz": "America/New_York"},
    "den":  {"series": "KXHIGHDEN",   "acis": "KDEN", "lat": 39.847,  "lon": -104.656, "tz": "America/Denver"},
    "chi":  {"series": "KXHIGHCHI",   "acis": "KMDW", "lat": 41.786,  "lon": -87.752,  "tz": "America/Chicago"},
    "aus":  {"series": "KXHIGHAUS",   "acis": "KAUS", "lat": 30.183,  "lon": -97.680,  "tz": "America/Chicago"},
    "mia":  {"series": "KXHIGHMIA",   "acis": "KMIA", "lat": 25.788,  "lon": -80.317,  "tz": "America/New_York"},
    "lax":  {"series": "KXHIGHLAX",   "acis": "KLAX", "lat": 33.938,  "lon": -118.389, "tz": "America/Los_Angeles"},
    "phl":  {"series": "KXHIGHPHIL",  "acis": "KPHL", "lat": 39.868,  "lon": -75.231,  "tz": "America/New_York"},
    "dc":   {"series": "KXHIGHTDC",   "acis": "KDCA", "lat": 38.847,  "lon": -77.034,  "tz": "America/New_York"},
    "lv":   {"series": "KXHIGHTLV",   "acis": "KLAS", "lat": 36.072,  "lon": -115.163, "tz": "America/Los_Angeles"},
    "dal":  {"series": "KXHIGHTDAL",  "acis": "KDFW", "lat": 32.898,  "lon": -97.019,  "tz": "America/Chicago"},
    "bos":  {"series": "KXHIGHTBOS",  "acis": "KBOS", "lat": 42.361,  "lon": -71.010,  "tz": "America/New_York"},
    "sea":  {"series": "KXHIGHTSEA",  "acis": "KSEA", "lat": 47.445,  "lon": -122.314, "tz": "America/Los_Angeles"},
    "atl":  {"series": "KXHIGHTATL",  "acis": "KATL", "lat": 33.630,  "lon": -84.442,  "tz": "America/New_York"},
    "sat":  {"series": "KXHIGHTSATX", "acis": "KSAT", "lat": 29.544,  "lon": -98.484,  "tz": "America/Chicago"},
    "nola": {"series": "KXHIGHTNOLA", "acis": "KMSY", "lat": 29.993,  "lon": -90.251,  "tz": "America/Chicago"},
    "okc":  {"series": "KXHIGHTOKC",  "acis": "KOKC", "lat": 35.389,  "lon": -97.601,  "tz": "America/Chicago"},
}


def fetch(url, post_json=None, tries=3):
    """GET (or POST json) a url with curl, cache the parsed result forever."""
    os.makedirs(CACHE, exist_ok=True)
    key = hashlib.md5((url + (json.dumps(post_json) if post_json else "")).encode()).hexdigest()
    path = os.path.join(CACHE, key + ".json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    cmd = ["curl", "-s", "--max-time", "90", url]
    if post_json is not None:
        cmd += ["-X", "POST", "-H", "Content-Type: application/json", "-d", json.dumps(post_json)]
    for i in range(tries):
        out = subprocess.run(cmd, capture_output=True, text=True)
        try:
            data = json.loads(out.stdout)
            with open(path, "w") as f:
                json.dump(data, f)
            time.sleep(0.15)
            return data
        except Exception:
            time.sleep(1.5 * (i + 1))
    raise RuntimeError("fetch failed after retries: " + url)


def settled_markets(series):
    """Every settled market in a series, walked through /events.

    The markets endpoint only retains about 67 days. Events page back
    to series birth (NYC reaches August 2021), legacy pre-rename
    tickers included, with bands and results nested.
    """
    out, cursor, pages = [], "", 0
    while True:
        url = (BASE + "/events?series_ticker=" + series +
               "&status=settled&limit=200&with_nested_markets=true")
        if cursor:
            url += "&cursor=" + cursor
        d = fetch(url)
        evs = d.get("events", [])
        for ev in evs:
            date = ticker_date(ev.get("event_ticker", ""))
            for m in ev.get("markets") or []:
                m["_date"] = date
                out.append(m)
        cursor = d.get("cursor") or ""
        pages += 1
        if not cursor or not evs or pages > 40:
            break
    return out


def ticker_date(ticker):
    """KXHIGHNY-26JUL21 or HIGHNY-21AUG06 -> the climate day it names."""
    try:
        part = ticker.split("-")[1]
        return datetime.datetime.strptime(part, "%y%b%d").date().isoformat()
    except Exception:
        return None


def by_day(markets):
    """Group a series' settled markets into {date: [markets]}."""
    days = {}
    for m in markets:
        d = m.get("_date") or ticker_date(m.get("ticker", ""))
        if d:
            days.setdefault(d, []).append(m)
    return days


def pick_band(day_markets, f):
    """The market whose band contains forecast f (a rounded whole degree).

    Mid bands are floor to cap inclusive, like 83 to 84. The top tail
    has no cap and resolves yes when the high is above its floor. The
    bottom tail has no floor and resolves yes when the high is below
    its cap.
    """
    if f is None:
        return None
    top, bot = None, None
    for m in day_markets:
        lo, hi = m.get("floor_strike"), m.get("cap_strike")
        if lo is not None and hi is not None:
            if lo <= f <= hi:
                return m
        elif lo is not None:
            top = m
        elif hi is not None:
            bot = m
    if top is not None and f > top["floor_strike"]:
        return top
    if bot is not None and f < bot["cap_strike"]:
        return bot
    return None


def band_contains(m, actual):
    """Would this market have resolved yes for this official high."""
    lo, hi = m.get("floor_strike"), m.get("cap_strike")
    if lo is not None and hi is not None:
        return lo <= actual <= hi
    if lo is not None:
        return actual > lo
    if hi is not None:
        return actual < hi
    return False


def acis_maxt(sid, sdate, edate):
    """Official daily highs from NOAA ACIS, {date: whole degrees F}."""
    d = fetch("https://data.rcc-acis.org/StnData",
              post_json={"sid": sid, "sdate": sdate, "edate": edate, "elems": "maxt"})
    out = {}
    for row in d.get("data", []):
        try:
            out[row[0]] = int(row[1])
        except (ValueError, IndexError):
            pass
    return out


def om_forecast_maxes(lat, lon, tz, sdate, edate):
    """Archived model forecast highs from Open-Meteo previous runs.

    Per date: d1 is the run from the day before (what you knew the
    night before), d0 is the same-day run (an upper bound on
    morning-of knowledge, because afternoon hours use afternoon runs),
    d2 is two days before. Daily max over local hours.
    """
    chunks = []
    start = datetime.date.fromisoformat(sdate)
    end = datetime.date.fromisoformat(edate)
    a = start
    while a <= end:
        b = min(datetime.date(a.year, 12, 31), end)
        chunks.append((a.isoformat(), b.isoformat()))
        a = b + datetime.timedelta(days=1)
    out = {}
    for s, e in chunks:
        url = ("https://previous-runs-api.open-meteo.com/v1/forecast?latitude=%s&longitude=%s"
               "&hourly=temperature_2m,temperature_2m_previous_day1,temperature_2m_previous_day2"
               "&start_date=%s&end_date=%s&temperature_unit=fahrenheit&timezone=%s"
               % (lat, lon, s, e, tz.replace("/", "%2F")))
        d = fetch(url)
        h = d.get("hourly", {})
        times = h.get("time", [])
        cols = {"d0": h.get("temperature_2m", []),
                "d1": h.get("temperature_2m_previous_day1", []),
                "d2": h.get("temperature_2m_previous_day2", [])}
        for i, t in enumerate(times):
            date = t[:10]
            rec = out.setdefault(date, {"d0": None, "d1": None, "d2": None})
            for k, arr in cols.items():
                v = arr[i] if i < len(arr) else None
                if v is not None and (rec[k] is None or v > rec[k]):
                    rec[k] = v
    return out


def taker_fee_cents(price_cents):
    """Kalshi quadratic taker fee per contract, rounded up to the cent."""
    p = price_cents / 100.0
    return math.ceil(7 * p * (1 - p))


def candles(series, ticker, start_ts, end_ts):
    """Hourly candles for one market. Prices come back as dollar strings."""
    url = (BASE + "/series/" + series + "/markets/" + ticker +
           "/candlesticks?start_ts=%d&end_ts=%d&period_interval=60" % (start_ts, end_ts))
    return fetch(url).get("candlesticks", [])


def cents(dollar_string):
    """'0.1300' -> 13. None stays None."""
    if dollar_string is None:
        return None
    return round(float(dollar_string) * 100)
