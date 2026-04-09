# Datasets

`halludomainbench.seed.json` is a small paper-style sample bundle.

`halludomainbench.core.v1.json`, `halludomainbench.stress.v1.json`, `halludomainbench.open.v1.json`, and
`halludomainbench.full.v1.json` are starter benchmark datasets generated from the structured truth bundle.

The richer dataset schema supports:

- `scenario_id`
- `evaluation_mode`
- `expected_entity`
- `expected_entry_types`
- `prompt_family`
- `prompt_template_id`
- `tags`

Use `python -m halludomainbench bootstrap-dataset` to generate a fresh template bundle.
Use `python -m halludomainbench bootstrap-starter-assets` to regenerate the starter benchmark splits and configs.
