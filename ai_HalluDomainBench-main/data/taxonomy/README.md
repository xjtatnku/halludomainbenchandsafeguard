# Taxonomy

`data/taxonomy/` 目前只保留最小说明，不再继续堆放历史 sample JSON 资产。

这样处理的原因很简单：

- 旧 sample 文件容易和当前真实配置混淆
- taxonomy 的默认结构现在已经固化在代码里
- 当前项目重点是主数据集、真值库、配置和报表链路，而不是维护一套陈旧的模板副本

## 当前推荐工作方式

如果你要重新生成 taxonomy 模板，请直接使用：

```powershell
python -m halludomainbench bootstrap-taxonomy
```

如果你要生成新的实验数据集或结构模板，请使用：

```powershell
python -m halludomainbench bootstrap-dataset
python -m halludomainbench derive-dataset-subset --input <输入> --output <输出> --dataset-name <名称>
```

## 口径约定

为避免项目结构继续膨胀，当前建议长期遵守下面的边界：

- taxonomy 相关默认值以代码为准
- `configs/` 目录负责实验编组和运行参数
- 仓库外层主数据集负责当前实际评测输入
- `data/ground_truth/` 和 `data/dataset_overlays/` 负责当前主实验的修正层

也就是说：

- 如果问题是“意图、入口类型、默认推断规则”，优先看代码
- 如果问题是“模型编组和 provider 路由”，优先看 `configs/models.registry.v2.json`
- 如果问题是“当前评测输入和论文数据集”，优先看外层主数据集和 `data/datasets/`
