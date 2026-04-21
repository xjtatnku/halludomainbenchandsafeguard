# 实验配置说明

当前仓库维护两份主实验配置、两份回退配置，全部围绕两份主数据集展开：

- `../new_dataset.json`
- `../sample_all_quantity_variants.json`

此外还新增了一份论文统计专用配置：

- `new_dataset.paper_dedup.main5.v1.json`

它不替代主实验配置，而是服务于 prompt 级去重后的论文统计。

这四个配置在当前版本里都额外接入了两层补充资产：

- `dataset_overlay_path`
- `ground_truth_overlay_paths`

前者用于修正少量原始 prompt 的显式标注，后者用于在不改动 starter truth 的前提下补齐主实验所需实体。

## 当前主配置

### `new_dataset.main5.v1.json`

- 数据集：`../new_dataset.json`
- 实际编组：`main6_multi_provider`
- 输出目录：`data/experiments/new_dataset_main5/`
- 默认密钥：`SILICONFLOW_API_KEY`、`BAIDU_QIANFAN_API_KEY`、`VOLCENGINE_ARK_API_KEY`
- 默认特点：`resume = true`

使用场景：

- 当前主榜单
- 历史 `new_dataset_main5` 目录上的续跑
- 需要保持旧报表口径连续的实验

### `sample_all_quantity_variants.main5.v1.json`

- 数据集：`../sample_all_quantity_variants.json`
- 实际编组：`main6_multi_provider`
- 输出目录：`data/experiments/sample_all_quantity_variants_main5/`
- 默认密钥：`SILICONFLOW_API_KEY`、`BAIDU_QIANFAN_API_KEY`、`VOLCENGINE_ARK_API_KEY`

使用场景：

- 研究推荐数量 `1 / 3 / 5 / 10` 与风险之间的关系
- 做数量遵从度和安全退化分析

## 回退配置

### `new_dataset.main4_no_ernie.v1.json`

- 数据集：`../new_dataset.json`
- 实际编组：`main4_aggregated`
- 输出目录：`data/experiments/new_dataset_main4_no_ernie/`
- 默认密钥：仅 `SILICONFLOW_API_KEY`

使用场景：

- 只走聚合平台的稳定回退实验
- 预算、权限或 provider 侧条件受限时的 smoke test

### `sample_all_quantity_variants.main4_no_ernie.v1.json`

- 数据集：`../sample_all_quantity_variants.json`
- 实际编组：`main4_aggregated`
- 输出目录：`data/experiments/sample_all_quantity_variants_main4_no_ernie/`
- 默认密钥：仅 `SILICONFLOW_API_KEY`

使用场景：

- 单平台数量变体实验
- 低成本回退方案

### `new_dataset.paper_dedup.main5.v1.json`

- 数据集：`data/datasets/new_dataset.paper_dedup.v1.json`
- 实际编组：`main6_multi_provider`
- 输出目录：`data/experiments/new_dataset_paper_dedup_main5/`
- 默认密钥：`SILICONFLOW_API_KEY`、`BAIDU_QIANFAN_API_KEY`、`VOLCENGINE_ARK_API_KEY`
- 默认特点：`resume = false`

使用场景：

- 论文统计
- 去除 `new_dataset` 中 31 条重复 prompt 后的模型比较
- 需要减少重复题面对总体指标干扰时的汇总分析

## 命名与实际编组的关系

这里有三个容易误解的点：

1. 文件名里的 `main5` 是历史命名，不等于当前真的只跑 5 个模型。
2. `main4_no_ernie` 在当前版本里实际对应的是注册表中的 `main4_aggregated`。
3. `new_dataset.paper_dedup.main5.v1.json` 用的是仓库内派生 bundle，不是直接读取外层 `new_dataset.json`。

原因是项目已经从旧编组平滑过渡到多 provider 编组，但需要保留已有目录、脚本和历史实验口径。

## 数据入口

对 `new_dataset` 及其派生数据集，当前建议统一理解为三层：

1. 外层原始数据集
2. `data/dataset_overlays/new_dataset.curation.v1.json`
3. `data/ground_truth/entities.starter.v1.json` + `data/ground_truth/entities.new_dataset.supplement.v1.json`

如果是论文统计专用配置，还会再多一层：

4. `data/datasets/new_dataset.paper_dedup.v1.json`

这一层已经把 prompt 级去重结果固化成独立 bundle，因此运行时不再需要额外吃 `dataset_overlay_path`。

运行时再加上最后一层：

5. `data/experiments/<experiment_name>/`

前四层都是输入，最后一层是输出。这样设计的好处是：

- 原始题库保持不动
- prompt 标注修正和实体真值扩充相互独立
- `new_dataset` 与 `sample_all_quantity_variants` 可以复用同一套修正口径

## 模型注册表优先

团队共享实验时，优先使用：

- `model_registry_path`
- `model_selection.lineup`

而不是在单个配置里手写一长串模型名。这样做的好处是：

- 统一模型展示名
- 统一 provider 路由
- 统一历史兼容策略
- 后续换模型时改动面最小

## 历史结果续跑原则

如果你们要在已有输出目录上继续跑：

- 优先看 `collection.resume`
- 再看该配置的 `outputs.*` 指向哪个实验目录

当前最典型的是：

- `new_dataset.main5.v1.json`

它默认开启 `resume = true`，并继续写入历史 `new_dataset_main5` 目录。与此同时，后续 `verify`、`score`、`report` 阶段会只处理当前 lineup 中的模型，因此退役模型不会继续污染现有报表。

这意味着 `data/experiments/new_dataset_main5/` 应被视为历史资产目录，而不是普通临时输出目录。只要旧五模型结果还需要参与口径衔接，就不应删除。

## 推荐使用方式

### 继续跑主实验

```powershell
python -m halludomainbench --config configs/experiments/new_dataset.main5.v1.json collect --resume
python -m halludomainbench --config configs/experiments/new_dataset.main5.v1.json verify
python -m halludomainbench --config configs/experiments/new_dataset.main5.v1.json score
python -m halludomainbench --config configs/experiments/new_dataset.main5.v1.json report
```

### 数量变化主实验

```powershell
python -m halludomainbench --config configs/experiments/sample_all_quantity_variants.main5.v1.json run --max-prompts 20
```

### 单平台回退实验

```powershell
python -m halludomainbench --config configs/experiments/new_dataset.main4_no_ernie.v1.json run --max-prompts 20
```

### 论文统计去重实验

```powershell
python -m halludomainbench --config configs/experiments/new_dataset.paper_dedup.main5.v1.json inspect-dataset
python -m halludomainbench --config configs/experiments/new_dataset.paper_dedup.main5.v1.json run --max-prompts 20
```

## 查看编组与配置是否一致

```powershell
python -m halludomainbench inspect-models --registry configs/models.registry.v2.json --lineup main6_multi_provider
python -m halludomainbench inspect-models --registry configs/models.registry.v2.json --lineup main4_aggregated
```

## 对数量变体实验的阅读建议

对于 `sample_all_quantity_variants.json`，推荐优先查看：

- `target_count_summary.csv`
- `model_summary.csv`
- `response_report.csv`
- `candidate_report.csv`

这组报表通常最能反映“模型在被要求给出更多网站时，安全性是如何退化的”。

