# M2.7 时间切分校准协议

目标：研究“已经满足 Carney 身份规则的 forming 结构，哪些当时可见的质量特征更稳定”，但不让后验结果反向污染身份定义。

## 1. 输入

输入固定来自 `artifacts/calibration/m2-forming-walk-forward.json`。

只进入时间切分的数据：

- PRZ 在 signal 之前没有被碰过；
- signal 之后至少存在完整 60 根交易 K 线；
- 每条记录都有精确的 60-bar observation end date。

因此 late signal 与 immature signal 不参与这一阶段的质量研究。

## 2. 时间顺序

使用全体可用 signal date 的时间顺序生成：

- Train 60%
- Validation 20%
- Holdout 20%

切分只看 signal timestamp，不看 touch/completion/retirement 等 outcome。

## 3. Purge

为了防止 label window 穿越数据集边界：

- Train 中，若 signal+60 bars 的 observation end 已进入 Validation，则删除；
- Validation 中，若 observation end 已进入 Holdout，则删除。

这个 purge 是防未来标签泄漏，不是形态筛选。

## 4. Train-only 阈值

PRZ width、signal 到 PRZ 的距离、Pivot confirmation lag 的 Q1/Q2/Q3 桶边界仅从 Train 学习。

Validation 必须复用 Train 的原始边界，不得重新分位数化。

## 5. 可研究特征

只允许 signal 当时已经存在的字段：

- pattern/schema/direction
- source Pivot scale
- 同一结构当时的多尺度支持数
- source tolerance 是否启用
- PRZ width / reference span
- signal close 到 PRZ 的距离 / reference span
- terminal Pivot 的 confirmation lag

禁止把未来是否 touch、completion、retirement、未来收益等字段作为输入特征。

## 6. Outcome

60-bar research outcome 继续拆开：

- PRZ touch before frontier retirement
- Engine completion before frontier retirement
- Frontier retirement without prior touch

这些是研究标签，不是胜率或交易建议。

## 7. Holdout 封存

本阶段脚本只输出 Holdout 的样本数量、日期范围、identity 索引，不输出 Holdout outcome 统计。

只有在 Train + Validation 上冻结一个质量策略之后，才能单独执行最终 Holdout audit。冻结之后不得回头修改策略再反复查看同一个 Holdout。

## 8. Carney identity 永远冻结

时间切分、quality bucket、未来统计都不能修改：

- Fibonacci 身份规则
- X/A/B/C/D 或 0/X/A/B/C 节点定义
- PRZ 构成
- Pattern identity

HT-CN 的研究层只能回答“一个合法结构当时的质量证据如何”，不能为了历史命中率重写 Carney 方法。

## 9. 当前样本限制

目前本地 QFQ 只有少数股票完成初始化。因此所有统计都只是工程/方法校准，不能视为全 A 股总体规律。扩大数据覆盖以后必须按同一冻结协议重新运行。
