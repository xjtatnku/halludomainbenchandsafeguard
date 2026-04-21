# Derived Datasets

`data/datasets/` 保存的是从原始主数据集派生出来的“仓库内可复用数据集 bundle”。

这一层和外层原始数据集的区别是：

- 外层 `../new_dataset.json`、`../sample_all_quantity_variants.json` 是原始主数据源
- 这里的文件是为了实验复现、论文统计或特定分析目标生成的派生版本

## 当前文件

### `new_dataset.paper_dedup.v1.json`

这是面向论文统计的去重版 `new_dataset`。

它的特点是：

- 已吸收 `data/dataset_overlays/new_dataset.curation.v1.json` 的显式标注修正
- 以 `prompt` 文本为 key 做去重
- 输入 `2071` 条，输出 `2040` 条，去掉 `31` 条重复 prompt
- 保留每组重复中首个 source occurrence 作为 canonical record

### `new_dataset.paper_dedup.audit.v1.json`

这是对应的去重审计文件。

它记录：

- 每组重复 prompt 的 canonical 选择
- 被移除的 `prompt_id`
- 哪些重复组同时跨 `life_domain` 或 `intent`

## 设计原则

这里的派生数据集遵循三条原则：

1. 不直接回写外层原始数据集
2. 尽量把“字段修正”和“去重裁决”保留在仓库内可审计资产里
3. 让论文统计可以复现到具体 prompt 级决策
