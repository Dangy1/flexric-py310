# Hardware

Recorded per batch in `manifest.json` → `hardware` (from `LLM_SERVER_HARDWARE` and the orchestration host).

| Role | Host | Hardware | Software |
|---|---|---|---|
| Planner LLM (final batches) | `spark1.dice.aalto.fi` (130.233.154.151) | NVIDIA DGX Spark: GB10 Grace Blackwell, 128 GB unified CPU-GPU LPDDR5x memory (121 GiB visible; no separate VRAM, so `nvidia-smi` reports memory.total N/A) | vLLM, `gpt-oss-120b`, reasoning effort medium, temperature 0.2, seed 7 |
| Planner LLM (preliminary qwen pilot batches only) | 130.233.158.22 (tlt022.hut.fi) | GPU model not recorded | Ollama 0.40, `qwen3.6:27b`, reasoning off |
| Orchestration, RIC, E2 emulator, harness | `comlab-srs` | x86_64, Linux 6.8 | FlexRIC nearRT-RIC + `emu_agent_gnb`, Python 3.10 |

Source of the spark1 line: owner ran `nvidia-smi --query-gpu=name,memory.total --format=csv` and `free -g` on spark1 (2026-10-28).
Paper sentence: "The planner runs gpt-oss-120b under vLLM on an NVIDIA DGX Spark (GB10 Grace Blackwell, 128 GB unified memory)."
