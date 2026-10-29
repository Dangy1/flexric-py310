# Time and resources - `20261028T084337_250177Z_A_final_gptoss120b_spark1` (1500 records)

Median seconds per record (mean in brackets). planner = LLM call(s); validate includes the twin dry-run.

| Method | Planner | Validate | Dry-run | Lease wait | Deploy | Ack | Total | Prompt tok | Completion tok |
|---|---|---|---|---|---|---|---|---|---|
| manual_rule | 0.0 (0.0) | 0.0 (0.0) | 0.0 (0.0) | 0.0 (4.1) | 0.0 (0.0) | 6.0 (4.8) | 0.0 (4.1) | -- | -- |
| single_xapp | 0.0 (0.0) | 0.0 (0.0) | 0.0 (0.0) | 0.0 (2.7) | 0.0 (0.0) | 0.5 (1.2) | 0.0 (2.7) | -- | -- |
| llm_blind | 15.1 (16.4) | 0.0 (0.0) | 0.0 (0.0) | 0.0 (0.3) | 0.0 (0.0) | 0.0 (0.1) | 15.3 (16.7) | -- | -- |
| llm_only | 7.6 (8.4) | 0.0 (0.0) | 0.0 (0.0) | 0.0 (1.2) | 0.0 (0.0) | 6.0 (5.3) | 7.6 (9.6) | -- | -- |
| agentcard_no_repair | 18.9 (20.0) | 8.2 (9.6) | 8.2 (9.6) | 0.0 (0.7) | 0.0 (0.0) | 3.0 (2.8) | 26.5 (30.4) | -- | -- |
| langgraph_agentcard | 19.3 (20.6) | 8.2 (9.8) | 8.2 (9.8) | 0.0 (0.5) | 0.0 (0.0) | 3.0 (2.9) | 27.3 (31.0) | -- | -- |

Host resources over the batch (21442 samples):

| Component | CPU core-seconds | Mean RSS (MiB) |
|---|---|---|
| harness | 57.4 | 123.6 |
| health_probe | 6.2 | 37.4 |
| kpm_bus | 74.8 | 64.7 |
| live_emulator | 89.2 | 4.1 |
| live_ric | 408.0 | 82.2 |
| mcp_rpc | 16.3 | 94.1 |
| ns3 | 12733.3 | 246.4 |
| portal_server | 14.4 | 91.3 |
| sim_ric | 7.7 | 12.6 |
| twin_emulator | 3.4 | 3.8 |
| twin_ric | 8.6 | 4.6 |
| twin_validation | 134.9 | 74.4 |
| xapp:appweaver_actuator | 35.7 | 21.0 |
| xapp:kpm_rc_suite | 6.9 | 32.1 |
| xapp:l2_monitor | 0.1 | 22.6 |
| xapp:rc_ctrl | 5.5 | 44.2 |
| xapp:slice_suite | 43.8 | 33.6 |
| xapp:tc_suite | 11.7 | 31.6 |
