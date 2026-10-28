# ns-O-RAN-flexric simulator stack: review of the five known problems and fix plan

Scope: the simulated RAN used by AppWeaver's T6 twin experiment and the planned Validate-2 deploy gate
(`~/ns-oran-flexric` + `~/flexric-taap`, see `~/ns-oran-flexric/APPWEAVER_SETUP.md` §10). Written for the
sim session that owns those trees; nothing here was built or run. Line numbers are from the trees as of
2026-10-28. AppWeaver code referenced: `evaluation/twin/run_twin_validation.py`,
`evaluation/twin/xapp_appweaver_actuator.c`, `kpm_bus_service.py` (all under
`~/flexric/examples/xApp/python3/`).

## Executive summary

- **P1 (one KPM subscriber) is three bugs, not one.** (a) FlexRIC iApp: `eq_xapp_ric_gen_id()` compares an
  xApp id with *itself*, so a RIC-SUBSCRIPTION-DELETE from xApp B is mapped onto xApp A's subscription
  (both SDKs number requests 1, 2, 3…). (b) e2sim: *any* subscription delete closes the node's SCTP
  socket, and the next indication send calls `exit(EXIT_FAILURE)`, killing the whole ns-3 process.
  (c) ns-3 keeps a single subscription per node; a second subscriber is acked but never receives
  indications. (a) and (b) are one-line/ten-line fixes; (c) is ~150 lines and can wait because AppWeaver's
  KPM-bus pattern already solves multi-agent *reading* (ns-3 ignores subscription parameters anyway).
- **P2 (empty reports)** originates in ns-3: the neighbour-SINR loop counts the serving-cell marker as a
  neighbour, so with 2 gNBs a UE's neighbour list contains only the marker and the measurement record
  is encoded with 0 items. The FlexRIC patch 0004 is a correct *defensive* change (keep it); the
  simulator should additionally emit a `noValue` record so the RIC never forwards spec-invalid KPM.
- **P3 (load-gated reporting)** is by design in this fork: only KPM action-definition format 4 is handled,
  reporting starts when a 10-sample moving average of PRB use (checked every 100 ms) satisfies
  `IsStat <op> N`, i.e. ≥ 1.0 s of simulated time after subscription even with the trivial
  `< 101` test. Subscribing with formats 1/2/3/5 is acked but produces nothing. Fix: start at once when
  the condition is trivially true or the format carries no condition; make the window an attribute.
- **P4 (wall-clock timestamps)** is a 3-line bug: `BuildRicIndicationHeader` computes a sim-time
  `m_timestamp` that the encoder ignores in favour of `clock_gettime(CLOCK_REALTIME)`. Encode
  `Simulator::Now().GetMicroSeconds()` instead; AppWeaver's "indication count × period" workaround
  (and its `offset` estimate) becomes exact.
- **P5 (cells 1–9, no switch-on)**: the RC target cell is one ASCII digit on both sides (xApp encoders
  write a 1-byte string, ns-3 does `buf[0] - 48`); the energy-state handler ignores the action id and
  always switches *off*. Parsing a decimal string of any length and honouring action `'1'` (CELL_ON,
  already defined in the actuator) are ~20 lines; `SetBSTX` is a TX-power/noise-figure toggle, so
  switch-on is just the inverse call with the saved power.
- Side finding: a UE handed over by RC is put under "external HO control" forever
  (`m_e2ControlledUes` is never cleared), so it never hands over autonomously again. This is fine for
  the 8 s T6 windows but matters for longer twin runs and for switch-on (UEs do not return by themselves).
- Side finding: scenario-zero has **no UE-position input**. `ue_position.txt` is an output trace;
  positions come from `UniformDiscPositionAllocator` + random walk. The placement-synced twin in
  `FABLE_REVIEW_AND_PLAN.md` §5.2 needs a new `uePositionFile` GlobalValue (~30 lines, sketched in §7).
- Recommended order for AppWeaver: P1(a)+(b), P5, P4 first (all small, all unblock the energy-saving
  workflow and Validate-2), then P2 and P3, then P1(c) and the position input. After the P4/P3 changes
  the T6 batches must be re-run because the indication clock changes.
- AppWeaver-side workarounds that remain valid whatever is fixed: one KPM subscriber per simulation
  fronted by a KPM-bus collector; thresholds `KPM_PRB_LT=101`; cell ids ≤ 9 until P5a lands; never let an
  xApp unsubscribe/exit before the simulation ends until P1(b) lands.

---

## 1. Only one KPM subscriber per simulation (second xApp kills the stack)

### Root cause (three independent defects)

**(a) FlexRIC iApp maps a delete to the wrong xApp.**
`~/flexric-taap/src/ric/iApp/xapp_ric_id.c`, `eq_xapp_ric_gen_id()`:

```c
if(eq_xapp_id(m0->xapp_id, m0->xapp_id) == false)   // compares m0 with itself: always true
    return false;
return eq_ric_gen_id(&m0->ric_id, &m1->ric_id);
```

`find_ric_req_map_ric_id()` (`src/ric/iApp/map_ric_id.c` ~197-216) does a linear `find_if` over the
xApp-side tree with this predicate, and it is what
`e2ap_handle_e42_ric_subscription_delete_request_iapp()` (`src/ric/iApp/msg_handler_iapp.c` 328-352)
uses to translate an xApp's local `ric_req_id` into the RIC-side id. Every xApp SDK numbers its own
requests from 1 (`src/xApp/act_proc.c:70`, `e42_xapp.c:404-407`), the RIC renumbers them from 1021
(`src/ric/near_ric.c:221`, `fwd_ric_subscription_request` :774-804). So when xApp 2 deletes *its*
request 1, the iApp finds the first tree entry with `ric_id == 1`, which is xApp 1's → RIC id 1021.

Evidence in `~/ns-oran-flexric/logs/run2_second_subscriber_crash/`:
`ric.log` shows both xApps subscribing with RIC_REQ_ID 1…5, then
`[iApp]: RIC_SUBSCRIPTION_DELETE_REQUEST tx RIC_REQ_ID 1021` with **no** preceding
`Automatically removing pending …` line (so it was an explicit E42 delete, not a disconnect), and the
delete response forwarded as `RIC_REQ_ID 1` to the *other* xApp. `xapp_capture.log` (xApp 1) then asserts
in `assoc_rb_tree_extract` from `e2ap_handle_subscription_delete_response_xapp()`
(`src/xApp/msg_handler_xapp.c` 161-177): it has request 1 in its registry but no pending delete event.
`dbg.err` (xApp 2, run under `timeout`) asserts in `cond_wait_sync_ui` (`src/xApp/sync_ui.c:65`): its
delete response never came.

**(b) e2sim treats any subscription delete as "terminate the agent", then kills ns-3.**
`~/ns-oran-flexric/e2sim-kpmv3/e2sim/src/messagerouting/e2ap_message_handler.cpp` 206-233: on
`RICsubscriptionDelete` initiating message it calls the registered callback id 1
(`stopSendingAndCancelSchedule`, which sets `m_stopSendingMessages = true` permanently,
`mmwave-enb-net-device.cc` 296-300, registered at 896-897), acks, and `return true`.
`src/base/e2sim.cpp` run loop (~199-215): `if (e2ap_handle_sctp_data(...)) { sctp_close_clinet_connection(client_fd); break; }`.
The ns-3 report chain is a simulator event, not an e2sim-thread activity, so
`BuildAndSendReportMessage` (`mmwave-enb-net-device.cc` 1642-1742) keeps firing;
`E2Sim::encode_and_send_sctp_data` → `sctp_send_data` (`src/SCTP/e2sim_sctp.cpp` ~233-241):

```c
if(sent_len == -1) { LOG_E("[SCTP] sctp_send_data, error message: %s", strerror(errno)); exit(EXIT_FAILURE); }
```

`ns3.log` ends with exactly `sctp_send_data, error message: Bad file descriptor`; the RIC then logs five
`SCTP_SHUTDOWN_EVENT`s. This is why "the simulation has to be restarted after an xApp unsubscribes":
*any* delete — including the clean `rm_report_sm_xapp_api()` loop at the end of `xapp_kpm_capture` (-t)
or the iApp's automatic cleanup when an xApp disconnects (`e42_iapp.c` 173-190, 244-246) — ends the run.

**(c) ns-3 keeps one subscription per node.**
`MmWaveEnbNetDevice::KpmSubscriptionCallback` (`src/mmwave/model/mmwave-enb-net-device.cc` 226-293)
overwrites `m_lastSubscriptionParams`; `E2Termination::subs_details` is a single map
(`contrib/oran-interface/model/oran-interface.cc` 347). `CheckReportingFlag` (165-223) starts
`BuildAndSendReportMessage(m_lastSubscriptionParams)` once; the chain re-schedules itself with the
`params` captured by value (1739-1740), so the second subscriber's requestor/instance id is never used:
it gets a SUBSCRIPTION-RESPONSE and no indications (the iApp would drop them anyway:
`msg_handler_iapp.c:269-272` routes by RIC id). A second subscription also starts a second
`CheckReportingFlag` timer chain per node (harmless, but it leaks). `LteEnbNetDevice` (cell 1,
`src/lte/model/lte-enb-net-device.cc` 82-103) has the same single-subscription shape.

### Fix options

| Option | Where | Effort | Risk | Effect |
|---|---|---|---|---|
| 1.1 Fix `eq_xapp_ric_gen_id` | flexric-taap, 1 line | trivial | none | deletes go to the right subscription; the `assoc_rb_tree_extract` crash of the *other* xApp disappears |
| 1.2 e2sim: delete ≠ terminate; no `exit()` on send failure | e2sim, ~15 lines | small | low | an xApp can unsubscribe/exit/crash without ending the simulation |
| 1.3 ns-3: N subscriptions per node + delete by id | ns-3 + e2sim API, ~150 lines | medium | medium (touches the report chain used by T6) | real multi-subscriber support |
| 1.4 AppWeaver: one collector xApp + KPM bus fan-out | AppWeaver, ~80 lines Python | small | none to the sim | multi-agent sharing without 1.3 |
| 1.5 ns-3: reject a 2nd subscription with SUBSCRIPTION-FAILURE | ns-3, ~20 lines | small | FlexRIC xApp SDK asserts on failure → not useful | — |

### Recommended: 1.1 + 1.2 now, 1.4 on the AppWeaver side, 1.3 later

**1.1** (`~/ns-oran-flexric/patches/flexric-taap-0005-iapp-xapp-id-eq.patch`):

```diff
--- a/src/ric/iApp/xapp_ric_id.c
+++ b/src/ric/iApp/xapp_ric_id.c
@@ bool eq_xapp_ric_gen_id(...)
-  if(eq_xapp_id(m0->xapp_id, m0->xapp_id) == false)
+  if(eq_xapp_id(m0->xapp_id, m1->xapp_id) == false)
     return false;
```

**1.2** (`~/ns-oran-flexric/patches/e2sim-0001-subscription-delete-keeps-connection.patch`):

```diff
--- a/src/messagerouting/e2ap_message_handler.cpp
@@ case ProcedureCode_id_RICsubscriptionDelete:
                     e2ap_handle_RICSubscriptionDeleteRequest(pdu, socket_fd, e2sim);
-                    return true;
+                    // A subscription delete ends that subscription, not the E2 connection.
+                    return false;
--- a/src/SCTP/e2sim_sctp.cpp
@@ int sctp_send_data(int &socket_fd, sctp_buffer_t &data)
   if(sent_len == -1) {
     LOG_E("[SCTP] sctp_send_data, error message: %s", strerror(errno));
-    exit(EXIT_FAILURE);
+    return -1;   // caller decides; never terminate the host process (ns-3) from a library
   }
--- a/src/base/e2sim.cpp
@@ void E2Sim::encode_and_send_sctp_data(E2AP_PDU_t* pdu)
+  if (client_fd <= 0) { LOG_E("E2 connection closed, dropping PDU"); return; }
   data.len = e2ap_asn1c_encode_pdu(pdu, &buf);
```

Then the E2 side of a delete is: ack, stop reporting (via the callback), keep the socket. Make the stop
reversible in ns-3 so a later subscription restarts reporting (today `m_stopSendingMessages` is sticky
and `CheckReportingFlag` refuses to run while it is set):

```diff
--- a/src/mmwave/model/mmwave-enb-net-device.cc
@@ MmWaveEnbNetDevice::KpmSubscriptionCallback
   m_lastSubscriptionParams = m_e2term->ProcessRicSubscriptionRequest(sub_req_pdu);
   m_hasValidSubscription = true;
+  m_stopSendingMessages = false;      // a new subscription re-arms reporting after a delete
+  m_isReportingEnabled = false;       // let CheckReportingFlag start a fresh chain
```

(The old chain, if still scheduled, exits at the `if (m_stopSendingMessages) return;` check at 1721
before the flag is cleared only if the delete arrived first; if a subscribe follows a delete within one
`E2Periodicity`, the old chain may send one extra indication with stale ids — the iApp drops it with
"no xApp associated". Acceptable; 1.3 removes the race properly.) Same two lines in
`LteEnbNetDevice::KpmSubscriptionCallback` (`lte-enb-net-device.cc` 92-96, which also needs
`m_isReportingEnabled = false` on delete).

**1.3 sketch (defer until an experiment needs distinct subscriptions).** e2sim: add
`register_subscription_delete_callback(long func_id, SubscriptionCallback cb)` (same `void(E2AP_PDU_t*)`
type as the subscribe callback) and call it from the delete branch instead of `get_callback(1)`.
ns-3 `E2Termination`: `RicSubscriptionRequest_rval_s ProcessRicSubscriptionDeleteRequest(E2AP_PDU_t*)`
that extracts `RICrequestID`/`RANfunctionID` (the IE loop already exists in
`e2ap_handle_RICSubscriptionDeleteRequest`, lines 258-300). `MmWaveEnbNetDevice`: replace
`m_lastSubscriptionParams`/`m_isReportingEnabled` by
`std::map<uint32_t /*reqId<<16|instId*/, E2Termination::RicSubscriptionRequest_rval_s> m_subs;` and a single
`EventId m_reportEvent`; `BuildAndSendReportMessage()` builds the three KPM payloads once and loops over
`m_subs` to wrap each in an E2AP indication with that subscription's ids; delete erases one entry and
cancels the event when the map empties; `CheckReportingFlag` only arms the chain if `m_reportEvent` is not
running. Keep `subs_details` per subscription (`std::map<uint32_t, Subscription_map>`) so thresholds do not
overwrite each other. Test: two `xapp_kpm_capture` instances with different `KPM_CSV`; both CSVs must
grow at the same rate and be identical except `wall_us`; stop one with SIGINT; the other must continue
and ns-3 must reach `simTime`.

**1.4 AppWeaver side.** `kpm_bus_service.py` already does the right thing architecturally: one
supervised collector subprocess, a ring buffer with monotonically increasing `seq`, `GET /kpm/recent?after_seq=`,
optional Redis fan-out. Add a collector profile for the sim (env `KPM_BUS_COLLECTOR=sim`):
`_collector_command()` returns `[xapp_kpm_capture, -c, <flexric-taap conf>, -p, <libs>]` with
`KPM_CSV=/dev/stdout` (the xApp opens the path with `fopen`, so stdout works; the SDK's own prints go to the
same stream, so `_append_line` must keep only lines that split into 8 comma fields with a numeric first
field), and `_normalize_record` maps `wall_us,collect_start_us,node_type,nb_id,ue_imsi,meas,idx,value` to
`{"nb_id", "imsi", "meas", "idx", "value", "k"}` where `k` is the per-`nb_id` DU-report index (the same
rule `run_twin_validation.KpmState._row` uses). Agents then share one subscription and one simulation.
This covers the multi-agent KPM-sharing experiment without touching the stack, and loses nothing: ns-3
ignores measurement names and periods in subscriptions (one fixed KPI set, period = `--indicationPeriodicity`,
`APPWEAVER_SETUP.md` §5), so per-agent subscriptions would be identical feeds anyway.

### How to test (after 1.1 + 1.2)

1. `./start_sim_stack.sh -g 2 -u 4 -t 30 -x capture`; after ~5 wall-minutes start a second
   `xapp_kpm_capture -c … -p … -t 20` with another `KPM_CSV`. Expected: second CSV stays empty of DU rows
   (1.3 not done), **no** crash of the first xApp, ns-3 keeps running, `ric.log` shows the delete for the
   second xApp's own RIC ids (1026…), not 1021.
2. Stop the first xApp with SIGINT (it sends five deletes). Expected: ns-3 keeps running to `simTime`
   (no `Bad file descriptor`), `ns3.log` shows `RIC-SUBSCRIPTION-DELETE-ACKNOWLEDGE` ×5, and starting a
   new `xapp_kpm_capture` resumes indications (checks the re-arm lines).
3. Re-run `logs/run2_second_subscriber_crash` conditions (4 gNB/10 UE) to confirm.

### Impact on AppWeaver

- T6 twin-vs-live: unaffected today (one actuator xApp per instance, runs to end of sim). After 1.2 the
  runner can stop the actuator early and reuse the simulation for several candidate policies.
- Validate-2 gate: needs 1.2 (the gate will start/stop xApps per candidate) and 5b (reset the twin).
- Multi-agent KPM sharing: 1.4 now; 1.3 only if an experiment specifically needs per-agent
  subscriptions (e.g. different `IsStat` thresholds, which P3 makes dubious anyway).
- Re-run after 1.1/1.2: nothing scientific (payloads unchanged); re-run the 2-xApp repro and the ES
  closed loop (`captures/es_cell_switch_off`) as regression.

---

## 2. RIC aborted on empty measurement records (2 gNBs)

### Root cause

ns-3 builds the per-UE neighbour SINR list in `BuildRicIndicationMessageCuCp`
(`src/mmwave/model/mmwave-enb-net-device.cc` 1184-1217): it takes the best
`nNeighbours = min(E2SM_REPORT_MAX_NEIGH, m_l3sinrMap[imsi].size() - 1)` entries of the UE's SINR map,
**including** the serving cell, which it negates as a marker (`if (cellId == m_cellId) cellId *= -1;`) and
counts (`itIndex++` at 1216). With 2 gNBs a UE's map has 2 entries → `nNeighbours = 1` → the single
best entry is almost always the serving cell → the list is `[-servingCell]` only.
`KpmIndicationMessage::getMesDataItem(const MeasResultListNR*, …)`
(`contrib/oran-interface/model/kpm-indication.cc` 839-875) uses the negative entry only to name the item
(`updateNeighMsg` → `L3neighSINRListOf_UEID_<imsi>_of_Cell_<c>`) and `continue`s, so the
`MeasurementRecord` ends with **0 items**; the caller (683-700) adds it because `list.count` (1) `> 0`.
KPM v3 requires 1…N records, hence `dec_meas_data.c:24` asserting in FlexRIC.

Latent second case: if the map has only the serving cell (`size()==1`, a UE that has never measured a
neighbour), `nNeighbours = 0`, the RRC list is empty, `measureDataItem` stays `nullptr` and
`ASN_SEQUENCE_ADD(&measurementDataList->list, nullptr)` (1009) is executed — undefined for the APER
encoder (not yet observed; the LTE anchor keeps UEs measured, but it will bite with 1 gNB).

### Is the FlexRIC patch right?

`patches/flexric-taap-0004-kpm-tolerate-empty-meas-records.patch` relaxes the decoder, encoder and copy
asserts to `len <= max` and returns an empty `dst` from `cp_meas_data_lst` when `len == 0`. It is correct
as a *defensive* change (the RIC must never abort on a peer's malformed PDU) and it is consumed by the
xApp SDK too (same static lib), so xApps iterate 0 records safely. Keep it. But it makes the RIC forward
spec-invalid KPM to any xApp that is not built from this tree, and it hides the real defect, so the
simulator should stop producing such items.

### Fix options

| Option | Where | Effort | Risk |
|---|---|---|---|
| 2.1 Emit a `noValue` record when the list would be empty | ns-3 `kpm-indication.cc`, ~12 lines | small | none (FlexRIC decodes `MeasurementRecordItem_PR_noValue` → `NO_VALUE_MEAS_VALUE`, `dec_meas_data.c:44`) |
| 2.2 Count neighbours excluding the serving marker (`nNeighbours = min(8, size())`, don't `itIndex++` for the marker) | ns-3 enb device | small | changes the "best 8" semantics (serving + up to 8 neighbours instead of 8 total) — avoid |
| 2.3 Skip the item (and its `MeasurementInfoItem`) when empty | ns-3 `kpm-indication.cc` | small | the CU-CP report loses the `L3neighSINRListOf…` entry for that UE; AppWeaver's `_best_target` then has no candidate list — worse than a `noValue` |
| 2.4 Keep only the FlexRIC patch | — | none | silently non-conformant; breaks any other RIC |

### Recommended: 2.1 (+ keep 0004), patch `oran-interface-0002-kpm-no-empty-records.patch`

```diff
--- a/contrib/oran-interface/model/kpm-indication.cc
@@ KpmIndicationMessage::getMesDataItem (const MeasResultListNR *_measResultListNR, …)
       ASN_SEQUENCE_ADD (&measure_record->list, measure_record_item2);
     }
+  if (measure_record->list.count == 0)
+    {
+      // KPM v3 requires >= 1 record. A UE with no neighbour cell gets an explicit "no value".
+      MeasurementRecordItem_t *nv = (MeasurementRecordItem_t *) calloc (1, sizeof (MeasurementRecordItem_t));
+      nv->present = MeasurementRecordItem_PR_noValue;
+      ASN_SEQUENCE_ADD (&measure_record->list, nv);
+    }
   measure_data_item->measRecord = *measure_record;
@@ KpmIndicationMessage::FillKpmIndicationMessageFormat1 (…)   // ~line 1006
       MeasurementDataItem_t *measureDataItem = _pairInfo.second;
+      if (measureDataItem == nullptr)
+        measureDataItem = getMesDataItem (0.0);   // existing real-valued builder, 1 record
       ASN_SEQUENCE_ADD (&measurementDataList->list, measureDataItem);
```

(`getMesDataItem(double)` exists at ~900-940; using it for the nullptr case keeps info/data lists
aligned, which the non-standard "data[i] belongs to info[i]" layout relies on.)

### How to test

`./start_sim_stack.sh -g 2 -u 4 -t 20 -x capture` on a nearRT-RIC built **without** patch 0004
(or with the assert temporarily restored): no abort, `kpm.csv` contains `L3neighSINRListOf_UEID_*` rows
for every UE, with an empty `value` (NO_VALUE) where the UE has no neighbour. Then `-g 1 -u 2` for the
latent nullptr case.

### Impact on AppWeaver

- Parsers: `xapp_kpm_capture.c` (86-98) and the actuator (528-534) print any non-integer/non-real record
  as an empty `value` field, and `run_twin_validation.KpmState._row` drops rows whose `value` is empty, so a
  `noValue` neighbour record is ignored rather than becoming a 0 dB candidate for `_best_target`. No
  AppWeaver change needed.
- T6: no numeric change (4 gNBs never hit the case). The 2-gNB and 1-gNB configurations become usable
  for cheaper Validate-2 what-ifs (wall cost ≈ 4.5× real time at 3 nodes/4 UEs, `APPWEAVER_SETUP.md` §8).
- Re-run: the 2-gNB repro only.

---

## 3. A gNB reports only once its PRB average passes the subscription threshold

### Root cause (by design of the fork, with an unhelpful default)

- The KPM RAN function definition advertises one REPORT style with action-definition format 4
  (`contrib/oran-interface/model/kpm-function-description.cc` 150-200); the subscription parser
  (`oran-interface.cc` 185-345) stores `Action Definition Format`, `Test Condition Type/Expression/Value`,
  `Granularity Period` in a **single per-node map** (`subs_details`, last subscription wins).
- `MmWaveEnbNetDevice::KpmSubscriptionCallback` (`mmwave-enb-net-device.cc` 226-293) handles only
  `actionDefinition_Format4`; every other format logs `Action Definition NOT supported` and **never
  starts reporting** although the subscription was acknowledged.
- For format 4 it schedules `CheckReportingFlag` every `m_checkPeriod` = 100 ms (ctor, 384).
  `CalculatePrbAverage` (111-162) pushes one sample per call and returns −1 until exactly
  `MAX_PRB_HISTORY` = 10 samples are present (then keeps a sliding window), so the **earliest possible
  first indication is 1.0 s of simulated time after the subscription**, whatever the threshold. The test is
  `MATH_CALL_BACKS[expr](avg, threshold)` (equal/greater/less); once true, `m_isReportingEnabled` latches
  and reporting never stops (the `else` branch at 203-208 only re-sets the flags).
- The PRB average is a cell-level estimate (`macNumberOfSymbols / (slots × 14) × 139` summed over UEs,
  capped at 100 %), not the `RRU.PrbUsedDl` values in the reports, so a threshold in the subscription and a
  threshold on the reported KPI are not the same quantity.
- The LTE anchor (`lte-enb-net-device.cc` 82-97) ignores the condition and reports immediately — hence
  cell 1 always leads the other nodes in `kpm.csv`.

### Fix options

| Option | Where | Effort | Risk |
|---|---|---|---|
| 3.1 Start immediately when the condition is trivially true (`lessthan` with value ≥ 100, `greaterthan` with value < 0) or when the format is not 4 (treat as periodic) | ns-3 enb device, ~25 lines | small | none for AppWeaver (uses `< 101`); the shipped ES xApp (`< 40`) keeps its semantics |
| 3.2 Make `MAX_PRB_HISTORY` and `m_checkPeriod` ns-3 attributes (`E2PrbHistoryLen`, `E2PrbCheckPeriod`) | ns-3, ~15 lines | small | none |
| 3.3 Remove the gate altogether | ns-3 | small | breaks the fork's ES demo and its paper claim — do not |
| 3.4 xApp side: always subscribe with `KPM_PRB_LT=101` and tolerate the 1 s + E2-setup lead | AppWeaver | none | already the case |

### Recommended: 3.1 + 3.2 (`mmwave-LENA-oran-0002-kpm-immediate-report.patch`)

```diff
--- a/src/mmwave/model/mmwave-enb-net-device.cc
@@ MmWaveEnbNetDevice::KpmSubscriptionCallback
+  auto startNow = [this] () {
+    if (m_isReportingEnabled) return;
+    m_is_reported = true; m_isReportingEnabled = true;
+    Simulator::ScheduleWithContext (1, Seconds (0), &MmWaveEnbNetDevice::BuildAndSendReportMessage,
+                                    this, m_lastSubscriptionParams);
+  };
   const auto &sub_map = m_e2term->SubscriptionMapRef();
-  if (!sub_map.empty())
+  if (sub_map.empty () ||
+      std::any_cast<int> (sub_map.at ("Action Definition Format")) !=
+          E2SM_KPM_ActionDefinition__actionDefinition_formats_PR_actionDefinition_Format4)
+    { startNow (); return; }          // formats 1/2/3/5: plain periodic report
   …
         case E2SM_KPM_ActionDefinition__actionDefinition_formats_PR_actionDefinition_Format4:
           {
+            int const thr = std::any_cast<int> (sub_map.at ("Test Condition Value"));
+            bool const trivial = (index == TestCond_Expression_lessthan && thr >= 100) ||
+                                 (index == TestCond_Expression_greaterthan && thr < 0);
+            if (trivial) { startNow (); break; }
             m_prbHistory.clear();
@@ GetTypeId
+          .AddAttribute ("E2PrbHistoryLen", "Samples in the PRB moving average that gates KPM format-4 reporting",
+                         UintegerValue (10), MakeUintegerAccessor (&MmWaveEnbNetDevice::m_prbHistoryLen), MakeUintegerChecker<uint32_t> (1))
+          .AddAttribute ("E2PrbCheckPeriod", "Period of the PRB gate check", TimeValue (MilliSeconds (100)),
+                         MakeTimeAccessor (&MmWaveEnbNetDevice::m_checkPeriod), MakeTimeChecker ())
```

(`MAX_PRB_HISTORY` becomes `m_prbHistoryLen`; the `"Test Condition Value"` any-cast must guard the
non-int variants stored at `oran-interface.cc` 266-293 — wrap in the existing try/catch.)

### How to test

Capture with `KPM_PRB_LT=101`: the first gNB DU indication must appear in the same 100 ms period as the
subscription response (compare `collect_start_us` after P4, or count rows before the first gNB row vs cell
1). With `KPM_PRB_LT=40` behaviour must be unchanged versus `captures/es_cell_switch_off`.

### Impact on AppWeaver

- `run_twin_validation.py` estimates the first-report offset as `SIM_TIME − n_final × IND_PERIOD`
  (409-419), i.e. it assumes every node reports continuously to the end. With 3.1 the offset shrinks
  by ~1 s, `T_ACT = 1.5 s` after the first report moves earlier in the run and the KPI window grows by
  ~1 s: **both T6 batches must be re-run** and the numbers in `TWIN_VALIDATION.md` refreshed (energy
  deltas will move slightly because the window is longer).
- Validate-2: the gate's latency budget (one ns-3 run ≈ 3–4 min wall for 8 sim-s) improves by ~25 s
  wall per run; more importantly the twin can act on the first second of the run.
- Energy-saving workflow with the shipped ES xApp threshold `< 40` is unusable for a loaded cell (it
  never reports); AppWeaver should keep `< 101` and apply its own load logic in the rApp.
- Do **not** rely on different thresholds per agent for the multi-agent experiment: one map per node.

---

## 4. Indication timestamps are wall-clock, not simulated time

### Root cause

`MmWaveEnbNetDevice::BuildRicIndicationHeader` (`mmwave-enb-net-device.cc` 925-947) computes
`headerValues.m_timestamp = m_startTime + Now().GetMilliSeconds()` — but `m_startTime` is never set
(`SetStartTime` at 1745 has no caller; the scenario's `m_startTime` is a local in `PrintPosition`), and
`KpmIndicationHeader::FillAndEncodeKpmRicIndicationHeader` (`kpm-indication.cc` 236-257) ignores
`values.m_timestamp` entirely: `colstartTime = get_time_now_us ()` → `time_now_us_clck ()` →
`clock_gettime (CLOCK_REALTIME)` (118-141), byte-swapped with `ntohll` into the 8-byte
`colletStartTime` OCTET STRING. So `collect_start_us` in `kpm.csv` is host time at encoding, which at
25× slowdown bears no fixed relation to simulated time; `analyze_kpm_capture.py` and
`run_twin_validation.KpmState` therefore count DU indications per node instead.

### Fix options

| Option | Where | Effort | Risk |
|---|---|---|---|
| 4.1 Encode `Simulator::Now().GetMicroSeconds()` in `colletStartTime` | ns-3, 3 lines | trivial | the three reports of one period (CU-UP, CU-CP, DU) get the **same** stamp; consumers that keyed on distinct stamps per report must key on (stamp, report type) |
| 4.2 Same, plus a wall-clock epoch offset attribute (`E2TimestampEpochUs`, default 0) for consumers that want "real-looking" times | ns-3, +8 lines | small | none |
| 4.3 Leave it; keep count × period | — | none | fragile: a dropped/late report shifts every later estimate, and the offset estimate in T6 assumes no gaps |

### Recommended: 4.1 (+4.2 if cheap), `oran-interface-0003-sim-time-collect-start.patch`

```diff
--- a/contrib/oran-interface/model/kpm-indication.cc
@@ FillAndEncodeKpmRicIndicationHeader
-  colstartTime = get_time_now_us ();
-  uint64_t original_time; memcpy (&original_time, colstartTime.buf, sizeof (uint64_t));
+  // Simulated time in microseconds (values.m_timestamp), not host time: the simulation runs ~25x slower
+  uint64_t original_time = values.m_timestamp;
--- a/src/mmwave/model/mmwave-enb-net-device.cc
@@ BuildRicIndicationHeader   (and the LTE equivalent in lte-enb-net-device.cc)
-      uint64_t timestamp = m_startTime + (uint64_t) time.GetMilliSeconds ();
+      uint64_t timestamp = m_startTime + (uint64_t) time.GetMicroSeconds ();   // m_startTime: epoch offset, default 0
```

Initialise `m_startTime (0)` in both constructors (it is currently uninitialised garbage). The
`cu-*/du-*` CSV traces use the same `m_startTime + ms` expression (1065, 1253, 1584, …) and become
consistent with the E2 stream for free. Leave `get_time_now_us()` in place for anyone wanting the wall
clock; or expose `E2WallClockTimestamps` (bool, default false) if the fork's GUI needs it.

### How to test

Capture 10 sim-s with `-p 0.1`: `collect_start_us` of DU rows per gNB must be an arithmetic progression
with step 100 000 and the first value ≈ (E2 setup + 1 s gate, or ~0.1 s after P3) × 1e6; the energy file
timestamps (`energyfilecell*.csv`, written with sim time) must align within one period.

### Impact on AppWeaver

- `run_twin_validation.KpmState`: `ind_index[nb_id][collect_start]` still works (one DU stamp per
  period) but `sim_time()` can become `max(collect_start)/1e6` and `offset = first_collect_start/1e6` —
  exact, no end-of-run estimate. `act_sim_time_s`, `first_report_sim_s`, and the KPI window then no
  longer depend on `n_final`. Update the comment at 409-419 and `analyze_kpm_capture.py`'s docstring.
- `APPWEAVER_SETUP.md` §5 bullet "Header collectStartTime is wall-clock" → update.
- Re-run: T6 both batches (window boundaries shift by up to one period); the 60 s capture summary
  (`captures/kpm_60s_4gnb_10ue/summary.txt`) is unaffected numerically but its `collect_start_us` column
  changes meaning — regenerate so the archived capture matches the documented format.

---

## 5. Control limits: cells 1–9 only, no cell switch-on

### Root cause

**5a — single-digit cell id on both ends.**
ns-3 `RicControlMessage::GetTargetCell()` (`contrib/oran-interface/model/ric-control-message.cc` 263-293)
walks Target Primary Cell ID → CHOICE Target Cell → NR Cell → NR CGI, then

```c
uint8_t nr_cgi_value;
memcpy(&nr_cgi_value, NR_CGI.buf, NR_CGI.size);   // writes NR_CGI.size bytes into a 1-byte variable
uint16_t targetCellId = nr_cgi_value - 48;         // one ASCII digit
```

(a 2-byte CGI would overflow the stack variable). The xApp encoders write exactly one byte:
`char nr_cgi_str[1] = {targetcell}` + `assert(targetcell >= '0' && targetcell <= '9')`
(`~/flexric-taap/examples/xApp/c/orange/xapp_es_with_cell_util.c` 640, 701-705;
`evaluation/twin/xapp_appweaver_actuator.c` 102, 117, 163, 683, 693 — `'0' + a`). With cells
numbered 1 (LTE) and 2…N+1 (gNBs), N ≤ 8.

**5b — no switch-on.**
`MmWaveEnbNetDevice::ControlMessageReceivedCallback` (`mmwave-enb-net-device.cc` 748-870), case
`Energy_state` (= 300, `ric-control-message.h:49`): the action id is not inspected; for the matching
cell it schedules `SetBSTX (enbPhy, 0, cell_id, true)` after 15 ms (862). `SetBSTX` (726-746) is
`phy->SetTxPower (val)` + `SetNoiseFigure (val == 0 ? 100 : 5)`: "off" is 0 dBm with a 100 dB noise
figure (not a radio power-down; the energy trace goes flat because no UE stays attached, so the
energy model's state current drops, `mmwave-radio-energy-model-enb.cc` 337-341). The re-enable call is
commented out (864). Default TX power is 30 dBm (`mmwave-enb-phy.cc` 104-107).

**5c — handed-over UEs never regain autonomous mobility.** `TakeUeHoControl(imsi)` (`lte-enb-rrc.cc`
4072-4077) is called before every RC handover (`mmwave-enb-net-device.cc` 806) and
`m_e2ControlledUes` is never erased; the RRC's own SINR-based handover loop skips those UEs (4298-4302).
After a switch-on, UEs will not come back unless RC hands them back, and in long twin runs RC-touched UEs
behave differently from untouched ones.

### Fix options

| Option | Where | Effort | Risk |
|---|---|---|---|
| 5a.1 Decimal string of any length: encoders `snprintf("%u")`, decoder `std::stoi(std::string(buf,size))` | ns-3 (5 lines) + actuator (10 lines) + ES xApp (optional) | small | backward compatible with 1-digit senders; the `assert('0'..'9')` in `set_EUTRA_CGI` must go |
| 5a.2 Proper 36-bit NR CGI bit string | both sides, ~60 lines | medium | breaks the fork's own xApps; not needed |
| 5b.1 Honour `ctrl_act_id`: `'0'`/0 → off, `'1'`/1 → on with the saved TX power | ns-3, ~15 lines | small | none; `CELL_ON='1'` already defined in the actuator (:47) |
| 5b.2 Model a real power-down (phy stop + energy state OFF) | ns-3 energy model | medium-large | changes the energy numbers of T6 — do not now |
| 5c.1 `LteEnbRrc::ReleaseUeHoControl(imsi)` on handover completion, or RC style 300 action `'2'` = "release all E2 HO control on this cell" | ns-3, ~15 lines | small | changes UE behaviour after RC HO in the twin (auto-HO resumes): keep behind an attribute `E2HoControlSticky` (default true = today) so T6 is reproducible |

### Recommended: 5a.1 + 5b.1 now; 5c.1 behind an attribute

ns-3 (`oran-interface-0004-rc-multi-digit-cell.patch`, `mmwave-LENA-oran-0003-rc-cell-on.patch`):

```diff
--- a/contrib/oran-interface/model/ric-control-message.cc
@@ uint16_t RicControlMessage::GetTargetCell() const
-            uint8_t nr_cgi_value;
-            memcpy(&nr_cgi_value, NR_CGI.buf,NR_CGI.size);
-            uint16_t targetCellId = nr_cgi_value - 48 ;
-            return targetCellId ;
+            // ns-O-RAN convention: the "NR CGI" carries the cell id as a decimal ASCII string ("2", "12")
+            std::string s (reinterpret_cast<const char*> (NR_CGI.buf), NR_CGI.size);
+            return static_cast<uint16_t> (std::stoi (s));
--- a/src/mmwave/model/mmwave-enb-net-device.cc
@@ SetBSTX
-void SetBSTX (Ptr<MmWaveEnbPhy> phy, int val, uint16_t cellid, bool m_esON)
+void SetBSTX (Ptr<MmWaveEnbPhy> phy, double val, uint16_t cellid, bool m_esON)
 {
-  printf ("in function");
+  static std::map<uint16_t, double> savedTxPower;              // dBm before switch-off
   if (val == 0) { NS_LOG_UNCOND ("Cell turned off " << cellid …); savedTxPower[cellid] = phy->GetTxPower (); }
-  else { NS_LOG_UNCOND ("Cell turned on " …); }
+  else { if (savedTxPower.count (cellid)) val = savedTxPower[cellid]; NS_LOG_UNCOND ("Cell turned on " << cellid << " txPower " << val); }
   phy->SetTxPower (val);
@@ case RicControlMessage::ControlMessageServiceStyle::Energy_state:
         uint16_t targetCellId = controlMessage->GetTargetCell ();
+        long const act = controlMessage->m_e2SmRcControlHeaderFormat1->ric_ControlAction_ID;
+        bool const on = (act == '1' || act == 1);              // '0'/0 = CELL_OFF (today), '1'/1 = CELL_ON
         for (…) if (cell_id == targetCellId)
-            Simulator::ScheduleWithContext (1, MilliSeconds (15), &SetBSTX, enbPhy, 0, cell_id, true);
+            Simulator::ScheduleWithContext (1, MilliSeconds (15), &SetBSTX, enbPhy, on ? 30.0 : 0.0, cell_id, !on);
```

(`MmWaveEnbPhy::GetTxPower` exists, `mmwave-enb-phy.h:77-79`. A switched-on cell with no UE still shows
flat energy until a UE is handed to it; that is the energy model, not a bug.)

Actuator (`evaluation/twin/xapp_appweaver_actuator.c`): change `gen_Target_Primary_Cell_ID(…, char)`,
`set_EUTRA_CGI(…, char)`, `gen_rc_ctrl_msg_frmt_1_*(char)`, `gen_handover_rc_ctrl_msg(…, uint8_t)`,
`gen_cell_trigger_rc_ctrl_msg(…, char)` to take `uint16_t cell` and build the string once:

```c
char cell_str[8]; snprintf(cell_str, sizeof cell_str, "%u", cell);
byte_array_t nr_cgi = cp_str_to_ba(cell_str);       // replaces char nr_cgi_str[1] = {targetcell}
```

drop the two `assert(targetcell >= '0' && targetcell <= '9')`, and add the command
`ON <cell>` → `gen_rc_ctrl_hdr(FORMAT_1_E2SM_RC_CTRL_HDR, ue, ENERGY_STATE, CELL_ON)` next to the
`OFF` branch (~692). Same edit in `xapp_es_with_cell_util.c` only if the shipped ES demo must keep
working with >8 gNBs (it also caps at `MAX_REGISTERED_CELLS 10` / `MAX_REGISTERED_UES 20`, :102-104).

### How to test

1. `-g 4 -u 3` ES scenario, actuator commands `OFF 5` at 2.0 s, `ON 5` at 4.0 s, `HO <imsi> 5` at 4.5 s:
   `ns3.log` shows `Cell turned off 5` then `Cell turned on 5 txPower 30`; `energyfilecell5.csv` goes flat
   after 2.0 s and resumes after the handover; `ue_serving_cell.csv` shows the UE back on cell 5.
2. `-g 10 -u 10` (11 E2 nodes, cells up to 11): `HO <imsi> 11` and `OFF 11` are applied
   (`PerfomeE2RCHO(): … to CellId 11`), and a 1-digit `OFF 5` still works.

### Impact on AppWeaver

- Energy-saving workflow: the rApp can finally emit a *reversible* policy (sleep → wake when load
  returns); today a sleeping cell is lost for the rest of the run, so the ES chain is one-shot and the
  "switch back on" step of the workflow is untested. T6's protocol does not need to change for the
  existing numbers, but a wake-up variant becomes possible.
- Validate-2: switch-on lets the gate reuse one running twin for several candidate policies
  (switch off / wake up / hand back) instead of a fresh 3–4 min ns-3 run per candidate; combine with
  1.2 (xApp restarts) — this is the biggest wall-clock win available.
- Topologies > 8 gNBs become possible (cost ≈ linear in UEs × traffic, so 10 gNB/10 UE ≈ 4 gNB/10 UE).
- 5c: leave sticky (default) for T6 reproducibility; switch it off for long-horizon twin runs and say so
  in the run manifest.
- Re-run: ES closed loop capture (`captures/es_cell_switch_off`) as regression; T6 unchanged unless 5c
  is enabled.

---

## 6. Prioritised implementation plan

All patches go to `~/ns-oran-flexric/patches/` (numbering continues: `flexric-taap-0005-…`,
`e2sim-0001-…`, `oran-interface-0002…0004-…`, `mmwave-LENA-oran-0002…0003-…`) and `APPWEAVER_SETUP.md`
§2/§10 are updated. Build cost: FlexRIC `make -j12 && make install` in `~/flexric-taap/build` (~2 min);
e2sim `make -j12 && make install` in `e2sim-kpmv3/e2sim/build` then `./ns3 build -j14` in
`mmwave-LENA-oran` (static `libe2sim.a`, ~4.5 min per profile); the actuator via
`evaluation/twin/Makefile` (links `~/flexric-taap/build/src/xApp/libe42_xapp.a`, so rebuild it after
any FlexRIC rebuild). Nothing here touches `~/flexric`, ports 36421/36422/8088/8000/8091.

| # | Step | Problem | Size | Must re-run afterwards |
|---|---|---|---|---|
| 1 | FlexRIC `eq_xapp_ric_gen_id` fix (1.1) | P1a | 1 line | 2-xApp repro (§1 test 1) |
| 2 | e2sim: delete keeps connection, no `exit()`, drop on closed fd; ns-3 re-arm on new subscription (1.2) | P1b | ~20 lines | §1 tests 2–3; ES closed loop regression |
| 3 | RC multi-digit cell id, both sides (5a.1) + `ON` action and command (5b.1) | P5 | ~40 lines | §5 tests; ES closed loop regression |
| 4 | Sim-time `colletStartTime` (4.1/4.2) | P4 | ~10 lines | **T6 base + loadcal batches**, 60 s capture + `summary.txt`, `analyze_kpm_capture.py` docstring, `run_twin_validation.py` offset logic (simplify) |
| 5 | `noValue` record instead of empty list; nullptr guard (2.1) — keep FlexRIC 0004 | P2 | ~15 lines | 2-gNB/4-UE and 1-gNB captures (parsers already treat NO_VALUE as empty) |
| 6 | Immediate start for trivial/absent condition; history/period attributes (3.1/3.2) | P3 | ~40 lines | **T6 both batches again** (first report ≈1 s earlier → longer window); refresh `TWIN_VALIDATION.md` numbers |
| 7 | AppWeaver: `kpm_bus_service.py` sim collector profile wrapping `xapp_kpm_capture` (1.4) | P1 multi-agent | ~80 lines Python, AppWeaver side, independent of 1–6 | multi-agent KPM-sharing experiment |
| 8 | ns-3 N subscriptions per node + e2sim delete callback with ids (1.3) | P1c | ~150 lines | 2-xApp test (both CSVs identical); T6 regression (payload unchanged) |
| 9 | `uePositionFile` input for scenario-zero (see below) | Validate-2 placement sync | ~30 lines | new T6 "placement-synced" batch |
| 10 | `ReleaseUeHoControl` behind `E2HoControlSticky` (5c.1) | P5 side effect | ~15 lines | only runs that disable it |

Steps 1–4 are independent of each other and can land in one rebuild; do 4 and 6 before any new T6 batch
so the twin numbers are produced once, on the final indication clock. Step 8 is optional for AppWeaver
as long as step 7 exists; it becomes necessary only if an experiment needs agents with *different*
subscriptions on the same simulation.

**Step 9 sketch** (`scratch/scenario-zero-with_parallel_loging.cc`): add
`static GlobalValue g_uePositionFile("uePositionFile", "CSV imsi,x,y of initial UE positions", StringValue(""), MakeStringChecker())`;
at 689-701 if non-empty, replace `UniformDiscPositionAllocator` by a `ListPositionAllocator` filled from
the file (rows in IMSI order), keep `RandomWalk2dOutdoorMobilityModel` (or `ConstantPositionMobilityModel`
when a second flag `ueStatic=1` is given, so the twin reproduces a placement exactly). AppWeaver writes the
file from the live instance's `ue_position.txt` at t_act (`timestamp,id,x,y,type,cell,simid`; after step 4
the timestamp is sim ms). Note `ue_position.txt` is an **output** today (`PrintPosition`, 205-250);
`FABLE_REVIEW_AND_PLAN.md` §5.2 calls it an input and should be corrected.

## 7. What should not be fixed (and the AppWeaver workaround)

- **25–50× slowdown**: inherent (single-threaded full-PHY simulation). Workaround unchanged: plan in
  sim-time, ≤ 10 UEs, parallel instances on distinct `E2Port`/`E2LocalPort` (the twin runner already
  uses `36500 + 10·slot`).
- **Python SDK without KPM/RC** (`APPWEAVER_SETUP.md` §3): wrapping the C xApps (step 7) is cheaper and
  more robust than adding SWIG bindings to a pinned FlexRIC.
- **Subscription parameters ignored by ns-3** (names, period, granularity): accept; the period is the
  scenario flag, and all consumers get the same KPI set. Document it in the agent prompt so agents do not
  "re-subscribe with a shorter period" expecting a change.
- **"Off" = 0 dBm, not power-down** (5b.2): the energy deltas in T6 depend on this model; changing it
  would invalidate the published numbers. State it in the paper's limitations instead.
- **LTE anchor (cell 1) cannot be switched off / handed to**: scenario design; AppWeaver already excludes
  `nb_id < 2` from capacity cells (`KpmState._row`).
