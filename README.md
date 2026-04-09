# HalluDomainBench And SafeEntryGuard

This repository contains two related projects:

- `ai_HalluDomainBench-main/`
  Research benchmark and platform for evaluating LLM domain hallucination security.
- `SafeEntryGuard/`
  Practical post-generation safety filter that selects the safest and most direct website from LLM answers.

Recommended reading order:

1. `ai_HalluDomainBench-main/README.md`
2. `SafeEntryGuard/README.md`

Project roles:

- `HalluDomainBench` focuses on benchmark construction, measurement, labeling, scoring, and experiment reporting.
- `SafeEntryGuard` focuses on practical deployment, filtering, and downstream defense.

These two projects are designed to evolve together:

- datasets and truth stores can be shared or aligned
- benchmark findings can feed the filter policy
- filter outputs can be evaluated back through the benchmark workflow
