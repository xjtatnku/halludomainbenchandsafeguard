# SafeEntryGuard

SafeEntryGuard 是一个大模型回答后置过滤引擎。它的目标不是重新生成答案，而是从模型原始回答中提取候选网址，判断哪些链接更安全、更符合用户意图，并只保留可信候选或直接拒绝危险结果。

## 当前解决的问题

SafeEntryGuard 主要用于处理以下风险：

- 模型回答里同时给出多个网址，用户不知道该点哪个
- 模型给出“官方但错入口”的网址
- 模型给出结构异常、相似仿冒或跳转漂移的域名
- 需要把 HalluDomainBench 的评测结果进一步转化为面向用户的安全过滤能力

## 当前能力

- 单条问答过滤
- 批量 JSONL 过滤
- 目标实体与入口意图识别
- 官方 / 授权 / 可疑候选判定
- 只保留最安全候选
- 输出拒绝理由和过滤标签
- 提供最小 Web API

## 目录结构

```text
SafeEntryGuard/
├─ safeentryguard/
│  ├─ cli.py              命令行入口
│  ├─ api.py              最小 Web API
│  ├─ config.py           配置加载
│  ├─ guard.py            过滤主链路
│  ├─ truth_store.py      真值库加载与匹配
│  ├─ extractors.py       URL / 域名抽取
│  ├─ domain_intel.py     域名结构与风险检查
│  ├─ scoring.py          推荐分与拒绝判定
│  └─ ...
├─ configs/
│  └─ guard.default.json
├─ docs/
│  └─ research_notes.md
├─ tests/
└─ README.md
```

## 安装方式

```powershell
cd SafeEntryGuard
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
```

## 默认配置

默认配置文件：

- `configs/guard.default.json`

配置内容主要包括：

- 真值库路径
- 风险阈值
- 推荐策略
- 过滤行为
- API 服务端口

如果你需要单独修改配置：

```powershell
python -m safeentryguard inspect-truth
```

## 最快上手方式

### 1. 单条过滤

```powershell
python -m safeentryguard filter-one --prompt "GitHub 登录入口" --response "请访问 https://github.com/login"
```

### 2. 批量过滤 JSONL

```powershell
python -m safeentryguard filter-jsonl --input outputs\sample_inputs.jsonl --output outputs\sample_filtered.jsonl --summary outputs\sample_summary.json
```

### 3. 直接处理 HalluDomainBench 输出

典型输入是：

- `ai_HalluDomainBench-main/data/experiments/<实验名>/response/model_real_outputs.jsonl`

例如：

```powershell
python -m safeentryguard filter-jsonl --input ..\ai_HalluDomainBench-main\data\experiments\sample_all_quantity_variants_main4_no_ernie\response\model_real_outputs.jsonl --output outputs\filtered.jsonl --summary outputs\summary.json
```

## 启动 Web API

```powershell
python -m safeentryguard serve
```

默认接口：

- `GET /health`
- `GET /truth/summary`
- `POST /filter`
- `POST /filter/batch`

示例：

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8765/filter -ContentType "application/json" -Body '{"prompt":"GitHub 登录入口","response":"请访问 https://github.com/login"}'
```

## 典型输出

SafeEntryGuard 会输出：

- 推荐网址
- 拒绝结果
- 风险标签
- 过滤理由
- 批量汇总摘要

批量处理时常见输出文件：

- `filtered.jsonl`
- `summary.json`

## 与 HalluDomainBench 的关系

推荐协作方式：

1. 先用 HalluDomainBench 跑实验，得到原始回答与评分结果
2. 再用 SafeEntryGuard 对原始回答做二次过滤
3. 对比“过滤前”和“过滤后”的风险变化

也就是说：

- HalluDomainBench 负责研究评测
- SafeEntryGuard 负责工程防护

## 注意事项

1. 当前过滤结果依赖真值库覆盖范围，真值不全时会更保守。
2. SafeEntryGuard 不负责调用模型 API，它处理的是模型已经生成的回答。
3. 当前重点是网址安全过滤，不是完整网页内容理解。
4. 如果要做浏览器插件或企业网关，建议先复用当前过滤核心，再单独做上层接口。

## 当前推荐用途

- 实验结果二次净化
- 面向用户的安全推荐原型
- 聊天助手和搜索助手的后处理组件
- 浏览器插件 / 本地 API / 企业中间件的核心引擎
