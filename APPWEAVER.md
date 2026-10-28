# AppWeaver: agentic discovery and composition of O-RAN apps

This repository is a FlexRIC fork that carries AppWeaver, the code, benchmark, results and paper source
for *AppWeaver: Agentic Discovery and Composition of O-RAN Apps for AI-Native 6G*
(IEEE Wireless Communications, WCM-26-00422, under major revision). Branch: `appweaver-revision`.

Status 2026-10-28: the revision code is being finalised. The numbers in `evaluation/runs/` are
**preliminary** (planner qwen3.6:27b); the final batches run on gpt-oss-120b once the code freeze is
committed. `examples/xApp/python3/docs/MASTER_PLAN_STATUS.md` tracks what is done and what is left.

## What is where

Everything AppWeaver-specific is under `examples/xApp/python3/` (paths below are relative to it).

| Part | Path |
|---|---|
| Agent portal: Agent Registry, planner, scheduler and leases, A2A JSON-RPC, MCP | `flexric_agent_portal.py`, `backend/` |
| AppWeaver graph (Discover → Compose → Validate → Deploy → Recover) | `backend/appweaver/` |
| Agent Cards v2 and compose-time checks | `backend/common/models.py`, `backend/agents/`, `backend/orchestration/compat.py` |
| Card retrieval (BM25, pinned xApps) | `backend/orchestration/discovery.py` |
| FlexRIC xApps used by the workflows (KPM, SLICE, TC, RC) | `xapp_*.py` |
| rApp directory: 46 emulated rApps, catalog generator, runtime | `rapps/` |
| Benchmark: intents, label rules, harness, metrics | `evaluation/` (`intents_50.json`, `intents_v2.json`, `label_rules.py`, `run_harness.py`, `METRICS.md`, `CONFLICTS.md`) |
| Batch results (records, summaries, manifests) | `evaluation/runs/<batch>/` |
| Tables, figures, LaTeX macros | `evaluation/paper_results/` |
| Twin-vs-live experiment on ns-3 | `evaluation/twin/`, `evaluation/TWIN_VALIDATION.md` |
| ns-O-RAN-flexric simulator: patches, start/stop, regression tests, setup guide | `simulator/ns-oran-flexric/` |
| Paper source (submitted and revised), revision notes, reference check | `paper/` |
| Reviewer response, plans, independent reviews | `docs/` |

## Reproduce

1. **Build FlexRIC and the Python xApp SDK** (Ubuntu 22.04, conda env from `examples/xApp/python3/environment.yml`):
   ```bash
   cmake -S . -B build -DXAPP_TARGET_LANGUAGE=PYTHON_LANG -DPython3_EXECUTABLE="${CONDA_PREFIX}/bin/python"
   cmake --build build -j8 && cmake --build build --target xapp_sdk -j8
   ```
   CMake copies the portal, `evaluation/`, `rapps/` and scripts into `build/examples/xApp/python3/`.
2. **Planner LLM**: any OpenAI-compatible server (vLLM) or Ollama; settings in
   `examples/xApp/python3/README.md` → "vLLM". Check it with `scripts/check_llm_provider.py`.
3. **Benchmark batches A and B, tables and figures**: the commands in
   `examples/xApp/python3/README.md`, section "AppWeaver reproduction".
4. **Twin-vs-live experiment**: build the simulator with `simulator/ns-oran-flexric/APPWEAVER_SETUP.md`
   (ns-3 + 5G-LENA + a second, pinned FlexRIC; apply the patches in `simulator/ns-oran-flexric/patches/`),
   then run `evaluation/twin/run_twin_validation.py` as in `evaluation/TWIN_VALIDATION.md`.
5. **Paper**: `cd examples/xApp/python3/paper && tectonic main.tex` (or Overleaf).

The upstream FlexRIC documentation is in `README.md`.
