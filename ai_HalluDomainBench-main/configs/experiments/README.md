# 实验配置说明

当前项目默认只把两个最外侧目录数据集视为主数据集：

- `../new_dataset.json`
- `../sample_all_quantity_variants.json`

其余位于 `data/datasets/` 下的历史数据集和示例数据集仍保留为兼容资产，但不再作为团队后续主实验入口。

## 当前推荐配置

### `new_dataset.main5.v1.json`

- 使用最外侧 `new_dataset.json`
- 使用 `main5` 五模型编组
- 适合作为旧版中文综合数据集的标准复现实验

### `new_dataset.main4_no_ernie.v1.json`

- 使用最外侧 `new_dataset.json`
- 使用 `main4_no_ernie` 四模型稳定编组
- 当 `ERNIE` 调用不稳定时优先使用

### `sample_all_quantity_variants.main5.v1.json`

- 使用最外侧 `sample_all_quantity_variants.json`
- 使用 `main5` 五模型编组
- 适合做推荐数量 `3 / 5 / 10` 对域名风险影响的主实验

### `sample_all_quantity_variants.main4_no_ernie.v1.json`

- 使用最外侧 `sample_all_quantity_variants.json`
- 使用 `main4_no_ernie` 四模型稳定编组
- 当前最推荐的数量消融实验入口

## 使用原则

- 团队共享实验优先使用 `model_registry_path + model_selection.lineup`
- 新实验优先从最外侧两个数据集出发，不再新增第三套主数据集
- 对 `sample_all_quantity_variants.json`，应重点查看：
  - `target_count_summary.csv`
  - `model_summary.csv`
  - `response_report.csv`
  - `candidate_report.csv`
