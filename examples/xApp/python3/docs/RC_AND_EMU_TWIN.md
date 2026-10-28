# E2SM-RC xApp and the tier-1 emulator twin

Workstream A of the WCM-26-00422 revision. This covers (1) the real E2SM-RC xApp that
replaces the RC scaffold and (2) the FlexRIC emulator "twin" used as AppWeaver's tier-1
Validate stage (interface-conformance dry-run before deploying a step on the live stack).
See `FABLE_REVIEW_AND_PLAN.md` §3 (RC row) and §5 for the motivation.

## 1. RC xApp (`xapp_rc_ctrl.py`)

| Profile | E2 procedure | Content | Success line | Failure line |
|---|---|---|---|---|
| `control` | RIC CONTROL REQUEST to RAN function 3 (E2SM-RC v1.03) | Control Service Style 1 *Radio Bearer Control*, Control Action 2 *QoS flow mapping configuration*: header format 1 (gNB UE ID: AMF UE NGAP ID + GUAMI from the node PLMN), message format 1 with RAN parameter 1 (DRB ID) and 2 (list of QoS flows: 4 = QFI, 5 = mapping indication UL/DL). Defaults: UE 1, DRB 5, QFI 10, DL. | `RC CONTROL-ACK received: ... latency_ms=<x>` | `RC CONTROL-FAILED: <reason>` |
| `report` | RIC SUBSCRIPTION to RAN function 3 | REPORT Service Style 4 *UE Information*, event trigger format 4 (UE information change, RRC state = any), action definition format 1 with every RAN parameter the node lists for that style (emulator: 202 *RRC State*). | `RC indication received: #n <summary>` (one per indication) | `RC REPORT-FAILED: <reason>` |

Both profiles end with `RC xApp finished: profile=... ok=True|False ...` and exit 0 on success, 1 otherwise.
Options: `--duration-s` (control: how long to stay connected after the ACK; report: subscription
window), `--ric-conf PATH` (target another nearRT-RIC, see §2), `--amf-ue-ngap-id`, `--drb-id`,
`--qfi`, `--dir ul|dl`, `--node-timeout-s`.

The messages are only sent when the E2 node advertised the matching style/action at E2 Setup;
the xApp prints what the node advertised, e.g.

```
E2 node 0 E2SM-RC: report_styles=[4:UE Information ev_trig_fmt=4 act_fmt=1 params=202(RRC State)] control_styles=[1:Radio Bearer Control actions=2(QoS flow mapping configuration)]
```

### How the ACK is detected (and why there are two processes)

`control_sm_xapp_api()` in the FlexRIC E2 library waits for the RIC CONTROL ACKNOWLEDGE with
`cond_wait_sync_ui()`. In the Release build (`-DNDEBUG`, the build used here) the assert that would
catch a timeout is compiled out, so after `wait_ms + 1 s` (= 6 s) the call returns normally and the
library prints `[xApp]: Successfully received CONTROL-ACK` **even when no ACK arrived**; a CONTROL
FAILURE would hit `assert(0)` (also compiled out) and likewise end in the timeout. The only line
printed exclusively on a real acknowledgement is `[xApp]: CONTROL ACK rx` (in
`e2ap_handle_control_ack_xapp`, `src/xApp/msg_handler_xapp.c`).

`xapp_rc_ctrl.py` therefore runs as a small supervisor that starts the E2 worker (the same script
with `--worker`) as a child with line-buffered C stdout, relays its output, prints
`RC CONTROL-ACK received` when it sees the library's `[xApp]: CONTROL ACK rx` line, and prints the
failure line if the worker ends (or aborts, or exceeds its time budget) without it. For `report`,
the indication line is printed by the Python RC callback itself, i.e. only for indications that
actually reached the xApp.

### SWIG helpers (`src/xApp/swig/swig_wrapper.{h,cpp}`)

`rc_sub_data_t` / `rc_ctrl_req_data_t` are nested unions with calloc'd arrays and cannot be built
sensibly from Python, so (like `report_kpm_sm_auto` for KPM) the messages are built in C++ from the
node-advertised RAN function definition:

| Function | Purpose |
|---|---|
| `int control_rc_sm_qos_flow_map(id, amf_ue_ngap_id, drb_id, qfi, dir)` | Build and send the style-1/action-2 control; 0 when the call returned, -1 node has no E2SM-RC, -2 style 1/action 2 not advertised. Releases the GIL while waiting. |
| `int report_rc_sm_auto(id, rc_cb*)` | Build and send the style-4 subscription; handle or -1. Releases the GIL while waiting for the SUBSCRIPTION RESPONSE (the emulator sends its indications immediately, so holding the GIL could deadlock against the indication callback). |
| `std::string rc_ran_func_summary(id)` | Advertised RC report/control styles (empty if none). |
| `std::string rc_ind_summary(rc_ind_data_t const*)` | One-line indication summary (formats, UE ids, integer RAN parameter values). |
| `init()` | Now honours `FLEXRIC_XAPP_CONF=<conf file>`; unset keeps the FlexRIC default `/usr/local/etc/flexric/flexric.conf`. This lets every Python xApp (KPM/SLICE/TC suites too) be pointed at another nearRT-RIC without code changes. |

No change to the E2 library, the RIC or the agent; `libe42_xapp_shared.so` is unchanged.

**Rebuild.** `cmake --build ~/flexric/build --target xapp_sdk -j8` works, but its POST_BUILD step also
copies `backend/`, `evaluation/`, `rapps/`, `scripts/` and many `.py` files from the source tree into
the build tree and overwrites `_xapp_sdk.so` in place (unsafe while xApps are running). Because the
live stack was running, the module was built in a side build directory and swapped in atomically:

```bash
SB=/tmp/flexric_sidebuild   # any scratch dir
cmake -S ~/flexric -B $SB -DCMAKE_BUILD_TYPE=Release -DE2AP_VERSION=E2AP_V2 -DKPM_VERSION=KPM_V2_03 \
      -DXAPP_MULTILANGUAGE=ON -DXAPP_TARGET_LANGUAGE=PYTHON_LANG -DPython3_EXECUTABLE=$(which python) -DUNIT_TEST=FALSE
cmake --build $SB --target xapp_sdk -j12
L=~/flexric/build/examples/xApp/python3
cp $SB/src/xApp/swig/_xapp_sdk.so $L/._new.so && patchelf --set-rpath ~/flexric/build/src/xApp $L/._new.so
cp $SB/examples/xApp/python3/xapp_sdk.py $L/._new.py
mv -f $L/._new.so $L/_xapp_sdk.so && mv -f $L/._new.py $L/xapp_sdk.py   # rename: running xApps keep the old inode
```

(The tracked `examples/xApp/python3/xapp_sdk.py` in the source tree is an old generated copy that
predates `get_ran_func_ids`; run the xApps from the build tree.)

### Agent card (`backend/agents/rc.py`, id `rc`)

| Action id | Scope | Command |
|---|---|---|
| `rc-control` | write, `ue`, `rc_control` | `xapp_rc_ctrl.py --profile control --duration-s 10` |
| `rc-report` | read, `ue`, `rc_control` | `xapp_rc_ctrl.py --profile report --duration-s 10` |

`interfaces=['E2SM-RC v1.03']` (the old card also claimed KPM, which the RC xApp does not use),
`produces=['rc.control_ack', 'rc.ue_info']`, capabilities
`['radio_bearer_control', 'qos_flow_mapping', 'control_validation', 'ue_info_report']`. The old
`policy_gate` capability is gone: nothing in the RC xApp gates anything (the LangGraph "approve" stage
in `backend/graph/nodes/approve.py` is labelled `agent_id="rc"` but is a platform-health check, not RC).
`control_validation` is kept because the labels' "validate" role for the final RC step relies on it
(`evaluation/label_rules.py`), and the control step does report whether the E2 node acknowledged the
control. Whether RC should rather be role `control` is a labelling decision. `backend/orchestration/config.py`
workflow templates now name `rc-control` instead of the removed `rc-scaffold`.

## 2. Tier-1 twin (FlexRIC E2 emulator)

```bash
scripts/start_twin_emu_stack.sh     # idempotent; prints pids, endpoints and the conf path
scripts/stop_twin_emu_stack.sh
```

* A second `nearRT-RIC` and `emu_agent_gnb` from the same build, started with `-c /tmp/flexric_twin_emu/flexric_twin.conf`.
  Logs (line-buffered), pids, the generated conf and xApp DBs are under `/tmp/flexric_twin_emu`
  (`TWIN_LOG_DIR` overrides).
* **Endpoints.** In this FlexRIC tree the E2 and E42 ports are compile-time constants (36421 in
  `src/ric/near_ric.c:208` and `src/agent/e2_agent_api.c:94`; 36422 in `src/ric/iApp/e42_iapp.c:37`
  and `src/xApp/e42_xapp.c:182`); the only runtime knob is `NEAR_RIC_IP` in the conf file (read by
  the RIC, the agent and the xApps; `DB_DIR` is the xApp DB directory). The live RIC binds
  127.0.0.1, so the twin binds the second loopback address **127.0.0.2** (`TWIN_RIC_IP` overrides;
  127.0.0.1 is refused). It is therefore a fully separate SCTP endpoint pair,
  127.0.0.2:36421 (E2) / 127.0.0.2:36422 (E42), with its own E2 node. Moving the ports instead would
  have required rebuilding the RIC, agent and `libe42_xapp_shared.so` that the live stack is using.
* **Targeting the twin from an xApp:** `FLEXRIC_XAPP_CONF=/tmp/flexric_twin_emu/flexric_twin.conf`
  (all Python suites), or `xapp_rc_ctrl.py --ric-conf /tmp/flexric_twin_emu/flexric_twin.conf`.
  C xApps already accept `-c <conf>`.

### `backend/orchestration/emu_twin.py`

| Function | Returns |
|---|---|
| `twin_available()` | twin pids alive, SCTP listeners on the twin IP:36421/36422, E2 setup completed |
| `start_twin(restart=False)` | runs the start (and stop) script, then `twin_available()` |
| `twin_e2_ran_functions()` / `twin_e2_ran_function_defs()` | RAN function ids (and names) the twin's E2 node advertised at E2 Setup, from the twin RIC log |
| `twin_command(agent_id, action_id, duration_s)` | the command the dry-run executes |
| `dryrun_step(agent_id, action_id, duration_s=4)` | `{acked, detail, latency_ms, e2_ran_functions, command, tail, exit_code, ...}` |
| `dryrun_chain([(agent, action), ...])` | one report per step |

`dryrun_step` runs the **same command as the card action** with `--duration-s` shortened and
`FLEXRIC_XAPP_CONF` pointing at the twin. Exception: the KPM agent's actions read the live shared KPM
bus over HTTP rather than E2, so on the twin they run the bus collector's own E2 KPM subscription
(`xapp_kpm_rc_suite.py --profile kpm`). Before launching it rejects a step whose RAN function
(kpm 2, rc 3, slice 145, tc 146) the twin's E2 node does not advertise. Acknowledgement criteria:

| Step | acked when the xApp output contains |
|---|---|
| `kpm/observe-rru`, `kpm/observe-ue` | a KPM record (`meas=RRU.` / `meas=DRB.`), i.e. an indication arrived |
| `slice/monitor` | `SLICE ind tstamp=` (indication) |
| `slice/apply-static`, `tc/apply-codel`, `tc/apply-all` | `[xApp]: CONTROL ACK rx` (real E2 CONTROL-ACK, not the timeout-prone "Successfully received CONTROL-ACK") |
| `rc/rc-control` | `RC CONTROL-ACK received` |
| `rc/rc-report` | `RC indication received` |

`latency_ms` is launch-to-first-ack, so it includes Python start-up and the E42 setup (≈1.1 s for
controls, ≈2 s for TC which sends three controls, ≈3 s for KPM whose first indication comes after one
1 s period). rApp steps return `acked=False` with "no tier-1 E2 dry-run" (they do not use E2).
CLI: `python -m backend.orchestration.emu_twin kpm:observe-rru rc:rc-control ...` from the build tree.

### What the twin validates — and what it does not

`emu_agent_gnb` is an E2 *interface* emulator. It performs a real E2 Setup advertising
KPM/RC/MAC/RLC/PDCP/GTP/SLICE/TC, answers subscriptions with indications filled by
`test/rnd/fill_rnd_data_*` (random KPM values and random RC UE-information indications: the RC
report subscription produces exactly five indications right after it is accepted), and answers every
CONTROL with a CONTROL-ACK after printing it (`sm_rc.c` prints the decoded DRB/QFI/direction). It keeps
**no state**: an RC QoS-flow remap, a slice ADD or a TC queue does not change any later indication.

So a tier-1 pass means: the step's E2SM messages encode/decode end-to-end through a nearRT-RIC, the E2
node advertises the RAN function/style the card claims, the subscription is accepted or the control is
acknowledged, and the xApp process runs and terminates cleanly, within the measured time. It says
nothing about KPI effects, interference between controls, or state synchronisation with the live RAN.
KPI what-if belongs to tier 2 (ns-3 twin, §5.2 of the plan).

## 3. Test evidence (2026-10-28)

Twin (fresh RIC on 127.0.0.2), from the build tree:

```
RC CONTROL sending: E2SM-RC style 1 (Radio Bearer Control) action 2 (QoS flow mapping configuration) amf_ue_ngap_id=1 drb_id=5 qfi=10 dir=dl
[xApp]: CONTROL-REQUEST tx
[xApp]: CONTROL ACK rx
RC CONTROL-ACK received: E2 RIC CONTROL ACKNOWLEDGE for E2SM-RC style 1 action 2 (QoS flow mapping) latency_ms=0.3
```
twin emulator log for the same control: `QoS flow mapping configuration / DRB ID 5 / List of QoS Flows to be modified / qfi = 10 dir 1 / [E2-AGENT]: CONTROL ACKNOWLEDGE tx`;
twin RIC log: `[NEAR-RIC]: CONTROL SERVICE sent / CONTROL ACKNOWLEDGE rx / [iApp]: RIC_CONTROL_ACKNOWLEDGE tx`.

```
[xApp]: SUBSCRIPTION RESPONSE rx
RC REPORT subscribed: style 4 (UE Information) handle=1 in 0.8 ms
RC indication received: #1 hdr_fmt=1 msg_fmt=2 ues=2 [amf_ue_ngap_id=41 ...] [amf_ue_ngap_id=40 ...]
...
RC REPORT window closed: 5 indication(s) received
[xApp]: E42 SUBSCRIPTION DELETE RESPONSE rx
```

### 3.1 Dry-run of every executable step on the twin

`dryrun_step(agent, action, duration_s=4)`, 5 rounds over all eight steps (fresh twin, from the build tree):

| Step | acked | median launch-to-ack (ms) |
|---|---|---|
| kpm/observe-rru | 5/5 | 3089 |
| kpm/observe-ue | 5/5 | 3086 |
| slice/monitor | 5/5 | 1094 |
| slice/apply-static | 5/5 | 1086 |
| tc/apply-codel | 5/5 | 2086 |
| tc/apply-all | 5/5 | 2087 |
| rc/rc-control | 5/5 | 1102 |
| rc/rc-report | 5/5 | 1114 |

One earlier single run of `kpm/observe-ue` (directly after `observe-rru`) received no KPM indication in its
4 s window; 9 later runs of the same step acked. With `duration_s=4` a KPM step has about one spare
indication period, so use `duration_s>=5` for KPM steps if this matters.

Live stack (127.0.0.1, up since 09:26, ≈370 xApp connections served): the same RC control and RC
report were sent and **not acknowledged** (`RC CONTROL-FAILED: no E2 RIC CONTROL ACKNOWLEDGE received`,
`RC REPORT-FAILED: no RC indication received`), with `[E2AP]: Resending Setup Request after timeout`
lines and the library's 6 s timeout. The existing TC suite shows the same on the live RIC at the same
time: three `CONTROL-REQUEST tx` each followed by "Successfully received CONTROL-ACK" after the 6 s
timeout, and the real `[xApp]: CONTROL ACK rx` lines arriving 15–20 s later. The same binaries
acknowledge in < 1 ms on a freshly started RIC, so the live RIC is degraded, not the messages; restart
the live stack before a batch that relies on E2 control acknowledgements.

Note (10:18:10): the live stack's `emu_agent_gnb` stopped (the KPM bus's last indication is at
10:18:10.8, and `run_agent_portal_stack.sh` logged "emu_agent_gnb stopped unexpectedly" and took
nearRT-RIC down with it). The portal and KPM bus processes are still up but have no RIC behind them.
None of this workstream's xApps were connected to the live RIC then (the last one, an RC report
test, ended at 10:14:16; every later run used the twin conf, as their DB files in
`/tmp/flexric_twin_emu/db` show). The stop coincided with the start of an evaluation harness smoke run.
