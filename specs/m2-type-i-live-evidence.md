# M2.23 / M2.24 — Type-I T+5 实时证据层

## 目标

把已经完成确认并永久关闭的 Type-I `full_prz_exit_by_t5` 研究结果，转换成工作台可读的**证据状态**，而不是交易信号或新的形态规则。

证据来源现在有两层，而且必须分开保存、分开展示，不能事后合并成一个“胜率”：

- M2.22：冻结 45 股 Holdout，一次性确认性检验；
- M2.24：与原 45 股 `instrument_id` 零重叠的冻结 60 股外部复现，一次性确认性检验。

两套数据均已 `consumed/closed`。运行时只引用冻结结果，不重新计算，也不重新打开。

## 为什么不能直接挂在静态 D 点上

M2.22/M2.24 的确认性检验都以 Volume Three 的 source-aligned Terminal Price Bar 为时间零点；静态 completed pattern 的 D Pivot 需要右侧确认，时间语义不同。M2.17 的实证也表明，source-aligned Terminal Bar 与后来确认的终端 Pivot 不能机械视为同一个事件。

因此实时证据层单独重放 forming projection：

1. 只在 Pivot 自己的 `confirmed_at` 时刻暴露该 Pivot；
2. 冻结首次可见的 forming projection；
3. 从该 projection 搜索第一次测试 PRZ 极端测量的 Terminal Price Bar；
4. 从 Terminal Bar 起计算 T+5 完整脱离 PRZ、T1/T2 与后续 T+20 路径；
5. 输出为独立 `type_i_t5_events`，不回写静态 `completed`/`forming` 身份。

## 四种 T+5 状态

- `pending_t5_observation`：Terminal Bar 后不足 5 根 K 线，证据窗口尚未成熟。
- `t2_already_reached_by_t5`：T2 已在 T+5 前到达，因此不属于预注册的“到 T+5 仍待 T2”人群。
- `full_prz_exit_by_t5`：T+5 时仍待 T2，且 5 根内已在反转方向完整脱离 PRZ；对应冻结 exposure 组。
- `no_full_prz_exit_by_t5`：T+5 时仍待 T2，但 5 根内未完整脱离 PRZ；对应冻结 comparator 组。

只有后两种状态 `eligible_for_frozen_contrast=true`。

## 冻结 45 股 Holdout 证据

运行时原始 reference 必须与 `research/m2-type-i-holdout-result-v1.json` 完全一致，并由单元测试防止漂移：

- exposure：115 条，40 条在 T+6..T+20 到达 T2，progression rate `0.34782608695652173`；
- comparator：198 条，39 条到达 T2，progression rate `0.19696969696969696`；
- 绝对差 `0.15085638998682477`；
- 95% Newcombe CI `[0.049612411917687296, 0.2541290679331789]`；
- confirmatory result：`confirmed`。

## 独立 60 股外部复现证据

运行时 `external_replication` 必须与 `research/m2-type-i-external-replication-result-v1.json` 完全一致，并由单元测试防止漂移：

- 60/60 股票成功取得冻结 QFQ snapshot，与原 45 股零重叠；
- T+5 时仍待 T2 的 eligible events：1918；
- exposure：736 条，257 条在 T+6..T+20 到达 T2，progression rate `0.3491847826086957`；
- comparator：1182 条，213 条到达 T2，progression rate `0.1802030456852792`；
- 绝对差 `0.16898173692341648`；
- 95% Newcombe CI `[0.12831888515284715, 0.2098515212802209]`；
- confirmatory result：`confirmed`；
- eligible symbols：60，单只股票最大样本占比约 `0.026068821689259645`。

这组 60 股是预先冻结的跨行业 convenience replication set，不是随机抽样，不能宣称代表全部 A 股。其价值是：在另一组完全不重叠的股票历史样本中，相同的 source-aligned T+5 关系得到独立复现。

## 展示纪律

45 股 Holdout 与 60 股外部复现必须**分开显示**，禁止把两组简单合并后输出一个“成功率”。两组都只能称为冻结历史证据：

- 不得写成当前个股成功概率；
- 不得写成收益率预测或买卖建议；
- 不得写成全 A 股无条件胜率；
- 不得用复现后的 family / scale / direction / 股票子组再反向拟合阈值；
- 不得修改 Carney pattern identity、Pivot 或 PRZ。

## Endpoint 状态

实时层额外输出纯描述状态：

- `t2_hit_by_t5`
- `t2_hit_t6_t20`
- `pending_t20`
- `no_t2_by_t20`

该字段只描述当前窗口中已经发生或尚未成熟的路径，不产生新的确认性检验。

## API 集成

`GET /api/harmonic/{instrument_id}` 在原有 Carney 静态扫描结果之外增加：

```text
analysis.type_i_t5_events
```

API 使用 `analysis.bars` 中已经选择好的连续价格视图重新构造 DataFrame，因此静态扫描与证据回放使用完全相同的 QFQ/RAW 窗口；证据层仍由独立 no-lookahead walk-forward + Terminal-Bar audit 生成。

每个事件携带冻结 `historical_evidence`，其中原 45 股证据保持顶层字段，独立 60 股复现保存在 `historical_evidence.external_replication`。这样既能让 UI 同时展示两次确认性证据，又不会丢失其独立性。

## 不变量

- `geometry_score` 仍只表示几何贴合度。
- 实时证据层不改变任何 pattern identity、Pivot、PRZ、状态机或去重逻辑。
- 已消费的 45 股 Holdout 和 60 股 replication set 都不重新计算；运行时只引用冻结结果。
- 当前 T+5 分类只是 lifecycle/evidence 层，不自动转化为仓位或交易指令。
- 若未来研究更细阈值、family/scale/方向子组，必须使用新的独立冻结数据或向前推进的新样本，并在读取 outcome 之前完成新的预注册。
