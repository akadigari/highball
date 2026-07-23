<h1 align="center">H I G H B A L L</h1>

<p align="center"><b>the weather desk</b></p>

<p align="center">An AI in training. It learns how wrong forecasts run at 16 weather stations,<br>prices every Kalshi daily-high band from what it has learned,<br>and trades the gaps. In sim. Always in sim.</p>

<p align="center"><sub>zero api keys · zero repo secrets · zero real orders · every number below traces to a committed file</sub></p>

<br>

> Everyone shows you their winners.
> This repo shows you the ledger.

<br>

## three questions, answered with receipts

### WHERE
##### the famous cities are crowded. NYC and Miami overprice the obvious band and you lose. The money hid in the boring cities: Vegas paid +7.9c a contract after fees, Chicago +2.1c, on 65 nights of real prices. <sub>[lab/TIMING.md](lab/TIMING.md)</sub>

### WHEN
##### the night before, around 8pm local. By morning the market has already eaten the overnight model runs and raised its prices faster than the forecast got better. Morning entries lost in all five cities tested. <sub>[lab/TIMING.md](lab/TIMING.md)</sub>

### EXIT
##### hold to settlement. Selling into strength at 85c gave up more than it saved everywhere except Chicago. The registered exit only fires when the market's bid passes the model's own probability. <sub>[SPEC.md](SPEC.md)</sub>

<br>

## the proof

Beliefs were frozen on June 14. The desk then traded June 15 through July 20, days it had never seen, against real full-board prices.

<h3 align="center">+389 cents on 50 unseen trades</h3>
<p align="center">all three test cities non-negative · <b>+472</b> on the zero-maker-fee column</p>
<p align="center"><sub>and the sign survives re-pricing the same bets at 17:00, 20:00, 22:00 and 09:00.<br>That check exists because an earlier lab's +17.8% "edge" died by it. This one didn't.<br><a href="lab/REPLAY.md">REPLAY</a> · <a href="lab/ROBUSTNESS.md">ROBUSTNESS</a> · <a href="PRIORART.md">PRIOR ART</a></sub></p>

Fifty trades is a spark, not a verdict. The registered gates decide: G1 after 14 days of live snapshots, G2 at 300 counted trades. If it dies at a gate, the repo stays up with the numbers showing. Dead honestly beats alive vaguely.

<br>

## what it refuses to do

- buy anything under 10 cents. Cheap longshots lose over 60% of stake on Kalshi; that is measured, not vibes
- chase a fill more than 5 cents past its decision price
- claim maker fills it cannot prove. The maker column only counts the fee difference, never queue position
- trust its own backtest. Every price claim gets re-priced at other hours before it is believed

## how the sim stays honest

Fills walk the live order book level by level, partial fills stay partial, and the slippage sits in its own ledger column. Fees are the exact Kalshi formula, unit tested. Every settlement row records the closing line it beat or missed. Every snapshot stamps the model's probability next to the market's bid and ask, so anyone can score the model against the market later. Beliefs are files with a build date; the code cannot see past them.

## the training loop

Every settlement becomes a training row: what the forecast said, what the sky did. The error tables (26,912 station-days and counting) and a rolling 30-day bias term update on the next run. The desk gets a little less wrong every day, and [model/history.csv](model/history.csv) is the tape of it learning.

<br>

## the receipts, mapped

```
SPEC.md            the rules, written before the results existed. 8 addenda
PRIORART.md        the older lab that killed four weather edges. its checks now run here
lab/RESULTS.md     840 days: the naive night-before trade is dead everywhere
lab/TIMING.md      65 nights of real prices: where, when, exit
lab/REPLAY.md      the held-out proof
lab/ROBUSTNESS.md  the same bets at four other hours. sign stable
out/gates_status.json   what phase this desk is in, machine readable
data/ledger.csv    every sim action, fills, fees, slippage, closing line
data/snapshots/    the band archive Kalshi doesn't keep (they serve ~67 days, this keeps all)
```

## run it

```bash
python3 -m unittest discover tests    # 19 checks on the decision core
python3 desk.py                       # one live cycle: snapshot, decide, settle, learn
```

The cloud does the rest: four runs a day on a plain GitHub Actions cron. No keys to add, no secrets to configure, nothing to pay. Fork it and it runs.

<br>

<p align="center"><sub>a desk of the <b>knaves</b> table · sim only · not advice · the graveyard gets equal billing</sub></p>
