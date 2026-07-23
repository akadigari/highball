# Timing robustness: the same bets, re-priced at other hours

The old lab's rule, now this desk's rule: an edge that changes
sign when you change the measurement hour is an artifact. These
are the replay's exact entries with only the entry hour moved.

| Entry hour | N priced | Avg ask | Taker P&L | Maker P&L |
|---|---|---|---|---|
| eve17 | 50 | 31.4 | 341 | 429 |
| eve20 | 50 | 30.6 | 389 | 472 |
| eve22 | 50 | 31.6 | 337 | 421 |
| morn9 | 50 | 32.4 | 299 | 380 |

Verdict: SIGN STABLE across hours

