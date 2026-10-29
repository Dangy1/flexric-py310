#!/bin/bash
# Planner-only comparison on the Batch A intents with GLM-5.3-Flash via the Aalto LLM gateway (no RIC, no deploy).
unset OLLAMA_BASE_URL OLLAMA_URL OLLAMA_MODEL FLEXRIC_LLM_THINK OPENAI_API_KEY OPENAI_BASE_URL OPENAI_MODEL FLEXRIC_RAPP_DIRECTORY VLLM_API_KEY
. ~/.config/appweaver/aalto.env
export FLEXRIC_LLM_TEMPERATURE=0.2 FLEXRIC_LLM_SEED=7 FLEXRIC_L2_MONITORS=0
export PATH=$HOME/anaconda3/envs/flexric-py310/bin:$PATH
D=/tmp/claude-1001/-home-dang/a1e897dd-edab-408c-895b-f3499e47a15c/scratchpad/devcheck
for m in langgraph_agentcard appweaver_guided appweaver_v2; do
  python $D/devcheck.py $m $D/GLM_A_$m.jsonl > $D/GLM_A_$m.log 2>&1 &
done
wait; echo done
