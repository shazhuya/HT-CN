# HT-CN 复权与原始价格策略

## 结论

HT-CN 永久保存原始未复权 OHLCV，复权价格不覆盖原始行情。

当前 M1 使用独立的 `price_factor` 层生成前复权（QFQ）价格视图：

`adjusted_price(t) = raw_price(t) * price_factor(t)`

`price_factor(t)` 由同一数据源同一交易日的前复权收盘价与原始收盘价之比推导。

## 为什么不直接只存前复权 K 线

1. 原始行情是审计基准，不能因为复权算法或数据源变化而丢失。
2. 谐波 Pivot / XABCD 对除权跳变非常敏感，必须能区分真实价格运动与公司行为。
3. 独立因子层允许以后重新生成 QFQ/HFQ，而不用重新抓取全部 raw 历史。
4. 不同用途可以选择不同视图：实盘形态默认连续复权价格，成交量仍保留原始口径。

## 当前限制：Point-in-Time

M1 的 QFQ 因子是“以当前已知公司行为为基础”的现行前复权视图，适合当前图表与形态识别。

它暂时不用于严格的历史时点回测（point-in-time backtest）。严格回测需要保存“当时已知”的公司行为与因子版本，避免未来分红送转信息反向改变过去价格序列。这一能力后续单独实现。

## 存储

- 原始日线：`data/market/daily/<instrument>.parquet`
- QFQ 因子：`data/market/adjustment/qfq/<instrument>.parquet`

因子文件包含：

- `instrument_id`
- `trade_date`
- `price_factor`
- `mode`
- `source`

## HT-CN Core 使用原则

进入 Pivot / Pattern Core 前：

- 原始数据用于审计、成交量、成交额、源数据一致性检查。
- 谐波价格结构默认使用连续复权价格视图。
- 任何缺失、非正数、无法对齐的因子都必须显式报错，不允许静默填充导致假 Pivot。
