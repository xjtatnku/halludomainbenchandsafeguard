# HalluDomainBench

HalluDomainBench 是一个面向“大模型回答中的域名安全风险”问题的评测平台。项目的核心目标不是简单判断模型是否知道某个官网，而是评估模型在真实生活化场景中给出的域名、链接和入口建议是否安全、可达、与用户意图一致。

当前仓库已经收口到一条清晰链路：

- 数据集组织生活化提问场景
- 采集层批量调用多个大模型
- 验证层抽取并验证回答中的域名和 URL
- 评分层基于真值库和风险标签进行量化评估
- 报表层输出模型级、响应级、候选级统计结果

## 当前项目边界

当前主实验只围绕仓库外层的两份主数据集展开：

- `../new_dataset.json`
- `../sample_all_quantity_variants.json`

这两份数据分别承担不同职责：

- `new_dataset.json`：用于主榜单、真实场景测试和综合安全比较
- `sample_all_quantity_variants.json`：用于研究“要求模型推荐多少个网站”对风险的影响

此外，仓库内当前还维护一份派生论文数据集：

- `data/datasets/new_dataset.paper_dedup.v1.json`

它用于在不改动原始 `new_dataset.json` 的前提下，做 prompt 级去重后的论文统计。

当前主实验默认使用两层数据校正资产：

- `data/dataset_overlays/new_dataset.curation.v1.json`
- `data/ground_truth/entities.starter.v1.json`
- `data/ground_truth/entities.new_dataset.supplement.v1.json`

其中：

- `dataset overlay` 用于修正少量原始 prompt 的 `evaluation_mode / expected_entity`
- `starter truth` 保留基础样例真值
- `truth supplement` 补齐当前 `new_dataset` 主实验缺失的实体与入口

把数据入口统一理解成 5 层就不会乱：

1. 外层原始数据集：`../new_dataset.json`、`../sample_all_quantity_variants.json`
2. 仓库内数据修正层：`data/dataset_overlays/`
3. 仓库内真值层：`data/ground_truth/`
4. 论文统计派生 bundle：`data/datasets/`
5. 实验运行产物：`data/experiments/`

其中前 4 层是“输入资产”，最后 1 层是“输出结果”，不要混用。

## 目录结构

```text
ai_HalluDomainBench-main/
├─ halludomainbench/
│  ├─ cli.py
│  ├─ config.py
│  ├─ dataset.py
│  ├─ dataset_variants.py
│  ├─ extractors.py
│  ├─ validators.py
│  ├─ domain_intel.py
│  ├─ truth.py
│  ├─ semantic.py
│  ├─ risk.py
│  ├─ scoring.py
│  ├─ reporting.py
│  ├─ models.py
│  ├─ providers.py
│  └─ pipeline.py
├─ configs/
│  ├─ benchmark.default.json
│  ├─ models.registry.v2.json
│  ├─ validation_profiles.v1.json
│  ├─ local.secrets.json
│  └─ experiments/
├─ data/
│  ├─ datasets/
│  ├─ experiments/
│  ├─ dataset_overlays/
│  ├─ ground_truth/
│  └─ taxonomy/
├─ docs/
├─ scripts/
└─ tests/
```

## 模型与 Provider 结构

当前主注册表位于：

- `configs/models.registry.v2.json`

项目已经从“单一聚合平台”调整为“多 provider 混合采集”结构。当前主编组是：

- `main6_multi_provider`

包含 6 个对外展示模型：

- `Qwen/Qwen3.5-397B-A17B`
- `deepseek-ai/DeepSeek-V3.2`
- `Pro/moonshotai/Kimi-K2.5`
- `zai-org/GLM-4.6`
- `baidu/ERNIE-4.5-300B-A47B`
- `doubao-seed-character-251128`

其中实际路由如下：

- 前四个模型通过 SiliconFlow 聚合接口调用
- 豆包通过火山方舟单独调用
- 百度模型在报表里保留历史展示名 `baidu/ERNIE-4.5-300B-A47B`，但底层通过 `provider_model_id` 映射到当前百度千帆可访问的模型名

这一层设计的目的有两个：

- 保持历史实验、旧报表和模型对比口径连续
- 在 provider 侧模型名变化时，只修改注册表，不改主链路代码

此外还保留了一个仅聚合平台的稳定回退编组：

- `main4_aggregated`

它对应 `new_dataset.main4_no_ernie.v1.json` 和 `sample_all_quantity_variants.main4_no_ernie.v1.json`，适合只使用 `SILICONFLOW_API_KEY` 的场景。

## 实验配置

当前建议优先使用 `configs/experiments/` 下的两个主配置：

- `new_dataset.main5.v1.json`
- `sample_all_quantity_variants.main5.v1.json`

如果你们要做更干净的论文统计，还可以使用：

- `new_dataset.paper_dedup.main5.v1.json`

此外还保留两份回退配置：

- `new_dataset.main4_no_ernie.v1.json`
- `sample_all_quantity_variants.main4_no_ernie.v1.json`

这里有两个重要约定：

- 文件名里的 `main5` 是历史命名，为了复用既有输出目录和脚本入口而保留
- 这两个 `main5` 配置在当前版本里实际选择的是 `main6_multi_provider`

其中：

- `new_dataset.main5.v1.json`：当前主实验配置，默认启用多 provider 主编组，且默认 `resume = true`
- `sample_all_quantity_variants.main5.v1.json`：数量变体主实验配置，使用同一主编组
- `new_dataset.paper_dedup.main5.v1.json`：论文统计专用去重配置，基于仓库内去重 bundle，不复用历史 `new_dataset_main5` 输出目录
- `*.main4_no_ernie.v1.json`：仅在 provider 权限、预算或网络条件受限时使用的回退配置，不是当前主线配置

这些配置现在都显式接入了两层补充：

- `dataset_overlay_path`
- `ground_truth_overlay_paths`

这样做的目的不是“再造一份数据集”，而是把：

- 原始外层数据集
- 仓库内人工修正层
- 仓库内真值补充层

三者清楚分开，避免后续为了修一条 prompt 或补一个实体去直接污染原始数据源。

## 历史结果续跑逻辑

项目当前支持“在旧输出目录上继续跑新模型”。

以 `new_dataset.main5.v1.json` 为例：

- 它继续写入 `data/experiments/new_dataset_main5/`
- `collect` 阶段会按 `(model, prompt_id)` 去重续跑
- `verify`、`score`、`report` 阶段会只处理当前 lineup 中的模型

这意味着：

- 旧五模型阶段已经得到的几百条输出可以继续保留
- 当前新增模型可以在同一实验目录里平滑补跑
- 已下线或退役模型不会再混入当前报表

这里最重要的一条是：`data/experiments/new_dataset_main5/` 现在不是“旧垃圾输出目录”，而是你们主实验的历史资产目录。它应该保留，并作为后续六模型扩展时的续跑基座。

## 环境准备

### 1. 安装

```powershell
cd ai_HalluDomainBench-main
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
```

### 2. 本地密钥文件

创建：

- `configs/local.secrets.json`

示例：

```json
{
  "SILICONFLOW_API_KEY": "你的 SiliconFlow Key",
  "BAIDU_QIANFAN_API_KEY": "你的百度千帆 Key",
  "VOLCENGINE_ARK_API_KEY": "你的火山方舟 Key"
}
```

说明：

- 不要把密钥写入版本库
- `configs/local.secrets.json` 已在 `.gitignore` 中忽略
- 如果只跑 `main4_aggregated`，只配置 `SILICONFLOW_API_KEY` 即可

## 常用命令

### 查看数据集与真值

```powershell
python -m halludomainbench --config configs/experiments/new_dataset.main5.v1.json inspect-dataset
python -m halludomainbench --config configs/experiments/new_dataset.main5.v1.json validate-dataset
python -m halludomainbench --config configs/experiments/new_dataset.main5.v1.json inspect-truth
```

### 查看当前模型编组

```powershell
python -m halludomainbench inspect-models --registry configs/models.registry.v2.json --lineup main6_multi_provider
python -m halludomainbench inspect-models --registry configs/models.registry.v2.json --lineup main4_aggregated
```

### 查看验证档位

```powershell
python -m halludomainbench inspect-validation-profiles --profiles configs/validation_profiles.v1.json
```

### 主实验：继续跑 `new_dataset`

```powershell
python -m halludomainbench --config configs/experiments/new_dataset.main5.v1.json collect --resume
python -m halludomainbench --config configs/experiments/new_dataset.main5.v1.json verify
python -m halludomainbench --config configs/experiments/new_dataset.main5.v1.json score
python -m halludomainbench --config configs/experiments/new_dataset.main5.v1.json report
```

### 论文统计：去重版 `new_dataset`

```powershell
python -m halludomainbench --config configs/experiments/new_dataset.paper_dedup.main5.v1.json inspect-dataset
python -m halludomainbench --config configs/experiments/new_dataset.paper_dedup.main5.v1.json run --max-prompts 20
```

### 数量变化实验

```powershell
python -m halludomainbench --config configs/experiments/sample_all_quantity_variants.main5.v1.json run --max-prompts 20
```

### 单平台回退实验

```powershell
python -m halludomainbench --config configs/experiments/new_dataset.main4_no_ernie.v1.json run --max-prompts 20
```

### PowerShell 封装脚本

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_main5.ps1 -Dataset new_dataset -Command run -Resume
powershell -ExecutionPolicy Bypass -File scripts/run_main5.ps1 -Dataset sample_all_quantity_variants -Command run
```

说明：

- `scripts/run_main5.ps1` 当前只映射到两个 `main5` 配置
- 如果要跑 `main4_no_ernie`，请直接使用 `python -m halludomainbench --config ...`

## 输出结果

默认输出位于：

- `data/experiments/<实验名>/response/`
- `data/experiments/<实验名>/reports/`

常用文件包括：

- `model_real_outputs.jsonl`：模型原始回答
- `verified_links.jsonl`：抽取与网络验证后的结果
- `scored_links.jsonl`：真值匹配、风险标签和风险分
- `candidate_report.csv`：候选级报表
- `response_report.csv`：响应级报表
- `model_summary.csv`：模型级汇总
- `target_count_summary.csv`：按推荐数量汇总

## 与 SafeEntryGuard 的关系

HalluDomainBench 负责“评测、验证、量化、报表”这条科研链路。

如果你们要把这套能力进一步产品化，可以把 `SafeEntryGuard` 作为部署层的安全后处理组件。一个典型流程是：

1. 模型生成多个域名或入口候选
2. HalluDomainBench 完成抽取、验证和评分
3. SafeEntryGuard 过滤掉错误、高风险或与意图错配的候选
4. 最终只返回健康结果给用户

当前代码仓库本身没有把 SafeEntryGuard 深度耦合进主链路，但两者在研究逻辑上是连续的：

- HalluDomainBench 用于发现和量化问题
- SafeEntryGuard 用于把发现转成防御

## 当前建议

1. 需要延续旧五模型输出并继续扩展到当前六模型时，优先使用 `new_dataset.main5.v1.json`
2. 需要比较模型在推荐数量要求下的安全退化时，使用 `sample_all_quantity_variants.main5.v1.json`
3. `main4_no_ernie` 只作为单平台回退方案保留，不建议当主榜单配置
4. `data/experiments/` 下的历史结果默认视为实验资产，不应和缓存文件一样清理
5. 写论文或阶段汇报时，不要只看是否给出官网，还要同时看 `Top-1` 安全性、整条回答风险和入口错配比例

