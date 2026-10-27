# AppWeaver major-revision plan (WCM-26-00422)

Written 2026-10-27. Companion: `REVIEW_ASSESSMENT_2026-10-27.md` (what the code does vs. what the
paper says). This file is the working roadmap; tick items off and record decisions here.

## 0. Ground rules for whoever executes this (human or an Opus 5.5 session)

- Work in `~/flexric` on branch `appweaver-revision` (remote `dangy1` = github `Dangy1/flexric-py310`).
  Run things from `build/examples/xApp/python3` (CMake copies `evaluation/`, `backend/`, scripts there).
- Conda env `flexric-py310` (`~/anaconda3/envs/flexric-py310/bin/python`). Planner LLM: Ollama at
  `http://130.233.158.22:11434`, model `gpt-oss:latest` (the paper's model). Any OpenAI-compatible
  endpoint works via `OPENAI_BASE_URL/OPENAI_MODEL/OPENAI_API_KEY`.
- **LLM hosts (owner's words, 2026-10-27):** *spark2* = the Ollama host `130.233.158.22` (tlt022.hut.fi,
  Ollama 0.40); *spark1* = a **vLLM** server (OpenAI-compatible). spark1's address/port and model id are
  not on this machine and the names do not resolve here — ask the owner, then use the portal's existing
  OpenAI provider: `OPENAI_BASE_URL=http://<spark1>:<port>/v1 OPENAI_MODEL=<served model> OPENAI_API_KEY=<any>`.
- **gpt-oss is currently broken on spark2:** Ollama 0.40 fails to load `gpt-oss:latest`
  (`key not found in model: gpt-oss.expert_feed_forward_length`, HTTP 500). Other models load
  (`qwen3.6:27b` answers in ~20 s, `gemma3:1b` in 2 s). Fix on the server: `ollama pull gpt-oss:20b`
  (re-pull a build compatible with 0.40) — owner's decision, it is their machine. Until then run
  pilots with `OLLAMA_MODEL=qwen3.6:27b`; the paper's main batch must use the model named in the paper.
- Never reuse the May-2026 numbers (see assessment §3). Every number in the revised paper comes from a
  batch produced by the fixed harness, with `manifest.json` recording model, settings and hardware.
- Keep rerunnable: one command per batch, results committed under `evaluation/runs/<id>/`
  (records.jsonl + summary + manifest; per-record dumps and PNGs stay ignored).

## 1. Reviewer asks → deliverables

| # | Ask (reviewer) | Deliverable | Track |
|---|---|---|---|
| A | Distinction from AgentRAN etc.; what Agent Cards add; how dependency / interface / control-scope compatibility is *checked* (R1.1, R3.7) | Agent-Card schema v2 with O-RAN fields + explicit Compose-time checks that are logged per record; Table I criteria defined in a footnote | T2 |
| B | Twin fidelity, predicted vs actual KPI, network-level QoE/latency/throughput (R1.2, R2.2, R3.1, R4) | ns-3 (5G-LENA) via ns-O-RAN-flexric as the RAN; twin = second ns-3 instance; report predicted-vs-measured PRB/throughput/delay/energy deltas for ≥3 deployed workflows | T4, T6 |
| C | Which apps are real xApps, which are emulated rApps (R1.3) | Honest inventory table: 4 FlexRIC xApps (KPM, SLICE, TC, RC) + ns-3 energy-saving/RF xApps + N emulated rApps from the rApp Directory | T3 |
| D | Open-world meaning; registry size & composition (R1.4, R4) | Three splits: known-template / unseen-intent / unseen-capability; registry of 50–80 cards with distractors; report counts | T3, T5 |
| E | Catalog-aware LLM baseline + ablation; model & inference settings (R1.5, R3.4, R2.3) | Baselines: `rule_router`, `single_app`, `llm_blind` (no catalog), `llm_catalog` (today's llm_only), `appweaver_no_repair`, `appweaver`; settings in manifest | T1 |
| F | Reliability denominators, seeded conflicts, hallucination numbers (R1.6, R3.5, R4) | Report total tool calls, success criterion, hallucinated refs, 6 seed types × repeats, conflict precision/recall (not accuracy) | T1 |
| G | Variance, trials, latency distribution, Non-RT bound (R2.1, R3.3, R3.6, R4) | ≥5 repeats, no planner cache, mean ± sd and CI, median/p95/max latency, cite O-RAN Non-RT ≥1 s | T1, T5 |
| H | Benchmark & code release (R2.1, R4) | Public repo with `evaluation/`, intents, cards, reproduction script | T0 |
| I | Figure 2 hints the skill; Fig 3 dense; labels; typos; refs (R4 minor, R1.7) | Paper edits | T7 |

## 2. Tracks

### T0 — Repo publishable (done 2026-10-27, keep tidy)
- [x] Branch `appweaver-revision`; hardening pass committed; `evaluation/` tracked; `.gitignore` fixed; CMake copies evaluation.
- [ ] `README.md` top-level section "AppWeaver reproduction" (stack up → batch → figures, 3 commands).
- [ ] Optional: split `flexric_agent_portal.py` (3.5k lines) — only the planner/registry parts move into
      `backend/`; do not refactor the scheduler before the reruns.

### T1 — Harness methodology (`evaluation/run_harness.py`)
1. **Remove label leakage.** `validate_or_repair_agentcard_plan` must not read `intent["expected_workflow"]`
   or `open_world`. Repair may only use the registry (unknown ids dropped, duplicates collapsed).
2. **Metric definitions** (write them in `evaluation/METRICS.md` and implement in `analyze_results.py`):
   - *workflow accuracy*: exact ordered match, plus a second column *set match* (same capability set,
     any order) — reviewers asked whether more than one chain can be valid; label alternatives as
     `accepted_workflows: [[...], [...]]` in the intent file where they exist.
   - *tool-call success*: a call succeeds only if the launched action reaches `completed`/`running` **and**
     produced an observation/control acknowledgement (KPM records read, slice/TC control ack, RC ack).
     Launch-only is reported separately as *launch success*.
   - *hallucination*: references to agents/actions not in the registry, counted per record and per call.
   - *conflict detection*: precision/recall over seeded conflicts; a detection counts only when the method
     flags the conflict **before** the control action is issued (queue/lease decision, twin rejection).
     Recovery after the fact is a separate column.
   - *latency*: wall-clock intent→validated plan; report n, mean, sd, median, p95, max; no planner cache
     (`--planner-cache-ttl-s 0` becomes the default; observation cache off for the headline run).
3. **Baselines**: `rule_router` (today's manual_rule), `single_app`, `llm_blind` (prompt has *no*
   catalog; plan executed only where it names a real agent; hallucinations counted), `llm_catalog`
   (today's llm_only, repaired), `appweaver_no_repair` (cards, no repair), `appweaver` (cards + repair
   + twin validate). Drop `langgraph_override/enforced/llm` from the paper table (keep runnable).
4. **Repeats**: `--repeat 5` minimum; record `planner_provider`, `model`, `temperature` (set 0.2 and
   fixed `seed` in the Ollama call), prompt hash, GPU host name from a `HARDWARE` env var.
5. **Seeded conflicts**: keep the 6 seeds, document each in `evaluation/CONFLICTS.md` (what is started
   first, which lease it holds, what a correct detection looks like).

### T2 — Agent-Card schema v2 + compatibility checks (`backend/common/models.py`, `backend/agents/*`)
Add fields: `app_type` (xApp|rApp), `ric` (near-rt|non-rt), `interfaces` (E2SM-KPM v3, E2SM-RC v1.03,
E2SM-CCC, A1 policy type ids, O1), `data_models` (KPM measurement names consumed/produced),
`control_scope` (cell|ue|slice|node, write/read), `timescale_s`, `requires` (capabilities or data it
needs upstream), `conflicts_with` (control resource classes), `vendor`, `version`, `mcp_endpoint`,
`a2a_card_url`. Serve them at `/.well-known/agents/<id>.json`.
Compose checks (each logged as an event and a per-record flag): (i) dependency — every `requires`
of step k is produced by some step < k; (ii) interface — consecutive steps share an E2SM/A1 data model;
(iii) control-scope — two write steps on the same scope need an explicit lease order; (iv) timescale —
no near-RT step after a non-RT one without an observation step between. Failing checks → repair or
reject, never silently pass.

### T3 — rApp Directory (ARD at scale)
Goal: a directory like Ericsson's rApp Directory (categories: Network Evolution, Deployment,
Optimization, Healing, Automation/AI Foundation) with **50–80 rApp cards** backed by *emulated* rApp
services, so discovery is a real search problem.
- `rapps/catalog.yaml`: one entry per rApp — name, vendor (fictional), category, O-RAN use case
  (energy saving UC21, traffic steering, RET tilt, RCA, capacity, PM/KPI, QoE, MRO, slice SLA,
  anomaly, interference, PCI/ANR, ES wake-up, …), schema-v2 fields, tool list. Include deliberate
  distractors: near-duplicate names, deprecated versions, cards whose `control_scope` conflicts.
- `rapps/runtime.py`: one FastAPI process hosting all emulated rApps; each exposes its MCP tools
  (`get_kpi`, `predict_*`, `recommend_*`, `apply_policy` → A1 policy to the RIC) and an A2A card.
  Tools act on the simulator through the KPM bus / RC xApp, or return model outputs computed from
  live KPM (simple regressors — documented as emulated).
- Generator script seeds the Agent Registry from `catalog.yaml`; manifest records registry size.
- Benchmark v2 (`intents_v2.json`, ~100 intents): add intents that need rApps (energy, tilt, RCA,
  QoE) and the *unseen-capability* split (cards present in the registry but absent from any template
  and from the harness's deterministic fallback).
- Discovery: with 50+ cards the prompt can't hold everything. Implement real retrieval over cards
  (BM25 first — no GPU needed; `nomic-embed-text` on the Ollama server as the embedding option) and
  report top-k recall of the correct cards as its own metric (answers "RAG overkill" with data).

### T4 — Simulator substrate (separate session; long builds)
Use **Orange `ns-O-RAN-flexric`** (ns-3 + 5G-LENA + FlexRIC E2 termination; KPM v3, RC v1.03, CCC;
gNB/UE counts via `--N_MmWaveEnbNodes/--N_Ues`; ships cell on/off energy-saving and RF-reconfig
xApps). It needs FlexRIC at the pinned `oie-ric-taap-xapps` commit built with `E2AP_V1 + KPM_V3_00`
— a **second FlexRIC build** (`~/flexric-taap`), separate from `~/flexric` (E2AP v2.03). Run its
nearRT-RIC on a different port (e.g. 36423) so both stacks coexist.
- [ ] Clone + build ns-3/LENA + pinned FlexRIC on this box (Ubuntu 22.04, i9, 62 GB; ~1–2 h build).
- [ ] Baseline scenario: 1 eNB + 4–7 gNBs, 20–40 UEs, 60–120 s runs, KPM into the KPM bus.
- [ ] Wire the ns-3 energy-saving xApp and RC handover into Agent Cards (`xapp` type).
- [ ] Alternative if blocked: `duranta-project/flexric` emulators (random KPM, no fidelity) — only
      for scale tests of discovery, not for KPI claims.
- OAI rfsim gNB (`~/openairinterface5g`, E2 agent built) stays as the *live* RAN for one headline
  twin-vs-live workflow if time permits; otherwise twin = ns-3 seed A, live = ns-3 seed B + traffic
  perturbation, stated plainly in the paper.

### T5 — Benchmark reruns
1. Stack up: `scripts/run_agent_portal_stack.sh` (nearRT-RIC, emu/ns-3 E2, portal, RPC, MCP, KPM bus).
   Verify all four services healthy in the manifest **before** any batch (May batch had them down).
2. Batch A (apples-to-apples with the paper): `intents_50.json`, 6 methods, 5 repeats, gpt-oss.
3. Batch B (scale): `intents_v2.json`, registry 50–80 cards, retrieval on/off, gpt-oss and spark1.
4. Record GPU host hardware: run `nvidia-smi --query-gpu=name,memory.total --format=csv` on
   130.233.158.22 once and paste into `evaluation/HARDWARE.md`.

### T6 — Twin-vs-live KPI validation
For ≥3 deployed workflows (energy saving, transport QoS, slice assurance): run the composed workflow
on the twin, record predicted KPI deltas (PRB, DL throughput, RLC delay, energy if ns-3 reports it);
deploy on live; measure actual deltas over the same window; report MAPE and sign agreement per KPI.
Fig. 2's MOS numbers are replaced by measured values or removed.

### T7 — Paper
Rewrite §III-B/IV with the honest inventory, metric definitions, baselines table, registry
composition, results with variance, twin fidelity, hardware, and the release URL. Fix minor
comments (p3 l54, p5 l64, capitalisation, "Agent Card", Fig 5a labels, Fig 3 density, refs).

## 3. Parallelism and ownership

- T1 + T2 + T3(code) are pure Python in this repo → one session, sequential (shared files).
- T4 (simulator build) is independent and long → its own session/worktree from the start.
- T5 needs T1–T4; T6 needs T4 + T5; T7 last.
- Owner decisions needed: spark1 endpoint; whether OAI rfsim live run is in scope; GPU host specs.

## 3b. Status at handoff (2026-10-27, planning session → execution session)

Done and committed on `appweaver-revision` (pushed to `dangy1`):
- T0: repo publishable; `evaluation/`, `rapps/`, `docs/` tracked; CMake copies them to the build tree; README reproduction section.
- T1: all items except the paper table/figure scripts. `run_harness.py` has no label leak, methods
  `llm_blind` / `agentcard_no_repair`, acknowledged tool calls (`--tool-ack-timeout-s`), conflict
  precision/recall, latency distribution + CIs, planner/model/sampling/hardware/registry in the manifest,
  defaults = 5 repeats, caches off. `METRICS.md`, `CONFLICTS.md` written. Smoke-tested + 3-intent pilot only.
- T2: Agent-Card v2 fields on the 4 xApps; `backend/orchestration/compat.py` (dependency, interface,
  control-scope incl. capability conflicts, timescale) wired into the agent-card planner; report per record.
- T3: `rapps/build_catalog.py` → 46 cards (16 families, vendor variants + deprecated distractors);
  `rapps/runtime.py` (CLI + optional MCP); `backend/agents/rapps.py` loader (`FLEXRIC_RAPP_DIRECTORY=1`,
  registry = 55 cards / 50 executable); `backend/orchestration/discovery.py` BM25 + family de-dup
  (`--retrieval-k`); `evaluation/build_intents_v2.py` → `intents_v2.json` (11 known / 39 open-world /
  30 unseen-capability). Measured top-k recall (BM25, dedupe on): k=8 → 39/50 and 67/80; k=12 → 44/50, 73/80.
- T4: running in its own session (`ns-oran-sim`, Opus 5.5) — builds `~/flexric-taap` + `~/ns-oran-flexric`;
  its nearRT-RIC is already up (port 36423). Deliverables land in `~/ns-oran-flexric/APPWEAVER_SETUP.md`.

Running on this host at handoff:
- Portal stack from `~/flexric/build/examples/xApp/python3/scripts/run_agent_portal_stack.sh`
  (nearRT-RIC 36421, emu_agent_gnb, portal 8088, RPC 8090, MCP 8000, KPM bus 8091; logs `/tmp/flexric_portal_stack`),
  started with `OLLAMA_BASE_URL=http://130.233.158.22:11434 OLLAMA_MODEL=gpt-oss:latest
  FLEXRIC_LLM_TEMPERATURE=0.2 FLEXRIC_LLM_SEED=7 FLEXRIC_RAPP_DIRECTORY=1`.
- Pilot batch directory: `build/examples/xApp/python3/evaluation/runs/*_pilot/` (3 intents ×
  manual_rule / llm_blind / langgraph_agentcard × 1 repeat). Check `acknowledged`, `retrieval`,
  `compat_report`, `planner_model`, `hallucinated_reference_count` in `records.jsonl`.

Pilot `runs/20261027T160039_707043Z_pilot_qwen` (qwen3.6:27b, 3 known intents × 5 methods, directory ON,
k=8) validated the pipeline: all tool calls acknowledged (KPM/SLICE/TC/RC and rApp runtime), `llm_blind`
hallucinated 7 non-existent apps in 3 records, `llm_only` 3/3, AppWeaver 0/3 exact because it composed
rApp chains (e.g. `KPM→RAPP.QOE_PREDICTION→TC→RC`) that the xApp-only labels reject. Consequences:
batch A runs with `FLEXRIC_RAPP_DIRECTORY` unset (same registry as the paper); batch B on `intents_v2.json`
needs `accepted_workflows` extended for the 50 old intents where an rApp substitution is genuinely valid
(decide per intent, document the rule). `compat_ok=False` on a record means the check removed steps
before execution (designed behaviour; the executed chain is `generated_workflow`).

First tasks for the execution session:
1. Verify the ack path in the pilot records; tune `TOOL_ACK_MARKERS` if an xApp never acks.
2. Port `evaluation/paper_results/make_paper_figures.py` / `plot_final.py` to the new summary fields
   (`methods[*].latency`, `conflict_recall`, `by_split`, `retrieval_hit_rate`, `tool_call_acknowledged_rate`).
3. The build-tree `evaluation/runs/` still holds the 550 MB May batches (archived at
   `~/appweaver_eval_archive_2026-10-27.tar.gz`). New batches are written there; copy finished batches
   (without `records/`) into the source tree and commit.
4. T5 batch A (`intents_50.json`, 6 paper methods, 5 repeats, gpt-oss), batch B (`intents_v2.json`,
   `--retrieval-k 8` and `0`, with/without `FLEXRIC_RAPP_DIRECTORY`), then T6 once `ns-oran-sim` reports, then T7.
   Owner inputs still missing: spark1 endpoint/credentials, `LLM_SERVER_HARDWARE` line, OAI rfsim live-run decision.

## 3c. Owner inputs (open questions — execution session, 2026-10-27)

| # | Question | Blocks | Status |
|---|---|---|---|
| O1 | Re-pull gpt-oss on spark2 (`ollama pull gpt-oss:20b` or a build that loads under Ollama 0.40); check: `curl http://130.233.158.22:11434/api/generate -d '{"model":"gpt-oss:latest","prompt":"hi","stream":false}'` returns no `error` | Final batches A and B (paper model) | **open** — still HTTP 500 `gpt-oss.expert_feed_forward_length` at 18:15 |
| O2 | spark1 vLLM endpoint: `OPENAI_BASE_URL`, served model id, API key if any | Batch B second model | **open** |
| O3 | GPU line for spark2 (and spark1): `nvidia-smi --query-gpu=name,memory.total --format=csv` → `LLM_SERVER_HARDWARE` and `evaluation/HARDWARE.md` | manifests, paper hardware sentence | **open** (preliminary manifests say "GPU model pending owner") |
| O4 | Live side of the twin experiment: OAI rfsim gNB, or ns-3 seed B + traffic perturbation | T6 | **open** — default ns-3 seed B unless the owner says OAI |
| O5 | Reasoning mode for the final batch: gpt-oss reasons by default (keep `FLEXRIC_LLM_THINK` unset). Preliminary qwen batches use `FLEXRIC_LLM_THINK=false` (24 s → 1.4 s per call); confirm that is acceptable for any qwen numbers shown | labelling of qwen results | **open** |

## 3d. Execution log
- Ack path: pilot TC call unacknowledged because the TC suite prints ~30 setup lines before `Applied`
  and the portal tail is 20 lines; the E2 `CONTROL-ACK` line is now a TC/SLICE marker and a negative
  line is only final once the xApp exited.
- Harness writes `records.partial.jsonl` + a progress line per record (long batches are watchable).
- `FLEXRIC_LLM_THINK` switch (recorded in the manifest); OpenAI path now sends temperature/seed.
- `make_paper_figures.py` / `plot_final.py` rebuilt on records + CIs (see `evaluation/METRICS.md`).
- `accepted_workflows` rule for the 50 original intents in `build_intents_v2.py` (11 intents gain one chain).

- **RIC wedge (2026-10-27 20:30):** the portal nearRT-RIC reached 18 GB RSS after ~4k xApp runs and
  stopped answering E42 setup; preliminary batch A records from ~700 on had every SLICE/TC/RC call
  unacknowledged. Kept repeats 1–2 of `20261027T161707_898276Z_A_prelim_qwen36_nothink`, re-ran repeats
  3–5 with a stack restart every 200 records (`--maintenance-cmd scripts/restart_agent_portal_stack.sh`),
  merged with `evaluation/merge_runs.py`. Every later batch uses the restart hook.
- **T6:** ns-O-RAN-flexric twin-vs-live harness (`evaluation/twin/`), 8 seed pairs × 3 RC-actuated
  workflows (energy saving, traffic steering, QoE-driven steering) + no-op; A/A repeat shows the
  simulator deterministic (≤0.4 %). Second run with a load-calibrated twin (twin UE count = live).
  Transport QoS and slice assurance cannot be actuated in ns-O-RAN (no TC/SLICE SM) → not in T6.
- **RIC wedge, second form (2026-10-27 22:40):** after each restart the RIC stopped answering E42
  setup again within ~75 records (RSS stays 4.8 MB, so not the leak; `SCTP_SEND_FAILED` to
  disconnected xApps in its log). The fixed-interval restart cannot prevent it, so the r3–5 re-run
  `20261027T184147_635835Z_A_prelim_qwen36_nothink_r3to5` is discarded. New: `scripts/probe_e42.sh`
  (registers a throw-away xApp, 1 s when healthy, times out when wedged) runs after every record
  (`run_harness.py --health-cmd`); a record that ends on a wedged RIC goes to
  `records.discarded.jsonl`, the stack restarts and the record is re-run (`infra_attempts`,
  manifest `maintenance.health_failures`). Repeats 3–5 and Batch B re-launched this way
  (`/tmp/appweaver_batches/chain_AB_prelim_v2.sh`). Repeats 1–2 of the first run stay valid (RC acked
  100 % in every 50-record chunk up to record 700).
- **T6 results** in `evaluation/TWIN_VALIDATION.md`; twin RngRun 3 with 10 UEs aborts inside ns-3
  (deterministic), replaced by pair 9.

## 4. Done criteria
A fresh clone + the README's three commands reproduce every number and figure in the revised paper
from `evaluation/runs/<id>/records.jsonl`, and every reviewer row in §1 has a pointer to the
section/figure that answers it.
