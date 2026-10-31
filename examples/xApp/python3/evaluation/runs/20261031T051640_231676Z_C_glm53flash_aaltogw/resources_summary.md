# Time and resources - `20261031T051640_231676Z_C_glm53flash_aaltogw` (900 records)

Median seconds per record (mean in brackets). planner = LLM call(s); validate includes the twin dry-run.

| Method | Planner | Validate | Dry-run | Lease wait | Deploy | Ack | Total | Prompt tok | Completion tok |
|---|---|---|---|---|---|---|---|---|---|
| llm_only | 4.5 (4.8) | 0.0 (0.0) | 0.0 (0.0) | 0.0 (0.0) | 0.0 (0.0) | 6.0 (4.5) | 4.5 (4.8) | 421.8 | 610.2 |
| langgraph_agentcard | 16.7 (20.0) | 8.2 (9.9) | 8.2 (9.9) | 0.0 (0.0) | 0.0 (0.0) | 2.5 (2.8) | 23.3 (29.9) | 1816.2 | 2869.7 |
| appweaver_tpl | 12.7 (15.7) | 8.2 (10.7) | 8.2 (10.7) | 0.0 (0.0) | 0.0 (0.0) | 2.8 (2.9) | 19.7 (26.5) | 2151.2 | 2266.2 |
| appweaver_mem | 19.2 (21.2) | 8.2 (10.8) | 8.2 (10.8) | 0.0 (0.0) | 0.0 (0.0) | 2.5 (3.1) | 31.4 (32.0) | 2339.5 | 3121.5 |
| appweaver_mem2 | 22.3 (23.0) | 8.2 (11.3) | 8.2 (11.3) | 0.0 (0.0) | 0.0 (0.0) | 2.5 (3.1) | 31.7 (34.3) | 2351.4 | 3294.2 |

Host resources over the batch (58109 samples):

| Component | CPU core-seconds | Mean RSS (MiB) |
|---|---|---|
| harness | 88.4 | 110.8 |
| health_probe | 19.2 | 29.1 |
| kpm_bus | 311.2 | 63.2 |
| live_emulator | 228.2 | 4.0 |
| live_ric | 1019.6 | 5.7 |
| mcp_rpc | 53.6 | 94.5 |
| portal_server | 45.7 | 91.4 |
| twin_emulator | 22.3 | 3.8 |
| twin_ric | 72.3 | 5.1 |
| xapp:kpm_rc_suite | 29.0 | 32.1 |
| xapp:rc_ctrl | 23.5 | 44.1 |
| xapp:slice_suite | 150.6 | 32.2 |
| xapp:tc_suite | 50.2 | 34.6 |

CPU core-seconds per record, by method and component:

| Method | harness | health_probe | kpm_bus | live_emulator | live_ric | mcp_rpc | portal_server | twin_emulator | twin_ric | xapp:kpm_rc_suite | xapp:rc_ctrl | xapp:slice_suite | xapp:tc_suite |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| llm_only | 0.04 | 0.0 | 0.1 | 0.05 | 0.24 | 0.02 | 0.01 | 0.0 | 0.0 | 0.01 | 0.02 | 0.03 | 0.02 |
| langgraph_agentcard | 0.09 | 0.0 | 0.35 | 0.26 | 1.18 | 0.06 | 0.05 | 0.03 | 0.11 | 0.03 | 0.01 | 0.2 | 0.07 |
| appweaver_tpl | 0.09 | 0.0 | 0.32 | 0.24 | 1.09 | 0.05 | 0.04 | 0.03 | 0.09 | 0.03 | 0.02 | 0.21 | 0.06 |
| appweaver_mem | 0.09 | 0.0 | 0.37 | 0.26 | 1.18 | 0.06 | 0.05 | 0.03 | 0.09 | 0.04 | 0.03 | 0.2 | 0.06 |
| appweaver_mem2 | 0.09 | 0.0 | 0.39 | 0.29 | 1.3 | 0.07 | 0.06 | 0.03 | 0.09 | 0.04 | 0.03 | 0.2 | 0.07 |
