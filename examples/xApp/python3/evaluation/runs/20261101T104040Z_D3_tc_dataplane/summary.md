# D3: AppWeaver TC action on a real bottleneck

Bottleneck tbf 10mbit, child pfifo limit 2000 packets, 4 bulk TCP flows; xApp `xapp_tc_suite.py --profile codel --duration-s 10` (AppWeaver apply-codel) via a private RIC.

| Repeat | Control applied | RTT median before / after (ms) | RTT p95 before / after (ms) | Goodput before / after (Mbit/s) |
|---|---|---|---|---|
| 1 | codel 20 400 rc=0 at 17.13 s | 425.0 / 36.85 | 440.0 / 99.3 | 9.48 / 9.59 |
| 2 | codel 20 400 rc=0 at 17.18 s | 426.0 / 34.85 | 442.0 / 120.0 | 9.57 / 9.59 |
| 3 | codel 20 400 rc=0 at 17.13 s | 416.5 / 35.4 | 436.0 / 80.7 | 9.47 / 9.62 |
| 4 | codel 20 400 rc=0 at 17.12 s | 64.3 / 33.1 | 89.8 / 47.7 | 9.57 / 9.58 |
| 5 | codel 20 400 rc=0 at 17.12 s | 426.0 / 35.15 | 442.0 / 88.7 | 9.48 / 9.61 |
