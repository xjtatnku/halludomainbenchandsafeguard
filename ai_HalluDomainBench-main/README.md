# HalluDomainBench

`HalluDomainBench` 是一个面向大语言模型“幻觉域名 / 错误入口推荐”安全问题的评测平台。  
平台围绕真实生活场景构建，核心目标不是简单判断“模型有没有给出链接”，而是判断：

- 模型是否给出了正确实体的官方或授权域名
- 模型是否给出了正确的入口类型，例如 `homepage / login / payment / download / support / docs`
- 模型是否产生了高风险候选，例如可疑仿冒域、无法解析域、结构异常域、重定向漂移域
- 不同模型、不同提示词、不同证据强度下，整体安全性和可用性如何变化

当前版本已经完成以下工程化能力：

- 统一的包式流水线：`collect -> verify -> score -> report`
- 基于 `.json` 的数据集工作流，数据集不再依赖临时拼接或 CSV
- 基于模型注册表和 `lineup` 的模型选择机制，支持当前 `main5` 和后续 `expansion10`
- 面向现实场景的 prompt schema、真值库 schema、风险标签与评分链路
- 分阶段证据层：`baseline_http -> dns_enriched -> rdap_curated`
- 面向团队协作的实验配置、脚本包装、测试与兼容入口

## 1. 先理解 5 个核心概念

这个项目里最容易混淆的是下面 5 类文件：

### 1.1 数据集 `.json`

数据集文件存放的是 `prompt` 及其相关元数据，是“测试题库”。

典型字段包括：

- `prompt_id`
- `prompt`
- `scenario`
- `scenario_id`
- `intent`
- `evaluation_mode`
- `expected_entity`
- `expected_entry_types`
- `tags`

典型文件：

- `data/datasets/halludomainbench.core.v1.json`
- `data/datasets/halludomainbench.full.v1.json`
- `data/datasets/data330.legacy_v2.json`

### 1.2 真值库 `.json`

真值库是“标准答案库”，存放实体、官方域名、授权域名和入口定义。  
没有真值库，平台仍然可以跑采集和基础风险观察；但没有真值库，很多正式指标就不成立。

典型字段包括：

- `entity_id`
- `name`
- `aliases`
- `official_domains`
- `authorized_domains`
- `entry_points`

典型文件：

- `data/ground_truth/entities.starter.v1.json`
- `data/ground_truth/entities.legacy330.highrisk.v1.json`

### 1.3 实验配置 `.json`

实验配置文件定义“一次实验怎么跑”。  
它不是数据集，也不是真值库，而是把以下内容绑定在一起：

- 使用哪份数据集
- 使用哪份真值库
- 使用哪个模型编组
- 使用哪个验证档位
- 输出写到哪里
- 采样和验证参数是什么

典型文件：

- `configs/experiments/main5.core.v1.json`
- `configs/experiments/main5.core.dns_enriched.v1.json`
- `configs/experiments/legacy330.highrisk_targeted.main5.v1.json`
- `configs/experiments/legacy330.highrisk_targeted.main5.rdap_curated.v1.json`

### 1.4 模型注册表 `model registry`

模型注册表定义平台当前支持的模型，以及哪些模型属于哪个实验编组。

当前主文件：

- `configs/models.siliconflow.v1.json`

当前重要 `lineup`：

- `main5`
- `expansion10`
- `kimi_mode`
- `deepseek_reasoning`
- `qwen_scale`
- `glm_generation`

### 1.5 验证档位 `validation profile`

验证档位定义“证据层强度”，也就是回答清洗、网络验证、域名情报增强到底开到哪一层。

当前主文件：

- `configs/validation_profiles.v1.json`

当前三档：

- `baseline_http`
- `dns_enriched`
- `rdap_curated`

---

## 2. 平台工作流程

平台主流程固定为四步：

1. `collect`
   通过 SiliconFlow API 调用模型，对数据集中的 prompt 进行提问，保存原始回答。
2. `verify`
   从回答中抽取 URL / 域名，进行清洗、HTTP 验证、DNS 解析、可选 RDAP 增强等。
3. `score`
   将候选与真值库比对，进行实体归属、入口匹配、风险标签判定和风险评分。
4. `report`
   生成候选级、响应级、模型级和场景级 CSV 报表。

一句话理解：

`数据集 JSON + 真值库 JSON + 实验配置 JSON -> collect -> verify -> score -> report`

---

## 3. 目录结构

下面是团队成员最需要先理解的目录。

### 3.1 根目录

- `halludomainbench/`
  平台核心源码目录
- `configs/`
  所有实验配置、模型注册表、验证档位配置
- `data/`
  数据集、真值库、taxonomy、实验输出
- `scripts/`
  PowerShell 包装脚本
- `tests/`
  单元测试
- `collect.py / verify.py / verify2.py / report.py / run_all.py`
  旧入口兼容包装层，不再承载核心逻辑

### 3.2 `halludomainbench/` 核心模块

- `cli.py`
  正式 CLI 入口
- `legacy_cli.py`
  兼容旧脚本的转发入口
- `config.py`
  配置解析、默认参数、路径解析、validation profile 应用
- `dataset.py`
  JSON 数据集加载、校验、模板生成
- `dataset_variants.py`
  基于已有数据集派生子集
- `models.py`
  模型注册表加载、`lineup` 解析、每模型请求覆盖项
- `providers.py`
  API 提供方适配，目前主用 SiliconFlow
- `pipeline.py`
  主流水线编排：采集、验证、评分、报表
- `extractors.py`
  从回答中抽取 URL / 域名，并做清洗
- `domain_intel.py`
  域名结构情报，例如 registrable domain、unicode、词法可疑信号
- `validators.py`
  HTTP / DNS / RDAP 证据层验证
- `truth.py`
  真值库加载、实体匹配、入口匹配
- `risk.py`
  风险标签判定
- `scoring.py`
  风险分计算、响应级与模型级统计指标
- `reporting.py`
  CSV 报表生成
- `taxonomy.py`
  taxonomy 模板生成
- `starter_assets.py`
  starter 资产一键生成
- `experiment_assets.py`
  模型 lineup 和实验配置资产生成逻辑
- `legacy_migration.py`
  旧数据集迁移到新 schema
- `legacy_truth_assets.py`
  legacy330 高风险子集真值模板生成
- `validation_profiles.py`
  验证档位加载

### 3.3 `configs/` 重要文件

- `configs/models.siliconflow.v1.json`
  SiliconFlow 模型注册表和 lineup 定义
- `configs/validation_profiles.v1.json`
  分阶段证据层配置
- `configs/benchmark.default.json`
  默认兼容配置
- `configs/benchmark.paper.json`
  论文风格样例配置
- `configs/experiments/README.md`
  各实验配置的简要说明

### 3.4 `scripts/` 常用脚本

- `scripts/run_experiment.ps1`
  通用单配置运行脚本
- `scripts/run_main5.ps1`
  主榜单运行脚本
- `scripts/run_ablation_pairs.ps1`
  配对消融实验脚本
- `scripts/run_legacy330_highrisk.ps1`
  `legacy330` 高风险子集实验脚本

---

## 4. 环境要求与安装

### 4.1 Python 版本

项目要求：

- `Python >= 3.11`

### 4.2 安装依赖

建议在项目根目录执行：

```powershell
pip install -e .
```

当前主要依赖在 `pyproject.toml` 中定义，包括：

- `aiohttp`
- `requests`
- `tenacity`
- `tldextract`
- `dnspython`

### 4.3 API Key 配置

当前默认使用 SiliconFlow。  
平台读取 API key 的优先路径为：

1. 环境变量 `SILICONFLOW_API_KEY`
2. 本地文件 `configs/local.secrets.json`

推荐在仓库根目录新建：

`configs/local.secrets.json`

内容如下：

```json
{
  "SILICONFLOW_API_KEY": "你的apikey"
}
```

注意：

- `configs/local.secrets.json` 不要提交到 Git
- 如果团队成员本机代理不同，需要同时检查实验配置中的 `validation.proxy_url`

---

## 5. 新成员最快上手路径

如果你是刚接手项目的成员，建议按下面顺序理解和操作。

### 5.1 第一步：先看模型编组和验证档位

```powershell
python -m halludomainbench inspect-models --registry configs/models.siliconflow.v1.json --lineup main5
python -m halludomainbench inspect-models --registry configs/models.siliconflow.v1.json --lineup expansion10
python -m halludomainbench inspect-validation-profiles --profiles configs/validation_profiles.v1.json
```

### 5.2 第二步：检查数据集是否合规

```powershell
python -m halludomainbench --config configs/experiments/main5.core.v1.json inspect-dataset
python -m halludomainbench --config configs/experiments/main5.core.v1.json validate-dataset
```

### 5.3 第三步：做最小规模冒烟测试

```powershell
python -m halludomainbench --config configs/experiments/main5.core.v1.json run --max-prompts 2
```

### 5.4 第四步：看结果

优先查看：

- `data/experiments/main5_core/reports/model_summary.csv`
- `data/experiments/main5_core/reports/response_report.csv`
- `data/experiments/main5_core/reports/candidate_report.csv`

---

## 6. 推荐使用方式

### 6.1 直接使用 CLI

#### 查看数据集摘要

```powershell
python -m halludomainbench --config configs/experiments/main5.core.v1.json inspect-dataset
```

#### 校验数据集结构

```powershell
python -m halludomainbench --config configs/experiments/main5.core.v1.json validate-dataset
```

#### 查看真值库摘要

```powershell
python -m halludomainbench --config configs/experiments/main5.core.v1.json inspect-truth
```

#### 单步运行

```powershell
python -m halludomainbench --config configs/experiments/main5.core.v1.json collect --max-prompts 5
python -m halludomainbench --config configs/experiments/main5.core.v1.json verify
python -m halludomainbench --config configs/experiments/main5.core.v1.json score
python -m halludomainbench --config configs/experiments/main5.core.v1.json report
```

#### 一键跑完整流水线

```powershell
python -m halludomainbench --config configs/experiments/main5.core.v1.json run --max-prompts 5
```

### 6.2 使用 PowerShell 包装脚本

#### 主榜单

```powershell
.\scripts\run_main5.ps1 -Dataset core -EvidenceStage baseline_http -Command run
.\scripts\run_main5.ps1 -Dataset core -EvidenceStage dns_enriched -Command run
.\scripts\run_main5.ps1 -Dataset full -EvidenceStage baseline_http -Command run
```

说明：

- `core + baseline_http` 会使用 `configs/experiments/main5.core.v1.json`
- `core + dns_enriched` 会使用 `configs/experiments/main5.core.dns_enriched.v1.json`
- `full + baseline_http` 会使用 `configs/experiments/main5.full.v1.json`

#### 配对消融

```powershell
.\scripts\run_ablation_pairs.ps1 -Pair kimi_mode -Command run
.\scripts\run_ablation_pairs.ps1 -Pair deepseek_reasoning -Command run
.\scripts\run_ablation_pairs.ps1 -Pair qwen_scale -Command run
.\scripts\run_ablation_pairs.ps1 -Pair glm_generation -Command run
.\scripts\run_ablation_pairs.ps1 -Pair all -Command run
```

#### legacy330 高风险子集

```powershell
.\scripts\run_legacy330_highrisk.ps1 -EvidenceStage dns_enriched -Command run
.\scripts\run_legacy330_highrisk.ps1 -EvidenceStage rdap_curated -Command run
```

### 6.3 常见命令参数

- `--max-prompts`
  限制本轮测试的 prompt 数量，适合冒烟测试
- `--resume`
  从已有结果继续跑
- `--workers`
  控制采集并发
- `--sleep-sec`
  控制请求间隔
- `--temperature`
- `--top-p`
- `--presence-penalty`
- `--frequency-penalty`
- `--max-tokens`
- `--timeout-sec`
- `--max-retries`

示例：

```powershell
python -m halludomainbench --config configs/experiments/main5.core.v1.json collect --max-prompts 10 --workers 1 --sleep-sec 0.5 --temperature 0.0 --top-p 0.95
```

---

## 7. 输出结果如何理解

一次实验通常会在 `data/experiments/<experiment_name>/` 下生成结果。

### 7.1 原始结果

- `response/model_real_outputs.jsonl`
  原始模型输出
- `response/verified_links.jsonl`
  清洗、抽取、网络验证之后的结果
- `response/scored_links.jsonl`
  真值匹配和风险评分之后的结果

### 7.2 主要报表

- `reports/model_summary.csv`
  模型级汇总，比较模型表现最重要的文件
- `reports/response_report.csv`
  响应级汇总，分析单条 prompt 行为最重要的文件
- `reports/candidate_report.csv`
  候选级细节，分析具体域名最重要的文件
- `reports/domain_summary.csv`
  按域名聚合
- `reports/intent_summary.csv`
  按任务意图聚合
- `reports/scenario_summary.csv`
  按场景聚合
- `reports/risk_label_summary.csv`
  按风险标签聚合

### 7.3 最常看的 3 个文件

推荐优先看：

1. `model_summary.csv`
   先看模型整体安全性和趋势
2. `response_report.csv`
   再看具体 prompt 上的行为
3. `candidate_report.csv`
   最后看模型具体给出了哪些链接、为什么被判成某种风险

---

## 8. 当前评分链路测的是什么

当前平台的评测不是简单二分类“对 / 错”，而是完整链路式评估：

1. 回答里抽到了哪些链接或域名
2. 这些候选能否打开、是否能解析、是否发生重定向
3. 候选是否属于目标实体的官方或授权域
4. 候选是否命中用户真正需要的入口类型
5. 候选是否存在结构异常、可注册风险、重定向漂移等问题
6. 首位候选是否安全，整条回答是否整体安全

因此平台同时输出：

- `Top-1` 视角
- 全响应视角
- 候选细粒度风险标签
- 模型级聚合统计

---

## 9. 验证档位应该怎么选

### 9.1 `baseline_http`

适用场景：

- 刚开始跑新数据集
- 真值库还在补
- 先观察整体现象

特点：

- 速度快
- 成本低
- 不启用 DNS 解析器和 RDAP

### 9.2 `dns_enriched`

适用场景：

- 官方 / 授权域覆盖已经相对稳定
- 希望增强域名证据层

特点：

- 开启 DNS 增强
- 更适合正式实验前的中间阶段

### 9.3 `rdap_curated`

适用场景：

- 真值库已经人工复核
- 高风险子集要做更强证据分析

特点：

- 开启 DNS 和 RDAP
- 更慢、更重
- 不建议在真值库尚未稳定时盲目全量跑

注意：

- 不建议通过命令行临时硬改 `validation_profile`
- 推荐做法是新建一个专门的实验配置文件，并在其中指定 `validation_profile`

---

## 10. 当前推荐的实验组织方式

### 10.1 主榜单

使用：

- `configs/experiments/main5.core.v1.json`
- `configs/experiments/main5.full.v1.json`

说明：

- `main5` 是当前主榜单
- `full` 比 `core` 更广，但成本也更高

### 10.2 扩展到 10 模型

不要复制采集代码。  
正确做法是修改：

- `configs/models.siliconflow.v1.json`

优先扩展：

- `lineups.expansion10`

实验配置只需要引用：

- `model_registry_path`
- `model_selection.lineup`

### 10.3 配对消融

当前已支持：

- `kimi_mode`
- `deepseek_reasoning`
- `qwen_scale`
- `glm_generation`

适合研究：

- 推理模式差异
- 同家族大小模型差异
- 生成模式与候选污染之间的关系

---

## 11. 新成员应该先读哪些文件

如果你是后续接手的成员，建议按这个顺序阅读：

1. `README.md`
2. `configs/experiments/README.md`
3. `configs/models.siliconflow.v1.json`
4. `configs/validation_profiles.v1.json`
5. `halludomainbench/cli.py`
6. `halludomainbench/pipeline.py`
7. `halludomainbench/config.py`
8. `halludomainbench/dataset.py`
9. `halludomainbench/validators.py`
10. `halludomainbench/truth.py`
11. `halludomainbench/risk.py`
12. `halludomainbench/scoring.py`

如果只是想先跑实验，不必一开始读完整个代码库。

---

## 12. 数据集和真值库的现实边界

当前平台允许“真值库不完整”的情况下继续跑实验。  
这时平台仍然可以：

- 做 API 采集
- 做 URL 抽取和网络验证
- 做基础风险观测

但要注意：

- 真值覆盖不足时，模型级对比的结论会变弱
- `unknown_target_*`、`no_truth_match_*` 比例会升高
- 这类实验更适合作为现象观察或外部验证，不适合作为唯一正式主榜单

因此建议：

- 新数据集先跑小样本
- 确认可用后，再逐步补对应实体的真值库
- 真值库成熟后，再切到更强的 `dns_enriched / rdap_curated`

---

## 13. 注意事项

下面这些是团队成员最容易踩坑的地方。

### 13.1 数据集只接受 JSON

当前主流程明确只接受 `.json` 数据集。  
CSV 和临时拼接输入不再作为正式入口。

### 13.2 不要把 API key 写进代码或提交到 Git

推荐写入：

- 环境变量 `SILICONFLOW_API_KEY`
- 或 `configs/local.secrets.json`

不要写死在 Python 文件或实验配置里。

### 13.3 同一实验配置会写到同一输出目录

如果你用同一个实验配置反复测试不同样本、不同参数，结果可能覆盖。  
正式实验前建议：

- 新建独立实验配置
- 或先清理旧输出目录

### 13.4 默认只抽取 `response`

当前验证默认只使用模型面向用户可见的 `response`，不包含 `reasoning_content`。  
这是有意为之，因为评测目标是“用户会看到并可能点击的内容”。

### 13.5 `proxy_url` 需要按本机环境调整

当前很多配置默认使用：

- `http://127.0.0.1:7890`

如果你的本地没有代理，需要：

- 修改实验配置
- 或切换为直连可用环境

### 13.6 不要在共享配置里手写并行 `models` 数组

团队共享实验配置应优先使用：

- `model_registry_path`
- `model_selection.lineup`

避免每个配置各自维护一份 `models` 列表，导致主榜单和消融配置不一致。

### 13.7 不要过早全量打开最强证据层

`rdap_curated` 虽然更强，但更重、更慢，也更依赖真值库成熟度。  
推荐按阶段使用：

- `baseline_http`
- `dns_enriched`
- `rdap_curated`

---

## 14. 常用命令汇总

### 14.1 查看信息

```powershell
python -m halludomainbench inspect-models --registry configs/models.siliconflow.v1.json --lineup main5
python -m halludomainbench inspect-models --registry configs/models.siliconflow.v1.json --lineup expansion10
python -m halludomainbench inspect-validation-profiles --profiles configs/validation_profiles.v1.json
python -m halludomainbench --config configs/experiments/main5.core.v1.json inspect-dataset
python -m halludomainbench --config configs/experiments/main5.core.v1.json inspect-truth
python -m halludomainbench --config configs/experiments/main5.core.v1.json validate-dataset
```

### 14.2 主榜单实验

```powershell
python -m halludomainbench --config configs/experiments/main5.core.v1.json run --max-prompts 5
python -m halludomainbench --config configs/experiments/main5.full.v1.json run --max-prompts 5
```

### 14.3 高风险集实验

```powershell
python -m halludomainbench --config configs/experiments/legacy330.highrisk_targeted.main5.v1.json run --max-prompts 5
python -m halludomainbench --config configs/experiments/legacy330.highrisk_targeted.main5.rdap_curated.v1.json run --max-prompts 5
```

### 14.4 包装脚本

```powershell
.\scripts\run_main5.ps1 -Dataset core -EvidenceStage baseline_http -Command run -MaxPrompts 5
.\scripts\run_main5.ps1 -Dataset core -EvidenceStage dns_enriched -Command run -MaxPrompts 5
.\scripts\run_ablation_pairs.ps1 -Pair all -Command run -MaxPrompts 5
.\scripts\run_legacy330_highrisk.ps1 -EvidenceStage dns_enriched -Command run -MaxPrompts 5
```

### 14.5 数据集处理

```powershell
python -m halludomainbench migrate-legacy-dataset --input ..\data330.json --output data\datasets\data330.legacy_v2.json
python -m halludomainbench derive-dataset-subset --input data\datasets\data330.legacy_v2.json --output data\datasets\legacy330.highrisk_targeted.v1.json --dataset-name "legacy330 highrisk targeted" --evaluation-mode single_target --intent login_entry --intent payment_entry --intent download_entry --require-expected-entity
```

### 14.6 模板生成

```powershell
python -m halludomainbench bootstrap-truth
python -m halludomainbench bootstrap-dataset
python -m halludomainbench bootstrap-taxonomy
python -m halludomainbench bootstrap-starter-assets
python -m halludomainbench bootstrap-legacy330-highrisk-truth
```

---

## 15. 当前项目适合做什么

当前平台已经适合：

- 跑 5 模型主榜单
- 为后续 10 模型扩展预留统一接口
- 运行不同数据集和高风险子集
- 做不同证据层的逐阶段实验
- 生成论文可用的结构化报表
- 做配对消融研究

当前平台还不应该被误解为：

- 已经拥有完备真值库
- 已经拥有最终版恶意情报系统
- 已经可以替代人工复核

它现在是一个成熟的研究实验平台骨架，适合你们持续补数据集、补真值、扩模型、做系统实验。

---

## 16. 团队协作建议

建议按下面方式分工：

- 数据集成员负责 prompt 整理、schema 字段补充、样本分层
- 真值库成员负责实体、域名、入口与证据来源整理
- 平台成员负责配置、脚本、验证链路、评分链路和报表

工程上建议保持以下纪律：

- 所有正式实验都通过实验配置文件运行
- 所有共享模型选择都走 `model_selection.lineup`
- 所有新数据集先 `validate-dataset`
- 所有新主实验先做小规模 `--max-prompts` 冒烟测试
- 所有高风险强证据实验都先确认真值库覆盖情况

---

## 17. 回归检查

建议在提交较大改动前执行：

```powershell
python -m unittest discover -s tests -v
python -m compileall halludomainbench tests
```

如果你修改了：

- 数据集 schema
- 真值库 schema
- 风险标签
- 评分公式
- 配置解析

请务必同步检查：

- 对应测试是否需要补充
- README 是否仍与当前实现一致

---

## 18. 当前最短结论

如果只记住一句话：

`先准备数据集 JSON、真值库 JSON 和实验配置 JSON，再用 lineup 选模型、用 validation profile 选证据层，最后跑 collect -> verify -> score -> report。`

如果只记住两个命令：

```powershell
python -m halludomainbench --config configs/experiments/main5.core.v1.json validate-dataset
python -m halludomainbench --config configs/experiments/main5.core.v1.json run --max-prompts 5
```

这两个命令已经足够让新成员开始进入项目。
