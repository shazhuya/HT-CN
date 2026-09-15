# M1 — A 股数据引擎

## 目标

建立 HT-CN 的本地市场数据底座，为后续 Pivot、Pattern、Scanner 提供稳定、可追溯、可替换的数据接口。

## 范围

1. Security Master：证券代码、交易所、名称、板块、上市/退市日期、状态。
2. Trading Calendar：A 股交易日历。
3. MarketDataProvider 抽象接口：证券列表、日线、分钟线、复权因子、交易日历。
4. Local Store：Parquet + DuckDB。
5. 日线数据校验：字段、日期、重复、排序、OHLC 逻辑、成交量空值。
6. 增量更新：仅补本地最后日期之后的缺口。
7. 断点续传：任务状态 PENDING / DOWNLOADING / VALIDATING / COMPLETED / FAILED。
8. 数据来源元数据：source、download_time、row_count、checksum、version。
9. 数据源可替换：任何 Provider 故障不影响 Core。

## M1 验收标准

- 至少 5 只回归股票可建立本地日线数据。
- DuckDB 能按 symbol + date range 查询。
- Parquet 为权威本地历史存储。
- 重复执行更新不会产生重复行。
- 缺失区间可自动补齐。
- Provider 可以替换而无需修改 Core。
- pytest 覆盖存储、校验、增量更新。

## 暂不进入 M1

- 全 A 5000+ 股票初始化。
- Tick / Level-2。
- 自动交易。
- Pattern / PRZ / Scanner。
