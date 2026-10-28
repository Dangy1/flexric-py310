# AppWeaver revision: master plan and status

Snapshot 2026-10-28 10:30. This file merges every plan that was written for the revision:
`REVISION_PLAN.md` (tracks T0–T7, owner decisions O1–O8), `FABLE_REVIEW_AND_PLAN.md` (P0/P1/P2),
`FABLE_SIM_REVIEW.md` (ns-3 simulator fixes 1–10), `RC_AND_EMU_TWIN.md` (stream A) and the open rows of
`RESPONSE_TO_REVIEWERS.md`. Status was checked in the code, not copied from the docs. "Working tree" means
the change exists but is not committed yet (streams A, B and C in the execution session).

Legend: ✅ done · 🟡 in the working tree, or partly done · 🔄 being worked on now · ⬜ not started · ⛔ blocked on the owner

## 1. Where things stand

| Area | Status |
|---|---|
| Infrastructure (repo, metrics, Agent Cards v2, rApp directory, BM25 discovery, ns-3 simulator, LLM hosts) | ✅ committed |
| Preliminary results (qwen Batch A/B, gpt-oss pilot of 70 records) | ✅ exist but are **pilot only**: they ran with the label leak and the reset "recovery" |
| Twin-vs-live on ns-3 (T6 base + load-calibrated) | ✅ valid, kept; re-run only if simulator fixes 4/6 or P1-2 land |
| Fable P0 code fixes | 🟡 mostly in the working tree, 35 tests pass |
| Fable P1 (LangGraph planner, real RC, emulator dry-run, repair by insertion) | 🟡/🔄 streams A and C finishing |
| Simulator fixes (FABLE_SIM_REVIEW) | 🔄 3 of 10 done as patches |
| Final batches on spark1 gpt-oss-120b | ⬜ waits for the code fixes |
| Paper text, response letter, minor comments | ⬜ waits for the final numbers; minor comments ⛔ need the manuscript source |

## 2. Code and method fixes (Fable P0 / P1 / P2)

| # | Item | Status | Evidence / what is left |
|---|---|---|---|
| P0-1 | Remove `notes`/`category` from every method input | 🟡 | Prompts assert no `Notes:`/`Category:` line (`run_harness.py:879–881`); `route_intent` is keyword-only over the sentence |
| P0-2 | No forced reset; recovery = bounded wait or re-plan without the busy app | 🟡 | `reset_runtime()` raises if called inside a record (`:447`); metrics renamed in `CONFLICTS.md`/`METRICS.md` |
| P0-3 | Pre-registered partial-order label rule (O6/O8) | 🟡 | `evaluation/label_rules.py`, `build_label_rules.py`, `tests/test_labels.py`; intents files regenerated. Left: commit **before** the final batch so the date proves pre-registration |
| P0-4 | Remove the benchmark-tuned deterministic fallback | 🟡 | `deterministic_discovery_chain` gone |
| P0-5 | Card fixes (`slice_sla`, `pm_kpi`, RC, `slice.monitor` scope, `tc.apply-all`) | 🟡 | `build_catalog.py`, `backend/agents/*` changed; all labelled chains pass `check_chain` (test). Left: RC ack markers still include the old scaffold line "RC profile selected" — must go once stream A lands |
| P0-6 | Pin executable xApps in retrieval; k bounds rApp families; deprecated cards visible | 🟡 | `discovery.pinned_xapp_ids` |
| P0-7 | Honest Section IV and response letter (RC, emulator, measured path, BM25 not RAG, T6 chains) | ⬜ | Not touched since the review; rewrite after the final numbers |
| P0-8 | Manifest completeness (prompt hashes, intent-file hash, max prompt chars, hardware) | 🟡 | Prompt hashes and prompt cap recorded; hardware line known (O3), to be set in `spark1.env` |
| P0-9 | Final batches A, B k=8, B k=all on spark1 gpt-oss-120b | ⬜ | After everything above is committed |
| P1-1 | Validate-1: emulator dry-run per step, `validation_report` in records | 🟡 | `backend/orchestration/validate.py`, `emu_twin.py`, `--validate-mode dryrun`, twin emulator start/stop scripts |
| P1-2 | Validate-2: ns-3 twin gate + placement sync (3 sync levels, gate precision/recall) | ⬜ | Needs simulator fix 9 (`uePositionFile`) and a new T6 batch |
| P1-3 | Real RC control (E2SM-RC style 1, CONTROL-ACK) and RC REPORT | 🔄 | `xapp_rc_ctrl.py`, swig wrapper changes, `docs/RC_AND_EMU_TWIN.md`; stream A still testing |
| P1-4 | AppWeaver planner on LangGraph (Discover→Compose→Validate→Deploy→Recover) | 🔄 | `backend/appweaver/` graph + nodes, `graph_backend` in records, `test_appweaver_graph.py`; stream C running a live test on spark1 |
| P1-5 | Repair by inserting the missing producer, fixpoint re-check | 🟡 | `compat.py` repair loop |
| P1-6 | Card text: use / do-not-use sentences, better distractors | 🟡 | Partly in `build_catalog.py`; freeze before P0-9 |
| P1-7 | Ablation rows differ in one thing (`no_compat`, `no_recovery`) | ⬜ | Optional; otherwise rename the row "AppWeaver (plan only)" |
| P1-8 | Same conflict-seeding mechanism for every method | 🟡 | `seed_conflict_if_needed` ignores the method |
| P2-1…5 | Stateful emulator, embedding retriever, rApps over MCP, second model row, portal split | ⬜ | Optional, after the batches |

## 3. Simulator fixes (`FABLE_SIM_REVIEW.md` §6, ns-oran-sim session)

| # | Fix | Status |
|---|---|---|
| 1 | FlexRIC `eq_xapp_ric_gen_id` (second KPM xApp crashes the RIC) | ✅ patch `flexric-taap-0005` |
| 2 | e2sim: unsubscribe keeps the connection, no `exit()` | ✅ patch `e2sim-0001` |
| 3 | RC multi-digit cell ids + cell switch-ON | ✅ patch `appweaver-actuator-0001` |
| 4 | Simulated-time timestamps in indications | ⬜ (forces a T6 re-run) |
| 5 | `noValue` record instead of an empty list | ⬜ |
| 6 | Immediate reporting when the PRB condition is trivial | ⬜ (forces a T6 re-run) |
| 7 | KPM bus collector for the simulator (multi-agent sharing) | ⬜ |
| 8 | Several KPM subscriptions per node | ⬜ (larger, optional) |
| 9 | `uePositionFile` for placement sync | ⬜ (needed by P1-2) |
| 10 | `ReleaseUeHoControl` behind an attribute | ⬜ (optional) |

## 4. Reviewer deliverables (REVISION_PLAN §1)

| Ask | Deliverable | Status |
|---|---|---|
| A — novelty, Agent Cards, compatibility checks (R1.1, R3.7) | Cards v2 + four compose-time checks logged per record | ✅ code; text in P0-7 |
| B — twin fidelity, network KPIs (R1.2, R2.2, R3.1, R4) | T6 on ns-3; plus Validate-1/2 | ✅ T6; 🟡 Validate-1; ⬜ Validate-2 |
| C — real vs emulated apps (R1.3) | Honest inventory, real RC | 🔄 RC; text in P0-7 |
| D — open world, registry size (R1.4, R4) | 3 splits, 55-card registry, retrieval metrics | ✅ (labels being re-registered) |
| E — catalog-aware LLM baseline, settings (R1.5, R3.4, R2.3) | 6 methods, settings in manifest | ✅ |
| F — reliability, conflicts, hallucination (R1.6, R3.5, R4) | Acknowledged calls, conflict P/R, hallucinations | 🟡 conflict semantics redone (P0-2) |
| G — variance, latency, Non-RT bound (R2.1, R3.3, R3.6, R4) | 5 repeats, CIs, latency distribution | ✅ method; numbers from P0-9 |
| H — release (R2.1, R4) | Public repo, one command per batch | ✅ (README updated after P0-9) |
| I — figures, typos, references (R4 minor, R1.7) | Paper edits | ⛔ manuscript `.tex` not on this machine |

## 5. Owner decisions

| # | Question | Status |
|---|---|---|
| O1/O2 | LLM host and model | ✅ spark1 vLLM `gpt-oss-120b` (spark2 `gpt-oss:120b` as backup) |
| O3 | GPU line for manifests and the paper | ✅ 2026-10-28: spark1 = NVIDIA DGX Spark, GB10, 128 GB unified CPU-GPU memory (121 GiB visible; `nvidia-smi` reports memory N/A by design) |
| O4 | Live side of the twin: OAI rfsim or ns-3 seed B | ⛔ open — default ns-3 seed B |
| O5 | Reasoning mode for gpt-oss | ✅ decided 2026-10-28: reasoning effort medium for gpt-oss-120b in the final batches, recorded in the manifest |
| O6/O7/O8 | Label rule, recovery semantics, extra analytics rApps | ✅ decided 2026-10-28 |
| — | Manuscript source for minor comments | ⛔ needed |

## 6. Remaining work and time estimate

Times are wall-clock. Agent work runs in parallel where marked; the final batches are the critical path
because they share one portal stack and one LLM host and must run one after another.

| Step | Depends on | Estimate |
|---|---|---|
| 1. Finish streams A (RC) and C (LangGraph), merge with B, drop the old RC ack line, run all tests | — | 2–3 h |
| 2. Commit labels + code (pre-registration timestamp), smoke batch on spark1 (3 intents × 6 methods) | 1 | 1 h |
| 3. **Batch A** final (1,500 records, ≈15 s/record) | 2 | ≈ 6.5 h |
| 4. **Batch B k=8** final (1,440 records) | 3 | ≈ 6–7 h |
| 5. **Batch B k=all** final (1,440 records) | 4 | ≈ 6–7 h |
| 6. Tables, figures, macros; Section IV and response letter rewrite (P0-7) | 3–5 | 3–4 h (drafting can start during 3) |
| *In parallel with 3–5 (CPU only, does not use spark1):* | | |
| 7. Simulator fixes 4, 5, 6, 9 | — | 3–4 h |
| 8. P1-2 ns-3 twin gate + placement sync code | 7 | 3–4 h |
| 9. New T6 batches (re-run base/load-cal after fixes 4/6, plus the sync batch) | 7, 8 | 6–8 h of ns-3 |
| 10. Minor comments in the manuscript | manuscript source | 2–3 h |

**Total:** about **30 hours of wall-clock time** from now to final numbers and text, if the batches run overnight without RIC wedges (the health probe re-runs wedged records, each
wedge costs ~1 min). Realistic finish: **Thursday 2026-10-30**. Without P1-2 and the simulator fixes,
the critical path is unchanged (≈ 26 h); they fit inside the batch window.

Risks that would add time: a fault found in the smoke batch (+½ day per fix-and-rerun), spark1 downtime
(it returned 502 for ~30 min on 10-28), or a new review finding that changes the labels after the batches
(would force a full re-run, ~20 h).
