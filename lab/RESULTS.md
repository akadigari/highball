# Study 1 results: can the archived forecast find the winning band

Window: 2024-04-01 to 2026-07-20. Bands and winners are real settled Kalshi
markets (walked through the events endpoint, which reaches series
birth). Forecasts are the Open-Meteo previous-runs archive at the
settlement station. d1 is the day-before run (what you knew the
night before). d0 is the same-day run and is an UPPER BOUND on
morning-of skill, because afternoon hours use afternoon runs.
d1c and d0c add the walk-forward trailing 30-day bias correction
(causal, known the night before). The G0 gate judges raw d1 only.

| City | Days | d1 hit | d1c hit | d0 hit | d0c hit | d1 MAE | d1 bias | Tail rate | Warm d1c | Cold d1c |
|---|---|---|---|---|---|---|---|---|---|---|
| lv | 67 | 0.6119 | 0.614 | 0.3881 | 0.7895 | 0.98 | -0.04 | 0.0299 | 0.614 | None |
| nyc | 67 | 0.2537 | 0.4561 | 0.4328 | 0.5439 | 3.35 | -2.92 | 0.3433 | 0.4561 | None |
| okc | 67 | 0.2985 | 0.4561 | 0.5373 | 0.6667 | 2.54 | -1.53 | 0.2388 | 0.4561 | None |
| mia | 67 | 0.2388 | 0.4386 | 0.3582 | 0.614 | 1.88 | 1.55 | 0.0896 | 0.4386 | None |
| aus | 67 | 0.2985 | 0.4211 | 0.2687 | 0.7193 | 2.16 | 1.6 | 0.1194 | 0.4211 | None |
| lax | 67 | 0.209 | 0.4211 | 0.597 | 0.7018 | 2.24 | 1.21 | 0.0746 | 0.4211 | None |
| bos | 67 | 0.4328 | 0.4211 | 0.5373 | 0.6842 | 2.33 | 0.49 | 0.2836 | 0.4211 | None |
| nola | 67 | 0.3284 | 0.4211 | 0.4776 | 0.4912 | 2.42 | 1.11 | 0.1194 | 0.4211 | None |
| den | 67 | 0.3433 | 0.3509 | 0.5075 | 0.6491 | 2.17 | -0.7 | 0.2388 | 0.3509 | None |
| phl | 67 | 0.3433 | 0.3509 | 0.2687 | 0.5965 | 2.04 | 0.75 | 0.1194 | 0.3509 | None |
| chi | 67 | 0.3134 | 0.3333 | 0.6269 | 0.5789 | 2.39 | -0.53 | 0.1791 | 0.3333 | None |
| dc | 67 | 0.3731 | 0.3333 | 0.5672 | 0.5088 | 1.97 | -1.26 | 0.1642 | 0.3333 | None |
| sea | 67 | 0.1642 | 0.3333 | 0.4627 | 0.7018 | 2.82 | 1.28 | 0.1045 | 0.3333 | None |
| sat | 67 | 0.3731 | 0.2456 | 0.5224 | 0.4386 | 2.02 | 1.01 | 0.1642 | 0.2456 | None |
| dal | 67 | 0.3134 | 0.2281 | 0.5672 | 0.6316 | 2.59 | 1.1 | 0.1194 | 0.2281 | None |
| atl | 67 | 0.2687 | 0.2281 | 0.2836 | 0.5088 | 2.46 | 1.13 | 0.0746 | 0.2281 | None |

G0 pass A (>=2 cities, n>=200, RAW d1 hit >= 0.47): False, cities: none
G0 pass B candidates (d0 hit >= 0.55): chi, lax, dc, dal (ask check lands in TIMING.md)
Corrected d1 at or over 0.47 (evidence for the Phase B model, not a gate): lv

Anomaly counts per city (days skipped for not having exactly one
yes band, and days where the yes band disagrees with the ACIS high):

- nyc: {'no_single_winner': 0, 'acis_mismatch': 0}
- den: {'no_single_winner': 0, 'acis_mismatch': 0}
- chi: {'no_single_winner': 0, 'acis_mismatch': 0}
- aus: {'no_single_winner': 0, 'acis_mismatch': 0}
- mia: {'no_single_winner': 0, 'acis_mismatch': 0}
- lax: {'no_single_winner': 0, 'acis_mismatch': 0}
- phl: {'no_single_winner': 0, 'acis_mismatch': 0}
- dc: {'no_single_winner': 0, 'acis_mismatch': 0}
- lv: {'no_single_winner': 0, 'acis_mismatch': 0}
- dal: {'no_single_winner': 0, 'acis_mismatch': 0}
- bos: {'no_single_winner': 0, 'acis_mismatch': 0}
- sea: {'no_single_winner': 0, 'acis_mismatch': 0}
- atl: {'no_single_winner': 0, 'acis_mismatch': 0}
- sat: {'no_single_winner': 0, 'acis_mismatch': 0}
- nola: {'no_single_winner': 0, 'acis_mismatch': 0}
- okc: {'no_single_winner': 0, 'acis_mismatch': 0}
