# M2.23 — Type-I T+5 实时证据层

## 目标

把 M2.22 已经一次性确认并关闭 Holdout 的 `full_prz_exit_by_t5` 关系，转换成工作台可读的**证据状态**，而不是交易信号或新的形态规则。

M2.23 不修改 Carney 几何身份，不修改 PRZ，不把冻结 Holdout 比例写成个股胜率，也不重新打开已经消费的 Holdout。

## 为什么不能直接挂在静态 D 点上

M2.22 的确认性检验以 Volume Three 的 source-aligned Terminal Price Bar 为时间零点；静态 completed pattern 的 D Pivot 需要右侧确认，时间语义不同。此前 M2.17 的实证也显示，source-aligned Terminal Bar 与后来确认的终端 Pivot 并不应被机械视为同一个事件。

因此 M2.23 单独重放 forming projection：

1. 只在 Pivot 自己的 `confirmed_at` 时刻暴露该 Pivot；
2. 冻结首次可见的 forming projection；
3. 从该 projection 搜索第一次测试 PRZ 极端测量的 Terminal Price Bar；
4. 从 Terminal Bar 起计算 T+5 完整脱离 PRZ、T1/T2 与后续 T+20 路径；
5. 输出为独立 `type_i_t5_events`，不回写静态 `completed`/`forming` 身份。

## 四种 T+5 状态

- `pending_t5_observation`：Terminal Bar 后不足 5 根 K 线，证据窗口尚未成熟。
- `t2_already_reached_by_t5`：T2 已在 T+5 前到达，因此不属于 M2.22 预注册的“到 T+5 仍待 T2”人群。
- `full_prz_exit_by_t5`：T+5 时仍待 T2，且 5 根内已在反转方向完整脱离 PRZ；对应冻结 Holdout exposure 组。
- `no_full_prz_exit_by_t5`：T+5 时仍待 T2，但 5 根内未完整脱离 PRZ；对应冻结 Holdout comparator 组。

只有后两种状态 `eligible_for_frozen_contrast=true`。

## 冻结历史证据

运行时 reference 必须与 `research/m2-type-i-holdout-result-v1.json` 完全一致，并由单元测试防止漂移：

- exposure：115 条，40 条 T+6..T+20 到达 T2，历史 progression rate `0.34782608695652173`；
- comparator：198 条，39 条到达 T2，历史 progression rate `0.19696969696969696`；
- 绝对差 `0.15085638998682477`；
- 95% Newcombe CI `[0.049612411917687296, 0.2541290679331789]`；
- confirmatory result：`confirmed`。

这些数字只能显示为“冻结45股 Holdout 历史证据”。禁止改写为当前个股成功概率、收益概率、买卖建议或全市场无条件胜率。

## Endpoint 状态

M2.23 额外输出纯描述状态：

- `t2_hit_by_t5`
- `t2_hit_t6_t20`
- `pending_t20`
- `no_t2_by_t20`

该字段只描述当前历史窗口中已经发生/尚未成熟的路径，不产生新的确认性检验。

## API 集成

`GET /api/harmonic/{instrument_id}` 在原有 Carney 静态扫描结果之外增加：

```text
analysis.type_i_t5_events
```

API 使用 `analysis.bars` 中已经选择好的连续价格视图重新构造 DataFrame，因此静态扫描与证据回放使用完全相同的 QFQ/RAW 窗口；证据层仍由独立 no-lookahead walk-forward + Terminal-Bar audit 生成。

## 不变量

- `geometry_score` 仍只表示几何贴合度。
- M2.23 不改变任何 pattern identity、Pivot、PRZ、状态机或去重逻辑。
- 已消费的 45 股 Type-I Holdout 不重新计算；运行时只引用冻结结果。
- 若未来研究更细阈值、family/scale/方向子组，必须使用新的独立冻结数据和新的预注册。
