# M5 Phase 5 — Parallel Daily Operator Build

状态：**Product throughput optimization; queue semantics frozen**

## 1. 目标

Phase 3 解决同交易日重复计算。
Phase 4 解决完整初始化 universe 不得漏扫。

Phase 5 解决：

> 首次当日全 universe Queue 构建不能长期保持逐只串行。

## 2. 并行模型

采用：

- bounded ThreadPoolExecutor；
- 默认 4 workers；
- 环境变量 `HTCN_OPERATOR_WORKERS` 可配置；
- hard bound: 1..16。

只有提供 `service_factory` 时才允许并行。

原因：

M3 service 读取本地 parquet / DuckDB / factor / context 数据。
不同 worker 不共享同一个 service 实例，降低共享状态与线程安全风险。

## 3. Worker isolation

parallel mode：

- 每个线程第一次执行任务时通过 service_factory 创建自己的 M3 service；
- 同一线程后续任务复用该线程自己的 service；
- 不把一个未知可变 service 实例跨线程共享。

若请求 max_workers > 1 但没有 service_factory：

- 自动回退 sequential；
- parallel_fallback_reason =
  `service_factory_required_for_parallel_isolation`。

## 4. Determinism

并发只改变任务完成顺序。

最终 Queue：

- 仍按 frozen workflow bucket；
- instrument_id；
- deterministic display_key

统一排序。

因此：

`parallel Queue semantics == serial Queue semantics`

## 5. Error isolation

单 instrument 分析失败：

- 只进入 errors；
- 不终止全 universe build；
- 其余 instruments 正常进入 Queue；
- progress callback 标记该 instrument 为 failed。

## 6. Progress

`build_operator_queue` 支持 product-only progress callback：

- completed
- total
- instrument_id
- success/failure

progress callback 自身异常不会改变 Queue 结果。

`scripts/m5_precompute_operator_snapshot.py`：

- 新增 `--workers`；
- 默认 4；
- 1..16 bounded；
- 第 1 个、每 25 个、最后一个、任何失败均实时打印。

## 7. Full-universe precompute

Phase 5 同时关闭旧 precompute subset 入口：

- 删除 `--limit`；
- precompute 永远 `discover_local_instruments(..., limit=0)`；
- 继续遵守 D-045 full-universe contract。

## 8. Cache interaction

cache hit：

- 直接返回；
- 不启动线程池；
- 不创建 worker service。

只有 cache miss / force refresh 才需要 worker build。

workers 不进入：

- candidate identity；
- cache identity；
- Delta identity；
- M4 research identity。

## 9. Product provenance

Queue `build_execution` 显式记录：

- mode
- requested_max_workers
- effective_max_workers
- service_isolation
- parallel_fallback_reason
- changes_queue_semantics=false
- authoritative_evidence=false
- writes_m4_evidence=false

## 10. Hard boundary

Phase 5 不允许：

- 改 harmonic identity；
- 改 Source Raw PRZ；
- 改 source lifecycle；
- 改 M4 evidence；
- 使用 outcome / alpha / win rate 排名；
- 生成 trade instruction。

## 11. Hosted validation

Validated checkpoint:

`96417f63d40d844b5d9d560fde5b47176b90aded`

GitHub Actions run #1601 / id `35376685726`:

- overall: success
- Python: 634 passed
- Web build: success
- Playwright: 21 passed
- browser evidence upload: success

专项回归包括：

- parallel vs serial Queue semantic equality；
- thread-local service isolation；
- no-factory safe fallback；
- per-instrument error isolation；
- progress completion coverage；
- cache hit skips worker creation。
