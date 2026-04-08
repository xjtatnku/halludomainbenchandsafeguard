# HalluDomainBench

`HalluDomainBench` is a benchmark platform for evaluating domain hallucination security in large language models.

## What The Platform Now Supports

- package-based pipeline instead of isolated scripts
- legacy compatibility wrappers for `collect.py`, `verify.py`, `verify2.py`, `report.py`, and `run_all.py`
- richer prompt schema with `scenario_id`, `evaluation_mode`, `expected_entry_types`, `prompt_family`, and `tags`
- truth-store schema with structured `entry_points` for homepage, login, payment, download, docs, support, and other real-life entry types
- risk labeling beyond official/unofficial, including `safe_*`, `caution_*`, `risky_*`, `unknown_target_*`, and `open_set_*`
- response-level and candidate-level exports for paper-grade analysis

## Core Modules

- `halludomainbench/config.py`: benchmark configuration and output layout
- `halludomainbench/dataset.py`: dataset loading, legacy normalization, richer prompt schema, dataset template writer
- `halludomainbench/taxonomy.py`: prompt/scenario taxonomy defaults and taxonomy template writer
- `halludomainbench/providers.py`: model provider abstraction and SiliconFlow adapter
- `halludomainbench/extractors.py`: URL and bare-domain extraction
- `halludomainbench/validators.py`: DNS/HTTP validation and response-level verification
- `halludomainbench/truth.py`: truth-store loading, entry-point matching, and entity classification
- `halludomainbench/risk.py`: candidate risk labeling and suspicion scoring
- `halludomainbench/scoring.py`: candidate scoring, DHRI-style response metrics, and aggregates
- `halludomainbench/reporting.py`: CSV report generation
- `halludomainbench/pipeline.py`: collect, verify, score, report, full-run orchestration
- `halludomainbench/cli.py`: formal CLI entrypoint

## Configs

- `configs/benchmark.default.json`: compatibility-oriented config over the existing dataset
- `configs/benchmark.paper.json`: paper-style sample config using richer dataset and truth assets
- `configs/experiments/main5.core.v1.json`: 5-model main leaderboard over the starter core split
- `configs/experiments/main5.full.v1.json`: 5-model main leaderboard over core + stress + open-set
- `configs/experiments/ablation.*.core.v1.json`: paired ablation configs for Kimi, DeepSeek, Qwen, and GLM

## Sample Assets

- `data/datasets/halludomainbench.seed.json`
- `data/datasets/halludomainbench.core.v1.json`
- `data/datasets/halludomainbench.stress.v1.json`
- `data/datasets/halludomainbench.open.v1.json`
- `data/datasets/halludomainbench.full.v1.json`
- `data/taxonomy/scenario_taxonomy.sample.json`
- `data/taxonomy/prompt_library.starter.v1.json`
- `data/ground_truth/entities.paper.sample.json`
- `data/ground_truth/entities.starter.v1.json`
- `configs/experiments/model_lineups.v1.json`

`entities.starter.v1.json` plus the generated starter datasets form the first project-grade seed benchmark:

- `26` starter entities
- `200` core targeted prompts
- `108` stress prompts
- `24` open-set prompts
- balanced `zh/en` coverage
- explicit `expected_entity` for all targeted rows

These assets are still starter-grade. Before publication, re-verify every evidence URL and region-specific entry point.

## CLI

```powershell
python -m halludomainbench run
python -m halludomainbench inspect-dataset
python -m halludomainbench bootstrap-truth
python -m halludomainbench bootstrap-dataset
python -m halludomainbench bootstrap-taxonomy
python -m halludomainbench bootstrap-starter-assets
python -m halludomainbench migrate-legacy-dataset --input ..\data330.json --output data\datasets\data330.legacy_v2.json
python -m halludomainbench --config configs/benchmark.paper.json inspect-dataset
python -m halludomainbench --config configs/experiments/main5.core.v1.json inspect-dataset
python -m halludomainbench --config configs/experiments/main5.core.v1.json inspect-truth
```

Legacy wrapper:

```powershell
python run_all.py
```

PowerShell experiment wrappers:

```powershell
.\scripts\run_main5.ps1 -Dataset core -Command inspect-dataset
.\scripts\run_main5.ps1 -Dataset full -Command run
.\scripts\run_ablation_pairs.ps1 -Pair all -Command run
```

## API Key

The collector now supports two ways to load your SiliconFlow API key:

1. Environment variable `SILICONFLOW_API_KEY`
2. Local file `configs/local.secrets.json`

Create the local file by copying `configs/local.secrets.json.example` and replacing the placeholder value.
`configs/local.secrets.json` is ignored by Git on purpose.

## Outputs

Default reports:

- `data/response/model_real_outputs.jsonl`
- `data/response/verified_links.jsonl`
- `data/response/scored_links.jsonl`
- `data/response/verification_report.csv`
- `data/response/verification_report_dead.csv`
- `data/reports/candidate_report.csv`
- `data/reports/response_report.csv`
- `data/reports/model_summary.csv`
- `data/reports/domain_summary.csv`
- `data/reports/intent_summary.csv`
- `data/reports/scenario_summary.csv`
- `data/reports/risk_label_summary.csv`

Paper sample reports:

- `data/paper/response/*.jsonl`
- `data/paper/reports/*.csv`

## Verification

```powershell
python -m unittest discover -s tests -v
python -m halludomainbench --config configs/benchmark.default.json inspect-dataset
python -m halludomainbench --config configs/benchmark.paper.json inspect-dataset
python -m halludomainbench --config configs/experiments/main5.core.v1.json inspect-truth
```

## Benchmark Defaults

- extraction and validation operate on user-visible `response` by default, not `reasoning_content`
- targeted tasks and open-set tasks are scored differently through `evaluation_mode`
- `entry_points` let the platform distinguish exact entry hits from same-domain but wrong-entry answers
- rows without truth coverage are preserved instead of discarded
- starter datasets separate `core`, `stress`, and `open` so leaderboard and ablation runs can target different realism/robustness tradeoffs
- paired ablation configs are restricted to the `core` split to reduce spend while keeping comparisons consistent
- seed truth files are intentionally incomplete and should be re-verified before real experiments
