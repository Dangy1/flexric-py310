# Related work for AppWeaver (literature scan, 2026-10-30)

Web search (not a Google Scholar export) for work similar to the AppWeaver evaluation: LLM agents that compose
or generate O-RAN xApps/rApps from operator intents, conflict handling among (LLM-driven) xApps, digital-twin
validation before deployment, and tool retrieval for LLM planning over large tool sets.

**Caveat.** Almost all entries are 2025-2026 arXiv preprints. Details marked *(secondary)* come from another
paper's or a blog's description and must be checked against the primary paper before citing. The paper allows
15 references, so a short list is proposed at the end.

## 1. LLM agents that compose / generate O-RAN applications from intents (closest to AppWeaver)

| # | Work | What it does | Evaluation | Difference from AppWeaver |
|---|---|---|---|---|
| 1 | **Multi-Agentic AI for Intent-Driven and Conflict-Aware rApp Policy Orchestration in Open RAN** — [arXiv 2610.24688](https://arxiv.org/html/2610.24688) | SMO-level agents: rApps select and compose xApps from a shared catalog per intent; a Reasoning Agent screens candidates against KPI contracts | Benchmark of 17 xApps, 19 operator intents, 10 incumbent/incoming-intent cases, 5 runs each, local LLM variants; PACIFISTA-based baseline; over-the-air testbed | **Most similar setup.** AppWeaver: 81-card registry (32 rApp families), 219 intents over A/B/C, known / open-world / unseen-capability splits, held-out batch, retrieval ablation (k=8 vs k=0), learning variants, E2-acknowledged deployment on FlexRIC |
| 2 | **Multi-Agentic AI for Conflict-Aware rApp Policy Orchestration in Open RAN** (earlier version) — [arXiv 2603.07375](https://arxiv.org/pdf/2603.07375) | Same line of work, LangChain + GPT-5 | 14 xApps; a pre-defined target policy per intent as ground truth | As #1; ground truth there is a single target policy, AppWeaver uses a pre-registered label rule (+ exact match, sensitivity row) |
| 3 | **ZTO-Agent: Advanced AI Service Provisioning in O-RAN through LLM Engine Integration** — [arXiv 2605.23809](https://arxiv.org/html/2605.23809v2) | Non-RT RIC rApp (Llama-3.1-8B, Ollama) parses intents and fills pre-verified Jinja2 xApp templates; deploys to FlexRIC with containerised OAI | Proof of concept; orchestration latency dominated by intent parsing (≈552 ms) | Generates xApp code from templates; AppWeaver composes existing apps into workflows and measures accuracy at scale |
| 4 | **Agentic Open RAN: A Deterministic and Auditable Framework for Intent-Driven Radio Control** — [arXiv 2604.13384](https://arxiv.org/html/2604.13384) | Non-RT agentic rApp translates operator goals into typed A1 policies; three near-RT agentic xApps enforce them (Gemini 2.5 Flash) | Deterministic, auditable loop | Policy translation rather than workflow composition from a catalog |
| 5 | **MX-AI** *(secondary)* | Agentic LLM system in the SMO on a live OAI + FlexRIC 5G testbed; natural-language intents to observe/control the RAN | Live testbed | Same platform (FlexRIC); no composition benchmark found. Primary paper not located; LLM stack described inconsistently across sources |
| 6 | **AutORAN** *(secondary)* | LLM generates xApps from natural-language specifications and validates them on an O-RAN testbed | Real O-RAN testbed | Code generation; primary source not located |
| 7 | **LLM-xApp: A Large Language Model Empowered Radio Resource Management xApp for 5G O-RAN** — [NDSS FutureG'25](https://www.ndss-symposium.org/wp-content/uploads/futureg25-57.pdf), [ResearchGate](https://www.researchgate.net/publication/394895682_LLM-xApp_A_Large_Language_Model_Empowered_Radio_Resource_Management_xApp_for_5G_O-RAN) | LLM inside one xApp for intent-driven slice resource allocation | OAIC testbed | One LLM-powered xApp, not orchestration of many apps |
| 8 | **ALLSTaR: Automated LLM-Driven Scheduler Generation and Testing for Intent-Based RAN** — [arXiv 2505.18389](https://arxiv.org/pdf/2505.18389), [ResearchGate](https://www.researchgate.net/publication/392105547_ALLSTaR_Automated_LLM-Driven_Scheduler_Generation_and_Testing_for_Intent-Based_RAN) | Turns intents into scheduler code deployed as O-RAN dApps | 5G testbed | Scheduler code generation |
| 9 | **Managing O-RAN Networks: xApp Development from Zero to Hero** — [arXiv 2407.09619](https://arxiv.org/pdf/2407.09619) | Tutorial on xApp development | — | Background |
| 10 | **AI-Native Open RAN: A Roadmap from xApps and rApps to Autonomous Network Agents** — [arXiv 2609.15704](https://arxiv.org/html/2609.15704) | Roadmap / survey | — | Background, positioning |
| 11 | **FlexRIC: an SDK for next-generation SD-RANs** — [ResearchGate](https://www.researchgate.net/publication/356763158_FlexRIC_an_SDK_for_next-generation_SD-RANs) | The RIC platform AppWeaver runs on | — | Platform reference |

## 2. Conflict handling among (LLM-driven) xApps, guardrails, digital twins

| # | Work | What it does | Relation to AppWeaver |
|---|---|---|---|
| 12 | **xTRUCE: A Provably Safe Arbiter for Multi-xApp Conflict Mitigation in Agentic O-RAN** — [arXiv 2608.28532](https://arxiv.org/html/2608.28532) | Near-RT RIC arbiter; a proposal gateway restricts LLM xApps to machine-readable proposals; live LLM xApps and over-the-air experiments on OAI/FlexRIC; notes prior digital-twin safeguards cover single-xApp cases only | Related to AppWeaver's lease-based contention handling (wait / re-plan, never pre-empt) and twin dry-run |
| 13 | **Twin-Fidelity-Aware Resolution of Direct xApp Conflicts in Open RAN** — [arXiv 2607.22857](https://arxiv.org/pdf/2607.22857) | Network digital twin as a validation environment before the live RAN | Related to the tier-1 twin dry-run and the T6 twin-vs-live study |
| 14 | **Agentic AI-RAN: Enabling Intent-Driven, Explainable and Self-Evolving Open RAN Intelligence** — [arXiv 2602.24115](https://arxiv.org/html/2602.24115v2) | Guardrails: gating, schema validation, rollback; addresses hallucination and twin drift | Architecture-level counterpart of AppWeaver's Validate step |
| 15 | **Toward Autonomous O-RAN: A Multi-Scale Agentic AI Framework for Real-Time Network Control and Management** — [arXiv 2602.14117](https://arxiv.org/html/2602.14117v1) ([pdf](https://arxiv.org/pdf/2602.14117)) | Arbitration by policy priority, confidence and observed impact; offline validation before deployment | Same design pattern (propose, validate, deploy) |
| 16 | **AgentRAN: An Agentic AI Architecture for Autonomous Control of Open 6G Networks** — [arXiv 2508.17778](https://arxiv.org/pdf/2508.17778) | LLM agents across rApps / xApps / dApps | Architecture background |
| 17 | **From RAN Control to Agentic Intelligence** — [arXiv 2606.21955](https://arxiv.org/pdf/2606.21955) | Survey of agentic RAN control | Background |
| 18 | **LLM-Powered Agentic AI for 5G/6G Networks: A Tutorial and Survey on Architectures, Protocols, and Standardization** — [arXiv 2607.16066](https://arxiv.org/pdf/2607.16066) | Tutorial/survey; security and trustworthiness as open challenges | Background |
| 19 | **AI-powered conflict management in Open RAN: Detection, classification, and mitigation** — [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S1389128626004445) | AI conflict detection/classification, ≈3.2× faster than rule-based in ns3-oran, 5-50 xApps | Simulation-based conflict management |
| 20 | **Experimental evaluation of xApp Conflict Mitigation Framework in O-RAN: Insights from Testbed deployment in OTIC** — [arXiv 2503.11566](https://arxiv.org/pdf/2503.11566) | Testbed evaluation of an xApp conflict mitigation framework | Experimental conflict-mitigation baseline |
| 21 | **O-RAN xApps: Intelligent Network Control** — [Emergent Mind topic page](https://www.emergentmind.com/topics/o-ran-xapps) | Topic overview | Background only (not citable) |

## 3. Tool retrieval for LLM planning over large tool sets (relates to the k=8 vs k=0 ablation)

| # | Work | What it does | Relation to AppWeaver |
|---|---|---|---|
| 22 | **Gorilla: Large Language Model Connected with Massive APIs** — [arXiv 2305.15334](https://ar5iv.labs.arxiv.org/html/2305.15334) | Retrieval-aware fine-tuned LLaMA selecting from a large, overlapping, changing API set; fewer hallucinated calls than GPT-4. *(secondary, blog)* per-hub zero-shot ≈59-84%; BM25 / GPT-Index retrieval degrades accuracy vs oracle | Same problem class: choose the right tools from a large catalog; AppWeaver retrieves the top-k Agent Cards (BM25) |
| 23 | **Retrieval Models Aren't Tool-Savvy: Benchmarking Tool Retrieval for Large Language Models (TOOLRET, ACL 2025)** — [review](https://www.themoonlight.io/review/retrieval-models-arent-tool-savvy-benchmarking-tool-retrieval-for-large-language-models), [review 2](https://liner.com/review/retrieval-models-arent-toolsavvy-benchmarking-tool-retrieval-for-large-language) | 7.6k tasks, 43k tools; Recall@K, NDCG@K, Completeness@K; better retrieval raises end-to-end pass rate | Supports AppWeaver's finding that retrieval (k=8) beats putting the whole catalog in the prompt (k=0) |
| 24 | **GRETEL: A Goal-driven Retrieval and Execution-based Trial Framework for LLM Tool Selection** — [arXiv 2510.17843](https://arxiv.org/pdf/2510.17843) | Tool selection at K=5/10 (Recall@K, NDCG@K, Pass Rate@K); ToolLLM as a baseline *(numbers not verified)* | Tool-selection evaluation methodology |
| 25 | NeurIPS 2024 tool-use paper — [proceedings pdf](https://proceedings.neurips.cc/paper_files/paper/2024/file/e4c61f578ff07830f5c37378dd3ecb0d-Paper-Conference.pdf) | Returned by the search; title to be checked | To be checked |
| 26 | Gorilla blog write-ups — [beancount.io research log](https://beancount.io/bean-labs/research-logs/2026/05/03/gorilla-llm-retrieval-augmented-api-calling), [Substack](https://offthegridxp.substack.com/p/what-is-gorilla) | Secondary descriptions of Gorilla | Not citable; used only for orientation |

## What sets the AppWeaver evaluation apart

1. **Scale and splits.** 81 Agent Cards (9 xApps + 72 rApp cards in 32 families); 219 intents in three batches with
   known / open-world / unseen-capability splits; a held-out batch (C) with a documented difficulty analysis
   (`evaluation/DIFFICULTY_A_VS_C.md`). The closest work (#1-2) uses 14-17 xApps and 19 intents.
2. **End-to-end on a real RIC.** Every plan is deployed on FlexRIC and must be acknowledged over E2
   (99.6-100 % acknowledged calls in Batch B k=8), not only judged as text.
3. **Digital twin in the loop.** A tier-1 twin dry-run of every E2 control step before deployment, and the T6
   ns-3 twin-vs-live study of how well the twin predicts the live network.
4. **Contention handling with explicit metrics.** Lease-based wait / re-plan with "never pre-empt" checked on every
   record (met conflict, completed after wait, unresolved, `preempted_other_workflow`).
5. **Retrieval ablation.** Top-k Agent Card retrieval (k=8) vs the whole catalog in the prompt (k=0).
6. **Learning from operator feedback.** Workflow-template cards and an experience memory built from Batch A
   (+6 points rule accuracy and 32 % → 48 % exact match on the 81-card batch); and a negative result:
   hand-written planning rules (guided / v2) do not transfer to the large registry.
7. **Two planners.** gpt-oss-120b (spark1, vLLM) and GLM-5.3-Flash (Aalto LLM gateway), plus a two-planner memory.

## Proposed citations within the 15-reference budget

#1 (or #2), #3, #12, #13 or #14, #22, #23, #11 (FlexRIC), and one survey (#18 or #10). Verify every entry against
its primary source first; #5, #6, #24 and #25 are not citable until the primary papers are located.
