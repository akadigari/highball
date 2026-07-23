# Prior art: the ProjectQuant weather lab (found 2026-07-22)

The owner half-remembered a built weather system. The hunt found it:
`~/Claude/Projects/ProjectQuant/prediction-markets/`, a pre-vault
Kalshi daily-high lab calibrated on Austin (KAUS) and Denver (KDEN),
with its own honest handoff note (weather_markets_findings.md). Its
launchd agent com.projectquant.autorun is still loaded today, running
the MLB props fade forward test; that was the fleet page's UNKNOWN.

## What it tested and killed (all four angles)

1. Forecast skill: killed. Its Austin "+7.3%" was an ERA5-vs-station
   data bug; on true KAUS data its Brier TIED the market. Denver fat
   tails are cold-season only and fee-walled.
2. Beating real prices: its +17.8% (p<0.001, all 6 cities) flipped to
   -27.6% when the same bets were re-priced at a different hour. The
   edge was stale thin morning quotes.
3. Latency: killed. Minute-level prices snap to information instantly
   (Denver lag-1 autocorrelation -0.093).
4. Post-peak (evening obs sniping): killed. By the time the high is
   locked, every bucket already sits at ~98c or ~2c.

Its five lessons are adopted as standing highball rules:
timing-robustness on every price claim, realistic ask-side fills,
no strawman benchmarks (compare Brier vs the market), station-exact
settlement data, and distrust of big clean numbers.

## Where highball stands against it

- The timing-robustness check now runs against the held-out replay:
  the same 50 bets stay positive at 17:00, 20:00, 22:00 night-before
  and 09:00 morning-of (+341, +389, +337, +299 cents taker). Sign
  stable, so not the angle-2 artifact. Still n=50, still one warm
  month, still 5-13 points of pick overconfidence to fix.
- What highball does that the old lab did not: prices the WHOLE board
  from an empirical error distribution and only trades EV outliers
  (the old lab bet its forecast bucket), uses 16 cities not 2, has
  the maker-fee zero route documented, and runs a forward desk with
  receipts instead of a backtest-only verdict.
- What the old lab already proved that highball must not re-litigate:
  speed plays and post-peak sniping are closed; cheap tails are
  fee-walled; the NWS forecast is already bias-corrected so naive
  correction is mostly pre-priced.
- Reusable code there: the fat-tail empirical model, the order book
  reader (orderbook_fp with yes_dollars, not orderbook.yes), the
  reprice-lag analyzer, and the exact fee module with its 15c floor
  argument (highball's registered floor is 10c; revisit at G1).

The old lab's verdict was "no retail edge on Kalshi weather." That
verdict stands as the null hypothesis. highball's replay is the first
result that survives the old lab's own checks; the G1 and G2 forward
gates decide whether it is real.
