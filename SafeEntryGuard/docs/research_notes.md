# Research Notes For SafeEntryGuard

## 1. 设计定位

`SafeEntryGuard` 的定位是“LLM 回答后置过滤器”，目标是在不重训模型的前提下，拦截或过滤回答中的错误、危险或不符合用户意图的域名与网址。

它属于以下几个研究方向的交叉区域：

- LLM 幻觉域名与错误命名空间输出
- AI 搜索 / LLM Agent 的恶意 URL 风险
- 品牌仿冒与 typosquatting 风险控制
- 生成后安全防护 `post-generation defense`
- 高风险入口 `login / payment / download` 的安全推荐

## 2. 直接相关的研究方向

### 2.1 AI 搜索与恶意 URL 风险

- `The Rising Threat to Emerging AI-Powered Search Engines`  
  说明 AI 搜索引擎可能返回恶意 URL，提示“生成后结果过滤”是合理防线。
- `SafeSearch`  
  说明联网搜索和外部网页已经构成新的攻击面，后置过滤器是现实需求。
- `MalURLBench`  
  提出了对恶意 URL 脆弱性的系统化评测，并给出了轻量防护模块 `URLGuard` 的思路。

这些工作直接启发了本项目的三个原则：

- 不只看模型会不会回答，还要看回答中的 URL 风险
- 过滤器应尽量轻量、可插拔、可后置接入
- 需要把“是否正确”与“是否安全”统一起来

### 2.2 命名空间幻觉与 authoritative namespace

- `We Have a Package for You!`  
  证明了 LLM 会稳定地产生不存在或错误的软件包名，这说明“权威命名空间过滤”是可行的话题。
- `PackMonitor`  
  强化了“对于 authoritative namespace，可以用额外验证或约束机制抑制幻觉输出”的思路。

这些工作对 `SafeEntryGuard` 的启发是：

- 域名和包名本质上都属于可行动命名空间
- 真值库和 authoritative set 非常关键
- 过滤器应该优先使用确定性规则，而不是完全依赖第二个 LLM

### 2.3 品牌仿冒与域名生成攻击

- `PhishReplicant`  
  说明生成式 typosquatting 是真实且高效的攻击路径。

这直接支持本项目要做：

- 可疑结构检测
- 近似域名检测
- 可注册域与高仿域警示

## 3. 借鉴的成熟开源组件

### 3.1 `tldextract`

用途：

- 解析 `registrable domain`
- 支持更稳健的域名规范化

借鉴方式：

- 过滤器内部用它统一处理根域比较
- 减少 `co.uk`、子域链、公共后缀导致的误判

### 3.2 `dnspython`

用途：

- DNS 解析
- A / AAAA / CNAME 记录检查

借鉴方式：

- 作为第二阶段证据层
- 帮助识别无法解析或结构异常的候选域

### 3.3 `dnstwist`

用途：

- typosquatting / 品牌仿冒域生成与检测

借鉴方式：

- 作为可选增强模块
- 在已知官方域存在时，对高相似候选做更强的品牌仿冒判断

### 3.4 RDAP

用途：

- 查询域名注册状态

借鉴方式：

- 用作第三阶段证据层
- 对“看似像官网但可能未注册 / 可注册”的域名进行进一步筛查

## 4. 当前实现采用的工程策略

### 4.1 轻量后置过滤

不过度依赖大模型自身纠错，而是采用：

- URL / 域名抽取
- 真值库匹配
- HTTP / DNS / RDAP 证据
- 可疑结构启发式
- 决策策略

优点：

- 成本低
- 易解释
- 易接到任何大模型或 Agent 系统之后

### 4.2 高风险意图严格化

当前对这些意图更严格：

- `login`
- `payment`
- `download`

默认策略是：

- 只有“可信域 + 精确入口匹配”才允许推荐
- 同域但错误入口只能降级为警示，不直接推荐

### 4.3 与评测平台共享真值资产

这是最重要的工程决策之一。

这样做的好处：

- 研究和工程使用同一套实体定义
- 不会出现“论文评测和实际过滤标准不一致”
- 后续真值库补充能同时服务两边

## 5. 当前没有直接做的东西

为了先落地 MVP，当前没有把以下东西做成默认能力：

- 外部恶意情报 feed 强绑定
- HTML 内容级钓鱼检测
- 截图级视觉检测
- 二次调用 LLM 做投票或自反思
- 浏览器侧实时页面拦截

这些都可以作为下一阶段扩展。

## 6. 下一阶段建议

### 6.1 工程扩展

- 增加浏览器插件或中间件接口
- 对接本地恶意域名 feed
- 支持批量品牌 allowlist / denylist
- 增加缓存层，减少重复 HTTP / DNS / RDAP 请求

### 6.2 研究扩展

- 比较“原始回答”与“过滤后回答”的用户安全收益
- 测试过滤器对不同模型族的拦截效果
- 研究“错入口”与“错域名”哪类更影响真实用户
- 研究真值库覆盖率对过滤性能的影响

## 7. 参考来源

以下是当前设计最直接参考的公开来源：

- Netcraft: `Large Language Models are Falling for Phishing Scams`
  https://www.netcraft.com/blog/large-language-models-are-falling-for-phishing-scams
- Luo et al.: `The Rising Threat to Emerging AI-Powered Search Engines`
  https://arxiv.org/abs/2502.04951
- Dong et al.: `SafeSearch`
  https://arxiv.org/abs/2509.23694
- Kong et al.: `MalURLBench`
  https://arxiv.org/abs/2601.18113
- Spracklen et al.: `We Have a Package for You!`
  https://www.usenix.org/conference/usenixsecurity25/presentation/spracklen
- PackMonitor
  https://arxiv.org/abs/2602.20717
- PhishReplicant
  https://arxiv.org/abs/2310.11763
- `tldextract`
  https://github.com/john-kurkowski/tldextract
- `dnspython`
  https://dnspython.readthedocs.io/
- `dnstwist`
  https://github.com/elceef/dnstwist
