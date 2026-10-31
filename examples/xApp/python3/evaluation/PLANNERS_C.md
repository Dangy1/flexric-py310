# Planner comparison on one batch

- **gpt-oss-120b**: `20261031T051600Z_C_final_merged_gptoss120b_spark1` - 60 intents x 11 methods x 3 repeats = 1980 records; planner `gpt-oss-120b`, settings {"provider": "vllm", "reasoning_effort": "medium", "seed": 7, "temperature": 0.2, "think": "model-default", "timeout_s": 180}, registry 9 cards, retrieval_k=0
- **zai-org/GLM-5.3-Flash**: `20261031T051640_231676Z_C_glm53flash_aaltogw` - 60 intents x 5 methods x 3 repeats = 900 records; planner `zai-org/GLM-5.3-Flash`, settings {"provider": "vllm", "reasoning_effort": "model-default", "seed": 7, "temperature": 0.2, "think": "model-default", "timeout_s": 90}, registry 9 cards, retrieval_k=0 **PRELIMINARY (not the paper's model)**

Rule accuracy is primary; 95% CIs are intent-clustered bootstrap. Latency = intent-to-plan, median.

| Method | Planner | Accuracy (rule) | Known | Open-world | Open-world, non-template | Exact | Ack. calls | Latency med (s) |
|---|---|---|---|---|---|---|---|---|
| LLM (catalog) | gpt-oss-120b | 53.3% [41, 66] | 88.9% [78, 98] | 17.8% [6, 32] | 0.0% [0, 0] | 44.4% [32, 57] | 99.8% [99, 100] | 8.52 |
| LLM (catalog) | zai-org/GLM-5.3-Flash | 60.0% [47, 73] | 98.9% [97, 100] | 21.1% [9, 36] | 0.0% [0, 0] | 49.4% [37, 63] | 100.0% [100, 100] | 4.48 |
| AppWeaver | gpt-oss-120b | 93.9% [88, 99] | 92.2% [82, 100] | 95.6% [88, 100] | 93.9% [83, 100] | 22.8% [13, 32] | 100.0% [100, 100] | 26.02 |
| AppWeaver | zai-org/GLM-5.3-Flash | 93.9% [88, 99] | 100.0% [100, 100] | 87.8% [77, 98] | 83.3% [67, 95] | 20.6% [11, 30] | 100.0% [100, 100] | 23.21 |
| AppWeaver + templates | gpt-oss-120b | 96.1% [91, 100] | 96.7% [90, 100] | 95.6% [88, 100] | 93.9% [83, 100] | 40.0% [29, 52] | 100.0% [100, 100] | 26.62 |
| AppWeaver + templates | zai-org/GLM-5.3-Flash | 94.4% [88, 99] | 98.9% [97, 100] | 90.0% [80, 100] | 86.4% [73, 100] | 30.0% [19, 41] | 100.0% [100, 100] | 19.57 |
| AppWeaver + tpl + memory | gpt-oss-120b | 96.1% [91, 100] | 96.7% [90, 100] | 95.6% [89, 100] | 93.9% [85, 100] | 48.9% [37, 61] | 100.0% [100, 100] | 27.60 |
| AppWeaver + tpl + memory | zai-org/GLM-5.3-Flash | 96.1% [91, 100] | 100.0% [100, 100] | 92.2% [82, 100] | 89.4% [76, 100] | 44.4% [33, 56] | 100.0% [100, 100] | 31.41 |
| AppWeaver + memory (2 LLMs) | gpt-oss-120b | 96.1% [91, 100] | 96.7% [90, 100] | 95.6% [88, 100] | 93.9% [83, 100] | 47.8% [37, 59] | 100.0% [100, 100] | 26.60 |
| AppWeaver + memory (2 LLMs) | zai-org/GLM-5.3-Flash | 96.1% [92, 99] | 98.9% [97, 100] | 93.3% [86, 99] | 90.9% [80, 98] | 46.7% [36, 57] | 100.0% [100, 100] | 31.66 |
