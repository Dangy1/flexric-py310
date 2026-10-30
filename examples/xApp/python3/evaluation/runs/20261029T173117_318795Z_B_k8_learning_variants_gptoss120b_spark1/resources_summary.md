# Time and resources - `20261029T173117_318795Z_B_k8_learning_variants_gptoss120b_spark1` (1308 records)

Median seconds per record (mean in brackets). planner = LLM call(s); validate includes the twin dry-run.

| Method | Planner | Validate | Dry-run | Lease wait | Deploy | Ack | Total | Prompt tok | Completion tok |
|---|---|---|---|---|---|---|---|---|---|
| appweaver_tpl | 25.1 (26.2) | 0.0 (4.7) | 0.0 (4.7) | 0.0 (0.1) | 0.0 (0.0) | 2.5 (2.6) | 30.4 (31.2) | 9277.1 | 722.7 |
| appweaver_mem | 26.9 (28.5) | 0.0 (5.7) | 0.0 (5.7) | 0.0 (0.3) | 0.0 (0.0) | 2.0 (2.6) | 32.5 (34.5) | 9554.9 | 784.9 |
| appweaver_guided | 38.2 (46.4) | 0.0 (4.3) | 0.0 (4.3) | 0.0 (0.3) | 0.0 (0.0) | 1.5 (2.1) | 42.5 (51.1) | 11550.8 | 1329.5 |
| appweaver_v2 | 38.0 (46.1) | 0.0 (4.2) | 0.0 (4.2) | 0.0 (0.1) | 0.0 (0.0) | 1.5 (2.1) | 41.4 (50.5) | 13522.6 | 1301.0 |

Host resources over the batch (124268 samples):

| Component | CPU core-seconds | Mean RSS (MiB) |
|---|---|---|
| harness | 169.1 | 141.8 |
| health_probe | 26.3 | 31.6 |
| kpm_bus | 626.2 | 62.7 |
| live_emulator | 335.8 | 4.1 |
| live_ric | 1501.2 | 5.5 |
| mcp_rpc | 113.6 | 94.0 |
| portal_server | 102.1 | 91.8 |
| rapp_runtime | 9.9 | 34.4 |
| twin_emulator | 12.5 | 3.8 |
| twin_ric | 37.5 | 4.7 |
| xapp:kpm_rc_suite | 64.0 | 32.1 |
| xapp:l2_monitor | 6.1 | 39.5 |
| xapp:rc_ctrl | 23.5 | 44.3 |
| xapp:slice_suite | 146.6 | 33.6 |
| xapp:tc_suite | 27.7 | 34.5 |

CPU core-seconds per record, by method and component:

| Method | harness | health_probe | kpm_bus | live_emulator | live_ric | mcp_rpc | portal_server | rapp_runtime | twin_emulator | twin_ric | xapp:kpm_rc_suite | xapp:l2_monitor | xapp:rc_ctrl | xapp:slice_suite | xapp:tc_suite |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| appweaver_tpl | 0.09 | 0.0 | 0.34 | 0.17 | 0.77 | 0.06 | 0.05 | 0.01 | 0.01 | 0.02 | 0.03 | 0.0 | 0.02 | 0.09 | 0.02 |
| appweaver_mem | 0.09 | 0.0 | 0.37 | 0.2 | 0.88 | 0.07 | 0.06 | 0.01 | 0.01 | 0.02 | 0.04 | 0.0 | 0.03 | 0.1 | 0.02 |
| appweaver_guided | 0.12 | 0 | 0.53 | 0.3 | 1.32 | 0.09 | 0.08 | 0.01 | 0.01 | 0.04 | 0.06 | 0.0 | 0.01 | 0.14 | 0.02 |
| appweaver_v2 | 0.12 | 0.0 | 0.53 | 0.29 | 1.3 | 0.09 | 0.08 | 0.01 | 0.01 | 0.03 | 0.05 | 0.0 | 0.01 | 0.12 | 0.02 |
