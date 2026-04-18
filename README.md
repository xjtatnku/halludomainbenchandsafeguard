# HalluDomainBench and SafeEntryGuard

本仓库包含两个相互配合的子项目：

- `ai_HalluDomainBench-main/`
  大语言模型幻觉域名安全评测平台，用于采集模型回答、抽取链接、做网络与域名验证、风险标注、量化评分和报表分析。
- `SafeEntryGuard/`
  大模型回答过滤引擎，用于从模型原始回答中筛出最安全、最符合意图的网址，或直接拒绝危险候选。

仓库根目录当前只保留两份主数据集：

- `new_dataset.json`
  面向真实生活场景的主数据集，适合常规评测和对比实验。
- `sample_all_quantity_variants.json`
  面向推荐数量变化研究的数据集，重点用于 `1 / 3 / 5 / 10` 推荐数量与风险关系分析。

## 项目关系

推荐工作流如下：

1. 使用 `HalluDomainBench` 运行大模型评测实验。
2. 读取输出的 `model_real_outputs.jsonl`、`verified_links.jsonl`、`scored_links.jsonl` 与 CSV 报表。
3. 将模型原始回答或批量输出进一步交给 `SafeEntryGuard` 进行过滤与安全推荐。

## 快速开始

### 1. HalluDomainBench

```powershell
cd ai_HalluDomainBench-main
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
```

配置本地密钥文件：

- `ai_HalluDomainBench-main/configs/local.secrets.json`

示例内容：

```json
{
  "SILICONFLOW_API_KEY": "你的 API Key"
}
```

运行最小实验：

```powershell
python -m halludomainbench --config configs/experiments/new_dataset.main4_no_ernie.v1.json run --max-prompts 5
```

### 2. SafeEntryGuard

```powershell
cd ..\SafeEntryGuard
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
```

运行单条过滤：

```powershell
python -m safeentryguard filter-one --prompt "GitHub 登录入口" --response "请访问 https://github.com/login"
```

启动最小 Web API：

```powershell
python -m safeentryguard serve
```

## 目录说明

```text
halludomainbenchandsafeguard/
├─ new_dataset.json
├─ sample_all_quantity_variants.json
├─ ai_HalluDomainBench-main/
│  ├─ halludomainbench/
│  ├─ configs/
│  ├─ data/
│  ├─ scripts/
│  ├─ tests/
│  └─ README.md
└─ SafeEntryGuard/
   ├─ safeentryguard/
   ├─ configs/
   ├─ docs/
   ├─ tests/
   └─ README.md
```

## 当前约定

- 主数据集只保留两份：`new_dataset.json` 与 `sample_all_quantity_variants.json`
- 旧版 legacy 配置、旧数据集资产、历史测试脚本已删除
- 本地密钥文件不会提交到仓库

## 推荐阅读顺序

1. 先看 `ai_HalluDomainBench-main/README.md`
2. 再看 `SafeEntryGuard/README.md`
3. 最后根据实验目标选择对应配置文件
