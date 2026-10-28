# AppWeaver major revision (WCM-26-00422): independent review and corrected plan

Written 2026-10-28 by an independent review pass over the code on branch `appweaver-revision`, the
batch records under `evaluation/runs/`, the submitted PDF, and the three existing docs
(`RESPONSE_TO_REVIEWERS.md`, `REVIEW_ASSESSMENT_2026-10-27.md`, `REVISION_PLAN.md`). Read-only;
nothing else was changed. All paths are relative to `~/flexric/examples/xApp/python3` unless absolute.

Reviewer comments were available only as paraphrases (`docs/RESPONSE_TO_REVIEWERS.md`); where the
verdict depends on the reviewer's exact wording this is said explicitly.

---

## Executive summary

1. **Label leakage is still in every planner prompt.** `intents_50.json` carries a `notes` field that
   paraphrases the labelled chain ("Closed-loop latency reduction with KPI observation, slice review, TC
   action, and RC validation", "TC-only action path", "Direct TC plus RC validation"). `run_harness.py`
   puts `Notes:` and `Category:` into the catalog-aware, blind and Agent-Card prompts
   (`llm_prompt` :712, `llm_blind_prompt` :728, `agentcard_prompt` :878) and into the retrieval query
   and fallback rules (`_intent_text` :220–226). The response letter's "the labelled chain is never read by
   any method" (RESPONSE :27) is therefore not true in spirit. The gpt-oss batch running now inherits
   this. P0: strip `notes`/`category` from all method inputs; re-run A and B.
2. **"Recovery" is an emergency reset that kills the other operator's workflow.** AppWeaver's seeded-conflict
   "recovery" (RESPONSE :176–180 "re-plans around the lease") is `reset_runtime()` →
   `_reset_runtime_locked` (portal :2185–2196: terminates *all* running runs, clears all leases) followed
   by re-running the *identical* chain (24/24 recovered Batch A records: same chain before and after; the
   harness forces the reset at `run_harness.py:1484` regardless of the planner's answer). This cannot be
   claimed as conflict handling; it is lease pre-emption. P0: remove the forced reset, define recovery as
   queue/wait or re-plan without the busy resource, re-run the seeded intents.
3. **The "RC validation xApp" does nothing.** `xapp_kpm_rc_suite.py --profile rc` prints "RC profile
   selected" and "RC auto-subscription builder is not exposed yet" (:58–60) and idles; the ack marker is
   that print. SLICE/TC controls reach the FlexRIC emulator, which prints and returns a CONTROL-ACK without
   changing state (`examples/emulator/agent/sm_slice.c:34–55`, `sm_tc.c:33–50`); KPM is `rand()`
   (`sm_kpm.c:13–34`). Section IV must say this; "RC validation" must be renamed or implemented.
4. **LangGraph, A2A and MCP are not on the measured path.** The AppWeaver method is
   `execute_agentcard_sequence` (`run_harness.py:1395–1428`): a Python loop calling portal functions
   in-process and launching xApps as subprocesses. LangGraph (`backend/graph/`) only runs the three
   template workflows used by `langgraph_*` methods that are not in the paper. The paper's Fig. 1/3/4
   claims must be re-scoped or the planner must be moved onto the graph runtime.
5. **Known-split labels and the agent-card prompt contradict each other.** The prompt says "Use KPM
   first … Use RC last" (:873–874) while two templates are SLICE→KPM→RC and TC-only. AppWeaver's 9 %
   known accuracy (5/55 records) is a label/prompt artefact, not evidence about composition. Fix by a
   pre-registered partial-order label (observe before control, validate last) reported next to exact
   template match, decided and committed before the final batch, applied to all methods.
6. **The v2 labels are internally inconsistent** on whether a control chain ends in RC and starts with
   KPM (`energy_saving_wakeup_guard` = KPM→ES but `night_energy_saving` = KPM→ES→RC;
   `priority_for_emergency_ues` without RC, `cell_edge_qoe_protection` with RC). 23/26 unseen-capability
   misses at k=all are exactly a missing/extra KPM or RC. Same fix as item 5.
7. **Two labelled chains are unreachable by construction.** `slice_sla_breach`'s expected chain
   KPM→RAPP.SLICE_SLA→SLICE→RC fails the dependency check (`rapp.slice_sla` consumes `slice.policy`, produced
   only by SLICE which comes later; 42 records dropped the step), and `night_energy_saving`'s accepted
   alternative `[RAPP.PM_KPI, RAPP.ENERGY_SAVING, RC]` fails (`energy_saving` requires `kpi_monitoring`,
   which `pm_kpi` does not provide). Fix the cards, not the labels.
8. **Top-k retrieval drops the platform's own control xApps.** 11 of the 13 k=8 retrieval misses are KPM,
   RC or SLICE outranked by rApp families (RC's card text — "Tracks control opportunities … policy gate" —
   matches no intent). Executable xApps should be pinned; k should apply to the rApp directory.
9. **Compat repair drops steps instead of inserting the missing producer**, and the drop is not re-checked
   (`healing_full_chain` at k=8 ends as AD→SELF_HEALING→RC with `self_healing`'s `requires root_cause_analysis`
   now violated). Repair should insert KPM/upstream producers, then re-run `check_chain` to a fixpoint.
10. **AppWeaver's deterministic fallback is a benchmark-tuned rule router** (`deterministic_discovery_chain`
    :253–273 keys on "xr", "urllc", "stadium congestion", "premium qos" …). It never fired in Batch A
    (`planner_repaired` = 0/250) but it must be removed from the method or declared as a baseline.
11. **The twin experiment (T6) is sound and the honest part of the revision**, but Section IV says the
    workflows were "composed by AppWeaver" — they are hard-coded chains (`evaluation/twin/run_twin_validation.py:61–66`).
    The FlexRIC emulator cannot be the KPI twin (random KPM, controls not applied); it can be an
    interface/conformance sandbox. A defensible Validate design is in §5.
12. **The rule router and single-app baselines read the `category` label** (`route_intent` :131–139). With
    categories `slice/transport/latency` mapping 1:1 to templates, the router's 100 % known accuracy is by
    construction. Make it keyword-only over the intent text.
13. **Numbers in the draft are preliminary (qwen3.6:27b, reasoning off) and the gpt-oss batch running
    now uses the leaky prompts.** After the P0 harness changes every batch (A, B×2) must be re-run; the
    current run can serve as a pilot but not as paper evidence.
14. **Honest naming is mostly done but not everywhere:** "AppWeaver" in tables = `langgraph_agentcard`;
    the response letter's R1.3 still calls RC a "validation xApp" and R1.1/R3.7 imply the planner runs
    under LangGraph.
15. Minimal re-run set after fixes: Batch A (1500 records, ≈6–7 h with gpt-oss-120b at the observed
    ≈15 s/record), Batch B k=8 and k=all (≈7 h each). T6 needs no re-run unless the placement-sync
    experiment (P1) is added.

---

## 1. Reviewer coverage

Verdicts: **answered** / **partly** / **not answered** / **overclaimed**. "Claim" = what the response
letter or the Section IV draft says now.

| Item | Current claim | Evidence found | Verdict | Gap / fix |
|---|---|---|---|---|
| R1.1 what Agent Cards add; dependency / interface / control-scope checks | Schema v2 + four compose-time checks logged per record (RESPONSE :43–56) | `backend/common/models.py:49–61` fields exist; `backend/orchestration/compat.py:149–201` implements dependency (requires/consumes), interface (warning only), control-scope (error on `conflicts_with`), timescale (warning only); `compat_report` in every AppWeaver record (226/250 Batch A, rest planner failures) | **partly** | Only two of four checks can reject (interface and timescale are warnings → never "rejected" as the letter says :52). The dependency check is the one that fires (`slice_sla` 42 records) and in one case fires against the label itself (item 7). Repair drops steps without re-check (item 9). The letter's "Compose runs four explicit checks … A failing check triggers repair (drop/reorder) or rejection" overstates: there is no reorder. |
| R1.2 twin fidelity, predicted vs actual | ns-3 twin vs ns-3 live, predicted/measured deltas, 8 pairs, two load settings (RESPONSE :61–83; §IV-C) | `evaluation/runs/20261027T171217Z_T6_twin_vs_live{,_loadcal}`, 72 jobs each, A/A noise bound; results in `TWIN_VALIDATION.md` match the draft macros | **answered** (with one wording fix) | "three RC-actuated workflows composed by AppWeaver" (tex :215) → they are the labelled chains hard-coded in `run_twin_validation.py:61–66`; the planner was not run. Say "the benchmark chains". Also the twin is not wired into the AppWeaver method (no Validate step in `run_harness.py`; 0 hits for "twin"). |
| R1.3 which apps are real | Four real FlexRIC xApps "KPM monitor, SLICE control, TC control, RC validation" + monitor cards + 46 emulated rApps (RESPONSE :85–94) | See §3. KPM reads a shared bus (real E2 subscription, synthetic values); SLICE/TC send real E2 control that the emulator acks and discards; RC is a print-only scaffold; MAC/RLC/PDCP/GTP cards have no actions (`backend/agents/{mac,rlc,pdcp,gtp}.py`) | **partly / overclaimed on RC** | Inventory table must state per app: E2 message sent? applied by the RAN? KPI effect? For RC: none/none/none. |
| R1.4 open-world meaning, registry size | Three splits; 55 cards / 50 executable (RESPONSE :96–104) | `build_intents_v2.py:5–9`; `rapps/catalog.json` 46 entries (33 active, 13 deprecated, 30 distractors, 16 families) + 9 portal cards | **answered** on definitions; **partly** on substance | "50 executable" counts 13 deprecated cards whose runtime refuses to run (`rapps/runtime.py:187–189`): executable = 37. Open-world (Batch A) = same four xApps, different wording — say so plainly. 13/50 intents have `notes` that spell out the chain (§4.2). |
| R1.5 catalog-aware baseline + ablation | `llm_only` = picks one of three templates; `llm_blind` new; `agentcard_no_repair` new (RESPONSE :106–115) | `llm_prompt` :692–714 (templates + Category + Notes); `execute_llm_only` :1546–1602 executes the chosen template; `plan_blind` :732; `agentcard_no_repair` :1679 (`repair=False, recover=False`) | **answered**, with two caveats | (a) all three LLM prompts receive `Notes:`/`Category:` (item 1); (b) the no-repair ablation differs from AppWeaver in *three* things at once (no fallback, no compat drop, no recovery) so "repair does not change accuracy" (tex :121–123) is not an isolated ablation. |
| R1.6 reliability denominators, seeds, hallucinations | n of tool calls, acknowledged fraction, 6 seeds × repeats, refused/recovered, FP rate, hallucinated refs (RESPONSE :117–124; Table II) | `make_paper_figures.method_metrics` :205–258; `CONFLICTS.md`; Batch A: AppWeaver 721 calls, 97.9 % acked; seeded 30 records, refused 24, "recovered" 24 | **overclaimed on "recovered"** | Recovered = reset-and-rerun (item 2). Denominators are now right. Hallucination for `llm_blind` is near-trivial (app ids are the service-model names; the blind model guesses "KPM/SLICE/TC/RC"); fine to report, but do not present it as a strong result. |
| R1.7 presentation (Fig. 2 hints the skill, Fig. 3 density, typos) | Manuscript edits listed (RESPONSE :126–127, :210–222) | Paper source not in repo | **not verifiable here** | Fig. 2's MOS numbers must go (no source); replace with a trace from a real record (e.g. Batch A `xr_latency_guard`, AppWeaver repeat 1: planner JSON, 4 acknowledged calls). |
| R2.1 benchmark transparency, trials, variance, release | 5 repeats, CIs, labels and rules released (RESPONSE :133–139) | Manifests complete; intent-clustered bootstrap (`make_paper_figures.py:158–178`); Wilson for conflicts | **answered** for A; **partly** for B (3 repeats) | Labelling rules for the 50 original intents are not written anywhere except the `notes` text itself; `build_intents_v2.py:17–29` documents only the rApp-alternative rule. Write the labelling rule for the base set (§4.4). |
| R2.2 network-level effect | Measured KPI deltas on live ns-3 instance (R1.2) | T6 | **answered** for RC-actuated chains; **not answered** for TC/SLICE chains, which are 100 % of Batch A | State explicitly that Batches A/B measure composition/execution only; the emulator returns random KPM (`sm_kpm.c`), so `before`/`after` fields in those records are meaningless and must not be plotted. |
| R2.3 model & inference settings | Manifest records provider/model/temperature/seed/think/timeout/prompt hashes/hardware (RESPONSE :149–155) | Batch A manifest has them; `prompt_builders_sha256` is `null` in the gpt-oss manifest (`…A_final_gptoss120b_spark1/manifest.json`) and absent from the qwen Batch A; `hardware.llm_server` = "GPU model pending owner" | **partly** | O3 (GPU line) still open; add the prompt hashes to the manifest *before* the final batch (they only exist in Batch B manifests). |
| R3.1 twin fidelity | = R1.2 | | **answered** | |
| R3.2 how intents were labelled; multiple valid chains | `accepted_workflows` + exact/set metrics (RESPONSE :162–166) | 11 base intents gained one alternative via `RAPP_TRIGGERS` (`build_intents_v2.py:76–91`); none gained an observe-first alternative (O6) | **partly** | Labelling rule for the base set undocumented; template-order labels contradict the prompt (item 5); two labels unreachable (item 7). |
| R3.3 variance, runs | = R2.1 | | **answered** | |
| R3.4 ablations | no-catalog LLM, no-repair AppWeaver, k=8 vs all (RESPONSE :170–171) | Batch B k0/k8 merged; retrieval hit 83 % at k=8 | **partly** | k=8 vs all is confounded by the pinned-xApp problem (item 8): the "cost of retrieval" is mostly losing KPM/RC. Add a `--retrieval-pin-xapps` ablation. |
| R3.5 conflict detection reported as accuracy | Replaced by refused/recovered/FP; the lease is shared, AppWeaver's contribution is recovery (RESPONSE :173–180; O7) | `analyze_results.conflict_flagged` :64–77 unified rule; Batch A refused: router 30/30, AppWeaver 24/30 | **overclaimed** (item 2) | Recovery as implemented is not safe. Either implement queue-and-resume / re-plan-without-resource, or report "proceeded after operator-level reset" honestly and drop the claim. Also seeding differs by method: `langgraph*` methods get an *enforced workflow* seed with a scheduler lease, direct-launch methods get a bare subprocess (`seed_conflict_if_needed` :578–608) — document or unify. |
| R3.6 latency distribution, Non-RT bound | median/p95/max, box plot, ≥1 s loop (RESPONSE :182–186) | Batch A AppWeaver 5.1 s median (qwen, think off); gpt-oss partial: 15 s median, 34 s max for 11 records | **answered** | Will change ×3 with gpt-oss; the "within the Non-RT timescale" sentence remains true. |
| R3.7 what is checked at composition time | = R1.1 | | **partly** | |
| R4 scalability ("RAG overkill for 9 cards"), extra capability, hardware, reliability | BM25 top-k, family de-dup, hit rate; unseen-capability split; distractor cost reported as limitation (RESPONSE :194–206) | `discovery.py:291–331`; Batch B unseen 71 %/62 %; open-world 17 %/12 % | **partly** | The scale result is dominated by three fixable defects (items 7–9) and by `notes` leakage; re-run after fixes. Hardware line still "pending owner". "RAG" in the paper should become "BM25 lexical retrieval over card text"; there is no embedding model. |
| Minor (typos, capitalisation, Fig. 5a labels, Fig. 3 split, refs) | Listed | — | **not verifiable** | — |

Claims in the letter/draft that the code or records do not support:

- RESPONSE :27 "the labelled chain is never read by any method" — `notes`/`category` are label-bearing and are read by every method (§4.2).
- RESPONSE :52–53 "(iv) timescale … A failing check triggers repair (drop/reorder) or rejection" — interface and timescale produce warnings only (`compat.py:180,198`); there is no reorder.
- RESPONSE :178–180 / tex :118–119 "AppWeaver recovers … (re-plans around the lease …)" — it resets the runtime and re-runs the same chain (§4.6).
- RESPONSE :88 "RC validation" xApp — scaffold, no E2 RC traffic (§3).
- tex :215 "workflows composed by AppWeaver" in T6 — hard-coded chains.
- tex :22 "AppWeaver runs on a FlexRIC near-RT RIC" + paper Fig. 1/3 (LangGraph, A2A bus, MCP tools) — benchmark path is in-process Python + subprocesses (`run_harness.py:40–48` imports portal functions; 0 occurrences of "mcp"/"a2a" in the harness).
- RESPONSE :100 "55 cards (50 executable)" — 37 executable once deprecated cards (which refuse to run) are excluded.

---

## 2. ARD: Agent Cards, registry, retrieval

**What the paper says.** Agent Cards describe functions, interfaces, control scope, resource demand,
dependencies, policy constraints and MCP endpoints; the Discover agent "retrieves candidate applications
from the Agent Registry, matching subgoals to advertised capabilities rather than names" via "RAG over
Agent Registry" (paper §III-B, Fig. 2 "RAG over Agent Registry → kpm-mon.xApp, qoe-pred.rApp, …").

**What is implemented.**

| Element | Code | Assessment |
|---|---|---|
| Card schema v2 | `backend/common/models.py:49–61`: `app_type, ric, vendor, version, interfaces, consumes, produces, control_scopes[{target,mode,resource}], timescale_s, requires, conflicts_with, mcp_endpoint, capabilities` | Adequate and O-RAN-specific. Missing: `policy_constraints` / resource demand that the paper lists; `a2a_card_url` from the plan (T2) not present. |
| Cards for xApps | `backend/agents/{kpm,slice,tc,rc}.py` | KPM: `E2SM-KPM v2.03`, produces PRB/thp/delay, read scope. SLICE: write `slice_control`. TC: write `tc_control`. RC: interfaces `E2SM-RC v1.03`, write `cell/rc_control`, capabilities `control_validation, policy_gate` — **RC's card describes a function the xApp does not have**. |
| rApp cards | `rapps/build_catalog.py` FAMILIES (16) → `catalog.json` (46) | Text is templated ("<Name> rApp (<use case>). Emulated rApp served by rapps/runtime.py; …"); every card in a family has identical capabilities/consumes/produces, differing only in vendor word and tool-id prefix. This makes vendor distractors trivially separable by the family de-dup and gives the planner no information about *when* to use an rApp. |
| Retrieval | `backend/orchestration/discovery.py`: BM25 over id/name/role/description/capabilities/skills/use cases/interfaces/consumes/produces/measurements/scope targets, with a 9-entry synonym table (:223–233); family de-dup (:313–327); deprecated excluded unless `include_deprecated`; `k<=0` returns all | Reasonable and reproducible; **it is lexical, not RAG**. Query = intent text + category + notes (`run_harness._intent_text`) — the `notes` leak inflates hit rate. |
| Prompt | `agentcard_prompt` :864–880: cards serialised as `{agent_id,label,app_type,description,capabilities,requires,control_scopes,status,actions}` | Omits `consumes/produces/interfaces/conflicts_with/timescale_s`, i.e. the planner never sees the fields the compat check will use; it is then "repaired" for violating constraints it was not shown. |
| Compose checks | `compat.py:149–201` | See §1 R1.1. Reasonable first version. |
| Prompt cap | portal `MAX_PROMPT_CHARS = 8000` (:723) applied in `api_run_task` (:3312); harness `--max-prompt-chars` raises it; Batch B re-ran the two card methods at 64 k | Fixed; the merged Batch B manifests record it. The gpt-oss Batch A manifest shows `max_prompt_chars: 8000` under `evaluation_runtime_config` — fine for Batch A (no directory), but the Batch B command must pass 64000 again. |

**Is it a faithful realisation of ARD?** Partly. Discovery is capability-text retrieval over machine-readable
cards and the compose step does check declared dependencies and scopes, which is the core of the claim.
It is not RAG (no embeddings, no generation-conditioned retrieval), the Discover/Compose/Validate/Deploy
"agents" are three Python functions in the harness, and there is no A2A traffic between them.

**Concrete weaknesses and fixes.**

1. *Retrieval loses the control primitives* (item 8). With k=8 and 4 xApps + 16 families competing, KPM/RC/SLICE
   are outranked in 39/240 records; `healing_full_chain` loses KPM 3/3. Fix: `discover(..., pin=executable xApps)`
   so k bounds the rApp candidates only; report hit rate with and without pinning as the R3.4 ablation.
2. *Card text quality.* Add per-family "use when / do not use when" sentences and 2–3 intent-like example
   phrases (written from the O-RAN use-case descriptions, **not** from the benchmark intents). Improve the
   RC card (today it matches nothing). Keep the templated line that says the rApp is emulated.
3. *Distractor design is weak.* Vendor variants are copies; deprecated cards are filtered before retrieval
   (`discovery.py:309`) so the "deprecated trap" tests nothing at k≥1 (the planner never sees `rapp.*.v0`).
   Better distractors: near-miss families with overlapping vocabulary but a different control target
   (e.g. "UL interference" vs "DL power control"), cards with a conflicting `control_scope` on the
   same resource, and an "all-in-one optimiser" card that claims every capability. Keep deprecated cards
   *visible* to the planner and let the compat/lifecycle check reject them, so the trap is real.
4. *Planner sees fewer fields than the checker.* Include `consumes/produces/conflicts_with/timescale_s`
   in the prompt serialisation (`executable_agent_cards` :187–217).
5. *Repair.* Replace drop-only repair by: insert the earliest producer of a missing `requires/consumes`
   (KPM for raw measurements, the rApp that `produces` the data model), then re-run `check_chain` until no
   error. Log each insertion as a compat event so it is visible in the record.
6. *Synonym table* (`discovery.py:223–233`) was written with the benchmark vocabulary in view; keep it but
   freeze it before the final batch and state it in the paper as part of the Discover design.
7. *Naming.* "RAG" → "lexical retrieval (BM25) over Agent-Card text"; "Agent Registry" is a Python dict
   in the portal (`AGENTS`), served at `/.well-known/agents/<id>.json` (`portal :1176`); fine, say so.

---

## 3. App inventory

| Id | Type / card | What really runs | E2 message sent? | Applied by RAN? | KPI effect? | Card correct? |
|---|---|---|---|---|---|---|
| `kpm` | real xApp card (`backend/agents/kpm.py`) | `xapp_kpm_bus_reader.py` reads the shared KPM bus (`kpm_bus_service.py`, port 8091) that holds indications from one E2 KPM subscription to `emu_agent_gnb` | KPM subscription by the bus collector (not by the action) | n/a (observation) | values are `rand()` (`sm_kpm.c:13–34`) | Mostly. `interfaces` says KPM v2.03 (the `~/flexric` build); rApp cards say v3.00 — the interface check only compares family, fine. |
| `slice` | real xApp | `xapp_slice_suite.py --profile monitor|static`: subscribes SLICE indications; `static` sends `control_slice_sm(ADDMOD)` (:318) | yes (E2 CONTROL) | emulator prints "SLICE CONTROL ADD rx" and acks (`sm_slice.c:34–55`); no state | none | Yes. Note `monitor` is read-only but the card's scope is write — add a per-action scope. |
| `tc` | real xApp | `xapp_tc_suite.py --profile codel|all` sends TC control (`xapp_tc_common.py`) | yes | acked, discarded (`sm_tc.c:33–50`) | none | Yes. `apply-all` is acknowledged in only 6/55 Batch A calls (marker never printed) — fix marker or drop the action. |
| `rc` | "RC validation" card: `control_validation, policy_gate`, write `rc_control` | `xapp_kpm_rc_suite.py --profile rc`: prints two lines (:58–60) and sleeps; no subscription, no control | **no** | — | none | **No.** Either implement RC (emulator supports RC control style 1 "Radio Bearer Control", `sm_rc.c:242–295`, and RC indications) or re-card it as "rc-probe: checks that the E2 node advertises E2SM-RC" with read scope and no `policy_gate` capability. |
| `mac`, `rlc`, `pdcp`, `gtp` | monitor cards, no actions | nothing | — | — | — | Harmless but inflate "9 cards"; say "4 executable xApps + 4 descriptive monitor cards". |
| `orchestrator` | card, no actions | the LLM task endpoint | — | — | — | It is the planner host, not an app. |
| `rapp.*` (46 cards, 16 families; 13 deprecated) | emulated rApps | `rapps/runtime.py: decide()` (:105–149): threshold/linear rules on the latest PRB/thp/delay per "cell" (keyed by `amf_ue_ngap_id`) from the KPM bus; `apply_*` tools write a JSON "A1 policy" to `/tmp/flexric_rapps/policies` (:157–175); nothing is pushed to the RIC or to an xApp (the docstring's "launching it through the portal" is not implemented) | no | no | none | Outputs **do** depend on live KPM (they read the bus) but on *random* KPM in Batches A/B, so decisions are noise; on ns-3 KPM (T6) they are meaningful. Cards: `slice_sla` consumes `slice.policy` → unreachable label (§1 item 7); `pm_kpi` does not provide `kpi_monitoring` → the PM-first alternative is unreachable; `ue_qos_control` requires `qoe_prediction` (ok); `traffic_steering.conflicts_with = [cell_power]` fires whenever a `cell_power` writer (`energy_saving`, `capacity_mgmt`) precedes it — intended for `steering_then_energy`, and in `stadium_congestion_surge` it correctly rejected a planner chain that put `capacity_mgmt` first (3/3 records). |

Fixes: (i) `slice_sla.consumes`: replace `slice.policy` by `RRU.PrbTotDl` (it already consumes it) so the
labelled KPM→SLICE_SLA→SLICE→RC chain is reachable, or relabel with SLICE before SLICE_SLA; (ii)
`pm_kpi.capabilities += kpi_monitoring` or drop the PM-first alternative; (iii) RC as above; (iv) honest
counts: 9 portal cards = 4 executable xApps + 4 monitor cards + orchestrator; directory = 46 cards = 33
active + 13 deprecated; executable in the planner's view = 4 + 33 = 37.

---

## 4. Test intents and labels

### 4.1 Splits
`intents_50.json`: 11 known (the three templates: 5× KPM→SLICE→TC→RC, 3× SLICE→KPM→RC, 3× TC-only
incl. the seeded `tc_conflict_recovery`), 39 open-world over the same four xApps
(7× KPM→SLICE→TC→RC, 10× KPM→TC→RC, 9× KPM→RC, 8× KPM→SLICE→RC, 5× TC→RC). `intents_v2.json` adds 30
unseen-capability intents (`build_intents_v2.py:41–71`). Definitions are clear and defensible.

### 4.2 Leakage into methods (P0)
- `notes` (all 50 base intents) describe the chain in words; a crude keyword mapping reproduces the exact
  chain for 13/50 and the structure ("TC-only", "Direct TC plus RC", "Observation plus transport control and
  RC validation", "Investigation-only path") for most others. v2 notes are worse ("Observe PRB load, pick sleep
  cells, validate the RC control", "QoS controller requires QoE prediction upstream (card dependency)",
  "Underspecified: planner must add the observation step", "the deprecated release must still not be selected").
- They enter: `llm_prompt` (:712), `llm_blind_prompt` (:728), `agentcard_prompt` (:878), `discover_cards`
  query (:172 via `_intent_text`), `deterministic_discovery_chain` (:254), `default_action_for_agent` (:235).
- `category` enters the same prompts and is the primary key of `route_intent` (:131–139).
- Verified in the records: Batch A AppWeaver `xr_latency_guard` prompt contains
  "Notes: Closed-loop latency reduction with KPI observation, slice review, TC action, and RC validation."

Fix: methods receive only `intent["intent"]`. Keep `notes`/`category` as annotation. Any method that
needs a category must derive it from the text (the rule router becomes a keyword router — which is what
the paper says it is).

### 4.3 Can a rule-based method pass by construction?
Yes on the known split: `route_intent` maps `category ∈ {slice, transport, latency}` to a template, and the
11 known intents are labelled with exactly those templates → 100 % by construction (tex :87 admits this).
After the fix it will be <100 % and that is fine. `deterministic_discovery_chain` (AppWeaver's fallback) is
likewise a benchmark-tuned router; it did not fire in Batch A but must go.

### 4.4 Observe-first (O6) and the known split
AppWeaver's known-split chains (Batch A, 55 records): KPM→SLICE→RC for the three SLICE→KPM→RC intents
(15/15), KPM→TC(→RC) for the three TC-only intents (15/15), KPM→TC→RC instead of KPM→SLICE→TC→RC for 3 of
the 5 four-step intents (15/15) and 4/5 repeats of a fourth; only `xr_latency_guard` matched (5/5).
The prompt instructs "Use KPM first" and "Use RC last" (:873–874), so the method is doing what it was told;
the labels encode the portal templates' order. This is a label/prompt mismatch, not a finding about
composition.

Principled, pre-registrable rule (decide and commit before the final batch; apply to all methods; report both):
- **Primary metric (new): required-steps match under a partial order.** Each intent gets `required: set of
  apps`, `order: {observe < control, control < validate}` and `forbidden: write-scope apps not in required`.
  A chain is correct iff it contains exactly the required set (plus, optionally, read-only analytics — see
  O8), respects the partial order, and contains no forbidden writer. This rule is derivable from the
  intent text and the cards' scopes and does not mention any method.
- **Secondary metric: exact match with the labelled (template) chain**, as today.
- What would be post-hoc and must not be done: adding `KPM→SLICE→RC` as an accepted chain *only* for the
  intents where AppWeaver produced it; changing the agent-card prompt to "match template order" after seeing
  results; or deleting the three TC-only intents.

### 4.5 Directory distractors (O8)
Batch B open-world misses (AppWeaver, k=all, 97/117 records): roughly a third add a read-only analytics
rApp and keep every required step in order (e.g. `downlink_jitter_containment` → KPM→RAPP.TRANSPORT_QOS→TC→RC;
`rlc_queue_anomaly_detection` → KPM→RAPP.ANOMALY_DETECTION — but drops RC); the rest replace the control
step (`backhaul_queue_conflict_recovery` → KPM→RAPP.TRANSPORT_QOS→RC with no TC; `stadium_congestion_surge` →
KPM→RAPP.CAPACITY_MGMT→RC). Under the partial-order rule of §4.4 the first group is correct (if the analytics
rApp is read-only and the intent's wording admits analysis), the second is wrong. Note that `RAPP.TRANSPORT_QOS`
is a *write*-scope card (`tc_control`), so chains that substitute it for TC are wrong even under O8's
"read-only extras" rule — the labels did this right.

Decision framing: adopt the partial-order rule as primary **for both batches**, state it in §IV-A, and keep
exact-match as the secondary column. This is defensible because the rule is written from the cards'
declared scopes, not from any method's output. Record the decision (date, rule, who) in `REVISION_PLAN.md`
§3c before launching the final batches.

### 4.6 Seeded conflicts and "recovery"
Mechanics are correct and documented (`CONFLICTS.md`). What the records show for AppWeaver (Batch A, 30
seeded records): 24 hit the lease (409) on TC/SLICE, the LLM recovery planner returned the same chain
with `reset_runtime: true` (rationale: "clears the busy state/conflict lock on the TC agent"), the harness
reset the portal runtime — killing the seed workflow — and re-ran the same chain cleanly. The other 6 records
never reached the busy app (chain without TC) and so neither detected nor recovered. "Recovered 80 %" is
therefore "pre-empted the other workflow 80 %". The baselines "0 %" is because they are never given a
second attempt.

Honest options (choose before re-run): (a) **queue-and-resume**: recovery waits for the lease (bounded by
`duration_s`) and resumes; metric = completed without pre-emption; (b) **re-plan without the resource**:
the recovery prompt is told the busy resource is unavailable and must produce a chain that excludes it
(for seeds where that is meaningful — not for `tc_conflict_recovery` whose whole intent is TC);
(c) report the reset path as "operator-level override" and make no claim. (a)+(b) are implementable in
`execute_langgraph_agentcard` (:1476–1496) by removing the forced reset at :1484 and passing
`busy_resources` to the recovery prompt. Give the baselines the same bounded wait so the comparison is
about planning, not about who gets a retry.

### 4.7 Other label checks
- v2 inconsistencies (RC/KPM presence) — see executive item 6; the partial-order rule resolves them if
  "validate" is declared optional-but-ordered for rApp-terminated chains, or required everywhere; pick one
  and apply to all 30.
- `slice_sla_breach`, `night_energy_saving` alternative — unreachable (item 7).
- `deprecated_card_trap` / `vendor_variant_trap`: the deprecated card is filtered before the prompt, so the
  trap is untested; vendor variant is accepted either way — fine.
- `expects_conflict` is `False` for all v2 intents; `energy_vs_capacity_conflict` and `rollout_blocked_by_energy`
  are "scope conflict" intents whose correct answer is *not composing* a card; they are scored only by chain
  match, which is right.

---

## 5. Digital twin

### 5.1 What the FlexRIC emulator can and cannot validate
`emu_agent_gnb` (`examples/emulator/agent/`) is an E2 *interface* emulator: it performs E2 setup with
RAN function definitions for KPM/RC/MAC/RLC/PDCP/GTP/SLICE/TC, answers subscriptions with indications
filled by `test/rnd/fill_rnd_data_*` (KPM values `rand()%1024`, `5 + rand()/…`; `ue_fullfills_predicate`
returns `rand()%2`), and answers CONTROL requests with a CONTROL-ACK after a `printf` (`sm_slice.c`,
`sm_tc.c`; RC control similar). It keeps no state: a slice ADD does not change later slice indications,
a TC policy does not change delay. Therefore:

- It **can** validate: E2 encode/decode of the control message, that the target E2 node advertises the
  RAN function and style the card claims, that the subscription is accepted, that the xApp process runs
  and acks, the portal's lease/compat logic, and the timing of the chain. This is an *interface
  conformance / dry-run sandbox*.
- It **cannot** validate: any KPI effect, any conflict that manifests as interfering control outcomes,
  any "state sync" (there is no state to sync). The paper's Fig. 4 "MAC/RLC/PDCP state sync" and §III-A
  "twin that mirrors the per-layer RAN state as a live replica" cannot be claimed for it.

The owner's suggestion to re-adopt the emulator as "the twin for testing results and updating state" is
defensible **only** as tier 1 below. If state updating is wanted, ~200 lines of C in `sm_slice.c`/`sm_tc.c`
(a slice table and a per-bearer policy table that later indications reflect) would make the emulator
stateful, but still without KPI semantics; a reviewer who asked "how faithful is the twin" will not accept
that as a network model.

### 5.2 Proposed Validate design (two tiers, honest names)

```
Compose ──► Validate-1 (conformance dry-run on the FlexRIC E2 emulator; every intent)
              • compat checks (compat.py) + lease simulation
              • launch each step against emu_agent_gnb with a short duration; require
                subscription OK / CONTROL-ACK for every control step; record per-step verdict
              • verdict: deployable-interface | reject (unknown RAN function, encode error, lease clash)
          ──► Validate-2 (KPI what-if on the ns-3 twin; only chains whose control is RC-actuable)
              • state sync from live KPM: per-cell UE count (and, P1, UE positions) → twin scenario args
              • run chain on twin at t_act, obtain policy P and predicted ΔKPI (vs twin no-op)
              • gate: accept P iff predicted Δenergy/ΔPRB within policy bounds and sign as intended
          ──► Deploy (live) only if V1 passes and (when applicable) V2 accepts
```

Tier 2 is exactly T6's protocol, turned into a gate. The defensible claim becomes: "the twin is a guard
for the policy *class* (it predicts the sign and magnitude of cell-level energy/PRB change); it does not
predict per-user QoS". The experiment that demonstrates it:

- **Gate accuracy.** For each (seed pair, workflow): twin verdict accept/reject (threshold e.g. predicted
  energy saving ≥ 5 % *and* predicted PRB increase on remaining cells ≤ 30 %) vs. live outcome
  (same thresholds on measured deltas). Report precision/recall of "accept" with Wilson CIs over the
  8–9 pairs × 3 workflows. This is the number reviewers want ("does validation prevent harmful deployments?").
- **Fidelity by sync level** (P1): none (base batch, already done) → load-synced (loadcal, done) → load +
  placement-synced (new: pass live UE drop positions to the twin via the scenario's `ue_position.txt`
  input, `~/ns-oran-flexric/APPWEAVER_SETUP.md` §"Scenarios write … ue_position.txt"). Show sign
  agreement and |error| improving monotonically. That is the "state sync" story with evidence.
- Keep: A/A noise bound, no-op baselines, per-pair scatter (Fig. 7).

Code needed (all new files, none touch the running stack):
- `backend/orchestration/validate.py`: `validate_chain(chain, mode)` returning a `ValidationReport`
  {compat, dryrun per-step verdicts, twin prediction, gate decision}; `--validate-mode none|dryrun|twin` in
  `run_harness.py`, `validation_report` in each record, and a `validate_rejects` metric.
- `evaluation/twin/twin_service.py`: wraps `run_twin_validation.py` pieces into "run chain X on twin with
  N_Ues/positions from this KPM snapshot, return policy + predicted deltas" (one ns-3 run ≈ 3–4 min wall
  for 8 sim-s at 25× — acceptable in the Non-RT loop; say so).
- `evaluation/twin/run_twin_validation.py`: add `--sync positions` and the gate computation to `summary.json`.
- Emulator statefulness (optional, P2): `examples/emulator/agent/sm_slice.c`, `sm_tc.c`.

What must be stated as limitation: both twin and live are ns-3; only RC-actuable chains get tier 2;
8 sim-s windows; rApps are emulated decision rules.

---

## 6. Corrected, prioritised plan

Legend: **Re-run** = which batches must be re-run after the change (A = Batch A, B = Batch B k8+k0,
T6 = twin). **Owner** = needs an owner decision. Items within a priority can be done in parallel unless a
dependency is noted. Nothing here touches the running stack until the final batches are launched.

### P0 — required for acceptance (fix, then one final set of batches)

| # | Change | Files | Acceptance criterion | Re-run | Owner |
|---|---|---|---|---|---|
| P0-1 | Remove `notes` and `category` from every method input: prompts, retrieval query, fallbacks, routing. Methods see `intent["intent"]` only. Add a harness assert that no prompt contains the `notes` string. | `evaluation/run_harness.py` (`_intent_text`, `llm_prompt`, `llm_blind_prompt`, `agentcard_prompt`, `agentcard_recovery_prompt`, `route_intent`, `default_action_for_agent`) | `grep -c "Notes:" records.jsonl` = 0; prompt hashes in manifest change; rule router known accuracy reported whatever it becomes | A, B | no |
| P0-2 | Replace forced-reset recovery: delete the `or initial_conflict or initial_failure` at :1484; recovery = bounded wait for the lease (queue) or re-plan with `busy_resources` excluded; give every method the same bounded wait. Rename metrics: *refused*, *completed after wait*, *re-planned around resource*, *pre-empted* (should be 0). | `run_harness.py:1431–1519`, `agentcard_recovery_prompt`, `analyze_results.py`, `make_paper_figures.py`, `METRICS.md`, `CONFLICTS.md` | No record calls `api_runtime_reset` inside a method; seeded-conflict columns recomputed; text in §IV and R3.5 rewritten | A (seeded intents at least; simplest: whole A), B | yes (which recovery semantics to claim) |
| P0-3 | Pre-register labels: partial-order rule (§4.4) implemented as `required`, `order`, `forbidden` per intent, generated by a script from the existing chains + card scopes; decide RC/KPM policy for v2; fix the two unreachable labels via cards (P0-5). Commit with date before launching batches. Report both metrics. | `evaluation/build_intents_v2.py` (new `label_rules.py`), `intents_50.json`, `intents_v2.json`, `make_paper_figures.py`, `METRICS.md`, `REVISION_PLAN.md §3c` (O6/O8 closed) | Rule text in `METRICS.md`; every intent passes its own label under the rule; git commit precedes batch manifest `created_at` | A, B | yes (O6/O8 — rule choice) |
| P0-4 | Remove `deterministic_discovery_chain` from AppWeaver (empty plan → failed record, counted). | `run_harness.py:253–273, :900–903` | `planner_repaired` reason "deterministic" never appears | A, B (no effect expected) | no |
| P0-5 | Card fixes: `slice_sla.consumes`; `pm_kpi.capabilities += kpi_monitoring`; RC card re-described as what it does (or P1-3); per-action scope for `slice.monitor`; drop or fix `tc.apply-all` ack marker. Regenerate `catalog.json`. | `rapps/build_catalog.py`, `backend/agents/{rc,slice,tc}.py`, `run_harness.TOOL_ACK_MARKERS` | Labelled chains of all 80 intents pass `check_chain` with 0 errors (add a unit test) | B (A only if RC/TC action ids change) | no |
| P0-6 | Pin executable xApps in retrieval; k bounds rApp families. Keep deprecated cards visible to the planner (so the trap is real) and reject them at compat time. | `backend/orchestration/discovery.py`, `run_harness.discover_cards` | k=8 hit rate reported with/without pinning; `deprecated_card_trap` prompt contains `rapp.energy_saving.v0` | B | no |
| P0-7 | Honest Section IV / letter text: RC is a probe; emulator = E2 interface emulator with synthetic KPM and acknowledged-but-not-applied control; benchmark path is in-process Python + subprocess xApps (LangGraph/A2A/MCP exist but are not on the measured path, or move the planner onto LangGraph — P1-4); "RAG" → BM25; T6 chains are the benchmark chains; executable card counts (4 + 33). Remove `before`/`after` KPI fields from any Batch A/B figure. | `evaluation/paper_results/evaluation_section.tex`, `docs/RESPONSE_TO_REVIEWERS.md`, paper §III/Fig. 1/3/4 | Every sentence listed in §1 "claims not supported" is gone or true | — | no |
| P0-8 | Manifest completeness before the final batch: `prompt_builders_sha256` non-null, `LLM_SERVER_HARDWARE` set (O3), `max_prompt_chars` 64000 for B, intent-file git hash. | `run_harness.manifest`, env | Manifest fields non-null | (part of A/B) | yes (O3 GPU line) |
| P0-9 | Final batches with the paper's model on spark1 (gpt-oss-120b, reasoning effort recorded, O5 closed): A (5 repeats), B k=8 and k=all (3 repeats). Discard the currently running A batch for paper use (leaky prompts); keep it as the pilot. | commands in `README.md` | Tables/figures regenerated from manifests whose `created_at` postdates the P0 commits | A, B | yes (O1/O2/O5 already leaning spark1) |

Dependencies: P0-1…P0-6 and P0-8 are code and must land before P0-9; P0-3 depends on P0-5 (labels must be
reachable). P0-7 can be written in parallel and finalised after P0-9. Estimated batch time with gpt-oss-120b
at the observed ≈15 s/record (70 records in 18 min in the running batch): A ≈ 6.5 h, each B ≈ 6–7 h.

### P1 — strengthens the paper (do before resubmission if time allows)

| # | Change | Files | Acceptance | Re-run | Owner |
|---|---|---|---|---|---|
| P1-1 | Validate-1 dry-run on the emulator as a real step of AppWeaver (`--validate-mode dryrun`), with per-step conformance verdicts in the record; report "chains rejected before deploy" (expect >0 only for hallucinated/deprecated/unsupported-RAN-function steps). | `backend/orchestration/validate.py` (new), `run_harness.py` | `validation_report` in every AppWeaver record; a seeded "unsupported RAN function" intent is rejected | A, B (if done before P0-9, no extra run) | no |
| P1-2 | Validate-2 gate + placement sync on ns-3 (§5.2): gate precision/recall, three sync levels. | `evaluation/twin/run_twin_validation.py`, `twin_service.py` (new), `TWIN_VALIDATION.md`, Fig. 7 | New table: gate P/R per workflow; fidelity improves with sync level | T6 (new batch, ≈ 72–108 ns-3 runs, parallel 4 → ~3–4 h) | yes (scope: is the placement-sync experiment wanted) |
| P1-3 | Implement RC for real: RC control style 1 (Radio Bearer Control / QoS flow mapping) against the emulator, or an RC REPORT subscription that returns indications; ack marker = CONTROL-ACK / indication. | `xapp_kpm_rc_suite.py` or new `xapp_rc_ctrl.py`, `backend/agents/rc.py` | RC acked by E2 CONTROL-ACK in records | A, B (if before P0-9) | no |
| P1-4 | Put the AppWeaver planner on the LangGraph runtime (Discover→Compose→Validate→Deploy nodes in `backend/graph/nodes/`), so Fig. 1 is true; keep in-process calls. | `backend/graph/`, `run_harness.execute_langgraph_agentcard` | `graph_backend` = langgraph in AppWeaver records | A, B (if before P0-9) | no |
| P1-5 | Repair by insertion + fixpoint re-check; planner prompt shows `consumes/produces/conflicts_with/timescale`. | `compat.py`, `run_harness.plan_with_agent_cards`, `executable_agent_cards` | No executed chain violates `check_chain`; unit test | B | no |
| P1-6 | Card text: use/do-not-use sentences, examples from O-RAN use-case text; better distractors (§2 item 3). Freeze before P0-9. | `rapps/build_catalog.py` | Retrieval hit ≥ current at k=8 without the notes leak | B | no |
| P1-7 | Ablation hygiene: `agentcard_no_repair` should differ from AppWeaver in exactly one thing; add `agentcard_no_compat` and `agentcard_no_recovery` if space allows, or rename the row "AppWeaver (plan only)". | `run_harness.execute_method` | Table II row names match the code | A | no |
| P1-8 | Seeding symmetry: use the same seed mechanism (enforced workflow + lease) for every method, or document the difference. | `run_harness.seed_conflict_if_needed` | `conflict_seed.type` identical across methods | A | no |

### P2 — nice to have

| # | Change | Files | Notes |
|---|---|---|---|
| P2-1 | Stateful emulator (slice table, TC policy table reflected in indications). | `examples/emulator/agent/sm_slice.c`, `sm_tc.c` | Makes Validate-1 catch "policy already present" conflicts; no KPI semantics. |
| P2-2 | Embedding retrieval behind `discover()` (nomic-embed on the Ollama host) as a second retriever; report hit rate vs BM25. | `discovery.py` | Answers R4 "RAG" literally. |
| P2-3 | Serve rApps over MCP (`rapps/runtime.py --serve`) and call them through the MCP client in the AppWeaver path; same for xApps via `flexric_mcp_server.py`. | `run_harness.invoke_action` | Makes Fig. 3(b) true; adds latency, record it. |
| P2-4 | Second planner model (qwen3.6:27b with reasoning on) as a robustness row. | — | Uses O2 endpoint; preliminary batches already exist but with leaky prompts — would need re-run. |
| P2-5 | Split `flexric_agent_portal.py` planner/registry parts into `backend/` (T0 leftover). | portal | No behaviour change; do after batches. |

### What must not be done
- Do not add accepted chains per intent after looking at which method produced them (O6/O8 by inspection).
- Do not change the agent-card prompt wording to match template order, or the templates to match the prompt,
  after seeing results; if the order rule changes, it changes through the label rule for all methods.
- Do not reuse any number from the running gpt-oss batch or the qwen batches in the paper once P0-1 lands.
- Do not present emulator KPM deltas as network effect, or the reset path as recovery.

### Minimal re-run set
After P0: **A** (1500), **B k=8** (1440), **B k=all** (1440) with gpt-oss-120b. **T6** stays as is unless
P1-2 is adopted (then one new T6 batch; the existing two remain valid as the "no sync"/"load sync" rows).

---

## Appendix: evidence pointers used above

- Batch A merged: `evaluation/runs/20261028T004100Z_A_prelim_qwen36_nothink_merged/records.jsonl` (1500;
  250 per method). AppWeaver known 5/55 exact; open-world 71.3 %; `planner_repaired` 0/250; `compat_ok`
  True 226 / None 24. Seeded: 30 records, 24 lease refusals, 24 "recovered" by reset + identical chain.
  Acks: `tc apply-all` 1/10 (AppWeaver), 2/11, 3/34; `rc rc-scaffold` 233/234 (print marker).
- Batch B: `…B_k0_…merged` and `…B_k8_…merged` (1440 each). AppWeaver unseen 64/90 and 56/90; open-world
  20/117 and 14/117; known 0/33 and 0/33. Compat errors: `rapp.slice_sla consumes slice.policy` 42 records (k0);
  retrieval misses 13 intents × 3 at k=8, 11 of them KPM/RC/SLICE.
- gpt-oss pilot (running, read-only): `~/flexric/build/examples/xApp/python3/evaluation/runs/20261028T072646_227695Z_A_final_gptoss120b_spark1/records.partial.jsonl`
  (70 records at 09:44 local; AppWeaver median 15.2 s, max 34.1 s; same `Notes:` prompt).
- Emulator: `~/flexric/examples/emulator/agent/sm_kpm.c:13–34, 280–304`, `sm_slice.c:34–55`, `sm_tc.c:33–50`,
  `sm_rc.c:242–295`.
- Twin: `evaluation/twin/run_twin_validation.py:1–80`, `evaluation/runs/20261027T171217Z_T6_twin_vs_live_loadcal/manifest.json`;
  simulator cost and single-subscriber limit: `~/ns-oran-flexric/APPWEAVER_SETUP.md` §8, §10.
- Portal: `flexric_agent_portal.py:723` (`MAX_PROMPT_CHARS`), `:2185–2212` (`_reset_runtime_locked`),
  `:2809` (`AgentBusyError`), `:3311–3319` (`api_run_task`), `:1137–1176` (A2A card paths).
