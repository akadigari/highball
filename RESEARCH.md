# What the verified sweep found (2026-07-22)

A 101-agent research pass with adversarial verification (claims had to
survive refutation votes). Only surviving claims are listed. Full
detail lives in the wiki and the session transcript; this file keeps
what changes decisions.

## The two links that started this

- weatherbot.bot and the reddit "I backtested 500 weather Kalshi bots"
  thread: NOTHING from either survived verification. No verifiable
  operator, methodology, or track record. The closest analog that was
  fully extracted (a Dev Genius article claiming a bot turned $1,000
  into $24,000) contained zero wallet addresses, zero profile links,
  zero transaction records in 397KB of HTML, and funnels to an SEO
  site. Treat both as unvetted marketing until proven otherwise. Do
  not copy numbers from them into anything.

## Strategy board, ranked by surviving evidence

1. Overdispersion value buying (grade B). The one live Kalshi
   daily-temperature track record found: Oalkhadra, +$1,817 net after
   fees on 1,038 settled trades (Feb 22 to Jul 4 2026), Sharpe 2.2,
   30.3% win rate at average entry 26.7c. Mechanism: the market
   spreads probability too wide (implied uncertainty about 1.27x
   realized), so underpriced sub-50c central buckets are the buy, NOT
   tail longshots. Self-reported but plausible; architecture is a
   replication blueprint (multi-source forecasts, Student-t band
   probabilities, robust Kelly sizing).
   https://github.com/Oalkhadra/prediction-market-trading
2. Maker-only execution (grade A mechanics, verified live). Kalshi
   fees are taker-only, quadratic, peak $0.0175 per contract at 50c.
   NO KXHIGH series is on the maker-fee list (checked 2026-07-22
   against the live fee page, 142 non-standard series, zero weather).
   Resting limit orders trade FREE. The best open backtest (OpenThomas
   below) is breakeven WITH taker fees, so maker execution is the
   difference between zero and positive.
   https://kalshi.com/fee-schedule
3. Longshot FADING, never buying (grade A-). Kalshi contracts under
   10c lose over 60% of stake on average (GWU working paper 2026-001,
   300k+ contracts), bias confirmed inside Climate and Weather
   specifically (29,924 contracts, p=0.000), corroborated by 8,494
   KXHIGHNY markets where 0-10c contracts resolved yes about 1.2% of
   the time. This kills blind Denver longshot buying. Weather-only
   fits put the low-price breakeven near 32c, so cheap bands are less
   toxic than the pooled number but still losers without a signal.
   https://www2.gwu.edu/~forcpgm/2026-001.pdf
4. Naive forecast-following (grade C, evidence negative). OpenThomas
   (21 days, real Kalshi order books, fees in) went -3.8c per
   contract naked, -1.8c with station bias plus market blending, and
   exactly breakeven only after fixing a lookahead leak. Their own
   words: expect losses. Matches our lab: night-before forecast-band
   buying fails in 14 of 16 cities, with Vegas and Chicago the two
   candidate exceptions on 65 real-price days.
   https://github.com/PredictionMarketTrader/openthomas
5. Obs sniping, climatology fades, entry-timing folklore: no
   surviving public evidence either way. Our Study 2 (night-before
   entry beats morning, hold beats sell-85 except Chicago) is close
   to the only receipts-backed timing data anyone has.

## The wallets (all public, all readable from MD)

- Polymarket weather all-time leaderboard: #1 gopfan2 +$350,451 on
  $4.63M volume, #2 aenews2 +$284,462, everyone from #3 down under
  $137k. The viral "$1.11M single London bet" (Hans323) was a gross
  single-bet win; that account's net weather P&L is +$83,290, rank 7.
  Realistic ceiling for the best humans: low-to-mid six figures.
  https://polymarket.com/leaderboard/weather/all/profit
- Bots are already on the board: automatedAItradingbot #12 (+$65,365,
  bio says meteorologist and IT engineer, 3,433 predictions) and
  WeatherTraderBot #16 (+$57,180). A weather specialist, ColdMath, is
  the #6 most-copied wallet on Polymarket. Wallet-follow is a
  legitimate later signal source.

## Open-source references worth stealing from

- suislanchez/polymarket-kalshi-weather-bot (520 stars): GFS 31-member
  ensemble from Open-Meteo to band-exceedance probabilities, trades
  only when model minus market exceeds 8 points, keyless, sim mode.
- ventry089/weatherbot: ECMWF plus HRRR blend to normal-CDF buckets,
  publishes zero P&L claims on purpose, and prescribes the go-live
  gate we are adopting: at least 2 weeks and 50 settled sim trades
  before any verdict counts.

## Mechanics pinned with citations

- Settlement is solely the next-morning NWS Daily Climate Report;
  expiration the first 7 or 8 AM ET after release, pushed to 11 AM ET
  on discrepancies; later NWS revisions ignored.
- CLI uses LOCAL STANDARD TIME: during daylight saving the climate
  day runs 1:00 AM to 12:59 AM local. Phase S must aggregate on the
  LST day, not the calendar day.
- Stations are platform-specific: Kalshi and Polymarket US NYC are
  KNYC Central Park; Chicago is Midway not O'Hare; legacy
  polymarket.com used LaGuardia for NYC and Love Field for Dallas.
  Forecast the station, never the city.
