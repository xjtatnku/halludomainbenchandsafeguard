# Experiment Configs

`main5.core.v1.json`

- 5-model main leaderboard on the targeted core split
- best for primary model ranking under budget constraints
- uses `model_selection.lineup = main5`
- defaults to `validation_profile = baseline_http`

`main5.full.v1.json`

- 5-model main leaderboard on `core + stress + open`
- best for the broader paper table after the core run is stable
- uses `model_selection.lineup = main5`
- defaults to `validation_profile = baseline_http`

`main5.core.dns_enriched.v1.json`

- same lineup as `main5.core.v1.json`
- switches validation to `dns_enriched`
- use after the starter truth bundle has matured enough to justify DNS record enrichment

`ablation.kimi_mode.core.v1.json`

- compare `Kimi-K2-Instruct-0905` vs `Kimi-K2-Thinking`

`ablation.deepseek_reasoning.core.v1.json`

- compare `DeepSeek-V3.2` vs `DeepSeek-R1`

`ablation.qwen_scale.core.v1.json`

- compare a large and a smaller Qwen 3.5 model

`ablation.glm_generation.core.v1.json`

- compare `GLM-4.6` vs `GLM-5`

`legacy330.highrisk_targeted.main5.v1.json`

- focused high-risk subset over `legacy330`
- uses `validation_profile = dns_enriched`

`legacy330.highrisk_targeted.main5.rdap_curated.v1.json`

- RDAP-enabled variant for the curated high-risk subset
- only use after the focused truth bundle has been manually reviewed and stabilized

Each experiment writes outputs under `data/experiments/<experiment_name>/...`.

Team-shared experiment configs should use `model_registry_path + model_selection.lineup` as the single source of truth for model selection. Future 10-model expansion should be done by editing the registry and lineup selection first, not by duplicating collection code or maintaining parallel `models` arrays.
