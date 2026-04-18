# HalluDomainBench

HalluDomainBench 是一个面向“大语言模型幻觉域名安全”问题的评测平台。当前项目已经收口到两份根目录主数据集，并围绕以下能力展开：

- 多模型 API 采集
- 回答中域名与 URL 抽取
- HTTP / DNS / RDAP 证据验证
- 真值匹配与风险标签判定
- 数量遵从度分析
- 报表导出与模型对比

## 当前保留的数据集

当前平台只面向仓库根目录的两份主数据集工作：

- `../new_dataset.json`
- `../sample_all_quantity_variants.json`

说明：

- `new_dataset.json` 适合常规评测、模型对比和真实场景测试
- `sample_all_quantity_variants.json` 适合研究“要求模型推荐多少个网站”这一数量因素对安全风险的影响

## 目录结构

```text
ai_HalluDomainBench-main/
├─ halludomainbench/
│  ├─ cli.py                    命令行入口
│  ├─ config.py                 配置加载与默认值
│  ├─ dataset.py                数据集读取、标准化、摘要
│  ├─ dataset_variants.py       数据集去重与变体处理
│  ├─ extractors.py             URL / 域名抽取与清洗
│  ├─ validators.py             网络验证与域名检查
│  ├─ domain_intel.py           DNS / RDAP / 结构风险情报
│  ├─ truth.py                  真值匹配
│  ├─ semantic.py               open-set 语义相关性启发式检查
│  ├─ risk.py                   风险标签器
│  ├─ scoring.py                评分与汇总统计
│  ├─ reporting.py              报表输出
│  ├─ models.py                 模型注册表与 lineup 选择
│  ├─ providers.py              模型 API 调用封装
│  ├─ pipeline.py               collect / verify / score / report 主链路
│  └─ ...
├─ configs/
│  ├─ benchmark.default.json
│  ├─ models.siliconflow.v1.json
│  ├─ validation_profiles.v1.json
│  ├─ local.secrets.json        本地密钥文件，不提交
│  └─ experiments/
│     ├─ new_dataset.main5.v1.json
│     ├─ new_dataset.main4_no_ernie.v1.json
│     ├─ sample_all_quantity_variants.main5.v1.json
│     └─ sample_all_quantity_variants.main4_no_ernie.v1.json
├─ data/
│  ├─ experiments/              运行输出目录
│  ├─ ground_truth/
│  │  └─ entities.starter.v1.json
│  └─ taxonomy/
├─ scripts/
│  └─ run_main5.ps1
├─ tests/
└─ README.md
```

## 三类核心 JSON 文件

### 1. 数据集 JSON

作用：定义提示词、场景、领域和数量要求。

当前主数据集：

- `../new_dataset.json`
- `../sample_all_quantity_variants.json`

### 2. 真值库 JSON

作用：定义官方域名、授权域名和入口信息。

当前默认真值库：

- `data/ground_truth/entities.starter.v1.json`

### 3. 实验配置 JSON

作用：定义这次实验如何运行，包括：

- 用哪份数据集
- 用哪份真值库
- 用哪组模型
- 用哪种验证强度
- 输出写到哪里

## 安装与环境准备

### 1. 创建虚拟环境

```powershell
cd ai_HalluDomainBench-main
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
```

### 2. 本地密钥配置

创建文件：

- `configs/local.secrets.json`

内容示例：

```json
{
  "SILICONFLOW_API_KEY": "你的 API Key"
}
```

说明：

- 不要把密钥写进代码
- `local.secrets.json` 已加入忽略列表，不会提交

## 模型与配置方法

### 1. 模型注册表

模型注册表位于：

- `configs/models.siliconflow.v1.json`

这里定义：

- 模型 ID
- 模型分组 lineup
- 5 模型与 4 模型方案

### 2. 当前推荐实验配置

#### new_dataset

- `configs/experiments/new_dataset.main5.v1.json`
- `configs/experiments/new_dataset.main4_no_ernie.v1.json`

#### sample_all_quantity_variants

- `configs/experiments/sample_all_quantity_variants.main5.v1.json`
- `configs/experiments/sample_all_quantity_variants.main4_no_ernie.v1.json`

说明：

- `main5` 使用 5 个主模型
- `main4_no_ernie` 去掉 ERNIE，适合你们当前更稳定的实际运行方式

### 3. 验证档位

验证档位位于：

- `configs/validation_profiles.v1.json`

当前支持：

- `baseline_http`
- `dns_enriched`
- `rdap_curated`

## 启动方式

### 1. 查看数据集摘要

```powershell
python -m halludomainbench --config configs/experiments/new_dataset.main4_no_ernie.v1.json inspect-dataset
python -m halludomainbench --config configs/experiments/sample_all_quantity_variants.main4_no_ernie.v1.json inspect-dataset
```

### 2. 校验数据集结构

```powershell
python -m halludomainbench --config configs/experiments/new_dataset.main4_no_ernie.v1.json validate-dataset
```

### 3. 查看模型 lineup

```powershell
python -m halludomainbench inspect-models --registry configs/models.siliconflow.v1.json --lineup main4_no_ernie
```

### 4. 查看验证档位

```powershell
python -m halludomainbench inspect-validation-profiles --profiles configs/validation_profiles.v1.json
```

### 5. 一步运行完整链路

```powershell
python -m halludomainbench --config configs/experiments/new_dataset.main4_no_ernie.v1.json run --max-prompts 5
```

### 6. 分步运行

```powershell
python -m halludomainbench --config configs/experiments/new_dataset.main4_no_ernie.v1.json collect --max-prompts 5
python -m halludomainbench --config configs/experiments/new_dataset.main4_no_ernie.v1.json verify
python -m halludomainbench --config configs/experiments/new_dataset.main4_no_ernie.v1.json score
python -m halludomainbench --config configs/experiments/new_dataset.main4_no_ernie.v1.json report
```

### 7. PowerShell 脚本入口

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_main5.ps1 -Dataset new_dataset -Command run -MaxPrompts 5
powershell -ExecutionPolicy Bypass -File scripts/run_main5.ps1 -Dataset sample_all_quantity_variants -Command run -MaxPrompts 5
```

## 输出结果位置

默认输出在：

- `data/experiments/<实验名>/response/`
- `data/experiments/<实验名>/reports/`

常用输出文件：

- `model_real_outputs.jsonl`：模型原始回答
- `verified_links.jsonl`：链接与网络验证结果
- `scored_links.jsonl`：风险标签与评分结果
- `model_summary.csv`：模型级汇总
- `response_report.csv`：响应级报表
- `candidate_report.csv`：候选域名级报表
- `target_count_summary.csv`：按数量要求汇总的报表

## 当前支持的分析维度

- 模型级安全风险比较
- 候选域名结构风险分析
- HTTP / DNS / RDAP 证据层分析
- 官方域 / 授权域 / 异常域分类
- open-set 场景下的初步语义跑题检测
- 推荐数量 `1 / 3 / 5 / 10` 遵从度分析

## 注意事项

1. `sample_all_quantity_variants.json` 主要适合做数量变化实验，不建议单独承担全部主榜单任务。
2. 当前 open-set 语义相关性是启发式判定，不是完整语义理解。
3. 真值库仍是 starter 版本，后续需要按正式实验继续扩充。
4. `new_dataset.json` 含旧格式问题，平台内部做了兼容修复，但不要继续扩散这种旧格式。
5. 运行大样本时优先使用 `main4_no_ernie`，更符合你们当前实际稳定性。

## 当前最推荐的运行方式

### 常规场景

```powershell
python -m halludomainbench --config configs/experiments/new_dataset.main4_no_ernie.v1.json run --max-prompts 20
```

### 数量变化研究

```powershell
python -m halludomainbench --config configs/experiments/sample_all_quantity_variants.main4_no_ernie.v1.json run --max-prompts 20
```
