# Study 1b: the 840-day formula estimate

Window 2024-04-01 to 2026-07-20, ACIS official highs, Open-Meteo previous runs.
hit_est = P(e=0) + 0.5*P(|e|=1) with e = high minus rounded
forecast. d1 is day-before, d0 same-day (upper bound), c adds the
walk-forward 30-day bias correction. far3/far5 are the longshot
rates: how often the high lands 3+ or 5+ degrees off the forecast.

| City | N | d1 est | d1c est | d0 est | d0c est | d1 MAE | far3 | far5 | Warm d1c | Cold d1c |
|---|---|---|---|---|---|---|---|---|---|---|
| lv | 841 | 0.3662 | 0.4302 | 0.5773 | 0.7702 | 1.88 | 0.2485 | 0.0773 | 0.5517 | 0.3423 |
| mia | 841 | 0.3448 | 0.3845 | 0.4649 | 0.6005 | 2.07 | 0.2925 | 0.1177 | 0.3276 | 0.4054 |
| aus | 841 | 0.173 | 0.3315 | 0.2711 | 0.6462 | 3.03 | 0.541 | 0.2045 | 0.3554 | 0.2883 |
| dal | 841 | 0.2467 | 0.3189 | 0.5351 | 0.6245 | 2.66 | 0.4269 | 0.17 | 0.3143 | 0.3108 |
| sat | 841 | 0.2735 | 0.3183 | 0.5886 | 0.5933 | 2.47 | 0.3757 | 0.1593 | 0.321 | 0.3131 |
| chi | 841 | 0.2354 | 0.3141 | 0.4067 | 0.5764 | 2.66 | 0.4197 | 0.1736 | 0.2891 | 0.3209 |
| lax | 841 | 0.2788 | 0.3135 | 0.5963 | 0.6426 | 2.29 | 0.3579 | 0.1034 | 0.3793 | 0.268 |
| nola | 841 | 0.283 | 0.3129 | 0.3698 | 0.5247 | 2.41 | 0.3841 | 0.1605 | 0.3249 | 0.3052 |
| okc | 841 | 0.2342 | 0.2984 | 0.6112 | 0.6534 | 2.68 | 0.4293 | 0.1641 | 0.2878 | 0.3018 |
| sea | 841 | 0.2218 | 0.2936 | 0.4251 | 0.6179 | 2.74 | 0.4732 | 0.1772 | 0.2772 | 0.3052 |
| dc | 841 | 0.2432 | 0.2912 | 0.434 | 0.5415 | 2.67 | 0.4447 | 0.1688 | 0.309 | 0.2691 |
| phl | 841 | 0.2586 | 0.2894 | 0.4358 | 0.5915 | 2.63 | 0.4245 | 0.1772 | 0.3143 | 0.2613 |
| den | 841 | 0.2658 | 0.2798 | 0.2759 | 0.586 | 2.65 | 0.4185 | 0.1498 | 0.3223 | 0.2365 |
| nyc | 841 | 0.2301 | 0.2792 | 0.4667 | 0.5 | 2.71 | 0.4411 | 0.176 | 0.2666 | 0.2703 |
| atl | 841 | 0.2146 | 0.2786 | 0.2551 | 0.5999 | 3.0 | 0.4863 | 0.2319 | 0.2825 | 0.2579 |
| bos | 841 | 0.2432 | 0.2774 | 0.453 | 0.5187 | 2.73 | 0.4411 | 0.1855 | 0.2772 | 0.2736 |

## Formula validation (formula on warm window vs measured real bands)

- nyc: {"d1": {"real_band": 0.2537, "formula": 0.2532, "gap": -0.0005}, "d0": {"real_band": 0.4328, "formula": 0.4667, "gap": 0.0339}}
- den: {"d1": {"real_band": 0.3433, "formula": 0.3269, "gap": -0.0164}, "d0": {"real_band": 0.5075, "formula": 0.2759, "gap": -0.2316}}
- chi: {"d1": {"real_band": 0.3134, "formula": 0.2584, "gap": -0.055}, "d0": {"real_band": 0.6269, "formula": 0.4067, "gap": -0.2202}}
- aus: {"d1": {"real_band": 0.2985, "formula": 0.2364, "gap": -0.0621}, "d0": {"real_band": 0.2687, "formula": 0.2711, "gap": 0.0024}}
- mia: {"d1": {"real_band": 0.2388, "formula": 0.3114, "gap": 0.0726}, "d0": {"real_band": 0.3582, "formula": 0.4649, "gap": 0.1067}}
- lax: {"d1": {"real_band": 0.209, "formula": 0.3101, "gap": 0.1011}, "d0": {"real_band": 0.597, "formula": 0.5963, "gap": -0.0007}}
- phl: {"d1": {"real_band": 0.3433, "formula": 0.3269, "gap": -0.0164}, "d0": {"real_band": 0.2687, "formula": 0.4358, "gap": 0.1671}}
- dc: {"d1": {"real_band": 0.3731, "formula": 0.301, "gap": -0.0721}, "d0": {"real_band": 0.5672, "formula": 0.434, "gap": -0.1332}}
- lv: {"d1": {"real_band": 0.6119, "formula": 0.4793, "gap": -0.1326}, "d0": {"real_band": 0.3881, "formula": 0.5773, "gap": 0.1892}}
- dal: {"d1": {"real_band": 0.3134, "formula": 0.2571, "gap": -0.0563}, "d0": {"real_band": 0.5672, "formula": 0.5351, "gap": -0.0321}}
- bos: {"d1": {"real_band": 0.4328, "formula": 0.2778, "gap": -0.155}, "d0": {"real_band": 0.5373, "formula": 0.453, "gap": -0.0843}}
- sea: {"d1": {"real_band": 0.1642, "formula": 0.2145, "gap": 0.0503}, "d0": {"real_band": 0.4627, "formula": 0.4251, "gap": -0.0376}}
- atl: {"d1": {"real_band": 0.2687, "formula": 0.2855, "gap": 0.0168}, "d0": {"real_band": 0.2836, "formula": 0.2551, "gap": -0.0285}}
- sat: {"d1": {"real_band": 0.3731, "formula": 0.3165, "gap": -0.0566}, "d0": {"real_band": 0.5224, "formula": 0.5886, "gap": 0.0662}}
- nola: {"d1": {"real_band": 0.3284, "formula": 0.3023, "gap": -0.0261}, "d0": {"real_band": 0.4776, "formula": 0.3698, "gap": -0.1078}}
- okc: {"d1": {"real_band": 0.2985, "formula": 0.2093, "gap": -0.0892}, "d0": {"real_band": 0.5373, "formula": 0.6112, "gap": 0.0739}}

Amended gate A2 (>=2 cities, n>=200, d1 est >= 0.47): see out/gates_status.json
