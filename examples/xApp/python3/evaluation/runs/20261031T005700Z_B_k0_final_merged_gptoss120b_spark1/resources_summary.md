# Time and resources - `20261031T005700Z_B_k0_final_merged_gptoss120b_spark1` (1962 records)

Median seconds per record (mean in brackets). planner = LLM call(s); validate includes the twin dry-run.

| Method | Planner | Validate | Dry-run | Lease wait | Deploy | Ack | Total | Prompt tok | Completion tok |
|---|---|---|---|---|---|---|---|---|---|
| manual_rule | 0.0 (0.0) | 0.0 (0.0) | 0.0 (0.0) | 0.0 (1.9) | 0.0 (0.0) | 6.0 (5.3) | 0.0 (1.9) | -- | -- |
| single_xapp | 0.0 (0.0) | 0.0 (0.0) | 0.0 (0.0) | 0.0 (1.2) | 0.0 (0.0) | 0.5 (0.9) | 0.0 (1.2) | -- | -- |
| llm_blind | 14.8 (15.8) | 0.0 (0.0) | 0.0 (0.0) | 0.0 (0.3) | 0.0 (0.0) | 0.0 (0.1) | 14.9 (16.1) | 323.2 | 515.8 |
| llm_only | 7.2 (7.9) | 0.0 (0.0) | 0.0 (0.0) | 0.0 (0.6) | 0.0 (0.0) | 6.0 (5.3) | 7.2 (8.5) | 470.2 | 252.4 |
| agentcard_no_repair | 32.0 (33.1) | 0.0 (4.7) | 0.0 (4.7) | 0.0 (0.0) | 0.0 (0.0) | 2.0 (2.4) | 35.4 (37.9) | 24569.5 | 746.7 |
| langgraph_agentcard | 32.9 (33.8) | 0.0 (4.3) | 0.0 (4.3) | 0.0 (0.1) | 0.0 (0.0) | 2.5 (2.4) | 36.2 (38.3) | 25020.8 | 768.1 |

Host resources over the batch (297145 samples):

| Component | CPU core-seconds | Mean RSS (MiB) |
|---|---|---|
| harness | 440.8 | 126.4 |
| health_probe | 108.4 | 29.4 |
| kpm_bus | 1558.9 | 63.1 |
| live_emulator | 1286.1 | 4.1 |
| live_ric | 5736.2 | 5.6 |
| mcp_rpc | 286.1 | 94.2 |
| portal_server | 249.9 | 91.8 |
| rapp_runtime | 17.8 | 34.0 |
| twin_emulator | 39.5 | 3.8 |
| twin_ric | 121.0 | 4.5 |
| xapp:kpm_rc_suite | 151.6 | 32.1 |
| xapp:l2_monitor | 9.9 | 38.4 |
| xapp:rc_ctrl | 80.4 | 44.3 |
| xapp:slice_suite | 429.3 | 32.8 |
| xapp:tc_suite | 127.6 | 33.8 |

CPU core-seconds per record, by method and component:

| Method | harness | health_probe | kpm_bus | live_emulator | live_ric | mcp_rpc | portal_server | rapp_runtime | twin_emulator | twin_ric | xapp:kpm_rc_suite | xapp:l2_monitor | xapp:rc_ctrl | xapp:slice_suite | xapp:tc_suite |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| manual_rule | 0.03 | 0.0 | 0.09 | 0.07 | 0.31 | 0.01 | 0.01 | 0 | 0.0 | 0.0 | 0.0 | 0 | 0.02 | 0.11 | 0.03 |
| single_xapp | 0.01 | 0 | 0.03 | 0.03 | 0.15 | 0.0 | 0.0 | 0 | 0.0 | 0.0 | 0.0 | 0 | 0 | 0.0 | 0.01 |
| llm_blind | 0.05 | 0.0 | 0.17 | 0.17 | 0.77 | 0.03 | 0.03 | 0 | 0.0 | 0.0 | 0.02 | 0 | 0.0 | 0.03 | 0.0 |
| llm_only | 0.05 | 0.0 | 0.15 | 0.13 | 0.58 | 0.02 | 0.02 | 0 | 0.0 | 0.0 | 0.01 | 0 | 0.02 | 0.1 | 0.03 |
| agentcard_no_repair | 0.08 | 0.0 | 0.41 | 0.45 | 2.03 | 0.07 | 0.06 | 0.01 | 0.01 | 0.03 | 0.04 | 0.0 | 0.01 | 0.1 | 0.03 |
| langgraph_agentcard | 0.09 | 0.0 | 0.42 | 0.44 | 2.01 | 0.07 | 0.06 | 0.01 | 0.01 | 0.03 | 0.04 | 0.0 | 0.01 | 0.09 | 0.03 |
