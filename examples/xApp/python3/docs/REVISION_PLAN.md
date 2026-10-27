# AppWeaver major-revision plan (WCM-26-00422)

Written 2026-10-27. Companion: `REVIEW_ASSESSMENT_2026-10-27.md` (what the code does vs. what the
paper says). This file is the working roadmap; tick items off and record decisions here.

## 0. Ground rules for whoever executes this (human or an Opus 5.5 session)

- Work in `~/flexric` on branch `appweaver-revision` (remote `dangy1` = github `Dangy1/flexric-py310`).
  Run things from `build/examples/xApp/python3` (CMake copies `evaluation/`, `backend/`, scripts there).
- Conda env `flexric-py310` (`~/anaconda3/envs/flexric-py310/bin/python`). Planner LLM: Ollama at
  `http://130.233.158.22:11434`, model `gpt-oss:latest` (the paper's model). Any OpenAI-compatible
  endpoint works via `OPENAI_BASE_URL/OPENAI_MODEL/OPENAI_API_KEY`.
- **Open item:** the owner mentioned a "spark1 gpt" model from the CloudAF6G project. No endpoint or
  credentials for it exist on this machine. Get the base URL + key, add it as a provider, and run the
  benchmark on both gpt-oss and spark1 so the paper has a two-model comparison.
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

## 4. Done criteria
A fresh clone + the README's three commands reproduce every number and figure in the revised paper
from `evaluation/runs/<id>/records.jsonl`, and every reviewer row in §1 has a pointer to the
section/figure that answers it.
