# Study 1 results: can the archived forecast find the winning band

Window: 2024-04-01 to 2026-07-20. Bands and winners are real settled Kalshi
markets. Forecasts are the Open-Meteo previous-runs archive at the
settlement station. d1 is the day-before run (what you knew the
night before). d0 is the same-day run and is an UPPER BOUND on
morning-of skill, because afternoon hours use afternoon runs.

| City | Days | d1 hit | d1 MAE | d0 hit | d0 MAE | d2 hit | Tail rate | Warm d1 | Cold d1 |
|---|---|---|---|---|---|---|---|---|---|
| lv | 67 | 0.6119 | 0.98 | 0.3881 | 1.3 | 0.4179 | 0.0299 | 0.6119 | None |
| bos | 67 | 0.4328 | 2.33 | 0.5373 | 1.02 | 0.194 | 0.2836 | 0.4328 | None |
| dc | 67 | 0.3731 | 1.97 | 0.5672 | 1.1 | 0.1791 | 0.1642 | 0.3731 | None |
| sat | 67 | 0.3731 | 2.02 | 0.5224 | 1.06 | 0.194 | 0.1642 | 0.3731 | None |
| den | 67 | 0.3433 | 2.17 | 0.5075 | 1.41 | 0.403 | 0.2388 | 0.3433 | None |
| phl | 67 | 0.3433 | 2.04 | 0.2687 | 2.14 | 0.209 | 0.1194 | 0.3433 | None |
| nola | 67 | 0.3284 | 2.42 | 0.4776 | 1.32 | 0.1343 | 0.1194 | 0.3284 | None |
| chi | 67 | 0.3134 | 2.39 | 0.6269 | 1.1 | 0.3134 | 0.1791 | 0.3134 | None |
| dal | 67 | 0.3134 | 2.59 | 0.5672 | 1.24 | 0.209 | 0.1194 | 0.3134 | None |
| aus | 67 | 0.2985 | 2.16 | 0.2687 | 1.95 | 0.2687 | 0.1194 | 0.2985 | None |
| okc | 67 | 0.2985 | 2.54 | 0.5373 | 1.1 | 0.1343 | 0.2388 | 0.2985 | None |
| atl | 67 | 0.2687 | 2.46 | 0.2836 | 1.98 | 0.209 | 0.0746 | 0.2687 | None |
| nyc | 67 | 0.2537 | 3.35 | 0.4328 | 1.78 | 0.2537 | 0.3433 | 0.2537 | None |
| mia | 67 | 0.2388 | 1.88 | 0.3582 | 1.35 | 0.4478 | 0.0896 | 0.2388 | None |
| lax | 67 | 0.209 | 2.24 | 0.597 | 0.83 | 0.2836 | 0.0746 | 0.209 | None |
| sea | 67 | 0.1642 | 2.82 | 0.4627 | 1.15 | 0.2985 | 0.1045 | 0.1642 | None |

G0 pass A (>=2 cities, n>=200, d1 hit >= 0.47): False, cities: none
G0 pass B candidates (d0 hit >= 0.55): chi, lax, dc, dal (ask check in TIMING.md)

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
