# M2.24 — Type-I T+5 独立股票集外部复现预注册与收口

## 为什么还要做外部复现

M2.22 已在冻结 45 股 Holdout 上一次性确认 `full_prz_exit_by_t5` 与后续 T2 progression 的关系，并且该 Holdout 已永久消费/关闭。这个结果不能再拿来调 family、scale、方向或阈值。

M2.24 的目标不是“再找一次正结果”，而是把**完全相同的主检验**搬到一组此前没有进入 45 股研究集的股票上，检验这种关系是否能跨 instrument set 复现。

## 数据冻结

外部复现集固定在：

- manifest：`research/a-share-type-i-external-replication-universe-v1.json`
- dataset：`a-share-type-i-external-replication-v1-60`
- 60 只股票，与原 45 股 `instrument_id` 零重叠
- QFQ
- 2016-01-01 开始
- snapshot cutoff：2026-09-15
- scales：3 / 5 / 8 / 13 / 21
- provider coverage gate：至少 48/60 成功

该集合是**跨行业预先冻结的 convenience replication set**，不是随机抽样，因此即便复现成功也不宣称代表全部 A 股。

股票清单在读取这些股票的 Type-I outcome 之前冻结。名称与 bucket 只作描述，不进入检验。

## 唯一主检验

保持 M2.21/M2.22 完全相同的时间语义：

1. no-lookahead forming projection；
2. M2.17 source-aligned Terminal Price Bar 为 T0；
3. 必须至少有 T+20 的完整后续观察窗口；
4. T+5 时已经到 T2 的事件先排除；
5. exposure = `full_prz_exit_by_t5`；
6. comparator = `no_full_exit_by_t5`；
7. endpoint = T+6..T+20 首次到达 T2。

不允许因为外部复现结果而改变 Terminal Bar、T+5、T2、PRZ full exit 定义。

## 统计规则

- 只运行 1 个 primary test。
- 每组至少 20 条，否则 `inconclusive`。
- 60 股至少 48 股取得有效冻结 QFQ snapshot，否则 `inconclusive`。
- effect = `p_exposure - p_comparator`。
- 95% Newcombe score difference interval (method 10)。
- 只有 coverage gate 通过、两组样本门槛通过且 CI 下界严格 > 0 才 `confirmed`。
- 门槛满足但 CI 下界 <= 0，则 `not_confirmed`。

方向、family、scale、单只股票等可在执行后输出描述性诊断，但**不能替代主检验，也不能用于结果失败后的补救性重定义**。

## 与原 Holdout 的隔离

原 45 股 Type-I Holdout 已 `consumed`，M2.24 不重新打开它。外部复现只使用新 60 股清单。原 M2.22 结果仅作为“要复现什么”的冻结来源，不参与新 60 股的阈值学习。

## 一次性复现结果

一次性 CI 运行在 commit `b1879e0b11d7ac89d1e09f515ba9f2bc3256ea50` 完成：

- provider coverage：60/60，超过冻结门槛 48/60；
- mature Terminal-Bar events：2212；
- T+5 时仍待 T2 的 eligible events：1918；
- `full_prz_exit_by_t5`：736 条，257 条在 T+6..T+20 首次到达 T2，比例 `0.3491847826086957`；
- `no_full_exit_by_t5`：1182 条，213 条达到 endpoint，比例 `0.1802030456852792`；
- absolute difference：`0.16898173692341648`；
- 95% Newcombe CI：`[0.12831888515284715, 0.2098515212802209]`；
- 预注册主结果：`confirmed`。

事件分布不是由单只股票主导：60 只股票都有 eligible event，单只股票最大记录数为 50，占 eligible events 的 `0.026068821689259645`。这只是集中度审计，不改变主检验。

原始 CI Artifact：

- workflow run：`35086009263`
- job：`104761064827`
- artifact id：`10444095342`
- artifact SHA256：`61db1866ef91cf570a6d6224acf0dca37313f982b61927ce1890f50948775f93`
- 原始 evaluation JSON SHA256：`61b858c9fa17f3149dbdb5a982734cb3b57884d739246147bf4b30eb885b4df8`
- snapshot manifest SHA256：`daa8758067b1da0660248c55ef274807b4f2988af21ac3e5958ca01da9f0a718`

## 收口规则

复现已经完成，因此 60 股 replication set 现在永久视为 `consumed`：

- `research/m2-type-i-external-replication-result-v1.json` 冻结一次性结果；
- authorization 关闭：`authorized=false`、`one_time_external_replication=false`、`evaluated_once=true`；
- CI 不再运行网络抓取和外部结果重算，只验证 preregistration 与 frozen result 的哈希和语义；
- 不允许在看到结果后改阈值、endpoint、family、方向、scale 或股票子集，然后把同一 60 股数据再次包装成确认性复现；
- 后续新的 confirmatory replication 必须使用新的、单独冻结的数据集或向前推进的新快照，并先建立新的预注册。

## 解释边界

这次独立 60 股复现与原 45 股 Holdout 的主效应方向和量级相近，并且预注册检验再次 `confirmed`。可以说：**同一个 source-aligned T+5 price-action 关系在另一组完全不重叠的股票历史样本中得到独立复现。**

仍然不能把结果写成：

- 当前个股的成功概率；
- 收益率预测；
- 买卖建议；
- 全 A 股无条件胜率；
- Carney 几何身份的新规则。

进入实战工具时，它仍只能作为 lifecycle/evidence 层，与 pattern identity、市场环境、风险管理分离。
