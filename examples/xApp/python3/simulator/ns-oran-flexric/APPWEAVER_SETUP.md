# ns-O-RAN-flexric simulated RAN for AppWeaver — setup notes

Status (2026-10-27, host: i9-11900KB, 16 threads, 62 GB, Ubuntu 22.04.5, kernel 6.8, gcc 12.3, CMake 4.4.4):
built and verified end to end.

- 60 s-simulated KPM capture, 4 gNB + 1 LTE eNB + 10 UEs, time-varying PRB/throughput:
  `captures/kpm_60s_4gnb_10ue/` (`kpm.csv` 237,720 rows, `summary.txt`)
- One energy-saving closed loop (RC handover + RC cell switch-off, cell energy goes flat):
  `captures/es_cell_switch_off/`
- Start/stop: `./start_sim_stack.sh`, `./stop_sim_stack.sh` (logs in `/tmp/ns_oran_stack/`)
- 2026-10-28: fixes for the review `~/flexric/examples/xApp/python3/docs/FABLE_SIM_REVIEW.md`
  (subscription delete/re-arm, sim-time timestamps, noValue records, immediate reporting, RC cell ids
  > 9 and switch-on) — **see §11**. They change the indication clock: captures made before 2026-10-28
  (incl. the two in `captures/`) have wall-clock `collect_start_us` and a ≥1 s gated start.
- 2026-10-28 (later): gNB E2 reports read the 100 ms trace window instead of resetting it, aligned to
  the trace tick, and trace files get a valid run-id timestamp (§11 fixes 8–9). This changes gNB E2
  KPI values and the first-report stamp; re-run anything captured with the earlier 2026-10-28 build.

Nothing under `~/flexric`, `~/flexric/build`, `/usr/local/lib/flexric`, `~/openairinterface5g`, `~/oai`,
`~/oai-cn5g` was modified. This RIC listens on **36423 (E2) / 36424 (E42)**, so it runs alongside the
`~/flexric` RIC on 36421/36422 (verified: both were up at the same time).

## 1. What is where

| Component | Path | Version |
|---|---|---|
| ns-O-RAN-flexric | `~/ns-oran-flexric` | `1398bb8` (main, "CCC Support, RF Reconfiguration xApp…") |
| e2sim (KPM v3) | `~/ns-oran-flexric/e2sim-kpmv3` → installed to `~/ns-oran-flexric/e2sim-install` | `732d647` |
| ns-3 + mmWave + 5G-LENA | `~/ns-oran-flexric/mmwave-LENA-oran` | `3b4c4f10`, ns-3.42, nr `35eeab6d` (NR-v3.3), oran-interface `95fba5a` |
| FlexRIC (pinned) | `~/flexric-taap` (branch `oie-ric-taap-xapps`) | `f56d4487507c7ace392f1ec3f598e7eeda670acc` (exact README commit, built fine) |
| FlexRIC SM libs + conf | `~/flexric-taap/install/{lib/flexric,etc/flexric/flexric.conf}` | E2AP v1.01, KPM v3.00, RC v1.03, CCC (JSON) |
| AppWeaver KPM capture xApp | `~/flexric-taap/examples/xApp/c/appweaver/xapp_kpm_capture.c` | new |
| Local patches (reproducible) | `~/ns-oran-flexric/patches/*.patch` | see §2 |
| Capture analysis | `~/ns-oran-flexric/tools/analyze_kpm_capture.py` | new |

## 2. Local changes (why they exist)

All are in `patches/`; apply them to fresh clones with `git apply`.

1. **`flexric-taap-0001-conf-ports-and-install-prefix.patch`** — this FlexRIC hard-codes E2 port 36421
   and E42 port 36422 (`near_ric.c`, `e42_iapp.c`, `e42_xapp.c`) and the default paths
   `/usr/local/lib/flexric`, `/usr/local/etc/flexric/flexric.conf`. The patch:
   - adds `get_conf_port()` and reads `NEAR_RIC_PORT` / `E42_PORT` from `flexric.conf` (defaults
     36421/36422 if absent), used by the RIC and by every xApp;
   - compiles the default conf/lib paths from `CMAKE_INSTALL_PREFIX` (`-DFLEXRIC_INSTALL_PREFIX`), so the
     binaries in `~/flexric-taap/build` load `~/flexric-taap/install/...` without `-c/-p`
     (the scripts still pass `-c/-p` explicitly);
   - adds `examples/xApp/c/appweaver` to the build.
2. **`flexric-taap-0002-flexric-conf-ports.patch`** — `flexric.conf` gets
   `NEAR_RIC_PORT = 36423`, `E42_PORT = 36424` (installed copy: `~/flexric-taap/install/etc/flexric/flexric.conf`).
3. **`flexric-taap-0003-appweaver-kpm-capture-xapp.patch`** — the capture xApp (§6).
4. **`flexric-taap-0004-kpm-tolerate-empty-meas-records.patch`** — ns-O-RAN sometimes sends a KPM
   measurement-data item with **0 records** (seen with 2 gNBs: a UE with no neighbour cell), which the
   spec forbids; stock FlexRIC then aborts the whole nearRT-RIC
   (`dec_meas_data.c:24: Assertion meas_record_len >= 1 ... failed`). The patch accepts 0 in the
   KPM v3 decoder/encoder/copy.
5. **`mmwave-LENA-oran-0001-e2sim-prefix.patch`, `oran-interface-0001-e2sim-prefix.patch`** — ns-3
   hard-codes `/usr/local/include/e2sim` and `/usr/local/lib`; replaced by a cache variable
   `E2SIM_PREFIX` (default `/usr/local`) plus `link_directories` at top level (the nr module links
   `-le2sim` too). This avoids the README's `sudo dpkg -i e2sim-dev*.deb`.
6. 2026-10-28 review fixes (§11): `flexric-taap-0005`, `flexric-taap-0006`, `e2sim-0001`,
   `mmwave-LENA-oran-0002`, `mmwave-LENA-oran-0003` (`uePositionFile`), `mmwave-LENA-oran-0004`
   (E2 report window, trace start time), `oran-interface-0002`, `nr-0001`, and `appweaver-actuator-0001` (for
   `~/flexric/examples/xApp/python3/evaluation/twin/xapp_appweaver_actuator.c`, not applied there).

## 3. Rebuild from scratch (exact commands)

No apt packages had to be installed: every required one was already present
(`build-essential git cmake libsctp-dev autoconf automake libtool bison flex libboost-all-dev
nlohmann-json3-dev libsqlite3-dev libpcre2-dev python3-dev libc6-dev swig 4.1`).
Not installed (optional, not needed for the mmWave scenarios): `libeigen3-dev` (5G-LENA MIMO
speedups; ns-3 configures "Eigen3 support: OFF"), `sqlite3` CLI, `g++-13` (README asks for it; gcc 12.3
builds everything), Python 3.8 (only used by the GUI trigger scripts; not needed), Docker GUI.

```bash
# --- sources
git clone https://github.com/Orange-OpenSource/ns-O-RAN-flexric ~/ns-oran-flexric
cd ~/ns-oran-flexric && git submodule update --init --recursive
#   (prints "Failed to recurse into submodule path 'e2sim-kpmv3'": a dangling gitlink
#    e2sim/e2sm_examples/kpm_e2sm/nlohmann_json_release without .gitmodules entry; harmless,
#    nlohmann-json3-dev is used instead)
git clone https://gitlab.eurecom.fr/mosaic5g/flexric.git ~/flexric-taap
cd ~/flexric-taap && git checkout f56d4487507c7ace392f1ec3f598e7eeda670acc
git apply ~/ns-oran-flexric/patches/flexric-taap-000{1,2,3,4,5}-*.patch
patch -p1 < ~/ns-oran-flexric/patches/flexric-taap-0006-kpm-capture-sigint-after-init.patch   # file added by 0003
cd ~/ns-oran-flexric/mmwave-LENA-oran && git apply ../patches/mmwave-LENA-oran-000{1,2,3,4}-*.patch
(cd src/nr && git apply ../../../patches/nr-0001-sim-time-indication-header.patch)
cd contrib/oran-interface && git apply ../../../patches/oran-interface-000{1,2}-*.patch
cd ~/ns-oran-flexric/e2sim-kpmv3 && git apply ../patches/e2sim-0001-subscription-delete-keeps-connection.patch

# --- FlexRIC (separate build + private install prefix; ~2 min)
cd ~/flexric-taap && mkdir -p build install && cd build
PY=~/anaconda3/envs/flexric-py310
cmake .. -DE2AP_VERSION=E2AP_V1 -DKPM_VERSION=KPM_V3_00 \
  -DXAPP_MULTILANGUAGE=ON -DXAPP_TARGET_LANGUAGE=PYTHON_LANG \
  -DCMAKE_INSTALL_PREFIX=$HOME/flexric-taap/install \
  -DPython3_EXECUTABLE=$PY/bin/python3.10 -DPYTHON_EXECUTABLE=$PY/bin/python3.10 \
  -DPYTHON_INCLUDE_DIR=$PY/include/python3.10 -DPYTHON_LIBRARY=$PY/lib/libpython3.10.so \
  -DUNIT_TEST=FALSE
make -j12 && make install        # no sudo: installs into ~/flexric-taap/install

# --- e2sim (no sudo/dpkg; ~1 min)
cd ~/ns-oran-flexric/e2sim-kpmv3/e2sim && mkdir -p build && cd build
cmake .. -DDEV_PKG=1 -DLOG_LEVEL=2 -DCMAKE_INSTALL_PREFIX=$HOME/ns-oran-flexric/e2sim-install
make -j12 && make install

# --- ns-3.42 + mmWave + 5G-LENA + oran-interface (~4.5 min per profile with -j14)
cd ~/ns-oran-flexric/mmwave-LENA-oran
./ns3 configure --build-profile=optimized --enable-logs --disable-python --disable-tests \
  --disable-examples --disable-werror -- -DE2SIM_PREFIX=$HOME/ns-oran-flexric/e2sim-install
./ns3 build -j14
```

Notes:
- `--enable-logs` matters: the scenarios print progress, UE positions/serving cell and per-cell
  energy via `NS_LOG_UNCOND`, which the plain `optimized` profile compiles out.
- The `default` profile was also built (binaries `build/scratch/ns3.42-*-default`, run with
  `PROFILE=default`); it is ~2.5× slower (§8). Re-running `./ns3 configure` switches the CMake cache
  between profiles; both sets of binaries stay in `build/`.
- FlexRIC Python SDK: `~/flexric-taap/build/examples/xApp/python3/{xapp_sdk.py,_xapp_sdk.so}` is
  built for Python 3.10 (`flexric-py310`), but **this branch's SWIG SDK has no KPM/RC/CCC bindings**
  (only MAC/RLC/PDCP/GTP/slice), so Python xApps cannot talk to the ns-3 nodes. Use the C xApps.

## 4. Running the stack

```bash
cd ~/ns-oran-flexric
./start_sim_stack.sh -g 4 -u 10 -t 62 -x capture   # RIC + scenario-zero + KPM->CSV capture
./stop_sim_stack.sh
```

`start_sim_stack.sh [-g N_GNB] [-u N_UE] [-t SIM_TIME_S] [-s SCENARIO] [-p IND_PERIOD_S] [-x capture|kpm|es|none] [-- extra ns-3 flags]`

| Option / env | Default | Meaning |
|---|---|---|
| `-g` | 4 | `--N_MmWaveEnbNodes` (gNBs; plus 1 LTE eNB always present → `N_GNB+1` E2 nodes) |
| `-u` | 10 | `--N_Ues`: total UEs in `scenario-zero*`; **UEs per cell** in `Energy_saving_*` (3 → 15 UEs) |
| `-t` | 100 | `--simTime` (simulated seconds) |
| `-s` | `scenario-zero-with_parallel_loging` | binary `build/scratch/ns3.42-<SCENARIO>-<PROFILE>` |
| `-p` | 0.1 | `--indicationPeriodicity` (s of sim time between KPM reports) |
| `-x` | none | `capture` → `$LOG_DIR/kpm.csv`; `kpm` → `xapp_kpm_rc_Enhanced`; `es` → `xapp_es_with_cell_util` |
| `-P` | — | initial UE positions file → `--uePositionFile=<abs path>` (scenario-zero* only, §11 fix 7) |
| `PROFILE` | optimized | `optimized` or `default` binaries |
| `LOG_DIR` | `/tmp/ns_oran_stack` | `ric.log`, `ns3.log`, `ns3.cmd`, `xapp_*.log`, `kpm.csv`, `*.pid`, `ns3_out/` (scenario trace files) |
| `ISD_CELLS`, `ISD_UES`, `CENTER_FREQ`, `BANDWIDTH` | 600, 500, 3.5e9, 20e6 | scenario geometry/carrier flags |
| `E2_PORT` | from `flexric.conf` (36423) | passed to ns-3 as `--ns3::MmWaveHelper::E2Port=` |
| `E2_HELPER` | `MmWaveHelper` (`NrHelper` for `RF_*`, `orange-*`, `opl_nr_*`) | which helper owns `E2Port` |

The script waits until all `N_GNB+1` nodes logged `Received SETUP-RESPONSE-SUCCESS` (gives up after
300 s), then starts the xApp. `stop_sim_stack.sh` signals only the PIDs recorded in `$LOG_DIR`
(xApp → ns-3 → RIC), never `~/flexric`'s RIC.

Manual equivalent (what the script runs):
```bash
R=~/flexric-taap; C=$R/install/etc/flexric/flexric.conf; L=$R/install/lib/flexric/
$R/build/examples/ric/nearRT-RIC -c $C -p $L                              # E2 36423, E42 36424
cd /some/output/dir && LD_LIBRARY_PATH=~/ns-oran-flexric/mmwave-LENA-oran/build/lib \
  ~/ns-oran-flexric/mmwave-LENA-oran/build/scratch/ns3.42-scenario-zero-with_parallel_loging-optimized \
  --e2TermIp=127.0.0.1 --ns3::MmWaveHelper::E2Port=36423 --hoSinrDifference=3 \
  --indicationPeriodicity=0.1 --simTime=62 --KPM_E2functionID=2 --RC_E2functionID=3 \
  --N_MmWaveEnbNodes=4 --N_Ues=10 --CenterFrequency=3.5e9 --Bandwidth=20e6 \
  --IntersideDistanceUEs=500 --IntersideDistanceCells=600
KPM_CSV=/tmp/kpm.csv $R/build/examples/xApp/c/appweaver/xapp_kpm_capture -c $C -p $L [-t SECONDS]
$R/build/examples/xApp/c/orange/xapp_es_with_cell_util -c $C -p $L
```

Other scenario flags (all scenarios in `scratch/`, ns-3 `GlobalValue`s): `--e2TermIp`, `--KPM_E2functionID`
(2), `--RC_E2functionID` (3), `--N_MmWaveEnbNodes` (uint8), `--N_Ues` (uint32), `--CenterFrequency`,
`--Bandwidth`, `--IntersideDistanceUEs`, `--IntersideDistanceCells`, `--indicationPeriodicity`,
`--simTime`, `--hoSinrDifference`, `--handoverMode` (DynamicTtt), `--outageThreshold`, `--bufferSize`,
`--e2lteEnabled/--e2nrEnabled/--e2du/--e2cuUp/--e2cuCp` (which reports to send),
`--reducedPmValues`, `--enableE2FileLogging` (file-only mode, no RIC), `--controlFileName`,
`--enableTraces`. UE traffic: per-UE UDP CBR downlink 200 B every 500 µs (3.2 Mb/s); UE mobility
`RandomWalk2dOutdoorMobilityModel`.

## 5. KPM (v3.00) — what the nodes emit

E2 nodes: LTE eNB = `nb_id 1` (cell 1), gNBs = `nb_id 2..N_GNB+1` (cells 2..). All register RAN
function 2 (KPM), 3 (RC), and the 5G-LENA nodes also 4 (CCC).

- The KPM RAN function definition advertises **one REPORT style 4 (format 4, "UE-level, matching
  condition") with a single unnamed measurement**; the node ignores the requested names and always
  reports its fixed KPI set. Subscribing with explicit names is pointless.
- Matching condition: gNBs start reporting only once their running **average PRB utilisation**
  (`E2PrbHistoryLen` = 10 samples, one per `E2PrbCheckPeriod` = 100 ms) satisfies the subscription test
  `IsStat <op> N` (`op` = equal/greater/less); once started they keep reporting every
  `indicationPeriodicity`. Since §11 fix 6 a condition that is always true (`< N` with N ≥ 100,
  `> N` with N < 0) or a format other than 4 starts reporting **at once** (before: ≥ 1 s of sim time,
  and never for formats 1/2/3/5). The ES xApp uses `< 40` (still gated); the capture xApp uses
  `< $KPM_PRB_LT` (default 101 = immediate).
- One subscription is served per node (§11 fix 2): further subscriptions are acknowledged but get no
  indications until the served one is deleted; deletes of non-served subscriptions are only acknowledged.
  Subscription parameters (names, period) are ignored; one node-wide condition map (last subscription wins).
- Indications are KPM format 3 (per-UE list of format-1 reports). UE id: the IMSI as an ASCII string
  packed little-endian into `amf_UE_NGAP_ID` (`ran_UEID` is junk). Layout is non-standard:
  `meas_data[i]` carries all records of `meas_info[i]`. Header `collectStartTime` (`collect_start_us`
  in the CSV) is **simulated time in µs** since §11 fix 4 (before: host wall-clock µs); the CU-UP,
  CU-CP and DU reports of one period carry the same stamp.
- gNB report window (§11 fix 8): a gNB report is sent 1 ns before each 100 ms trace tick (stamped with
  the tick, so gNB stamps are multiples of 100 000 µs) and reads, without resetting, the counters the
  trace loggers reset at every tick. Each gNB report therefore covers exactly the 100 ms window of the
  `du-cell-<id>.txt`/`cu-up-cell-<id>.txt` row written at the same tick, independent of when the xApp
  subscribed: same seed → same E2 values. The first gNB report comes at the first tick after the
  subscription. `RRU.PrbUsedDl.UEID` is the trace value truncated to an integer;
  `DRB.UEThpDl.UEID` is the current window's RLC-based rate (the du-cell trace row prints the
  previous tick's value). With `indicationPeriodicity` ≠ 0.1 s a report still covers only the last
  100 ms. The LTE eNB (own counters, no trace loggers) keeps reporting at subscription phase.
- A UE without neighbour cell (always with 2 gNBs) gets one `noValue` record in
  `L3neighSINRListOf_UEID_*` (§11 fix 5); the capture CSV shows an empty `value`.
- There is no cell-aggregate PRB metric; sum `RRU.PrbUsedDl.UEID` over UEs.

Measurement names observed in the 60 s capture (rows per name, 608 indications/gNB):

| Node | Report | Names |
|---|---|---|
| eNB (cell 1) | CU-UP | `DRB.PdcpSduVolumeDl_Filter.UEID` (kbit), `Tot.PdcpSduNbrDl.UEID`, `DRB.PdcpSduBitRateDl.UEID`, `DRB.PdcpSduDelayDl.UEID` |
| eNB | CU-CP | `DRB.EstabSucc.5QI.UEID`, `DRB.RelActNbr.5QI.UEID` |
| gNB | DU (23 per UE) | `TB.TotNbrDl.1.UEID`, `TB.TotNbrDlInitial.UEID`, `TB.TotNbrDlInitial.{Qpsk,16Qam,64Qam}.UEID`, `TB.ErrTotalNbrDl.1.UEID`, `QosFlow.PdcpPduVolumeDL_Filter.UEID`, `RRU.PrbUsedDl.UEID`, `CARR.PDSCHMCSDist.Bin{1..6}.UEID`, `L1M.RS-SINR.Bin{34,46,58,70,82,94,127}.UEID`, `DRB.BufferSize.Qos.UEID`, `DRB.UEThpDl.UEID` (kbit/s) |
| gNB | CU-UP | `QosFlow.PdcpPduVolumeDL_Filter.UEID`, `DRB.PdcpPduNbrDl.Qos.UEID`, `DRB.PdcpSduVolumeDL` |
| gNB | CU-CP | `DRB.EstabSucc.5QI.UEID`, `DRB.RelActNbr.5QI.UEID`, `L3servingSINR3gpp_cell_<c>_UEID_<imsi>` (dB), `L3neighSINRListOf_UEID_<imsi>_of_Cell_<c>` (records alternate SINR (real) / neighbour cell id (int), up to 8 neighbours) |

Time variation (from `captures/kpm_60s_4gnb_10ue/summary.txt`, per-cell sums per indication):

| Cell | DRB.UEThpDl [kbit/s] min/mean/max (distinct values) | RRU.PrbUsedDl min/mean/max (distinct) |
|---|---|---|
| 2 (7 UEs) | 0 / 9494 / 11807 (475) | 0 / 20.0 / 119 (19) |
| 3 | 0 / 2017 / 2839 (405) | 0 / 6.5 / 49 (4) |
| 4 | 0 / 2139 / 2839 (382) | 0 / 5.1 / 119 (5) |
| 5 | 0 / 1930 / 2839 (386) | 0 / 8.4 / 119 (7) |

`DRB.BufferSize.Qos` summed over cell 2's UEs ranges 1.0e6…3.1e7 (cell overloaded: 7 UEs × 3.2 Mb/s); the other cells stay at 230.
PRB values are coarse (multiples of the per-slot allocation, often 0/39) — PRB is the noisiest KPI.

## 6. AppWeaver KPM capture xApp

`xapp_kpm_capture [-c conf -p libdir] [-t SECONDS]`, env `KPM_CSV` (output file; else stdout, mixed
with SDK logs), `KPM_PRB_LT` (matching threshold, default 101), `KPM_DEBUG=1` (dump the raw
indication structure to stderr). Subscribes on every connected node, one callback trampoline per node
(the SDK callback has no node id), max 32 nodes. CSV columns:

`wall_us,collect_start_us,node_type,nb_id,ue_imsi,meas,idx,value`

Analyse with `python3 tools/analyze_kpm_capture.py kpm.csv [--out summary.txt]`.

## 7. Control: RC v1.03 and CCC

RC is RAN function 3. ns-3 (`MmWaveEnbNetDevice::ControlMessageReceivedCallback`) dispatches on the
control header (format 1) `ric_style_type` / `ctrl_act_id`; the UE id is E2SM gNB UE id with the IMSI
in `ran_UEID` bytes.

| Style (`ric_style_type`) | Action id | Effect in ns-3 | Parameters |
|---|---|---|---|
| 3 Connected Mode Mobility | 1 Handover Control | `LteEnbRrc::PerformE2RCHO(imsi, targetCell)` on the serving cell | UE IMSI in header; target cell in msg format 1: Target Primary Cell ID → CHOICE Target Cell → NR Cell → NR CGI (bit string carrying the cell id as a **decimal ASCII string of any length**, e.g. `"12"`, since §11 fix 3; before: one digit '1'..'9') |
| 3 | 2 Conditional HO, 3 DAPS HO | "Unsupported" | — |
| 300 Energy state (custom) | `'0'` = CELL_OFF | `SetBSTX`: TX power 0 dBm + noise figure 100 dB on the mmWave cell whose id matches (saves its TX power); no UE stays attached, energy flat | target cell id as same NR CGI structure; can be sent to any node |
| 300 | `'1'` (or 1) = CELL_ON (§11 fix 3) | `SetBSTX`: restores the saved TX power (30 dBm) and noise figure 5 dB. UEs do **not** come back by themselves (RC-handed-over UEs stay under E2 HO control) — hand them back with RC HO | same |
| 1 Radio Bearer Control, 2 Radio Resource Allocation | any | "Unsupported RIC Style Type" | — |

"Off" is not a radio power-down (energy deltas come from UEs leaving the cell). The
advertised RC RAN function definition only lists "Radio Bearer Control / QoS flow mapping
configuration", which is why `xapp_kpm_rc_Enhanced` sends that (ns-3 ignores it).
Reference encoder: `gen_handover_rc_ctrl_msg`, `gen_cell_trigger_rc_ctrl_msg`, `gen_rc_ctrl_hdr` in
`~/flexric-taap/examples/xApp/c/orange/xapp_es_with_cell_util.c`.

CCC (RAN function 4, JSON encoding, 5G-LENA `NrGnbNetDevice` only, scenarios `RF_Reconfiguration`,
`orange-rf-channel-reconfiguration`, `rf-channel-reconfiguration-scenario`): control header format 1,
service style 2, message format 2 whose `listOfCellsControlled` JSON is
`[{cellGlobalId:{nR-CGI:{pLMNIdentity, nRCellIdentity}}, listOfConfigurationStructures:[{ranConfigurationStructureName:"O-NESPolicy", oldValuesOfAttributes:{policyType:"TRX", antennaMask}, newValuesOfAttributes:{policyType:"TRX", antennaMask}}]}]`
→ switches gNB antenna ports on/off and rescales per-port power (`SetPortPower`). Reference: `xapp_rf_reconfiguration`
(`examples/xApp/c/orange/rf_reconfiguration_xapp.c`). **Not exercised in this setup** (the
LENA scenarios use their own flag set, not the `-g/-u` flags of the start script).

## 8. Wall-clock cost (measured on this host, single core, 100 %)

| Scenario / build | E2 nodes, UEs | Wall s per simulated s |
|---|---|---|
| scenario-zero, `default` profile | 5, 10 | ≈60 (0.7 sim-s during a 40 s capture) |
| scenario-zero, `optimized` + logs, no xApp | 5, 10 | 25 (4.8 sim-s / 120 s) |
| scenario-zero, `optimized` + logs, capture xApp | 5, 10 | 24.7 (61.9 sim-s / 1505 s) |
| scenario-zero, `optimized` + logs, capture xApp | 3, 4 | ≈4.5 |
| Energy_saving_with_cell_utilization, `optimized` + logs, ES xApp | 5, 15 | 52 (4.8 sim-s / 248 s) |

Startup (topology build + E2 setup of all nodes) adds ~10–60 s. Cost grows roughly with UEs × traffic
(each UE gets 3.2 Mb/s CBR through the full PHY). ns-3 is single-threaded: several independent
simulations can run in parallel only with different RIC ports *and* different
`--ns3::MmWaveHelper::E2LocalPort` (default 38470+node).

## 9. Energy-saving run (verified)

```bash
./start_sim_stack.sh -s Energy_saving_with_cell_utilization_scenario -g 4 -u 3 -t 120 -x es
```

Result (`captures/es_cell_switch_off/`): the ES xApp received KPM, marked cell 2 (≤1 UE) for shutdown,
sent RC handover of IMSI 6 cell 2 → 3 (applied at sim t = 1.6 s, `ue_serving_cell.csv`), then RC
style 300 CELL_OFF for cell 2; ns-3 printed `Cell Id 2`. Cell 2 energy (`energy_per_cell.csv`):
+93…167 J per 0.1 s until t = 1.6 s, then constant 2050.79 J (diff 0 J) from t = 1.7 s, while cells 3–5
keep consuming 140–300 J per 0.1 s.

## 10. Known problems

1. **One served KPM subscription per node.** *Fixed partly (§11 fixes 1–2):* a second xApp no longer
   crashes anything, an xApp can unsubscribe/exit without ending the simulation, and the next
   subscription restarts reporting. Still open: a second *concurrent* subscriber is acknowledged but
   gets no indications (review step 8, N subscriptions, deferred) → multiplex KPM through one xApp
   (KPM bus). Original crash logs: `logs/run2_second_subscriber_crash/`.
2. **Slow:** 25–50× slower than real time for 4 gNB/10–15 UE (§8). Plan agent experiments in sim-time,
   keep UE count/traffic small, or run several scenarios in parallel (16 threads).
3. ~~RC target cell id is a single ASCII digit~~ fixed (§11 fix 3) in ns-3 and the AppWeaver actuator
   patch; the shipped ES xApp still encodes one digit and caps at 10 cells / 20 UEs per cell.
4. ~~No cell switch-on~~ fixed (§11 fix 3): style 300 action `'1'`. UEs handed over by RC stay under
   E2 HO control for the rest of the run (no autonomous HO; review step 10, not done).
5. ~~KPM `collectStartTime` is wall-clock~~ fixed (§11 fix 4).
6. ~~nearRT-RIC aborts on empty KPM record lists~~ ns-3 now sends `noValue` (§11 fix 5); FlexRIC
   patch 0004 is kept as a defensive change.
7. FlexRIC SDK prints to stdout; that is why the capture xApp writes CSV to `$KPM_CSV`.
8. `xapp_kpm_rc_Enhanced` subscribes with `period_ms = 1000`, prints without node ids and asserts on
   unexpected RC styles; it works as a demo but is unsuitable for data capture.
9. Scenarios write ~30 trace files to their CWD (and tracked `gnbs.txt`/`ue_position.txt` in the
   source tree); the start script runs them in `$LOG_DIR/ns3_out/`.
10. ns-3 CMake prints `uninitialized variable 'USERPROFILE'` and a deprecation warning
    (`cmake_minimum_required(VERSION 3.13..3.13)`) under CMake 4.4; harmless.
11. The nested `e2sim-kpmv3` gitlink `nlohmann_json_release` has no `.gitmodules` entry
    (`git submodule update --recursive` reports failure); harmless.
12. The Python FlexRIC SDK of this branch has no KPM/RC/CCC → AppWeaver's Python portal cannot use it
    directly; wrap the C xApps (CSV/stdout) or add SWIG bindings later.
13. **CELL_OFF strands UEs (model limit).** Style 300 OFF only sets the gNB's TX power to 0
    (`SetBSTX`); nothing detaches its UEs or makes them re-attach elsewhere, so UEs still served by
    the cell get no downlink for the rest of the run (twin re-run: 1–3 UEs in 14/31 runs with an OFF,
    also UEs RC had just handed over there). Hand the UEs over with RC before switching a cell off,
    or treat stranded UEs as an outcome of the policy. (Not traced further into the LTE RRC's
    mmWave-outage / switch-to-LTE path.)
14. **UEs outside coverage (scenario setting).** scenario-zero places UEs uniformly in a disc of
    `IntersideDistanceUEs` (default 500 m) around the centre, which reaches beyond usable mmWave
    coverage for some seeds: some UEs get no downlink at all even without any RC (twin re-run: 47 UEs
    in 21/53 no-op runs). Use a smaller `--IntersideDistanceUEs`, or `-P` positions (§4), and drop
    or report never-served UEs explicitly.
15. **Open: `malloc(): invalid size` aborts** in scenario-zero, 10 UEs: `RngRun=3` before 2 s
    (also before the §11 fixes) and `RngRun=7` ~0.1 s after RC `HO 6 2`; reproducible. Commands:
    `~/flexric/examples/xApp/python3/evaluation/runs/20261028T085338Z_T6v2_twin_vs_live_loadcal/runs/*s3*/ns3.cmd`,
    `*s7*/ns3.cmd` (+ `rc_commands.txt`). Not investigated yet (needs a debug/ASan build).

## 11. Fix log 2026-10-28 (review `~/flexric/examples/xApp/python3/docs/FABLE_SIM_REVIEW.md`)

All rebuilt (FlexRIC, e2sim, ns-3 `optimized`+logs) and regression-tested; the `default`-profile
binaries were **not** rebuilt (re-run `./ns3 configure --build-profile=default …` + build if needed).
Regression scripts: `tools/regress_kpm_subscriptions.sh` (2 gNB/4 UE, ~6 wall-min),
`tools/regress_rc_controls.sh` (10 gNB/3 UE), `tools/regress_ue_positions.sh`,
`tools/regress_kpm_window.sh` (2 × 20 s sim, ~4 wall-min). Results: §11.1.

| # | Problem (review §) | What changed | Where (patch) | Regression test |
|---|---|---|---|---|
| 1 | P1a: delete from xApp B hit xApp A's subscription | `eq_xapp_ric_gen_id()` compared `m0->xapp_id` with itself; now `m0` vs `m1` | `~/flexric-taap/src/ric/iApp/xapp_ric_id.c` (`flexric-taap-0005`) | subs test: B's deletes go out as RIC ids 1024–1026 (B's own), A unaffected |
| 2 | P1b: any subscription delete closed the SCTP socket → next indication `exit()`ed ns-3 | e2sim: delete no longer ends the run loop; `sctp_send_data` returns −1 instead of `exit()` (and `MSG_NOSIGNAL`); sends on a closed fd are dropped; e2sim exposes the RIC request id being deleted. ns-3 (gNB + LTE eNB): reporting state is changed on the simulator thread (`ArmKpmReporting`/`DisarmKpmReporting`, cancellable `EventId`s); one subscription is served, a delete only stops it if the ids match, a later subscription re-arms reporting | e2sim `e2ap_message_handler.cpp`, `e2sim_sctp.cpp`, `e2sim.{cpp,hpp}` (`e2sim-0001`); `mmwave-enb-net-device.*`, `lte-enb-net-device.*` (`mmwave-LENA-oran-0002`); `E2Termination::GetDeletingRequestId` (`oran-interface-0002`) | subs test: B ignored, A SIGINT → `deleted, reporting stopped` ×3, ns-3 runs on, C receives again, ns-3 reaches simTime |
| 2b | capture xApp ignored SIGINT (SDK `init_xapp_api()` overrides the handler → no deletes on stop) | install the handler after `init_xapp_api()` | `xapp_kpm_capture.c` (`flexric-taap-0006`); same in the actuator patch | subs test step "stop A" |
| 3 | P5: RC cell id 1 digit, no switch-on | ns-3 parses the NR CGI as a decimal string of any length; style 300 honours action `'1'`/1 = CELL_ON (restores saved TX power); actuator encodes `"%u"` and has `ON <cell>` | `ric-control-message.cc` (`oran-interface-0002`); `mmwave-enb-net-device.cc` (`mmwave-LENA-oran-0002`); actuator (`appweaver-actuator-0001`, built in `tools/actuator/build/`) | RC test: `OFF 11`, `ON 11` (txPower 30), `HO <imsi> 11`, `OFF 5` |
| 4 | P4: `collectStartTime` was host wall-clock | encoder uses the node's `m_timestamp` = `Simulator::Now()` in µs (gNB, LTE eNB, NR gNB) | `kpm-indication.cc` (`oran-interface-0002`); header builders (`mmwave-LENA-oran-0002`, `nr-0001`) | subs test: per-node stamps step exactly 100 000 µs, first 0.525 s, last 59.925 s for simTime 60 |
| 5 | P2: KPM records with 0 items | `L3neighSINRListOf…` with only the serving-cell marker gets one `noValue` record; a measurement item with no data gets a `noValue` item (keeps data[i]↔info[i]) | `kpm-indication.cc` (`oran-interface-0002`) | subs test (2 gNB): 1778/1778 neighbour rows are noValue, RIC never sees an empty list |
| 7 | Review step 9: no UE-position input for a placement-synced twin | GlobalValue `uePositionFile` in `scenario-zero-with_parallel_loging`: CSV `ue_index,x,y[,z]` (0-based = IMSI−1; header `imsi,x,y[,z]` switches to IMSI numbering; rows in any order; z default 0; `#` comments). Replaces the uniform-disc placement by a `ListPositionAllocator`; mobility after t = 0 unchanged (random walk 2–4 m/s, bounds 0…4000 m). Missing UEs, out-of-range ids or positions outside the bounds are fatal errors. `start_sim_stack.sh -P file` | `scratch/scenario-zero-with_parallel_loging.cc` (`mmwave-LENA-oran-0003`) | `tools/regress_ue_positions.sh`: both formats, t = 0 rows of `ue_position.txt` equal the file, UEs move afterwards |
| 8 | Twin validation (T6v2): E2 DU PRB differed up to 13× between same-seed runs | The gNB's E2 CU-UP/DU builders and the 100 ms trace loggers (`BuildGUI*`) read **and reset** the same PDCP/RLC/PHY counters, so an E2 report covered only the time since the last logger tick (0.3–98 ms, set by the wall-clock subscription time). Now the E2 builders only read (own throughput maps `m_e2DrbThr*`), and every gNB report is scheduled 1 ns before the next logger tick (`E2ReportDelay`, header stamp rounded to µs) → it covers the trace's 100 ms window | `mmwave-enb-net-device.*` (`mmwave-LENA-oran-0004`) | `tools/regress_kpm_window.sh`: same seed, xApp subscribing at 0.6 s vs 5.9 s → 1704 common DU values, 0 differ; PRB/TB values equal the du-cell trace rows (1552 + 1128, 0 differ); all gNB stamps on the 100 ms grid |
| 9 | Twin validation: du-cell/cu-*-cell trace timestamps used an uninitialised `m_startTime` | `MmWaveHelper::SetStartTime()` (default 0), passed to gNB **and** LTE eNB devices (`m_startTime{0}` in both); scenario-zero computes its run id before installing devices and passes it, so every trace = run id + sim ms like `ue_position.txt` (`simid`) | `mmwave-helper.*`, `*-enb-net-device.h`, `scenario-zero-with_parallel_loging.cc` (`mmwave-LENA-oran-0004`) | `tools/regress_kpm_window.sh`: all du-cell rows are `simid` + a multiple of 100 ms |
| 6 | P3: reporting gated ≥ 1 s / never for formats ≠ 4 | trivially true condition or non-format-4 → report at once; attributes `ns3::MmWaveEnbNetDevice::E2PrbHistoryLen` (10), `E2PrbCheckPeriod` (100 ms); the gate chain stops once reporting latches | `mmwave-enb-net-device.*` (`mmwave-LENA-oran-0002`) | subs test: all 3 nodes (LTE + 2 gNB) first stamp 0.525 s = subscription time |

Not done (review §6 steps 7, 8, 10): N concurrent subscriptions per node, releasing RC-handed-over UEs (`E2HoControlSticky`), and the AppWeaver KPM-bus collector
profile (AppWeaver side). Also not changed: the NR (5G-LENA) gNB's sticky stop on delete, the shipped
ES xApp's one-digit encoder, and §10 items 13–15 (found by the twin validation; 13–14 are model/scenario
limits, 15 is open).

Consequences for AppWeaver:
- `collect_start_us / 1e6` is the simulated time of the report; no more count × period estimate.
- The first gNB report comes at the subscription time (+ < 1 period) with `KPM_PRB_LT=101`, ~1 s
  earlier than before → **T6 batches must be re-run** (window boundaries and first-report offset change).
- After fix 8 gNB KPIs (PRB, TB counts, CU-UP volumes) are full 100 ms windows equal to the trace
  files, and the first gNB stamp is the next 100 ms tick after subscribing → twin/live comparisons
  made with the earlier 2026-10-28 build must be re-run.
- An xApp may now stop and a new one subscribe within one simulation (e.g. several candidate policies
  per twin run); with `ON <cell>` the energy-saving policy is reversible.
- The archived captures in `captures/` predate the fixes (wall-clock `collect_start_us`).
- The patched actuator source is `tools/actuator/xapp_appweaver_actuator.c`; apply
  `patches/appweaver-actuator-0001-*.patch` to `~/flexric/…/evaluation/twin/` (`patch -p1` from
  `examples/xApp/python3`) to adopt it there.

### 11.1 Regression results

After fixes 8–9 all four scripts were re-run on the rebuilt ns-3 — **ALL PASS**
(`logs/regress_2026-10-28/{window,subs,rc,pos}/`, files `*after_fix8*` and `window/`):
`regress_kpm_window.sh` as in the fix-8/9 rows; subscription test unchanged except that the gNBs'
first stamp is now 0.600 s (LTE eNB 0.527 s) and C's 11.000 s; RC test `OFF 11` 0.215 s, `ON 11`
txPower 30 1.217 s, `HO` IMSI 1 → 11 1.703 s, `OFF 5` 2.218 s; position test both formats.
The results below are from before fixes 8–9.

Logs: `logs/regress_2026-10-28/` (script outputs, RIC/xApp logs, filtered `ns3.log.xz`, `kpm*.csv.xz`).

`tools/regress_kpm_subscriptions.sh` (scenario-zero, 2 gNB + LTE eNB, 4 UEs, simTime 60 s,
capture xApps A/B/C) — **ALL PASS**:
- B subscribes while A runs → ns-3 `KPM subscription 1024/0 not served, node already reports to 1021/0`
  (per node); B gets 0 rows; B exits after 15 s → RIC sends deletes for **1024–1026** (B's own; before
  fix 1 they mapped to A's 1021) → ns-3 `RIC-SUBSCRIPTION-DELETE 1024/0 is not the served subscription`;
  A keeps receiving (4126 → 8471 gNB rows in 20 s).
- A stopped with SIGINT → 3 × `KPM subscription 102x/0 deleted, reporting stopped`; ns-3 keeps
  running, no `Bad file descriptor` (before fix 2 the process exited here).
- C subscribes → reporting re-armed, C receives; ns-3 reaches simTime 60 s.
- Clock: A's stamps per node 0.527 s … 7.427 s, C's 10.745 s … 59.945 s, every step exactly 100 000 µs;
  LTE eNB and both gNBs start in the same period (fix 6).
- noValue: all `L3neighSINRListOf…` rows (209 + 1474) carry an empty value (2 gNBs → no neighbour).

`tools/regress_rc_controls.sh` (scenario-zero, 10 gNB = cells 2…11 + LTE eNB, 3 UEs, simTime 6 s,
patched actuator) — **ALL PASS**:
`Cell turned off 11 at 1.0165 s`, `Cell turned on 11 txPower 30 at 2.01725 s`,
`2.50302s … Initiate handover for rnti 1 to  CellId 11` (IMSI 1 then reports from nb_id 11),
`Cell turned off 5 at 3.0188 s` (one-digit ids still work).

ES closed loop with the shipped `xapp_es_with_cell_util` (gated `IsStat < 40` path, unchanged
semantics; `Energy_saving_with_cell_utilization_scenario -g 4 -u 3 -t 3`): `Cell 2 marked for
shutdown`, `1.63825s … Initiate handover for rnti 1 to  CellId 3` (IMSI 6), `Cell turned off 2 at
1.65325 s` — same sequence and timing as `captures/es_cell_switch_off` (HO at 1.6 s). Logs:
`logs/regress_2026-10-28/es/`.

`tools/regress_ue_positions.sh` (2 gNB, 4 UEs, simTime 2 s, two runs) — **ALL PASS**: with
`ue_index,x,y,z` rows out of order (one without z) and with `imsi,x,y`, every UE's t = 0 row in
`ns3_out/ue_position.txt` equals the file exactly (e.g. IMSI 3 at 2300.5, 1800.25); by t = 1.9 s
the UEs have moved by 3–7 m.

Feeding a live run's positions to the twin: `ue_position.txt` rows are
`timestamp,id,x,y,type,cell,simid` with `id` = IMSI and `timestamp − simid` = simulated ms (one row per UE
every 100 ms). Take the rows with `timestamp − simid` = t_act, write `imsi,x,y` (header included) and
pass the file with `-P` (or `--uePositionFile=`). z is not in the trace; the default 0 equals the
uniform-disc placement's z. Only the position is synced: the twin's random-walk direction/speed after
t = 0 and the serving cell (initial attachment = closest eNB/gNB) are not.
