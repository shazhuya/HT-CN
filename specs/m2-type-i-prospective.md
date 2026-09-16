# M2.25 — Type-I 前瞻证据登记簿

## 目的

M2.22 的 45 股 Holdout 与 M2.24 的独立 60 股外部复现都已经一次性确认并永久 `consumed/closed`。下一步不再继续从这两组历史数据里寻找更细阈值，而是从冻结 cutoff 之后开始建立**前瞻、追加式、不可回删**的 Type-I 事件登记簿。

M2.25 的任务是保存“当时真正能看到什么”，不是再跑一个每天都会变化的显著性检验。

## 冻结协议

机器可读协议：`research/m2-type-i-prospective-protocol-v1.json`。

固定内容：

- protocol：`m2-type-i-prospective-v1`
- retrospective cutoff：`2026-09-15`
- 首个允许登记的 Terminal trade date：`2026-09-16`
- source clock：M2.17 source-aligned Terminal Price Bar
- scales：3 / 5 / 8 / 13 / 21
- forming horizon：60 bars
- landmark：T+5
- endpoint horizon：T+20
- exposure/comparator 定义继续沿用已经冻结的 `full_prz_exit_by_t5` / `no_full_exit_by_t5`
- endpoint 继续沿用“T+5 仍待 T2 时，T+6..T+20 首次到达 T2”

这些定义不能因为后续新数据表现而在同一个 registry 中变化。

## 为什么要有“首次看到”门槛

如果程序在某个历史事件已经走到 T+10 后才第一次扫描到它，那么再把该事件称为“前瞻样本”会产生回看偏差。因此 M2.25 冻结以下登记纪律：

- 第一次被本地 registry 观察到时，Terminal 后可见未来 K 线 `<= 5`：记为 `prospective_before_endpoint_window`；
- 第一次观察时已经 `> 5`：仍保留为 `backfilled_after_t5` 审计记录，但永久排除在未来任何前瞻主检验之外；
- T+5 时已经到 T2 的事件仍按既定规则作为 outcome-independent exclusion，不进入 exposure/comparator；
- cutoff 当日及之前的 Terminal 事件不进入该 registry。

允许第一次观察恰好发生在 T+5，是因为此时 exposure/comparator 已可确定，但预注册 endpoint 从 T+6 才开始，尚未观察到 endpoint window。

## 稳定事件 ID

UI 的历史 `event_id` 包含 rolling-window bar index；随着本地 3000 根窗口滚动，bar index 会变化，不适合做持久化主键。

M2.25 使用以下稳定字段生成 registry event id：

`instrument_id | pattern_id | schema | direction | source_scale | forming_signal_trade_date | terminal_trade_date`

绝对 QFQ 价格不进入主键。这样未来复权因子重基准不会制造一个“新事件”。

## 追加式状态

每个事件保存：

- 不变 core：证券、形态、schema、方向、scale、forming signal date、Terminal date；
- registration：首次观察日期、首次可见 future bars、是否满足前瞻登记门槛；
- observations：按本地数据观察日期追加的状态快照。

状态只允许单向演进：

- `pending_t5_observation` → `t2_already_reached_by_t5` / `full_prz_exit_by_t5` / `no_full_prz_exit_by_t5`
- exposure/comparator 一旦在 T+5 确定，不允许互相翻转；
- `pending_t20` → `t2_hit_t6_t20` 或 `no_t2_by_t20`
- endpoint 成熟后不允许回退。

同一观察日期若只有 QFQ 绝对价格发生重基准，registry 视为幂等，不重复追加；若同一天的分类状态发生变化，则直接报错，作为数据修订审计事件处理，而不是静默覆盖。

## 不删除原则

后续重新扫描时，如果一个已经登记的事件因为数据源修订、复权变化或滚动窗口变化暂时不再被扫描器返回，registry **不会删除它**。历史登记是“当时看到过什么”的审计记录，不是每次根据当前扫描结果重建的临时列表。

## 本地运行器

`scripts/m2_type_i_prospective_update.py`：

- 默认扫描本地已经同时具备 raw daily 与 QFQ factor 的证券；
- 可用 `--instrument SSE.688256` 重复指定个股；
- 可用 `--limit` 做小范围运行；
- 使用最多最近 3000 根连续价格 K 线和冻结 scales；
- 每完成一只股票就原子写回 registry，避免中断丢失此前登记；
- registry：`artifacts/prospective/m2-type-i-prospective-registry.json`
- summary：`artifacts/prospective/m2-type-i-prospective-summary.json`

该脚本不负责联网更新行情；应使用 M1 日更流程维护本地行情，然后更新 prospective registry。

## 这一阶段明确不做什么

M2.25 **没有 confirmatory test**，也不每天计算显著性、置信区间或“成功概率”。原因是反复查看并在任意时点宣布显著会引入 optional stopping。

Registry summary 只报告事件计数，例如：

- 已登记事件数；
- 真正前瞻登记数；
- 回填排除数；
- 等待 T+5 数；
- T+5 已排除数；
- exposure/comparator 当前计数；
- 已成熟到 T+20 的计数。

未来若要对这批前瞻事件做新的统计确认，必须在读取该次 confirmatory endpoint 结果进行推断之前，另建一个明确的 M2.26+ 预注册，包括固定样本停止条件和统计规则。

## 与实战工具的关系

实时工作台仍可以显示当前个股的 Type-I T+5 evidence state，因为这只是当前生命周期状态。Prospective registry 的职责不同：它负责研究完整性与时间戳审计，证明未来验证不是事后挑样本。

任何时候都保持：

- 不修改 Carney geometry；
- 不修改 PRZ；
- 不把 `geometry_score` 解释为概率；
- 不把历史 T2 progression rate 解释为当前个股收益概率；
- 不自动产生买卖或仓位指令。
