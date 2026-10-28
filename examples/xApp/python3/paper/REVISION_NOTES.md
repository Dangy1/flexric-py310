# Manuscript revision notes (WCM-26-00422)

`main_submitted.tex` is the submitted source, unchanged. `main.tex` is the working revision.
Build: `~/anaconda3/envs/texbuild/bin/tectonic main.tex` (XeTeX; font-shape warnings for Times are
expected, Overleaf/pdfLaTeX is the reference build).

## Done (2026-10-28): minor comments and build fixes

| Reviewer comment | Change in `main.tex` |
|---|---|
| p3 l54 "leaving this step manually" | → "leaving this step manual" |
| p5 l64 "an feedback loop" | → "a feedback loop" |
| "Planner agent" vs "planner agent", "Discover" vs "discover agent" (p6 l85–93) | unified to "Planner agent", "Discover agent" |
| "Agent Card" vs "Agent-Card" | "Agent Card" everywhere (16 places) |
| Fig. 3 too dense for print | MCP-server panel removed (its `tools/list`/`tools/call` exchange is already in the sequence diagram); Agent Card and sequence panels enlarged to 25 % / 72 % of the text width; text references updated. `Pictures/MCP.png` kept in the folder if you want it back |
| R1.7 reference completeness | All 15 cited references checked against Crossref/DOI (details and sources in `REFERENCE_CHECK.md`). Duplicate `chatzistefanidis2025agoran` removed (BibTeX error). 3 arXiv preprints replaced by their published versions (2 ICC 2026, 1 IEEE Network); ICC 2026 entry for `li2026multi` completed; volume/issue/pages/month added to 4 journal papers; months and DOIs added to 5 older entries; years corrected for RIC-O (2023→2024) and Maatouk et al. (2024→2025); acronyms protected in titles (RIC-O, RAN, xApp, 5G, O-RAN). **Still to do by hand:** AgentRAN (IEEE ComMag), Chatzimiltis et al. (IEEE ComStdMag) and Navidan et al. (IEEE Network) are early access in Crossref; open their Xplore pages (documents 11519587, 11494171, 11574930) and add the issue or early-access date |
| (build) | `xcolor` loaded twice with different options (fatal "option clash" outside Overleaf's non-stop mode) → loaded once with `[table]` |
| Non-RT ≥ 1 s bound, A2A and MCP specs | added as footnote URLs, not bibliography entries, so the reference count stays at 15 |

Not yet done from the minor comments:
- **Fig. 5a labels for the known-world bars**: Fig. 5 is regenerated from the final batches
  (`evaluation/paper_results/make_paper_figures.py` labels every bar).
- **Code / benchmark availability**: add a footnote with the public repository URL in §IV once the
  release location is final.

## Format limits of IEEE Wireless Communications (check before adding results)

The submitted paper is exactly at the magazine limits: **6 figures + tables** (Table I, Figs. 1–5) and
**15 references**; body ≈ 3,700 words (limit 4,500). The draft `evaluation/paper_results/evaluation_section.tex`
adds Tables II–III and Figs. 6–7, which would make 10. To fit, the new results must replace, not add to,
existing floats. Options:
1. Merge Fig. 5 and the new results into one multi-panel `figure*` (accuracy by split, latency, reliability,
   registry scale) and put Table II (methods × metrics) in place of Fig. 5's reliability panel.
2. Drop the ReAct trace (Fig. 2) or the testbed figure (Fig. 4) and describe them in text.
3. Fold the twin-vs-live result (Fig. 7) into a small table or two sentences with the numbers.
Decision for the authors; the response letter can point to the public repo for full tables.

## Claims to rewrite after the final batches (P0-7)

Line numbers refer to the current `main.tex`. Each needs to match what the final system does
(see `docs/FABLE_REVIEW_AND_PLAN.md` §1 and `docs/MASTER_PLAN_STATUS.md`).

| Line | Current claim | Problem |
|---|---|---|
| 120 (abstract), 179, 345 | "validated in a FlexRIC and OpenAirInterface test environment", "OAI and FlexRIC testbed" | Batches run on the FlexRIC E2 emulator; ns-3/5G-LENA for the twin experiment. OAI only if O4 chooses it |
| 203 | Discovery uses RAG; an SLM supports lightweight reasoning | Discovery is BM25 over Agent Cards; no SLM on the measured path |
| 212, 281 | Twin "mirrors the per-layer RAN state as a live replica"; "MAC, RLC, and PDCP state synchronization" | Emulator twin returns synthetic KPM and acknowledges controls without applying them; it is an interface/conformance dry-run. KPI prediction comes from the ns-3 twin, with measured fidelity |
| 221 (Fig. 2) | "RAG over Agent Registry" | → "BM25 retrieval over Agent Cards" |
| 281 | Planner "gpt-oss via Ollama" on "a separate GPU server" | gpt-oss-120b on vLLM, NVIDIA DGX Spark (GB10, 128 GB unified memory), reasoning effort medium |
| 281 | Four xApps "covering KPM monitoring, QoE prediction, mobility optimization, and QoS control" | The FlexRIC xApps are KPM, SLICE, TC and RC; QoE/mobility are emulated rApps in the 46-card directory |
| 316–318 | 50 intents, three baselines | 50 + 80-intent benchmarks, three splits, six methods incl. LLM without catalog, LLM with catalog, AppWeaver without repair |
| 336–340 | Accuracy 100 % / 50 %, "100 % tool-call success", conflicts caught "proactively … on the digital twin" | Replace with the final-batch numbers and the decided metrics (partial-order label rule, acknowledged calls, conflict refusal / wait / re-plan; no reset-based recovery) |
| Fig. 3(a) | Agent Card shows only A2A identity, skills, MCP endpoint and OAuth | R1.1 asks for the O-RAN-specific card content. Consider replacing the PNG with the real v2 card (interfaces E2SM-KPM/RC, control scope, consumes/produces, timescale, conflicts_with) using the `agentcard` listing style already defined in the preamble |
