# Time and resources - `20261028T185959_399193Z_B_k8_final_gptoss120b_spark1` (1962 records)

Median seconds per record (mean in brackets). planner = LLM call(s); validate includes the twin dry-run.

| Method | Planner | Validate | Dry-run | Lease wait | Deploy | Ack | Total | Prompt tok | Completion tok |
|---|---|---|---|---|---|---|---|---|---|
| manual_rule | 0.0 (0.0) | 0.0 (0.0) | 0.0 (0.0) | 0.0 (1.9) | 0.0 (0.0) | 6.0 (5.9) | 0.0 (1.9) | -- | -- |
| single_xapp | 0.0 (0.0) | 0.0 (0.0) | 0.0 (0.0) | 0.0 (1.2) | 0.0 (0.0) | 0.5 (0.9) | 0.0 (1.2) | -- | -- |
| llm_blind | 16.1 (17.5) | 0.0 (0.0) | 0.0 (0.0) | 0.0 (0.0) | 0.0 (0.0) | 0.0 (0.2) | 16.1 (17.5) | 323.2 | 567.0 |
| llm_only | 7.7 (8.5) | 0.0 (0.0) | 0.0 (0.0) | 0.0 (0.5) | 0.0 (0.0) | 6.0 (5.9) | 7.7 (9.0) | 470.2 | 272.9 |
| agentcard_no_repair | 28.7 (29.7) | 0.0 (3.9) | 0.0 (3.9) | 0.0 (0.0) | 0.0 (0.0) | 2.0 (2.4) | 32.8 (33.6) | 8748.7 | 863.1 |
| langgraph_agentcard | 28.9 (30.0) | 0.0 (4.2) | 0.0 (4.2) | 0.0 (0.0) | 0.0 (0.0) | 2.0 (2.6) | 32.8 (34.3) | 8968.9 | 872.8 |

Host resources over the batch (103941 samples):

| Component | CPU core-seconds | Mean RSS (MiB) |
|---|---|---|
| harness | 106.8 | 122.5 |
| health_probe | 39.8 | 32.7 |
| kpm_bus | 345.2 | 64.2 |
| live_emulator | 219.8 | 4.0 |
| live_ric | 1133.9 | 53.5 |
| mcp_rpc | 69.4 | 94.1 |
| ns3 (background, not evaluated) | 43025.1 | 245.5 |
| portal_server | 62.0 | 93.3 |
| rapp_runtime | 7.9 | 32.5 |
| sim_ric (background, not evaluated) | 30.0 | 12.3 |
| twin_emulator | 5.3 | 3.8 |
| twin_ric | 13.1 | 4.2 |
| twin_validation | 0.0 | 3.9 |
| xapp:appweaver_actuator | 122.3 | 20.8 |
| xapp:kpm_rc_suite | 31.8 | 32.0 |
| xapp:l2_monitor | 5.2 | 38.5 |
| xapp:rc_ctrl | 28.9 | 44.3 |
| xapp:slice_suite | 106.6 | 32.6 |
| xapp:tc_suite | 37.0 | 32.6 |

CPU core-seconds per record, by method and component:

| Method | harness | health_probe | kpm_bus | live_emulator | live_ric | mcp_rpc | portal_server | rapp_runtime | twin_emulator | twin_ric | xapp:appweaver_actuator | xapp:kpm_rc_suite | xapp:l2_monitor | xapp:rc_ctrl | xapp:slice_suite | xapp:tc_suite |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| manual_rule | 0.02 | 0 | 0.07 | 0.03 | 0.18 | 0.01 | 0.01 | 0 | 0.0 | 0.0 | 0.02 | 0.0 | 0 | 0.02 | 0.1 | 0.03 |
| single_xapp | 0.01 | 0.0 | 0.02 | 0.01 | 0.06 | 0.01 | 0.0 | 0 | 0.0 | 0.0 | 0.01 | 0.0 | 0 | 0 | 0.0 | 0.01 |
| llm_blind | 0.03 | 0.0 | 0.13 | 0.09 | 0.48 | 0.03 | 0.02 | 0 | 0.0 | 0.0 | 0.05 | 0.01 | 0.0 | 0 | 0.01 | 0.0 |
| llm_only | 0.03 | 0.0 | 0.12 | 0.07 | 0.35 | 0.02 | 0.02 | 0 | 0.0 | 0.0 | 0.04 | 0.01 | 0 | 0.03 | 0.09 | 0.03 |
| agentcard_no_repair | 0.06 | 0.0 | 0.26 | 0.17 | 0.91 | 0.05 | 0.04 | 0.01 | 0.01 | 0.02 | 0.1 | 0.03 | 0.01 | 0.01 | 0.06 | 0.02 |
| langgraph_agentcard | 0.07 | 0.0 | 0.27 | 0.18 | 0.93 | 0.05 | 0.05 | 0.01 | 0.01 | 0.02 | 0.1 | 0.03 | 0.01 | 0.01 | 0.06 | 0.02 |
