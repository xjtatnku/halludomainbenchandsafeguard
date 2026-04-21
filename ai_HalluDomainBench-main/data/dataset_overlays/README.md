# Dataset Overlays

`data/dataset_overlays/` 用来保存“原始题库之外的人工标注修正层”。

这一层的目标是：

- 保持外层原始数据集不被项目内的实验性修正污染
- 对少量启发式难以稳定判断的 prompt 做显式覆盖
- 让 `new_dataset` 与 `sample_all_quantity_variants` 这样的派生数据集复用同一套修正口径

当前约定：

- 优先通过代码中的默认规则推断 `intent / evaluation_mode / expected_entry_types`
- 只有当某条 prompt 具有明显歧义，且默认规则会系统性误判时，才在 overlay 中覆盖
- overlay 可以按 `prompt_id` 或原始 `source_prompt` 命中

当前活跃文件：

- `new_dataset.curation.v1.json`

它主要修正两类问题：

- 原始 `new_dataset` 中少量“其实是开放推荐”的 prompt 被误判成 `single_target`
- 少量泛化政府/金融服务 prompt 并不存在稳定唯一实体，需要显式标成 `open_set`

如果你们后续做论文统计，需要基于这层修正先生成独立的派生 bundle，而不是直接把“去重逻辑”继续塞进 overlay。当前对应产物是：

- `data/datasets/new_dataset.paper_dedup.v1.json`
