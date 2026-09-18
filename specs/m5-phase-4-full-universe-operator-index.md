# M5 Phase 4 — Full-Universe Operator Index

状态：**Product presentation/index layer; scan universe frozen independently from UI**

## 1. 目标

Phase 4 解决一个会直接导致漏扫的架构问题：

> UI 的展示数量不得决定实际扫描 universe。

Operator Queue 的 scan/cache universe 从本阶段起固定为：

`all_initialized_local_instruments`

## 2. Universe contract

GET /api/operator/queue：

- 永远通过 `discover_local_instruments(..., limit=0)` 获取完整当前本地初始化 universe；
- legacy `limit` 参数仅为兼容保留；
- legacy limit 不得缩小扫描范围；
- legacy limit 会在 operator_index provenance 中显式记录为 ignored。

## 3. Operator index provenance

Queue 顶层新增：

- schema_version
- universe_scope
- universe_instrument_count
- presentation_does_not_define_universe=true
- legacy_limit_ignored
- authoritative_evidence=false
- writes_m4_evidence=false

## 4. Presentation-only search/filter/pagination

前端允许：

- 代码/形态/生命周期/工作状态搜索；
- action state filter；
- lifecycle filter；
- pattern filter；
- direction filter；
- 25/50/100/200 本地分页。

这些操作：

- 不改变 cached full snapshot；
- 不改变 Delta comparison universe；
- 不触发新 harmonic scan；
- 不参与任何 predictive ranking。

## 5. Instrument picker

`/api/instruments` 支持最多 10,000 个本地初始化 instrument；
前端请求 10,000，以覆盖未来全 A 股本地 universe。

## 6. Hard boundary

Phase 4：

- no predictive score
- no outcome ranking
- no trade instruction
- no harmonic identity mutation
- no Source Raw PRZ mutation
- no lifecycle ownership
- no M4 evidence writes

## 7. Hosted validation

Validated checkpoint:

`41700e02bff874f7498c51bfbad6d8c5e708d4b2`

GitHub Actions run #1583 / id `35373726746`:

- overall: success
- Python: 629 passed
- Web build: success
- Playwright: 21 passed
- browser evidence upload: success

专项验收包括：

- `?limit=1` 仍扫描完整初始化 universe；
- 60 candidate fixture 默认只展示第一页；
- 翻页显示后续候选；
- 搜索后自动回第一页；
- action filter 在完整 candidate set 上生效；
- UI 请求不再携带 scan-limit。
