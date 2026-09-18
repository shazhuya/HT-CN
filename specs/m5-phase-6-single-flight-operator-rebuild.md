# M5 Phase 6 — Single-Flight Operator Rebuild

状态：**Product concurrency coordination; not research evidence**

## 1. 目标

Phase 3 已有 daily cache。
Phase 5 已有并行 full-universe build。

Phase 6 解决并发重复构建：

> 同一 cache identity 的多个同时请求，不得各自启动完整 universe rebuild。

实际触发来源包括：

- React dev-mode 双请求；
- 多个浏览器标签页；
- 用户重复刷新；
- 同一 API 进程内同时发生的普通请求和 force refresh。

## 2. Single-flight identity

single-flight key 绑定：

- cache_root
- expected_trade_date
- bars
- scales
- universe_hash
- operator cache contract version

workers 不进入 key，因为 D-046 已冻结 workers 只影响吞吐。

## 3. Owner / follower

同一 key：

- 第一个请求成为 owner；
- owner 执行真实 rebuild；
- 后续 follower 等待 owner Future；
- follower 直接复用 owner result；
- follower 不再次扫描 universe。

## 4. Cache interaction

普通 valid cache hit：

- 直接返回；
- 不进入 single-flight registry。

owner 获得 ownership 后：

- 非 force 请求会再次检查 cache；
- 如果别的本地/外部流程刚好已经写入有效 cache，则返回 hit_after_race；
- 避免不必要重算。

## 5. Force refresh

两个同时的 force refresh：

- 只允许一个 owner rebuild；
- follower 复用 owner 的 rebuilt_force 结果；
- follower 自己不执行第二次 force rebuild。

## 6. Product provenance

普通结果 product_cache：

- single_flight_scope = process_local_cache_identity
- coalesced_from_status = null

follower：

- status = coalesced_wait
- coalesced_from_status = owner 原始 status
- single_flight_scope = process_local_cache_identity

Phase 6 明确只做当前 API 进程内 single-flight。

它不是：

- 跨进程文件锁；
- 分布式锁；
- M4 evidence lock。

## 7. Failure behavior

owner exception：

- 同一 flight followers 接收同一 exception；
- registry 在 finally 中清理；
- 下一请求可以重新成为 owner；
- 不永久卡死 key。

## 8. Hard boundary

Single-flight：

- 不改变 Queue candidate；
- 不改变排序；
- 不改变 Source lifecycle；
- 不修改 harmonic identity；
- 不修改 Source Raw PRZ；
- 不写 M4 evidence；
- 不进入 outcome/alpha/ranking；
- 不生成 trade instruction。

## 9. Hosted validation

Validated checkpoint:

`ad76b7e62de49f7dbafb6898fbfdd055d096d338`

GitHub Actions run #1613 / id `35377167758`:

- overall: success
- Python: 637 passed
- Web build: success
- Playwright: 21 passed
- browser evidence upload: success

专项回归：

- concurrent cache miss -> exactly one real analysis；
- concurrent force refresh -> exactly one real analysis；
- follower -> coalesced_wait；
- regular cache hit unchanged。
