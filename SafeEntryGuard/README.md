# SafeEntryGuard

`SafeEntryGuard` 是一个面向真实使用场景的 LLM 回答后置过滤器。  
它的目标不是重新生成答案，而是对大模型已经给出的回答进行二次审查，只向用户输出“最安全、最直接、最符合意图”的网站入口；如果回答中的链接都不够可信，则明确拒绝推荐。

这个工程与 `ai_HalluDomainBench-main` 并列存在，但定位不同：

- `HalluDomainBench` 偏研究和评测
- `SafeEntryGuard` 偏落地和防护

两者共享核心思想：

- 只分析用户可见回答
- 区分实体正确性、域名可信度和入口意图匹配
- 对登录、支付、下载等高风险任务实行更严格的过滤策略

## 1. 这个项目解决什么问题

现实使用中，很多用户会这样使用大模型：

- “GitHub 登录入口是什么？”
- “给我 Python 官网下载地址”
- “支付宝支付入口在哪？”

模型常见问题不是“完全乱答”，而是：

- 给出官方但错误的入口
- 给出多个备用网址，其中混入错误域名
- 给出看似相似的高仿域名
- 给出无法解析、死链或重定向漂移链接

`SafeEntryGuard` 的核心策略是：

1. 从回答中抽取所有候选域名 / URL
2. 推断用户问的是哪个实体、什么入口类型
3. 对候选进行结构、网络和真值匹配验证
4. 只保留最可信的一个候选，或直接拒绝输出

## 2. 当前能力

当前版本已经支持：

- 单条问答过滤：输入 `prompt + response`，输出推荐结果
- 批量 JSONL 过滤：直接处理模型输出文件
- 最小 Web API：供前端、插件或中间件调用
- HalluDomainBench 真值库兼容
- 基于意图的入口过滤：`homepage / login / payment / download / support / docs`
- HTTP 可达性验证
- 可选 DNS 解析增强
- 可选 RDAP 注册状态增强
- 可选 `dnstwist` 变体检测增强
- 结构可疑特征打分：punycode、unicode、digit swap、长子域链、疑似品牌仿冒

## 3. 项目结构

- `safeentryguard/`
  核心源码
- `configs/guard.default.json`
  默认配置
- `data/truth/entities.sample.json`
  样例真值库
- `docs/research_notes.md`
  研究依据、论文话题和开源借鉴说明
- `tests/`
  基础测试

核心模块：

- `config.py`
  配置加载
- `truth_store.py`
  真值库加载、实体识别、入口类型推断、匹配逻辑
- `extractors.py`
  从回答中提取 URL / 域名
- `domain_intel.py`
  域名结构情报和可疑度分析
- `verifier.py`
  HTTP / DNS / RDAP 验证
- `policy.py`
  推荐策略和风险标签
- `guard.py`
  主过滤链路
- `cli.py`
  CLI 入口

## 4. 安装

在 `SafeEntryGuard` 目录下执行：

```powershell
pip install -e .
```

Python 要求：

- `Python >= 3.11`

当前依赖：

- `requests`
- `dnspython`
- `tldextract`

## 5. 配置

默认配置文件：

- `configs/guard.default.json`

默认会尝试复用上级评测工程里的真值库：

- `../ai_HalluDomainBench-main/data/ground_truth/entities.starter.v1.json`

这意味着两个工程可以共用一套实体和入口资产。

### 5.1 推荐的默认使用原则

- 真值库刚开始不完善时：
  使用 `HTTP + 结构启发式`
- 真值库逐步成熟后：
  再开启 `DNS`
- 高风险正式过滤时：
  再开启 `RDAP`

### 5.2 `dnstwist`

如果本机装了 `dnstwist`，可以把 `use_dnstwist` 设为 `true`，让过滤器额外识别常见品牌变体和仿冒域。

默认不强依赖 `dnstwist`，未安装时不会阻塞主流程。

## 6. 最快上手

### 6.1 查看真值库摘要

```powershell
python -m safeentryguard inspect-truth
```

### 6.2 过滤单条回答

```powershell
python -m safeentryguard filter-one --prompt "GitHub login page" --response "Use https://github.com/login to sign in."
```

### 6.3 指定期望实体和入口类型

```powershell
python -m safeentryguard filter-one --prompt "Give me the Python download page" --response "Official site: https://www.python.org/downloads/ ; docs: https://docs.python.org" --expected-entity python --entry-type download
```

### 6.4 批量过滤 HalluDomainBench 输出

如果你已经有 `model_real_outputs.jsonl`，并且有对应的数据集 JSON：

```powershell
python -m safeentryguard filter-jsonl --input ..\ai_HalluDomainBench-main\data\response\model_real_outputs.jsonl --dataset ..\ai_HalluDomainBench-main\data\datasets\halludomainbench.core.v1.json --output outputs\filtered_results.jsonl --summary outputs\filtered_summary.json --limit 5
```

说明：

- `--input` 指向模型原始输出 JSONL
- `--dataset` 用于通过 `prompt_id` 找回原始 prompt 和 `expected_entity`
- `--limit` 适合先做小规模冒烟测试

### 6.5 启动最小 Web API

```powershell
python -m safeentryguard serve
```

或指定地址与端口：

```powershell
python -m safeentryguard serve --host 127.0.0.1 --port 8766
```

启动后默认可用端点：

- `GET /health`
- `GET /truth/summary`
- `POST /filter`
- `POST /filter/batch`

示例：

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8765/filter -ContentType "application/json" -Body '{"prompt":"GitHub login page","response":"Use https://github.com/login"}'
```

## 7. 输出结果

### 7.1 单条过滤结果

`filter-one` 会直接打印一个结构化结果，主要字段包括：

- `inferred_entity`
- `requested_entry_types`
- `candidate_count`
- `recommended`
- `rejected`
- `filtered_text`
- `candidates`

### 7.2 批处理结果

`filter-jsonl` 会输出：

- `outputs/filtered_results.jsonl`
- `outputs/filtered_summary.json`

每条记录会包含：

- `recommended_url`
- `recommended_label`
- `recommended_score`
- `candidate_count`
- `rejected`
- `filtered_text`
- `detail`

### 7.3 Web API 返回结果

`POST /filter` 返回的核心字段包括：

- `status`
- `recommended_url`
- `recommended_label`
- `recommended_score`
- `candidate_count`
- `safe_candidate_count`
- `blocked_candidate_count`
- `rejected`
- `rejection_reason`
- `filtered_text`

`POST /filter/batch` 会返回：

- `summary`
- `items`

## 8. 当前过滤策略

当前是“确定性规则 + 真值库 + 轻量证据层”的设计，不依赖第二个 LLM 再判断一遍。  
这有两个优点：

- 成本低
- 容易解释与审计

典型标签包括：

- `trusted_exact_entry`
- `trusted_authorized_entry`
- `caution_wrong_entry`
- `risky_brand_impersonation`
- `risky_redirect_drift`
- `risky_structurally_suspicious`
- `risky_unregistered_domain`
- `risky_unreachable`
- `risky_untrusted_domain`

对 `login / payment / download` 这类高风险请求，默认要求“精确入口命中”才允许推荐。

## 9. 与 HalluDomainBench 的关系

这个工程不是替代 `HalluDomainBench`，而是承接它。

推荐工作流：

1. 用 `HalluDomainBench` 做研究评测、榜单和数据分析
2. 用 `SafeEntryGuard` 做真实回答过滤、防护实验和产品化验证
3. 逐步让两边共享：
   - 数据集 schema
   - 真值库 schema
   - 风险标签语义

## 10. 适用场景

当前最适合：

- 浏览器插件 / 前端中间层
- 聊天助手后处理模块
- 本地或内网 Web API 服务
- 企业内部知识助手的网页入口过滤
- 大模型搜索产品的安全防护层
- 作为评测平台之后的“落地原型”

## 11. 注意事项

- 这个项目不是网页内容检测器，当前主要分析回答中的 URL / 域名
- 真值库越完善，过滤质量越高
- 没有真值库时，过滤器仍可运行，但更偏启发式风险拦截
- `RDAP` 和 `dnstwist` 不建议一开始就全量打开
- 这个版本更强调“宁可少给，也不要错给”

## 12. 研究依据

相关论文、科研话题和开源借鉴，见：

- `docs/research_notes.md`

这份文档说明了当前设计借鉴了哪些研究方向，以及哪些成熟开源组件值得逐步接入。
