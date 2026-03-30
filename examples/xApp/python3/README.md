## Architecture

## Source Layout
- `backend/agents/`: one file per portal agent plus the shared registry
- `backend/orchestration/`: workflow templates, resource requirements, and graph-stage configuration
- `backend/graph/`: LangGraph runtime, state, tools, and per-stage node files
- `backend/common/`: shared backend models and runtime-scope constants
- `agent_portal/`: frontend HTML, styles, main controller, and shared JS helpers

In this folder you can run the Python xApp examples, the service-model suite runners, and the new agent-centric portal for FlexRIC.

The recommended runtime location is:

```bash
/home/dang/flexric/build/examples/xApp/python3
```

The canonical shell scripts now live in:

```bash
/home/dang/flexric/build/examples/xApp/python3/scripts
```

The old top-level `.sh` files are still there as compatibility wrappers, so both layouts work.

That build directory is where `_xapp_sdk.so`, `xapp_sdk.py`, the suite scripts, and the agent portal are copied together after `cmake --build build --target xapp_sdk`.

## Prerequisites

- Build FlexRIC against the same Python interpreter you will use at runtime.
- Ensure the SCTP runtime is installed on the host:

```bash
sudo apt install -y libsctp1 libsctp-dev
```

- Use the Python 3.10 environment prepared for this project:

```bash
conda activate flexric-py310
```

or run with the interpreter directly:

```bash
/home/dang/anaconda3/envs/flexric-py310/bin/python
```

## Rebuild The Python xApp SDK

From the project root:

```bash
cmake -S . -B build -DPython3_EXECUTABLE=/home/dang/anaconda3/envs/flexric-py310/bin/python
cmake --build build --target xapp_sdk -j4
```

This refreshes:

- `build/examples/xApp/python3/_xapp_sdk.so`
- `build/examples/xApp/python3/xapp_sdk.py`
- `build/examples/xApp/python3/flexric_agent_portal.py`
- `build/examples/xApp/python3/agent_portal/*`
- the suite and helper scripts copied into the build example

## Install Python Packages

From `build/examples/xApp/python3`:

```bash
/home/dang/anaconda3/envs/flexric-py310/bin/python -m pip install -r requirements-mcp.txt
```

The portal and MCP helpers use packages from `requirements-mcp.txt`, including:

- `fastapi`
- `uvicorn`
- `pydantic`
- `requests`
- `mcp`
- `a2a-sdk[http-server]`

## Run The Agent Portal

From the build example:

```bash
cd /home/dang/flexric/build/examples/xApp/python3
/home/dang/anaconda3/envs/flexric-py310/bin/python flexric_agent_portal.py
```

Bring up the full local stack directly from an existing build:

```bash
cd /home/dang/flexric/build/examples/xApp/python3/scripts
./run_agent_portal_stack.sh
```

The same script now exposes both local and LAN access by default.

It binds the services to `0.0.0.0` and prints both:

- local URLs such as `http://127.0.0.1:8088/`
- LAN URLs such as `http://192.168.88.224:8088/`

If the LAN IP needs to be forced, override it:

```bash
FLEXRIC_AGENT_PORTAL_PUBLIC_HOST=192.168.88.224 ./run_agent_portal_stack.sh
```

`run_agent_portal_lan.sh` is still available as a compatibility wrapper, but it is no longer required.

Stop the stack cleanly from the same directory:

```bash
./stop_agent_portal_stack.sh
```

Or configure/build first and then start it:

```bash
cd /home/dang/flexric/build/examples/xApp/python3/scripts
./build_agent_portal_stack.sh
```

`scripts/run_agent_portal_stack.sh` now:

- uses the existing build directly
- serves both local and LAN access from the same command
- runs `./stop_agent_portal_stack.sh` first by default so a new launch cleans up the previous stack
- starts `nearRT-RIC`
- starts `emu_agent_gnb`
- starts the agent portal
- starts the xApp RPC server
- starts the MCP metrics HTTP service
- starts the shared KPM bus service
- waits until the web pages and service ports are reachable
- keeps watching the processes so you know if one drops

`scripts/build_agent_portal_stack.sh`:

- configures and builds FlexRIC
- then hands off to `run_agent_portal_stack.sh`

`scripts/stop_agent_portal_stack.sh`:

- stops the build-specific `nearRT-RIC`
- stops `emu_agent_gnb`
- stops the agent portal, xApp RPC, and MCP services
- also cleans up listeners on the default portal/RPC/MCP ports for this stack

`run_rl_demo_base.sh` is still present only as a compatibility wrapper and now forwards into `scripts/run_rl_demo_base.sh`.

Default bind:

- Host: `127.0.0.1`
- Port: `8088`

Optional overrides:

```bash
export FLEXRIC_AGENT_PORTAL_HOST=0.0.0.0
export FLEXRIC_AGENT_PORTAL_PORT=8088
```

There is no `vite` or `npm` frontend project in this folder today. The UI is served directly by FastAPI, so LAN access is handled by the Python service bind host rather than by adding a separate Vite dev server.

## Shared KPM Bus

The Python agent stack now treats KPM as a shared telemetry source instead of letting each agent open its own FlexRIC KPM subscription.

- `kpm_bus_service.py` owns the single live KPM subscription
- `xapp_kpm_bus_reader.py` reads filtered RRU or UE records from that shared bus
- the portal stack now starts the KPM bus automatically
- KPM agent actions in the portal read from the bus instead of opening fresh KPM subscriptions
- optional Redis publishing is supported with `KPM_BUS_REDIS_URL=redis://host:6379/0`

This means multiple agents can consume KPM data without each starting a conflicting direct KPM monitor process.

Main UI:

- `/` opens the single-page portal workspace
- the top menu switches between `Overview`, `LangGraph`, `Orchestrator`, `KPM`, `MAC`, `Slice`, `TC`, `RC`, `RLC`, `PDCP`, `GTP`, `Scheduler`, and `Comparison`
- `Overview` is now the lean operational dashboard for stack health, workflow launch, recent events, and recent runs
- `LangGraph` is now the orchestration and architecture workspace for the RIC orchestrator, workflow history/detail, providers, A2A, LangChain, LangSmith, MCP control, and agent topology
- `Scheduler` is the queue-and-lease operations page for resource leases, queued workflows, targeted controls, operator actions, and the implementation log
- `Comparison` compares KPM snapshots and workflow outcomes before and after optimization
- `/agents/{agent_id}` also works and opens the same one-page workspace with that agent preselected
- `/workflows/{run_id}` opens the same portal with that workflow run preselected in the workflow detail panel
- `/platform` opens the `LangGraph` page for LangGraph, MCP control, A2A, LangChain, and LangSmith
- `/scheduler` opens the scheduler operations page for resource leases, queue state, reconcile, and audit history
- `/comparison` opens the comparison page for before/after optimization views


On the `LangGraph` page:

- LangGraph workflows can still run in recommend-only mode even if MCP is stopped
- you can start or stop MCP directly from the UI
- the `Overview` page and the normal portal flow still use MCP automatically when it is available

## Agent Model

The portal exposes agent cards and workflows around the FlexRIC service models:

- `KPM Agent`: KPI and measurement analysis
- `MAC Agent`: scheduler and PRB interpretation
- `Slice Agent`: slice monitoring and policy application
- `TC Agent`: shaping, CoDel, ECN, and queue policy actions
- `RC Agent`: control validation and policy gating
- `RLC Agent`: bearer health validation
- `PDCP Agent`: session continuity and transport-side diagnostics
- `GTP Agent`: user-plane tunnel observation
- `RIC Orchestrator`: multi-agent routing and workflow chaining

Each workspace shows:

- current status
- active task text
- supported skills
- use cases
- measurements
- peers
- runnable actions when a local suite exists
- latest run status and live log tail
- provider-backed reasoning output
- handoff and test controls

## Workflow Templates

The portal currently includes these built-in workflow chains:

- `observe-diagnose-optimize`
- `slice-assurance`
- `transport-qos`

These are orchestration templates that hand work across agents and record timeline updates inside the UI.

There is also a `Test All Agents` control in the header to validate the whole chain quickly from one place.

## A2A-Style Endpoints

The portal exposes A2A-aligned discovery and JSON-RPC-style handoff endpoints:

- `GET /.well-known/agent-card.json`
- `GET /.well-known/agents/{agent_id}.json`
- `GET /api/stack`
- `GET /api/workflows/{run_id}`
- `GET /api/workflows/{run_id}/events`
- `POST /api/a2a/rpc`

Supported RPC methods:

- `agents.list`
- `agent.get_card`
- `message.send`
- `workflow.run`
- `workflow.status`
- `workflow.events`
- `agent.task.run`
- `portal.test_all`

Example:

```bash
curl -s http://127.0.0.1:8088/api/a2a/rpc \
  -H 'content-type: application/json' \
  -d '{
    "jsonrpc": "2.0",
    "id": "1",
    "method": "workflow.run",
    "params": {
      "workflow_id": "observe-diagnose-optimize",
      "goal": "Collect KPIs and recommend a slice or TC action"
    }
  }'
```

Note: the current implementation is A2A-aligned and useful for agent-to-agent experiments, but it is not yet a full certification-grade Google A2A integration.

## LangGraph Backend

The portal now includes a first LangGraph-oriented backend scaffold under:

- `backend/graph/state.py`
- `backend/graph/tools.py`
- `backend/graph/nodes/*`
- `backend/graph/runtime.py`
- `backend/a2a_adapter.py`

Design notes:

- LangGraph is used as the internal orchestration runtime when `langgraph` is installed.
- If `langgraph` is not installed yet, the same backend falls back to a deterministic linear runner so the portal still works.
- A2A remains the network-facing contract through the portal endpoints, and now also supports `workflow.status` and `workflow.events`.
- The first graph is workflow-oriented and currently maps real actions for `KPM`, `Slice`, `TC`, and `RC`, while `MAC`, `RLC`, `PDCP`, and `GTP` remain observation/diagnosis roles.

### LangSmith Tracing

Optional LangSmith tracing is now supported by the LangGraph runtime and surfaced on the `LangGraph` page. To enable it:

```bash
export LANGSMITH_TRACING_V2=true
export LANGSMITH_API_KEY=your_langsmith_key
export LANGSMITH_PROJECT=flexric-agent-portal
# optional
export LANGSMITH_ENDPOINT=https://api.smith.langchain.com
```

When enabled, the workflow runner emits a top-level `flexric_graph_workflow` trace and per-stage spans for `observe`, `diagnose`, `approve`, `act`, `verify`, and `summarize`.

## Provider Routing

The portal can surface both local and hosted LLM backends:

### Ollama

```bash
export OLLAMA_BASE_URL=http://127.0.0.1:11434
export OLLAMA_MODEL=qwen2.5:14b
```

### OpenAI API

```bash
export OPENAI_BASE_URL=https://api.openai.com/v1
export OPENAI_MODEL=gpt-5.4
export OPENAI_API_KEY=your_key_here
```

These provider settings are displayed in the overview page so the orchestrator and domain agents can advertise which inference backends are available.

Once configured, each agent tab can send real reasoning prompts through Ollama or OpenAI from the `Reasoning Task` panel.

## Running Local Suite Actions

The portal can launch the local suite runners directly from the build example:

- `xapp_kpm_rc_suite.py`
- `xapp_slice_suite.py`
- `xapp_tc_suite.py`

Examples without the UI:

```bash
/home/dang/anaconda3/envs/flexric-py310/bin/python xapp_kpm_rc_suite.py --profile kpm --period-ms 1000 --duration-s 30 --kpm-metrics rru
```

```bash
/home/dang/anaconda3/envs/flexric-py310/bin/python xapp_slice_suite.py --profile monitor --duration-s 30 --verbose
```

```bash
/home/dang/anaconda3/envs/flexric-py310/bin/python xapp_tc_suite.py --profile all --duration-s 30 --monitor-rlc
```

## Useful REST Endpoints

- `GET /api/overview`
- `GET /api/providers`
- `GET /api/agents`
- `GET /api/agents/{agent_id}`
- `POST /api/agents/{agent_id}/actions/{action_id}/run`
- `GET /api/runs`
- `GET /api/runs/{run_id}`
- `POST /api/agents/{agent_id}/message`
- `GET /api/workflows`
- `POST /api/workflows/{workflow_id}/run`

## Notes

- The build example is the correct place to run the Python portal and suites because it contains the generated `xapp_sdk.py` and `_xapp_sdk.so`.
- If you see a Python version mismatch, rebuild with the exact interpreter you plan to use.
- If you see `libsctp.so.1` errors, install the SCTP runtime on the host.
- Some agents currently expose cards and handoff behavior before they have a dedicated standalone suite. Those agents are intended to be extended incrementally.
