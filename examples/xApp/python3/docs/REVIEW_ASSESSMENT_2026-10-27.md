# AppWeaver — implementation vs. paper vs. reviewer comments

Assessment written 2026-10-27 after reading the submitted PDF and the code on this machine.

## 1. Where things actually are

| What | Location | State |
|---|---|---|
| Live code (portal + LangGraph backend) | `~/flexric/examples/xApp/python3/` (branch `flexric-py310`, GitHub `Dangy1/flexric-py310`) | 4 files modified, uncommitted (the July hardening pass in `CLAUDE_CHANGES.md`) |
| Evaluation harness, 50-intent benchmark, 29 run batches, paper figures + LaTeX | `~/flexric/build/examples/xApp/python3/evaluation/` | **Never committed.** `build/` is gitignored, and `.gitignore` also ignores `*.py` and `*.json`. One `rm -rf build` loses the paper's evidence. |
| `~/flexric-py310-repo` | March-2026 snapshot | Stale, behind the remote; ignore |
| Planner LLM | Ollama 0.40 on GPU server `130.233.158.22:11434` | Reachable now; `gpt-oss:latest` (20.9B MXFP4) still present |
| RIC / emulator / OAI | `~/flexric/build` (nearRT-RIC, emu_agent_gnb), `~/openairinterface5g` (nr-softmodem, nr-uesoftmodem, librfsimulator), `~/oai-cn5g` (docker) | All built; nothing currently running |

The paper's "AppWeaver" is the `langgraph_agentcard` method inside `run_harness.py` (1702 lines). The portal itself has **no** intent-to-workflow planner — its README says so. Planner, Discover, Compose, Validate are prompt + repair functions in the harness; "Deploy" is `api_run_action` launching a suite subprocess.

## 2. What the paper describes that the code does not do

| Paper claim | Code reality |
|---|---|
| Digital twin mirrors MAC/RLC/PDCP state; Validate agent runs what-if, predicts MOS 2.8→3.6, counts conflicts | No twin anywhere (0 hits for twin/emulator/digital in portal or harness). "Validate" = RC approve node checking service health; "conflict" = scheduler lease collision. Fig. 2's MOS numbers have no source. |
| RAG over the Agent Registry | No embeddings/vector store in the env; the full card list (4 executable agents, 7 actions) is pasted into the prompt. |
| Four Codex-written xApps: KPM, QoE prediction, mobility optimisation, QoS control | Executable agents are KPM, SLICE, TC, RC (FlexRIC suites). No QoE or mobility code exists. |
| Agents communicate over A2A during orchestration | Harness calls portal functions in-process. A2A JSON-RPC endpoints exist but are not on the benchmark path. |
| LLM-only baseline is ungrounded, "prone to referencing unavailable applications" | `llm_prompt` includes the 3 templates and `validate_or_repair_plan` forces any answer onto `route_intent`'s template. It is catalog-grounded *and* rule-repaired. Hence 0 hallucinations for every method is trivial. |
| Live OAI gNB + separate RAN emulator twin | The stack script starts only `emu_agent_gnb`. OAI binaries exist but nothing links them into the evaluation. |

## 3. Problems with the reported numbers (final batch `20260508T130259_final`, 700 records)

1. **Known-world 100% is label leakage.** `validate_or_repair_agentcard_plan` replaces the plan with `intent["expected_workflow"]` for every non-open-world intent (16 of 22 known-world records were "repaired" this way). The paper says AppWeaver "recovers the same workflows through planner-driven orchestration" — it reads the answer key.
2. **Conflict detection 96% ≠ detection.** Confusion matrix for AppWeaver: 88 true negatives, **0/12 seeded conflicts detected directly**, 8/12 credited because an internal recovery ran. Scheduler-based `langgraph_enforced/override` detected 12/12. The paper's framing (AppWeaver catches conflicts proactively, baselines reactively) is inverted by the data.
3. **Tool-call success = subprocess started.** `classify_tool_status` maps `running/starting/launching` → success. During the batch RPC, MCP and KPM bus were all **down** (manifest), so no tool did anything measurable; all before/after KPIs are `null`.
4. **Latency is partially cached.** Planner cache TTL 7200 s: `llm_only` repeat 2 costs 2 ms, so the paper's 1.0 s is really ~2.0 s uncached. AppWeaver is uncached: n=100, mean 3.25 s, median 2.80 s, p95 7.4 s, max 9.4 s, sd 1.6 s — this is the distribution Reviewer 3 asked for and it's fine to report.
5. **Open-world 50%** = 39/78 records (39 intents × 2 repeats), genuinely uncached. The result itself is honest; the 2-repeat count explains the "exactly 50%".
6. **Registry size** = 9 cards, 4 executable, 7 actions; expected chains use only 4 capabilities. Reviewer 4's "RAG is overkill" is correct.
7. Inference settings: Ollama `/api/generate`, default temperature, no seed, 90 s timeout, system prompt from `_invoke_provider`. Not recorded in the paper.

## 4. Mapping reviewer comments → required work

| Reviewer ask | Work |
|---|---|
| R1.1 what Agent Cards add; how dependency / interface / control-scope checks are done | Extend `AgentCard` with `service_models`, `control_scope`, `requires`, `conflicts_with`, `interfaces`; make Compose check them explicitly and log the checks |
| R1.2, R2.2, R3.1 twin fidelity; predicted vs measured KPI | Build the twin for real: run `emu_agent_gnb` as twin and OAI rfsim gNB as live, same xApp against both, record predicted-vs-actual PRB/throughput/delay deltas. This is a genuine new experiment |
| R1.3 which apps are real | Rename honestly: KPM/SLICE/TC/RC xApps + emulated rApp endpoints; drop QoE/mobility claims or implement them |
| R1.4 open-world meaning, registry size | Define: unseen intents, same capability set; add an unseen-capability split (energy saving, R4) |
| R1.5, R3.4 catalog-aware LLM baseline / ablation | Make today's `llm_only` the "catalog-aware LLM" row; add a truly ungrounded `llm_blind` row; add `agentcard_no_repair` ablation |
| R1.6, R3.5, R4 reliability detail | Report total tool calls (1778), failure criteria, hallucination count, 6 seeded conflicts × 2 repeats, precision/recall not accuracy |
| R2.1, R3.2, R3.3 benchmark transparency, variance | Publish `intents_50.json` + harness; ≥5 repeats, no planner cache, mean ± sd / CI; document labelling (one valid chain per intent, or accept alternatives) |
| R3.6 latency distribution, Non-RT bound | Report median/p95/max; cite O-RAN Non-RT ≥1 s loop |
| R4 scalability, extra capability | Add an energy-saving (or MAC) executable agent card and show discovery picks it up unmodified |
| R4 hardware | Record GPU server model/VRAM in manifest (needs a one-line `nvidia-smi` on 130.233.158.22) |
| Repo release | Move `evaluation/` into the source tree, fix `.gitignore`, delete `.bak`/`copy` files, split the 3.5k-line monolith into the existing `backend/` package, add README + reproduction script |

## 5. Suggested order

1. Make the repo safe and publishable (git-track the evaluation, restructure) — no behaviour change.
2. Fix the harness methodology (leakage, metric definitions, baselines, repeats, no cache, per-record inference settings).
3. Add the new capability + Agent-Card compatibility checks.
4. Bring the stack up (RIC + emulator + KPM bus + MCP) and rerun the 50-intent batch on gpt-oss with ≥5 repeats.
5. Twin-vs-live experiment with OAI rfsim.
6. Regenerate figures/table and rewrite Section IV.
