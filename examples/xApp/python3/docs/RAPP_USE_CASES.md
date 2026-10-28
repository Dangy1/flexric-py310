# rApp Directory extension: public use cases behind the new cards

Workstream E of the AppWeaver revision, 2026-10-28. The rApp Directory (`rapps/build_catalog.py`, which generates
`rapps/catalog.json`) grew from 16 to 32 families. In the same change the four FlexRIC L2 monitor cards
(MAC, RLC, PDCP, GTP) became executable read-only xApps backed by `xapp_l2_monitor.py`.

Each new card is modelled on a use case that is publicly documented in one of these places:
- a vendor rApp or xApp product page;
- an O-RAN Alliance specification or blog;
- a 3GPP SON or management specification.

This file holds the provenance. The directory-extension intents in `evaluation/intents_v2.json` cite rows of the
table below by anchor in their `provenance` field (`docs/RAPP_USE_CASES.md#E01`, …).

**Vendor names.** Real vendor and product names appear only in this file, as provenance. Every card in the
directory is an *emulated* rApp. Its vendor field uses the fictional vendors already in `build_catalog.VENDORS`
(Aalto 6G Lab, Northwind Radio, …), and its decision rule is a simple documented estimator in `rapps/runtime.py`.
No card describes or impersonates a commercial product. The A1 policy-type numbers on the cards (e.g. 20030) are
identifiers inside the emulation, not registered O-RAN policy types.

**How sources were checked.** Sources were collected by web search on 2026-10-28. Column "Seen" in the source
tables records how far each source was checked:
- **F**: the page or PDF was fetched and read.
- **L**: only the one-line description on the fetched Ericsson rApp Directory A–Z listing pages was read, not
  the product page itself.
- **S**: only seen as a search result. The source is not used alone for any row.

Use cases with no source found were left out, for example RAN sharing as a vendor rApp and an alarm
de-duplication rApp. O-RAN UC16 "Congestion Prediction and Management" is "Void" in the specification version
read, so it is not cited.

The source tables abbreviate long URLs:
- `EIAP/<slug>` stands for `https://www.ericsson.com/en/portfolio/cross-portfolio/rapp-directory/a-z-directory/<slug>`
  (Ericsson Intelligent Automation Platform rApp Directory, about 117 products from Ericsson and partners).
- O-RAN WG1 use cases are cited from **ETSI TS 104 036 V12.0.0** (2025-04), which is
  O-RAN.WG1.Use-Cases-Detailed-Specification R003 v12.00:
  <https://etsi.org/deliver/etsi_TS/104000_104099/104036/12.00.00_60/ts_104036v120000p.pdf> (F).
- 3GPP SON is cited from **ETSI TS 128 313 V17.9.0** (2024-01), 3GPP TS 28.313 "SON for 5G networks":
  <https://www.etsi.org/deliver/etsi_ts/128300_128399/128313/17.09.00_60/ts_128313v170900p.pdf> (F).
- TS 38.300 clauses were read on the itecspec.com mirror. Cite them by TS and clause number.

## Use-case table

In the table:
- *Card* is the registry id that the intents use (upper-cased in the chains).
- *Inputs* are the measurement names on the card. They are E2SM-KPM / TS 28.552 style names: a raw RAN
  measurement starts with `RRU.`, `DRB.`, `RRC.`, `CARR.` or `PEE.`.
- *Write scope* is the lease resource that the card's control scope declares. "read" means the card is
  read-only.

| ID | Use case | Card (family) | RIC / loop | Inputs (card `consumes`) | Outputs / policy (write scope) | Timescale |
|---|---|---|---|---|---|---|
| <a id="E01"></a>E01 | Automatic Neighbour Relation management: add missing NRs, remove or blocklist unwanted ones | `rapp.anr` (Neighbour Relation Manager) | non-RT rApp, O1 CM | `RRC.HO_attempts`, `RRC.HO_failures`; real inputs are UE measurement reports with neighbour PCI and the NCRT | NR create/delete, HO blocklist (`neighbour_relations`) | 15 min |
| <a id="E02"></a>E02 | PCI collision / confusion detection and resolution | `rapp.pci_optimization` (PCI Conflict Resolver) | non-RT rApp, O1 CM | `RRC.HO_failures`, `CARR.SINR_dist` | PCI reassignment, `nRPci` (`pci_config`) | hours |
| <a id="E03"></a>E03 | Sleeping-cell / cell-outage detection: a cell with no alarm but no traffic | `rapp.sleeping_cell` (Sleeping Cell Detector) | non-RT rApp | `RRU.PrbTotDl`, `DRB.UEThpDl`, `RRC.ConnMean` | sleeping-cell list (read) | 15 min |
| <a id="E04"></a>E04 | Mobility load balancing by cell individual offset (CIO) / HO-trigger change, cell-level | `rapp.mobility_load_balancing` (Cell Offset Load Balancer) | non-RT rApp, O1/A1 | `RRU.PrbTotDl`, `RRU.PrbTotUl`, `RRC.ConnMean` | CIO / HO-trigger deltas (`handover_offsets`); declared conflict with MRO handover-margin tuning | 15 min |
| <a id="E05"></a>E05 | RACH optimisation: PRACH configuration, root sequence index, zero-correlation zone | `rapp.rach_optimization` (RACH Optimizer) | non-RT rApp, O1 CM | `RRC.ConnEstabAtt`, `RRC.ConnEstabSucc`, `RRU.PrbTotUl`; real inputs are TS 28.552 RACH preamble / access-delay distributions and the UE RA report | PRACH / RSI / ZCZ (`rach_config`) | hours |
| <a id="E06"></a>E06 | Massive-MIMO grid-of-beams (GoB) beamforming optimisation | `rapp.beamforming` (Beam Pattern Optimizer) | non-RT rApp, O1 | `RRU.PrbTotDl`, `CARR.SINR_dist`, `DRB.UEThpDl` | per-beam azimuth / tilt / width (`beam_config`); declared conflict with RET tilt and RF channel muting | hours |
| <a id="E07"></a>E07 | Energy saving by RF channel reconfiguration / MIMO muting while the cell stays on; carrier and cell switch-off is the existing `rapp.energy_saving` | `rapp.mimo_sleep` (MIMO Sleep Controller) | non-RT rApp, O1/A1 | `RRU.PrbTotDl`, `DRB.UEThpDl` | active RF channels, e.g. 64T64R to 32T32R (`rf_channels`); declared conflict with capacity boost and beam changes | minutes |
| <a id="E08"></a>E08 | Traffic / load forecasting per cell or cluster | `rapp.traffic_forecast` (Traffic Forecaster) | non-RT rApp (AI) | `RRU.PrbTotDl`, `DRB.UEThpDl` | load forecast `tf.load_forecast` (read) | 15 min–hours |
| <a id="E09"></a>E09 | RAN fault prediction / predictive maintenance from PM, CM and FM trends | `rapp.fault_prediction` (RAN Fault Predictor) | non-RT rApp (AI) | `PEE.AvgPower`, `PEE.AvgTemperature`, `DRB.RlcSduDelayDl` | fault-risk scores and recommendations (read) | hours–days |
| <a id="E10"></a>E10 | Tenant / slice-aware admission control | `rapp.slice_admission` (Slice Admission Controller) | rApp + xApp (A1 policy, E2 enforcement) | `RRU.PrbTotDl`, `RRC.ConnMean` | per-slice admission limits (`slice_admission`) | seconds |
| <a id="E11"></a>E11 | Signalling storm protection: detect connection-attempt storms, throttle or reject | `rapp.signalling_storm` (Signalling Storm Protector) | rApp (A1 policy) + xApps (E2) | `RRC.ConnEstabAtt`, `RRC.ConnEstabSucc` | throttle / reject policy (`rrc_admission`) | near-RT detection, non-RT policy |
| <a id="E12"></a>E12 | Uplink interference detection and UL power-control retuning | `rapp.ul_interference` (Uplink Interference Optimizer) | non-RT rApp, O1 | `RRU.PrbTotUl`, `CARR.UlInterference` (emulated name for UL interference per PRB) | `p0NominalPusch`, `alpha` (`ul_power_control`) | hours |
| <a id="E13"></a>E13 | 5G NSA (EN-DC) traffic optimisation: dual-connectivity distribution profiles | `rapp.endc_steering` (EN-DC Traffic Optimizer) | non-RT rApp | `RRU.PrbTotDl`, `DRB.UEThpDl` | DC distribution profile (`dc_profile`) | 15 min |
| <a id="E14"></a>E14 | Configuration consistency audit against a golden baseline | `rapp.config_audit` (Configuration Consistency Auditor) | non-RT rApp, O1 CM | CM (no KPM input) | deviation report (read) | hours |
| <a id="E15"></a>E15 | Crossed feeder / swapped sector detection | `rapp.crossed_feeder` (Crossed Feeder Detector) | non-RT rApp | `RRC.HO_attempts`, `RRC.ConnMean`; real inputs are UE measurement reports and topology | suspect sectors (read) | hours |
| <a id="E16"></a>E16 | Special event handling: temporary parameter profile with revert | `rapp.special_events` (Special Event Handler) | non-RT rApp, O1 | `RRU.PrbTotDl`, `RRC.ConnMean` | event profile and scheduled revert (`event_profile`); declared conflict with energy saving and MIMO sleep | hours |
| <a id="E17"></a>E17 | Per-UE MAC scheduler / link-quality monitoring (CQI, MCS, BLER, scheduled RBs): the evidence that ML link adaptation and MU-MIMO scheduling apps act on | `mac` xApp (`xapp_l2_monitor.py --sm mac`) | near-RT xApp, FlexRIC MAC SM (RAN function 142) | E2 MAC indications | read-only (`mac_subscription`) | 10 ms reports |
| <a id="E18"></a>E18 | RLC bearer buffer / retransmission monitoring | `rlc` xApp (`--sm rlc`) | near-RT xApp, FlexRIC RLC SM (143) | E2 RLC indications | read-only (`rlc_subscription`) | 10 ms reports |
| <a id="E19"></a>E19 | PDCP bearer volume / discard / reordering monitoring | `pdcp` xApp (`--sm pdcp`) | near-RT xApp, FlexRIC PDCP SM (144) | E2 PDCP indications | read-only (`pdcp_subscription`) | 10 ms reports |
| <a id="E20"></a>E20 | GTP-U (N3) tunnel inventory: TEIDs and QFI per UE | `gtp` xApp (`--sm gtp`) | near-RT xApp, FlexRIC GTP SM (148) | E2 GTP indications | read-only (`gtp_subscription`) | 10 ms reports |

## Sources per use case

### E01: ANR
| Source | Vendor / spec | What it says (in our words) | Seen |
|---|---|---|---|
| Ericsson 5G Centralized Neighbor Relations rApp, solution sheet: <https://www.ericsson.com/4ac330/assets/local/core-network/doc/ericsson-5g-centralized-neighbor-relations-rapp.pdf> | Ericsson (EIAP) | Centralised ANR. It creates neighbour relations to high-band NR cells from cell geography and topology via CM requests, and complements node-level ANR. | F |
| HCLSoftware ANE-O rApp, `EIAP/hclsoftware-ane-o-rapp` | HCLSoftware | ANR for 4G/5G. Creates and removes neighbour relations and X2/Xn links, with optional blacklisting. | F |
| O-RAN UC19 Integrated SON (§4.19.2.2, §4.19.4.1), ETSI TS 104 036 | O-RAN WG1 | Scopes PCI allocation/conflict resolution and ANR as rApp, xApp or E2-node functions. Inputs: measurement reports with neighbour PCI, NCRT. | F |
| 3GPP TS 28.313 §6.1.1.3 / §6.4.1.3 "ANR management in NG-RAN"; TS 38.300 §15.3.3 | 3GPP | ANR management: NCR add/delete, HO allow/blocklisting, Xn blocklisting | F |

### E02: PCI optimisation
| Source | Vendor / spec | What it says | Seen |
|---|---|---|---|
| AirHop Auptim Physical Cell Identity Optimization rApp, `EIAP/airhop-auptim-physical-cell-identity-optimization-rapp` | AirHop | Detects and resolves PCI collisions and confusions | L |
| Wipro PCI rApp (`EIAP/wipro-pci-physical-cell-identity-rapp`); Satori PCI Planning & Optimization (`EIAP/satori-pci-planning--optimization-rapp`) | Wipro, Satori | PCI conflict detection and reallocation | L |
| 3GPP TS 28.313 §7.1.3 (D-SON PCI configuration, `nRPciList`); TS 38.300 §15.5.6 "Support for PCI Optimisation" | 3GPP | Centralised and distributed PCI (re)assignment | F |
| O-RAN UC19 (PCI conflict resolution), ETSI TS 104 036 | O-RAN WG1 | Inputs include PCI range and PCI confusion/conflict information; output via O1/A1 or E2 | F |

### E03: Sleeping cell / COD
| Source | Vendor / spec | What it says | Seen |
|---|---|---|---|
| Ericsson Sleeping Cell Detection rApp, `EIAP/ericsson-sleeping-cell-detection-rapp` | Ericsson | Detects silent "sleeping cell" faults that raise no alarm, from data trends | F |
| AirHop Auptim RAN Anomaly Detection rApp, `EIAP/airhop-auptim-ran-anomaly-detection-rapp` | AirHop | Classifies PM-KPI anomalies, including cell outage and sleeping cell | F |
| 3GPP TS 32.541 (SON self-healing: cell outage detection and compensation) | 3GPP | COD/COC concepts | S (cited as the spec; the definition is taken from the two F sources) |

### E04: Mobility load balancing (CIO)
| Source | Vendor / spec | What it says | Seen |
|---|---|---|---|
| Rimedo Labs Traffic Steering rApp, `EIAP/rimedo-labs-traffic-steering-rapp` | Rimedo Labs | Cell-level load balancing that adjusts Cell Individual Offsets on long-term PRB and user counts. It is non-RT, in contrast to per-UE E2 steering. | F |
| AirHop Auptim Mobility Load Balancing rApp, `EIAP/airhop-auptim-mobility-load-balancing-rapp` | AirHop | Offloads users from loaded cells by adjusting cell boundaries, coordinated with MRO | F |
| 3GPP TS 28.313 §7.1.5 Load Balancing Optimisation (`maximumDeviationHoTrigger`, PRB usage input); TS 38.300 §15.5.1.4 | 3GPP | HO-trigger changes for load balancing within OAM ranges | F |
| O-RAN SC Traffic Steering xApp User's Guide: <https://docs.o-ran-sc.org/projects/o-ran-sc-ric-app-ts/en/latest/user-guide.html> | O-RAN SC | Per-UE handover control. This is the existing `rapp.traffic_steering` side of the distinction, the contrast case. | F |

### E05: RACH optimisation
| Source | Vendor / spec | What it says | Seen |
|---|---|---|---|
| AirHop Auptim Random Access Channel Optimization rApp, `EIAP/airhop-auptim-random-access-channel-optimization-rapp` | AirHop | Resolves RSI collisions and confusions, adjusts PRACH frequency offset and ZCZ from UE timing advance | F |
| O-RAN blog "46 demos … MWC Barcelona 2022": <https://www.o-ran.org/blog/46-demos-of-o-ran-technology-prepared-for-mwc-barcelona-2022-or-the-o-ran-virtual-exhibition> | Juniper + AirHop | Demo of a RACH optimisation xApp on a near-RT RIC | F |
| 3GPP TS 38.300 §15.5.3 "Support for RACH Optimization"; TS 28.313 §7.1.1 | 3GPP | RA report and PRACH parameter exchange. Inputs: preamble and access-delay distributions per SSB. | F |

### E06: Massive-MIMO beamforming
| Source | Vendor / spec | What it says | Seen |
|---|---|---|---|
| O-RAN UC6 "Massive MIMO Beamforming Optimization" (§4.6), ETSI TS 104 036 | O-RAN WG1 | Non-RT GoB optimisation from the inferred user and traffic distribution. Configures beam width, azimuth and tilt over O1. | F |
| Rimedo Labs Beamforming Optimization rApp, `EIAP/rimedo-labs-beamforming-optimization-rapp` | Rimedo Labs | Selects or rotates the GoB pattern to user clusters, configured via O1 | F |
| NTIA/ITS RIC Forum booklet (Mar 2024): <https://its.ntia.gov/media/gamjzib2/ric-forum-booklet.pdf> | TIP demo | mMIMO SSB/GoB configuration from predicted traffic | F |

### E07: RF channel / MIMO muting energy saving
| Source | Vendor / spec | What it says | Seen |
|---|---|---|---|
| O-RAN UC21 Energy Saving (§4.21), ETSI TS 104 036 | O-RAN WG1 | Carrier/cell switch-off for low load. RF channel (M-MIMO antenna) switch-off for medium load, on a seconds-to-minutes scale. | F |
| O-RAN blog "57 new or updated O-RAN specifications released since March 2023": <https://o-ran.org/blog/57-new-or-updated-o-ran-specifications-released-since-march-2023> | O-RAN WG1 | The Network Energy Saving TR covers Carrier and Cell Switch Off/On and RF Channel Reconfiguration Off/On | F |
| Rimedo Labs RF Channel Reconfiguration rApp, `EIAP/rimedo-labs-rf-channel-reconfiguration-rapp` | Rimedo Labs | Reduces active M-MIMO RF channels (64T64R to 32T32R/16T16R) from per-beam load and throughput | F |
| AirHop Auptim AI/ML Energy Savings MIMO Adaptation rApp, `EIAP/airhop-auptim-aiml-energy-savings-mimo-adaptation-rapp` | AirHop | MIMO-layer adaptation for energy saving | L |

### E08: Traffic forecasting
| Source | Vendor / spec | What it says | Seen |
|---|---|---|---|
| Zinkworks Network Traffic Prediction rApp, `EIAP/zinkworks-network-traffic-prediction-rapp` | Zinkworks | Graph-ML forecast of traffic load across cell clusters. Not closed loop; feeds other rApps. | F |
| HCLTech Energy Optimizer rApp, `EIAP/hcltech-energy-optimizer-rapp` | HCLTech | Uses an AI/ML load forecast to switch cells, carriers or RF channels off, and back on as load rises. This is the forecast-then-act pattern of `forecast_then_cell_sleep`. | F |
| 3GPP TR 37.817 §5.1.2.5 (AI/ML for NG-RAN, energy saving outputs) | 3GPP | Predicted load / energy state as AI/ML outputs | F |

### E09: Fault prediction
| Source | Vendor / spec | What it says | Seen |
|---|---|---|---|
| Ericsson RAN Fault Prediction rApp, `EIAP/ericsson-ran-fault-prediction-rapp` | Ericsson | Predicts faults from PM/CM/FM with AI/ML and recommends preventive actions | F |
| Ericsson SFP Predictive Maintenance (`EIAP/ericsson-sfp-failure-prediction-rapp`) | Ericsson | Forecasts transceiver life | L |

### E10: Slice / tenant admission control
| Source | Vendor / spec | What it says | Seen |
|---|---|---|---|
| Juniper RAN Intelligent Controller datasheet, Table 1: <https://www.juniper.net/content/dam/www/assets/datasheets/us/en/network-automation/juniper-ran-intelligent-controller-datasheet.pdf> | Juniper | Lists a "Tenant/Slice-aware admission control" app next to slice SLA assurance | F |
| TelecomTV "Juniper boasts successful RIC trial with Vodafone" (2023-02-23): <https://www.telecomtv.com/content/open-ran/juniper-boasts-successful-ric-trial-with-vodafone-46760/> | Juniper / Vodafone | Admission control realised as rApp + xApp | F |
| 3GPP TS 23.501 §5.15.11 Network Slice Admission Control | 3GPP | Per-slice limits on UEs and PDU sessions. A core-network analogue, cited for the definition. | F |

### E11: Signalling storm protection
| Source | Vendor / spec | What it says | Seen |
|---|---|---|---|
| O-RAN UC15 "Signalling Storm Protection" (§4.15), ETSI TS 104 036 | O-RAN WG1 | Detection xApp on per-UE connection-establishment events plus a mitigation xApp (reject/throttle via E2). A non-RT detection rApp pushes A1 policies (thresholds, throttling ratios). | F |

### E12: Uplink interference
| Source | Vendor / spec | What it says | Seen |
|---|---|---|---|
| Ericsson Uplink Interference Optimizer rApp, `EIAP/ericsson-uplink-interference-optimizer-rapp` | Ericsson | Recommends UL power-control parameters (`pZeroNominalPusch`, `alpha`) for UL-interfered cells | F |
| Ericsson Uplink Anomaly Detector rApp, `EIAP/ericsson-uplink-anomaly-detector-rapp` | Ericsson | Classifies UL interference as traffic, external or infrastructure | F |
| Spectrum Effect Spectrum-NET rApp, `EIAP/spectrum-net` | Spectrum Effect | Interference detection and classification with closed-loop resolution | F |
| 3GPP TS 38.300 §17.1 Remote Interference Management | 3GPP | UL interference from atmospheric ducting (background) | F |

### E13: EN-DC / NSA traffic optimisation
| Source | Vendor / spec | What it says | Seen |
|---|---|---|---|
| Ericsson 5G NSA Traffic Optimizer rApp, `EIAP/ericsson-5g-nsa-traffic-optimizer-rapp` | Ericsson | Steers EN-DC devices on NR load by automating dual-connectivity distribution profiles | F |

### E14: Configuration consistency audit
| Source | Vendor / spec | What it says | Seen |
|---|---|---|---|
| Ericsson Automated Configuration Consistency rApp, `EIAP/ericsson-automated-configuration-consistency-rapp` | Ericsson | Configuration consistency checking with KPI-based rollback | L |
| Future Connections NIx Configuration Consistency Auditor, `EIAP/future-connections-nix-configuration-consistency-auditor-rapp` | Future Connections | Configuration consistency audit | L |

The card keeps only the read-only audit part. Rollout of a correction is the existing `rapp.ran_lifecycle`.
Both sources are listing-level (L), so this row has the weakest provenance in the table.

### E15: Crossed feeder detection
| Source | Vendor / spec | What it says | Seen |
|---|---|---|---|
| VIAVI Crossed Feeder Detection rApp, `EIAP/viavi-crossed-feeder-detection-rapp` | VIAVI | Detects crossed feeders from UE measurement reports and topology | L |
| Wipro Cross Feeder Detection, `EIAP/wipro-cross-feeder-detection-rapp` | Wipro | Same function | L |

### E16: Special event handling
| Source | Vendor / spec | What it says | Seen |
|---|---|---|---|
| Aspire Special Event Handling rApp, `EIAP/aspire-special-event-handling-rapp` | Aspire | Scheduled configuration changes for events, with revert | L |
| Future Connections NIx Special Events Handler, `EIAP/future-connections-nix-special-events-handler-rapp` | Future Connections | Same function | L |

### E17–E20: FlexRIC L2 monitor xApps
| Source | What it says | Seen |
|---|---|---|
| FlexRIC SDK, EURECOM: <https://gitlab.eurecom.fr/mosaic5g/flexric>. R. Schmidt, M. Irazabal, N. Nikaein, "FlexRIC: an SDK for next-generation SD-RANs", ACM CoNEXT 2021, doi:10.1145/3485983.3494870 | FlexRIC's custom MAC, RLC, PDCP and GTP statistics service models. They are advertised by the FlexRIC emulator used here (`MAC_STATS_V0` 142, `RLC_STATS_V0` 143, `PDCP_STATS_V0` 144, `GTP_STATS_V0` 148) and used by the repository's own `xapp_mac_rlc_pdcp_gtp_moni.py`. | repository code (F) |
| Capgemini "Intelligent 5G L2 MAC Scheduler": <https://www.capgemini.com/insights/research-library/intelligent-5g-l2-mac-scheduler/> | ML link adaptation and MAC scheduling on a near-RT RIC: the consumer of the per-UE scheduler and link statistics that E17 observes | F |
| O-RAN UC22 MU-MIMO Optimization / UC14 SU/MU-MIMO grouping, ETSI TS 104 036 | Near-RT loops on per-UE channel and scheduling information | F |

The monitor cards are read-only observers. They do not implement link adaptation, buffer control or tunnel
management.

## Mapping notes

- **Card text.** Card descriptions follow the existing pattern "<what it does>. Use when … Do not use when …"
  and are written from the definitions above. Each description names the neighbouring family that the request
  should *not* go to, for example MLB vs per-UE traffic steering, MIMO sleep vs cell sleep, beamforming vs RET,
  and traffic forecast vs capacity planning. For the same reason, five existing cards got one clarifying clause
  in their "Do not use when" text:
  - `traffic_steering`
  - `energy_saving`
  - `ret_tilt`
  - `capacity_mgmt`
  - `interference`: its use-when no longer claims PCI clashes, and its `pci_optimization` capability became
    `sinr_recovery`, since PCI now has its own family.
- **Declared conflicts.** These conflicts are new. Each is justified by the source definitions:
  - MLB and MRO both change the handover trigger. In TS 28.313, both the MRO (Table 7.1.2.2.3-1) and the LBO
    (Table 7.1.5.2.2-1) "parameters to be updated" are the same attribute, `maximumDeviationHoTrigger`
    (TS 28.541). The MRO card now declares `cio_load_balancing`, and MLB declares `handover_tuning`.
  - Beamforming conflicts with RET tilt and with MIMO sleep, because the same antenna configuration would be
    reshaped twice.
  - MIMO sleep conflicts with capacity-boost functions, the same rule as cell sleep.
  - Special events conflicts with energy saving and MIMO sleep. Its cards carry `capacity_boost`, so cell sleep
    in turn refuses to run after it.
- **Emulated decision rules.** These live in `rapps/runtime.py` (`decide_extended`). The FlexRIC emulator's KPM
  bus carries no handover, RACH, RRC-setup, PCI, alarm or power counters. Rules that would need those inputs use
  the KPM proxy named in the code and report it in the output (`proxy`).
- **Vendor variants and deprecated releases.** Five new families have one fictional vendor variant and one
  deprecated 0.9.0 release each: `anr`, `pci_optimization`, `mobility_load_balancing`, `mimo_sleep` and
  `traffic_forecast`.
