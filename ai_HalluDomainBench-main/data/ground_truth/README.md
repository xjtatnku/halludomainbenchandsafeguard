# Ground Truth Assets

`data/ground_truth/` 保存的是评分阶段使用的实体真值资产。

当前仓库里应把它理解成两层：

- `entities.starter.v1.json`
- `entities.new_dataset.supplement.v1.json`

## 各文件职责

### `entities.starter.v1.json`

这是基础 starter truth。

它的特点是：

- 结构完整
- 适合作为 schema 样例和最小可运行真值库
- 但对当前 `new_dataset` 主实验覆盖不足

### `entities.new_dataset.supplement.v1.json`

这是当前主实验使用的补充真值库。

它的职责是：

- 补齐 `new_dataset` 中真实 `single_target` prompt 所需的缺失实体
- 尽量补充关键登录、支付、下载等入口
- 不去覆盖原 starter 文件中已经稳定的基础样例

## 当前推荐口径

主实验不再把 `entities.starter.v1.json` 单独当成完整真值库，而是使用：

```text
starter truth + truth supplement
```

对应到配置层就是：

- `ground_truth_path`
- `ground_truth_overlay_paths`

## 与 dataset overlay 的区别

容易混淆的一点是：

- `ground_truth` 负责“实体、官方域名、授权域名、入口点”
- `dataset overlay` 负责“prompt 的显式标注修正”

也就是说：

- 如果问题是“这个品牌根本不在真值库里”，改 `ground_truth`
- 如果问题是“这条 prompt 本该是 open_set / single_target 或缺 expected_entity”，改 `data/dataset_overlays/`
