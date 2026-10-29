# Time and resources - `20261029T075856_628139Z_C_final_gptoss120b_spark1` (1440 records)

Median seconds per record (mean in brackets). planner = LLM call(s); validate includes the twin dry-run.

| Method | Planner | Validate | Dry-run | Lease wait | Deploy | Ack | Total | Prompt tok | Completion tok |
|---|---|---|---|---|---|---|---|---|---|
| manual_rule | 0.0 (0.0) | 0.0 (0.0) | 0.0 (0.0) | 0.0 (0.0) | 0.0 (0.0) | 6.0 (5.7) | 0.0 (0.0) | -- | -- |
| single_xapp | 0.0 (0.0) | 0.0 (0.0) | 0.0 (0.0) | 0.0 (0.0) | 0.0 (0.0) | 0.5 (0.8) | 0.0 (0.0) | -- | -- |
| llm_blind | 18.6 (18.9) | 0.0 (0.0) | 0.0 (0.0) | 0.0 (0.0) | 0.0 (0.0) | 0.0 (0.2) | 18.6 (18.9) | 337.0 | 602.4 |
| llm_only | 8.5 (9.3) | 0.0 (0.0) | 0.0 (0.0) | 0.0 (0.0) | 0.0 (0.0) | 6.0 (4.7) | 8.5 (9.3) | 484.0 | 292.4 |
| agentcard_no_repair | 19.3 (21.7) | 8.2 (9.4) | 8.2 (9.4) | 0.0 (0.0) | 0.0 (0.0) | 2.5 (2.8) | 26.4 (31.1) | 1870.0 | 677.5 |
| langgraph_agentcard | 19.2 (21.2) | 8.2 (8.7) | 8.2 (8.7) | 0.0 (0.0) | 0.0 (0.0) | 3.0 (2.8) | 26.0 (29.9) | 1870.0 | 652.0 |
| appweaver_tpl | 18.8 (21.0) | 8.2 (8.6) | 8.2 (8.6) | 0.0 (0.0) | 0.0 (0.0) | 2.5 (2.9) | 26.7 (29.6) | 2204.0 | 643.7 |
| appweaver_mem | 20.1 (21.6) | 8.2 (9.3) | 8.2 (9.3) | 0.0 (0.0) | 0.0 (0.0) | 2.5 (2.9) | 27.6 (31.0) | 2397.7 | 664.8 |

Host resources over the batch (71253 samples):

| Component | CPU core-seconds | Mean RSS (MiB) |
|---|---|---|
| harness | 107.0 | 114.7 |
| health_probe | 30.0 | 29.5 |
| kpm_bus | 377.7 | 63.3 |
| live_emulator | 439.1 | 4.0 |
| live_ric | 1953.5 | 5.6 |
| mcp_rpc | 70.0 | 94.6 |
| portal_server | 59.0 | 91.4 |
| twin_emulator | 17.6 | 3.8 |
| twin_ric | 55.2 | 4.7 |
| xapp:kpm_rc_suite | 35.7 | 32.0 |
| xapp:rc_ctrl | 24.0 | 44.4 |
| xapp:slice_suite | 125.5 | 32.2 |
| xapp:tc_suite | 54.6 | 34.2 |

CPU core-seconds per record, by method and component:

| Method | harness | health_probe | kpm_bus | live_emulator | live_ric | mcp_rpc | portal_server | twin_emulator | twin_ric | xapp:kpm_rc_suite | xapp:rc_ctrl | xapp:slice_suite | xapp:tc_suite |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| manual_rule | 0.02 | 0.0 | 0.06 | 0.03 | 0.13 | 0.01 | 0.0 | 0.0 | 0.0 | 0.0 | 0.02 | 0.05 | 0.02 |
| single_xapp | 0.01 | 0 | 0.01 | 0.01 | 0.05 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 0 | 0.0 |
| llm_blind | 0.04 | 0.0 | 0.19 | 0.24 | 1.06 | 0.04 | 0.03 | 0.0 | 0.0 | 0.02 | 0 | 0.0 | 0.0 |
| llm_only | 0.04 | 0 | 0.14 | 0.15 | 0.66 | 0.02 | 0.02 | 0.0 | 0.0 | 0.01 | 0.02 | 0.04 | 0.02 |
| agentcard_no_repair | 0.08 | 0 | 0.36 | 0.4 | 1.8 | 0.06 | 0.05 | 0.03 | 0.09 | 0.03 | 0.01 | 0.15 | 0.07 |
| langgraph_agentcard | 0.09 | 0.0 | 0.34 | 0.41 | 1.83 | 0.06 | 0.05 | 0.03 | 0.08 | 0.03 | 0.01 | 0.16 | 0.07 |
| appweaver_tpl | 0.09 | 0 | 0.34 | 0.41 | 1.84 | 0.06 | 0.05 | 0.02 | 0.06 | 0.03 | 0.02 | 0.13 | 0.05 |
| appweaver_mem | 0.09 | 0 | 0.34 | 0.42 | 1.88 | 0.06 | 0.05 | 0.02 | 0.06 | 0.03 | 0.02 | 0.15 | 0.06 |
