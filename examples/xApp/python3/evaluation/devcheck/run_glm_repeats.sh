#!/bin/bash
# GLM-5.3-Flash planner-only runs of frozen AppWeaver on the Batch A intents, repeats 2-5 (repeat 1 = GLM_A_langgraph_agentcard.jsonl):
# training data for the two-model experience memory (owner decision 2026-10-29).
unset OLLAMA_BASE_URL OLLAMA_URL OLLAMA_MODEL FLEXRIC_LLM_THINK OPENAI_API_KEY OPENAI_BASE_URL OPENAI_MODEL FLEXRIC_RAPP_DIRECTORY VLLM_API_KEY
. ~/.config/appweaver/aalto.env
export FLEXRIC_LLM_TEMPERATURE=0.2 FLEXRIC_LLM_SEED=7 FLEXRIC_L2_MONITORS=0
export PATH=$HOME/anaconda3/envs/flexric-py310/bin:$PATH
D=/tmp/claude-1001/-home-dang/a1e897dd-edab-408c-895b-f3499e47a15c/scratchpad/devcheck
for r in 2 3 4 5; do
  python $D/devcheck.py langgraph_agentcard $D/GLM_A_langgraph_agentcard_r$r.jsonl > $D/GLM_A_r$r.log 2>&1 &
done
wait; echo done
