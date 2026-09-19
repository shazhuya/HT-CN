# M5 Phase 3 — Daily Operator Snapshot Cache

状态：**Product acceleration layer; not research evidence**

## 1. 目标

Phase 1 已有全 universe Operator Queue。
Phase 2 已有最近两个交易日的 product-only Delta。

Phase 3 解决可扩展性：

> 同一交易日重复打开工作台，不应再次逐只运行完整 M3 分析。

## 2. Cache identity

缓存身份绑定：

- expected local trade date
- bars
- scales
- universe hash
- cache contract version

任一变化都必须重算。

## 3. Cache semantics

product cache 永久声明：

- authoritative_evidence = false
- writes_m4_evidence = false

它：

- 不修改 harmonic identity；
- 不修改 Source Raw PRZ；
- 不拥有 lifecycle；
- 不写 M4 evidence store；
- 不进入 outcome inference；
- 只用于加速已存在的产品 Queue。

## 4. Freshness gate

只有满足：

- queue observation_integrity = single_as_of
- queue as_of_trade_date 已解析
- queue as_of_trade_date == expected local trade date

才允许落入“当日 cache”。

如果本地交易日历已经是新交易日，但 Queue 只能分析到旧交易日：

- 返回 live result；
- freshness=stale；
- status=live_not_cached；
- 绝不能把旧 Queue 写进新交易日缓存。

## 5. Failure mode

缓存文件：

- JSON；
- 原子 temp write + fsync + os.replace。

cache hit 校验失败、缓存损坏或 contract/universe 不匹配：

- 不阻断产品；
- 自动回退 live rebuild。

## 6. Presentation filter

完整 cache 永远保存完整 Queue。

“隐藏证据不足”等 UI filter：

- 只作用于 presentation copy；
- 不改变 cache identity；
- 不改变 Delta comparison universe。

## 7. API

GET /api/operator/queue 新增：

- refresh=false 默认优先 cache；
- refresh=true 强制重算。

默认打开页面：

- cache hit 优先。

用户显式“刷新队列”：

- refresh=true；
- 重新运行当前本地 universe；
- 产生 rebuilt_force。

## 8. Precompute

新增：

`scripts/m5_precompute_operator_snapshot.py`

用途：

- 可在每日 M1 数据更新后预热 Operator Queue；
- 避免首次打开 UI 才计算；
- 输出产品报告；
- 不产生 M4 research evidence。

## 9. UI provenance

Queue 显示：

- cache status
- queue as-of trade date
- freshness
- 明确“产品缓存，不是 M4 evidence”

## 10. Hosted validation

Validated checkpoint:

`3f666c53fa4856eb5ef973e27679583ffa604435`

GitHub Actions run #1525 / id `35372981759`:

- overall: success
- Python: 628 passed
- Web build: success
- Playwright: 19 passed
- browser evidence upload: success

Phase 3 diff 仅包含 M5 product/cache/API/UI/tests，不触及 harmonic core / M4 evidence / Outcome Engine。
