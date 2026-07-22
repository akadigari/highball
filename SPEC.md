# VANE, the spec

Committed before any build, per the architecture-first rule. The lab
and the bot get built to this document, not to chat.

## Goal

Answer, with receipts, whether a keyless-data weather bot can beat
Kalshi's daily high temperature markets on sim, and if it can, run it
as a live sim desk that knaves can render as a card.

Three questions the lab must answer with numbers:

1. WHERE: which cities are predictable enough to clear the fee hurdle.
2. WHEN: how much accuracy is gained by waiting from the day before to
   the morning of, and what that says about entry timing.
3. EXIT: whether selling into strength beats holding to settlement.

## The honesty up front

The July 18 scout sweep already scored this family (candidate 13,
"Kalshi weather microstructure") a 6/10 PLAUSIBLE with this catch:
plain forecast-following is crowded, public model-vs-market tools
already exist. So vane does not claim the naive edge. The lab measures
it anyway (it is the baseline), but the desk only goes live if the
numbers clear the gates below. A dead verdict still becomes a knaves
card. Dead cards are content.

## Hard limits

- Sim only. Zero real orders. No customer money, ever.
- Keyless public data only: Kalshi public market API, NOAA ACIS,
  Open-Meteo archives, NWS api.weather.gov. Nothing behind a login.
- Plain English everywhere, no em dashes in any file.
- Public wording is "sim", never "paper".
- No hand-typed numbers in anything public: every reported number is
  written by a script into a committed artifact.

## Markets and stations (verified live 2026-07-22)

Settlement is the NWS Daily Climatological Report (CLI product) for a
specific station. Bands are 2 degrees wide with an or-above and an
or-below tail. Band edges move day to day and parity differs by city,
so the lab must use each day's real bands pulled from settled markets,
never an assumed grid. Fees are Kalshi standard quadratic: taker fee
per contract is 0.07 x P x (1-P) rounded up to the cent, maker fee is
25 percent of taker.

| City | Series | Station | ACIS sid | Lat | Lon |
|---|---|---|---|---|---|
| NYC (Central Park) | KXHIGHNY | KNYC | KNYC | 40.779 | -73.969 |
| Denver | KXHIGHDEN | KDEN | KDEN | 39.847 | -104.656 |
| Chicago (Midway) | KXHIGHCHI | KMDW | KMDW | 41.786 | -87.752 |
| Austin (Bergstrom) | KXHIGHAUS | KAUS | KAUS | 30.183 | -97.680 |
| Miami | KXHIGHMIA | KMIA | KMIA | 25.788 | -80.317 |
| Los Angeles (LAX) | KXHIGHLAX | KLAX | KLAX | 33.938 | -118.389 |
| Philadelphia | KXHIGHPHIL | KPHL | KPHL | 39.868 | -75.231 |
| Washington DC | KXHIGHTDC | KDCA | KDCA | 38.847 | -77.034 |
| Las Vegas | KXHIGHTLV | KLAS | KLAS | 36.072 | -115.163 |
| Dallas | KXHIGHTDAL | KDFW | KDFW | 32.898 | -97.019 |
| Boston | KXHIGHTBOS | KBOS | KBOS | 42.361 | -71.010 |
| Seattle | KXHIGHTSEA | KSEA | KSEA | 47.445 | -122.314 |
| Atlanta | KXHIGHTATL | KATL | KATL | 33.630 | -84.442 |
| San Antonio | KXHIGHTSATX | KSAT | KSAT | 29.544 | -98.484 |
| New Orleans | KXHIGHTNOLA | KMSY | KMSY | 29.993 | -90.251 |
| Oklahoma City | KXHIGHTOKC | KOKC | KOKC | 35.389 | -97.601 |

Traps already found and coded around:

- Austin settles on Bergstrom now, not Camp Mabry. The rules text on
  the live market is the truth, not old blog posts.
- Houston daily-high series exist but are not active. Skipped.
- Kalshi prices come back as dollar strings. Parse as strings.
- The CLI climate day is the local calendar day. Forecast maxes are
  computed over local hours 0 to 23 from the station's timezone.
  There is a known one-hour daylight-time wrinkle. Accepted as noise
  at this stage, noted so nobody rediscovers it.

## Phase L: the lab (this build)

Two studies, both from history, both scripted, both committed.

### Study 1, G0 feasibility backtest

For every day from 2024-04-01 to 2026-07-20 where data exists, per
city:

- Forecast: Open-Meteo previous-runs archive at the station point.
  Lead-1 is temperature_2m_previous_day1 (yesterday's run), lead-0 is
  temperature_2m (same-day run), lead-2 for the decay curve. Daily
  max over local hours, rounded to the nearest degree.
- Truth: the settled Kalshi band that resolved yes for that day, plus
  the exact official high from ACIS for error stats.
- The bet: which real band the forecast lands in, and whether that
  band resolved yes.

Reported per city: days, MAE by lead, real-band hit rate by lead,
tail settle rate, summer vs winter split, and the ACIS vs Kalshi
settlement cross-check count.

### Study 2, timing and exit, on real prices

For NYC, Denver, and Miami over the trailing ~60 days (candlestick
retention permitting): pull hourly candles for the forecast band and
the winning band. Measure:

- Sim ROI after taker fees of buying the lead-1 forecast band at
  three entry times: 20:00 local the day before, 09:00 local day of,
  12:00 local day of. Hold to settlement.
- The sell-into-strength variant: same entries, but sell the first
  hour the bid touches 85 cents. Compare to holding.
- The longshot table: the winning band's ask at 20:00 the day before,
  distribution per city. This is the "11 cent Denver" question: how
  often does the eventual winner trade cheap the night before.

### G0 gates (pre-registered, written before any results were seen)

The desk advances to Phase S only if, on Study 1:

- PASS A: at least 2 cities with n >= 200 show lead-1 real-band hit
  rate >= 47 percent (that is breakeven for buying the forecast band
  at an assumed 45 cents plus 2 cents taker fee), OR
- PASS B: at least 2 cities show lead-0 hit rate >= 55 percent AND
  Study 2 shows a morning-of entry still gets average asks of 60
  cents or less.

If neither passes, vane stays a lab, the verdict is written into
RESULTS.md, and the knaves card is born dead with the numbers shown.

## Phase S: snapshots (only if G0 passes)

A GitHub Actions cron, three times a day (early morning, midday,
evening ET), keyless, appends to data/:

- NWS point forecast and Open-Meteo model highs per station.
- Full band list with bid/ask for every active city.
- Yesterday's settlement per city.

G1 gate after 14 days of snapshots: using real captured prices, the
projected EV of the G0-passing entries is positive after taker fees
in at least 3 cities. Then and only then the sim ledger starts.

## Phase B: the sim desk (only if G1 passes)

- Model v1: per-city empirical error distribution of the lead-1 and
  lead-0 forecasts from the lab, converted into a probability for
  every listed band. No learning loop until the simple version has a
  verdict.
- Entry v1: at each snapshot, sim-buy any band where model
  probability minus ask minus taker fee >= 5 cents, sized flat at
  100 sim contracts, max one position per city per day.
- Exit v1, pre-registered: sell when the bid is at or above model
  probability plus 5 cents (the edge is gone), or when the bid is at
  or above 90 cents with more than 4 hours until the high typically
  locks. Otherwise hold to settlement. Every sim exit also logs the
  hold-to-settle counterfactual so the exit rule earns its keep on
  data.
- Ledger: data/ledger.csv, append only, one row per sim action, with
  the quote used, the fee charged, and both outcomes.
- G2 verdict at 300 settled sim bets: net sim P&L after fees > 0.
  Report either way.

## The knaves seat

vane is built receipts-first so knaves can render it without a single
hand-typed number:

- out/gates_status.json: current phase, each gate, pass or fail or
  pending, with the numbers.
- data/ledger.csv once Phase B starts, plus out/heartbeat.json from
  the cron.
- knaves gets cards/vane.yml pointing at those artifacts. Status
  chip: LAB until G0, COLLECTING in Phase S, ALIVE or DEAD after
  verdicts. A dead vane card ships anyway.

## Parked for later phases, on purpose

- Obs sniping (buying nearly-settled bands off 5-minute METAR obs
  before the market reacts). Needs a fast loop and obs feeds, and it
  is the part most likely to be crowded by bots already. Phase 2
  research, not this build.
- The NWS human forecast (NDFD) as a second signal beside the model.
- Polymarket weather wallets as a read-only sharp-flow signal
  (public data is readable from MD even though trading is blocked).
- Any learning loop beyond the empirical error table.

## Lab addendum, 2026-07-22, committed before the extended run

Found while building. Written down before the extended numbers were
seen, so the gates stay honest:

1. The markets endpoint only returns about the last 67 days of
   settled weather markets no matter how you page it. The events
   endpoint pages all the way back to series birth (NYC reaches
   August 2021) and carries the same bands and results nested. The
   lab now reads events. The first short-window run stays in git
   history.
2. The same-day model run reads systematically cold at hot stations
   (Vegas, Austin, Philadelphia, Atlanta in the short window),
   because hourly model values undershoot the true continuous daily
   max. The lab therefore also reports a walk-forward corrected
   forecast: raw forecast plus the trailing 30-day mean error, known
   by the night before, minimum 10 samples, no peeking. The G0 gate
   still judges the RAW lead-1 number exactly as registered. The
   corrected number is evidence for the Phase B model, not a gate.
3. Band parity is not stable per city, so there is no honest way to
   simulate bands for days the exchange did not list. Real bands
   only, which caps the join at the forecast archive's start (early
   2024) rather than the exchange's (2021).
4. Study 2 grows from 3 cities to 5: adds Las Vegas (the
   short-window accuracy leader) and Chicago (a morning-of
   candidate).
5. The retention wall covers market detail too. Event shells go back
   to 2021, but bands and results only attach for about the last 67
   days, and event-scoped queries return empty markets past that.
   Same lesson as the trades firehose: history has to be archived by
   us, starting now. Phase S snapshots are therefore also the
   archiver.
6. Because real-band n >= 200 is unreachable from a cold start, G0
   gets evaluated two ways, both reported: the registered PASS A on
   real bands with its small n stated plainly, and an amended PASS
   A2 on the 2024-04 to 2026-07 formula estimate
   hit_est = P(e = 0) + 0.5 x P(|e| = 1), where e is the official
   ACIS high minus the rounded forecast. The half weight is the
   expected hit under the observed 50/50 band parity mix. The
   formula is validated against the real-band window first and the
   validation gap is printed next to every use. Threshold stays 47
   percent in two or more cities, committed here before the extended
   numbers were computed. ACIS earned truth status: zero
   disagreements with Kalshi settlement across 1072 city-days in the
   retention window.

## Rollout

1. Commit this spec.
2. Build the lab, run both studies, commit results and
   gates_status.json.
3. File the verdict in the wiki and hand knaves its card facts.
4. If G0 passed, build Phase S in a fresh session against this spec.
