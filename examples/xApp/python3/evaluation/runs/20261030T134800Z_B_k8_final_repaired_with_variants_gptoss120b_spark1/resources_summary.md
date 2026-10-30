# Time and resources - `20261030T134800Z_B_k8_final_repaired_with_variants_gptoss120b_spark1` (3270 records)

Median seconds per record (mean in brackets). planner = LLM call(s); validate includes the twin dry-run.

| Method | Planner | Validate | Dry-run | Lease wait | Deploy | Ack | Total | Prompt tok | Completion tok |
|---|---|---|---|---|---|---|---|---|---|
| manual_rule | 0.0 (0.0) | 0.0 (0.0) | 0.0 (0.0) | 0.0 (1.9) | 0.0 (0.0) | 6.0 (5.5) | 0.0 (1.9) | -- | -- |
| single_xapp | 0.0 (0.0) | 0.0 (0.0) | 0.0 (0.0) | 0.0 (1.2) | 0.0 (0.0) | 0.5 (0.9) | 0.0 (1.2) | -- | -- |
| llm_blind | 16.1 (17.5) | 0.0 (0.0) | 0.0 (0.0) | 0.0 (0.0) | 0.0 (0.0) | 0.0 (0.2) | 16.1 (17.5) | 323.2 | 567.1 |
| llm_only | 7.7 (8.4) | 0.0 (0.0) | 0.0 (0.0) | 0.0 (0.5) | 0.0 (0.0) | 6.0 (5.7) | 7.7 (8.9) | 470.2 | 270.3 |
| agentcard_no_repair | 28.6 (29.6) | 0.0 (4.0) | 0.0 (4.0) | 0.0 (0.0) | 0.0 (0.0) | 2.0 (2.3) | 32.7 (33.6) | 8748.7 | 859.7 |
| langgraph_agentcard | 29.0 (30.1) | 0.0 (4.2) | 0.0 (4.2) | 0.0 (0.0) | 0.0 (0.0) | 2.0 (2.5) | 32.5 (34.3) | 8968.9 | 872.7 |
| appweaver_tpl | 25.1 (26.2) | 0.0 (4.7) | 0.0 (4.7) | 0.0 (0.1) | 0.0 (0.0) | 2.5 (2.6) | 30.4 (31.2) | 9277.1 | 722.7 |
| appweaver_mem | 26.9 (28.5) | 0.0 (5.7) | 0.0 (5.7) | 0.0 (0.3) | 0.0 (0.0) | 2.0 (2.6) | 32.5 (34.5) | 9554.9 | 784.9 |
| appweaver_guided | 38.2 (46.4) | 0.0 (4.3) | 0.0 (4.3) | 0.0 (0.3) | 0.0 (0.0) | 1.5 (2.1) | 42.5 (51.1) | 11550.8 | 1329.5 |
| appweaver_v2 | 38.0 (46.1) | 0.0 (4.2) | 0.0 (4.2) | 0.0 (0.1) | 0.0 (0.0) | 1.5 (2.1) | 41.4 (50.5) | 13522.6 | 1301.0 |

Host resources over the batch (314830 samples):

| Component | CPU core-seconds | Mean RSS (MiB) |
|---|---|---|
| harness | 407.4 | 127.1 |
| health_probe | 103.5 | 31.3 |
| kpm_bus | 1430.8 | 63.3 |
| live_emulator | 1010.7 | 4.0 |
| live_ric | 4645.9 | 19.7 |
| mcp_rpc | 270.1 | 94.2 |
| ns3 (background, not evaluated) | 43025.1 | 245.5 |
| portal_server | 239.9 | 92.2 |
| rapp_runtime | 18.6 | 33.2 |
| sim_ric (background, not evaluated) | 30.0 | 12.3 |
| twin_emulator | 37.0 | 3.8 |
| twin_ric | 110.6 | 4.5 |
| twin_validation | 0.0 | 3.9 |
| xapp:appweaver_actuator | 122.3 | 20.8 |
| xapp:kpm_rc_suite | 139.3 | 32.1 |
| xapp:l2_monitor | 12.5 | 39.1 |
| xapp:rc_ctrl | 80.2 | 44.3 |
| xapp:slice_suite | 399.2 | 32.7 |
| xapp:tc_suite | 126.4 | 33.6 |

CPU core-seconds per record, by method and component:

| Method | harness | health_probe | kpm_bus | live_emulator | live_ric | mcp_rpc | portal_server | rapp_runtime | twin_emulator | twin_ric | xapp:appweaver_actuator | xapp:kpm_rc_suite | xapp:l2_monitor | xapp:rc_ctrl | xapp:slice_suite | xapp:tc_suite |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| manual_rule | 0.02 | 0 | 0.07 | 0.03 | 0.15 | 0.01 | 0.01 | 0 | 0.0 | 0.0 | 0.01 | 0.0 | 0 | 0.02 | 0.09 | 0.03 |
| single_xapp | 0.01 | 0.0 | 0.02 | 0.01 | 0.06 | 0.0 | 0.0 | 0 | 0.0 | 0.0 | 0.01 | 0.0 | 0 | 0 | 0.0 | 0.01 |
| llm_blind | 0.04 | 0.0 | 0.13 | 0.09 | 0.44 | 0.03 | 0.02 | 0 | 0.0 | 0.0 | 0.04 | 0.01 | 0.0 | 0 | 0.01 | 0.0 |
| llm_only | 0.04 | 0.0 | 0.12 | 0.07 | 0.33 | 0.02 | 0.02 | 0 | 0.0 | 0.0 | 0.03 | 0.01 | 0 | 0.02 | 0.08 | 0.02 |
| agentcard_no_repair | 0.07 | 0.0 | 0.27 | 0.18 | 0.88 | 0.05 | 0.05 | 0.01 | 0.01 | 0.02 | 0.08 | 0.03 | 0.01 | 0.01 | 0.07 | 0.02 |
| langgraph_agentcard | 0.07 | 0.0 | 0.28 | 0.18 | 0.9 | 0.05 | 0.05 | 0.01 | 0.01 | 0.02 | 0.08 | 0.03 | 0.01 | 0.01 | 0.06 | 0.02 |
| appweaver_tpl | 0.09 | 0.0 | 0.34 | 0.17 | 0.77 | 0.06 | 0.05 | 0.01 | 0.01 | 0.02 | 0 | 0.03 | 0.0 | 0.02 | 0.09 | 0.02 |
| appweaver_mem | 0.09 | 0.0 | 0.37 | 0.2 | 0.88 | 0.07 | 0.06 | 0.01 | 0.01 | 0.02 | 0 | 0.04 | 0.0 | 0.03 | 0.1 | 0.02 |
| appweaver_guided | 0.12 | 0 | 0.53 | 0.3 | 1.32 | 0.09 | 0.08 | 0.01 | 0.01 | 0.04 | 0 | 0.06 | 0.0 | 0.01 | 0.14 | 0.02 |
| appweaver_v2 | 0.12 | 0.0 | 0.53 | 0.29 | 1.3 | 0.09 | 0.08 | 0.01 | 0.01 | 0.03 | 0 | 0.05 | 0.0 | 0.01 | 0.12 | 0.02 |
