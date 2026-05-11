./run-dev.sh
Error: port 2024 is already in use (LangGraph backend)pip
You can get results by building a small evaluation harness around your current platform, not by evaluating everything manually.

1. Log every LangGraph run

For each intent, save one JSON record:

{
  "intent": "Guarantee XR latency below 5 ms",
  "generated_workflow": ["KPM", "Slice", "TC", "RC", "Validate"],
  "expected_workflow": ["KPM", "Slice", "TC", "RC", "Validate"],
  "tool_calls": [
    {"xapp": "KPM", "status": "success", "latency_ms": 120},
    {"xapp": "Slice", "status": "success", "latency_ms": 180}
  ],
  "policy_valid": true,
  "hallucinated_api": false,
  "conflict_detected": true,
  "recovered_from_failure": true,
  "before": {
    "latency_ms": 8.2,
    "throughput_mbps": 42,
    "prb_utilization": 0.81,
    "sla_violation_rate": 0.34
  },
  "after": {
    "latency_ms": 4.7,
    "throughput_mbps": 39,
    "prb_utilization": 0.76,
    "sla_violation_rate": 0.08
  }
}

This one log gives you almost all evaluation metrics.

⸻

2. Workflow correctness results

Prepare 20–50 network intents and define the expected workflow manually.

Example:

Intent	Expected xApp graph
Reduce XR latency	KPM → Slice → TC → RC
Reduce congestion	KPM → TC → Slice
Improve mobility	KPM → RC
Detect anomaly	KPM → Anomaly → RC

Then compute:

Workflow accuracy = correct workflows / total intents
Tool-call success rate = successful tool calls / total tool calls
Recovery rate = recovered failed runs / total failed runs
Average orchestration latency = total LangGraph runtime

These are easy to produce from LangGraph logs.

⸻

3. Network-control effectiveness results

Use your current O-RAN/FlexRIC/emulator platform.

For each scenario:

Step 1: Run baseline without AppOrchest
Step 2: collect KPM metrics
Step 3: run LangGraph orchestration
Step 4: apply xApp actions
Step 5: collect KPM metrics again
Step 6: compare before/after

Metrics table:

Metric	Before	After	Improvement
Latency	8.2 ms	4.7 ms	42.7% ↓
SLA violation rate	34%	8%	76.5% ↓
PRB utilization	81%	76%	6.2% ↓
Throughput	42 Mbps	39 Mbps	7.1% ↓

Even if the first version uses emulator data, it is still acceptable if clearly stated.

⸻

4. Agent reliability results

You can evaluate this using execution logs plus rule checks.

Metric	How to measure
Policy validity	JSON schema check + allowed parameter range
Hallucination rate	invalid xApp/API/parameter calls
Conflict detection accuracy	compare with manually labeled conflict cases
Recovery success	whether retry/repair produces valid workflow
Human intervention rate	number of runs needing manual fix

Example result table:

Method	Policy validity	Hallucination rate	Conflict detection	Recovery rate
LLM-only	72%	18%	55%	40%
LangGraph	88%	7%	71%	68%
LangGraph + validation	96%	2%	89%	84%

⸻

5. Baselines you should compare

Use these four:

B1: Manual rule-based orchestration
B2: Single xApp only
B3: LLM-only agent without LangGraph
B4: LangGraph without digital-twin validation
Proposed: LangGraph + xApp tools + digital-twin validation

This gives a strong paper story.

⸻

6. Minimum experiment you can finish fast

For a first paper result, do:

10 intents
3 xApps: KPM, Slice, TC
1 RC validation xApp
3 baselines
30 repeated runs

Then report:

workflow accuracy
tool-call success
hallucination rate
orchestration latency
SLA violation reduction

This is enough for a magazine-style or architecture paper.




###################

You should compare your platform at three levels simultaneously:

1. LLM orchestration intelligence
2. Executable O-RAN runtime capability
3. Real network-control effectiveness

This is the key difference between your work and recent papers.

⸻

1️⃣ First Define Your Core Claim

Your paper is NOT:

better LLM prompting

Your actual claim is:

AppOrchest enables executable,
closed-loop, multi-xApp orchestration
for AI-native O-RAN.

Everything in evaluation should support this claim.

⸻

2️⃣ The Correct Comparison Dimensions

You need a comparison table like this:

System	Multi-Agent	Runtime Execution	Real xApps	E2 Control	Digital Twin	Closed-loop Feedback	Conflict Awareness
ORION	✓	✗	✗	✗	✗	✗	Partial
Multi-Agentic AI (Bristol)	✓	✗	✗	✗	✗	✗	✓
OREO	Partial	Partial	✓	✓	✗	Partial	✗
Rule-based orchestration	✗	✓	✓	✓	✗	✓	✗
AppOrchest	✓	✓	✓	✓	✓	✓	✓

This already gives strong positioning.

⸻

3️⃣ Your Evaluation MUST Have 4 Figures

This is the correct magazine-style evaluation structure.

⸻

FIGURE 1 — Workflow Correctness

Goal

Show:

Can the agent orchestrate valid xApp workflows?

⸻

X-axis

Different intents/scenarios.

Example:

* XR latency
* mobility optimization
* energy saving
* congestion mitigation
* URLLC slice

⸻

Y-axis

Workflow correctness (%)

⸻

Compare

Method

Rule-based

Single-agent LLM

Multi-Agentic AI

LangGraph only

AppOrchest

⸻

Expected result

AppOrchest highest correctness
under complex multi-xApp workflows

⸻

FIGURE 2 — Conflict Detection & Recovery

Goal

Show:

Can the system detect and resolve
cross-xApp conflicts?

⸻

Metrics

* conflict detection rate
* successful recovery rate
* SLA preservation

⸻

Example scenario

Slice xApp:
increase PRB
Energy xApp:
reduce transmit power
Traffic xApp:
redirect load

⸻

Show

AppOrchest:

* detects conflicts earlier,
* retries safely,
* validates via digital twin.

⸻

FIGURE 3 — Runtime Orchestration Latency

THIS is VERY important.

Other papers usually miss this.

⸻

Goal

Measure:

intent
→ workflow generation
→ xApp execution
→ E2 control
→ validation

⸻

Metrics

Metric

workflow generation latency

orchestration overhead

xApp execution time

E2 control delay

recovery latency

⸻

Expected claim

LangGraph orchestration overhead
remains acceptable for Near-RT workflows.

⸻

FIGURE 4 — Real Network KPI Improvement

THIS is your strongest differentiator.

⸻

Goal

Show actual RAN improvements.

⸻

Metrics

KPI

latency

PRB utilization

throughput

SLA violation rate

packet loss

handover success

⸻

Compare

Without orchestration
vs
AppOrchest

⸻

4️⃣ Evaluation Architecture (VERY important)

You should clearly separate:

⸻

A. Orchestration Layer

Evaluate:

* LLM,
* LangGraph,
* workflow generation.

⸻

B. Runtime Layer

Evaluate:

* xApp calls,
* E2 messaging,
* execution latency.

⸻

C. Network Layer

Evaluate:

* real KPIs,
* telemetry,
* SLA.

⸻

5️⃣ Your Best Evaluation Environment

You already have the ideal setup:

Component	Use
FlexRIC	Near-RT RIC
OAI / srsRAN	RAN
Python xApps	executable agents
LangGraph	workflow engine
KPM E2SM	telemetry
RC/Slice/TC xApps	orchestration targets
E2 emulator	digital twin

This is MUCH stronger than simulated orchestration papers.

⸻

6️⃣ How To Talk With Codex

This is VERY important.

Do NOT ask:

build evaluation

Too vague.

⸻

Instead split implementation into modules.

⸻

MODULE 1 — Workflow Logger

Ask Codex:

Implement LangGraph execution tracing.
Log:
- node transitions
- tool/xApp calls
- latency
- retries
- failures
- generated policies
- telemetry feedback
Store results in JSONL.

⸻

MODULE 2 — Conflict Injection Framework

Implement synthetic cross-xApp conflict scenarios.
Examples:
- conflicting PRB allocations
- conflicting scheduler weights
- power-saving vs URLLC
- duplicate RC actions
Generate reproducible evaluation cases.

⸻

MODULE 3 — KPI Collector

Implement KPI collection from KPM E2SM.
Collect:
- latency
- throughput
- PRB utilization
- UE count
- slice metrics
Export to CSV.

⸻

MODULE 4 — Baseline Implementations

Implement baseline orchestrators:
1. rule-based
2. single-agent LLM
3. LangGraph without validation
4. AppOrchest full pipeline

⸻

MODULE 5 — Evaluation Runner

Implement automated evaluation runner.
For each scenario:
- load intent
- execute orchestrator
- apply xApp workflow
- collect telemetry
- compute metrics
- generate plots

⸻

MODULE 6 — Figure Generation

Generate publication-quality matplotlib figures
for:
- workflow correctness
- conflict recovery
- orchestration latency
- network KPI improvement

⸻

7️⃣ VERY IMPORTANT PAPER STRATEGY

You do NOT need:

* huge telecom dataset,
* massive RF simulation,
* real gNB farm.

For IEEE Wireless Communications / IEEE Network:

Architecture + prototype + workflow evaluation is enough.

⸻

8️⃣ Best Initial Demo

Do THIS first:

Use only:

* KPM xApp
* Slice xApp
* RC xApp
* Traffic Control xApp

⸻

One scenario:

XR congestion mitigation

⸻

One intent:

Keep XR latency below 5 ms

⸻

One comparison:

Rule-based
vs
LLM-only
vs
AppOrchest

This is already enough for a strong first evaluation section.

⸻

9️⃣ Strong Final Storyline

Your evaluation should demonstrate:

1. AppOrchest generates better workflows
2. It detects conflicts earlier
3. It executes real xApp workflows
4. It improves actual network KPIs
5. It enables safe closed-loop orchestration

THAT is your real contribution.
