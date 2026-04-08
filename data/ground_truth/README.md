# Ground Truth

`entities.sample.json` and `entities.paper.sample.json` are seed truth stores for smoke tests and local development.
`entities.starter.v1.json` is the first larger starter truth bundle used by the generated benchmark splits.

For real benchmark runs, replace it with a curated truth file that includes:

- stable `entity_id`
- `entity_type`, `industry`, and optional `brand_tokens`
- official domains
- authorized domains
- structured `entry_points`
- evidence URLs and verification timestamps
- notes about regional or product-specific entry points

Each `entry_point` can describe:

- `domain`
- `entry_type`
- `trust_tier`
- `path_prefixes`
- `regions`
- `canonical`

These seed files are intentionally incomplete. The benchmark will still run, but uncovered rows will be scored as `unknown_target_*` or `open_set_*` instead of exact official matches.

Use `python -m halludomainbench --config configs/experiments/main5.core.v1.json inspect-truth` to inspect truth coverage.
