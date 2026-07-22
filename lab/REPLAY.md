# The held-out replay

Beliefs frozen at 2026-06-15, replayed 2026-06-15 to 2026-07-20 on real full-board
candle asks at 20:00 local the night before. The engine only
traded when its registered rules fired. Per contract, cents.

| City | Nights | Entries | Win rate | Avg ask | Avg model P | Taker P&L | Maker P&L |
|---|---|---|---|---|---|---|---|
| nyc | 36 | 15 | 0.533 | 36.9 | 57.7 | 221 | 247 |
| lv | 36 | 19 | 0.316 | 29.4 | 44.8 | 9 | 41 |
| chi | 36 | 16 | 0.375 | 26.0 | 44.4 | 159 | 184 |

Reading: if avg model P is close to the realized win rate, the
beliefs are calibrated out of sample. If taker P&L is positive,
the whole loop (forecast, bias, pricing, entry rule, fees)
makes money on days the tables never saw. Small samples stay
small; the verdict clock still starts at G1 per the spec.

