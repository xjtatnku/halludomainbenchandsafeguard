# Experiment Configs

`main5.core.v1.json`

- 5-model main leaderboard on the targeted core split
- best for primary model ranking under budget constraints

`main5.full.v1.json`

- 5-model main leaderboard on `core + stress + open`
- best for the broader paper table after the core run is stable

`ablation.kimi_mode.core.v1.json`

- compare `Kimi-K2-Instruct-0905` vs `Kimi-K2-Thinking`

`ablation.deepseek_reasoning.core.v1.json`

- compare `DeepSeek-V3.2` vs `DeepSeek-R1`

`ablation.qwen_scale.core.v1.json`

- compare a large and a smaller Qwen 3.5 model

`ablation.glm_generation.core.v1.json`

- compare `GLM-4.6` vs `GLM-5`

Each experiment writes outputs under `data/experiments/<experiment_name>/...`.
