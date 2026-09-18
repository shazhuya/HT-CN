# M5 Phase 10 — Daily Handoff Bundle v2

status: frozen
validated_code_checkpoint: `99e3bf7aba1e656601bdcf4831d4b215eede4e8d`
validated_ci_run_id: `35382676878`
validated_ci_run_number: `1665`
validation_pr: `#22` (draft CI carrier only)
date: `2026-09-19`

## 目标

把 Phase 9 每日收盘后的最终产品产物组织成可搬运、可复核的交接 ZIP，同时绝不把 transport 层升级成 M4 authoritative evidence，也不允许交接包失败改写已经完成的 Phase 9 产品就绪判定。

## 当前产品快照绑定

Phase 10 禁止通过“扫描目录后挑最新 JSON”猜当前快照。

当 `m5_product_ready=true` 时，唯一 current product snapshot 必须从最终
`artifacts/reports/m5-operator-snapshot.json` 的 `product_cache.cache_path`
反向锁定，并同时验证：

- M5 report schema v2；
- `product_ready=true`；
- `observation_integrity=single_as_of`；
- cache status 属于已持久化状态；
- cache freshness=current；
- `input_identity_stable_during_build=true`；
- expected trade date / queue trade date / report as-of 一致；
- report input identity 与 product_cache identity 一致；
- cache path 被限制在 `data/product/m5/operator_queue/`；
- 文件名为 canonical `{trade_date}__b420__s3-5-8-13.json`；
- snapshot schema v1 / contract v2；
- snapshot bars/scales/date 与最终 report 一致；
- snapshot 完整 input identity 与最终 report 完全相同；
- snapshot queue 仍为同一 as-of、single-as-of；
- snapshot 自身继续声明非 authoritative、不会写 M4 evidence。

可选 previous snapshot 只作为历史产品上下文，不参与 current 选择；它也必须满足 canonical contract、date、queue integrity 与非 authoritative 边界。

## Pipeline / report / snapshot 三方交叉核验

交接包必须包含实际 Phase 9 pipeline report，并要求传入 payload 与磁盘文件内容一致。

manifest 记录：
- pipeline report SHA-256；
- current M5 report SHA-256；
- current snapshot SHA-256；
- trade date；
- input identity fingerprint；
- input identity contract。

Verifier 不能只做 member hash 校验，还必须独立解析并交叉核对：
- pipeline 的 M5/M4 ready flags；
- pipeline overall status；
- M5 final report 的 ready/date/single-as-of/cache/input identity；
- current snapshot 的 contract/date/input identity。

## M4 evidence 嵌套边界

外层 handoff ZIP 永远：
- `transport_only=true`；
- `authoritative_evidence=false`；
- `writes_m4_evidence=false`；
- `is_trade_instruction=false`；
- `alpha_inference_allowed=false`。

M4 authority 仍只属于嵌套 evidence bundle 内的 frozen capture chain。

规则：
- `m4_research_ready=true` 时，必须存在且通过现有 `verify_evidence_bundle` 的当前 M4 bundle；
- research degraded 时，若存在有效旧 bundle，可作为 `m4_existing_evidence_bundle` 携带；
- degraded 情况下无效旧 bundle 直接省略并记录 warning；
- 外层 verifier 会再次验证所有嵌套 M4 bundle。

## 可搬运性与完整性

- ZIP member 名必须安全，禁止绝对路径/目录逃逸；
- manifest 内路径使用 repository-relative 表达，不泄露本机绝对路径；
- 每个 member 记录 size + SHA-256；
- member set 必须与 manifest 精确一致；
- 先写临时 ZIP；
- 原子替换前必须完整 verify；
- 原子替换后再次 verify。

## Transport failure 与 Phase 9 readiness 解耦

独立 `daily_handoff_runner`：
- 读取 Phase 9 pipeline report；
- 构建 handoff ZIP；
- 独立写 `m5-daily-handoff.json`；
- 记录 pipeline report 构建前/后的 SHA-256；
- 明确 `transport_failure_does_not_rewrite_pipeline_readiness=true`；
- output/report/pipeline 三个路径不得相互覆盖。

因此：
- handoff transport 失败可以返回自己的非零退出码；
- 但它不能编辑 pipeline report；
- 也不能把既有 `m5_product_ready=true` 改成 false；
- 更不能把 M4 research 的成功/失败重新解释。

## 一键入口

`运行HT-CN每日交接包.bat` 只构建交接包，不偷偷重跑 Phase 9 daily pipeline。

产物：
- `artifacts/reports/htcn-daily-handoff-v2.zip`
- `artifacts/reports/m5-daily-handoff.json`

## 冻结边界与验证

Phase 9 governance checkpoint → Phase 10 code checkpoint 只新增 7 个 handoff/product/test/BAT 文件。

Freeze audit：
- M4 capture methodology changed components: 0 / 37；
- Outcome Engine changed components: 0 / 4。

Hosted CI run `35382676878` / #1665：
- overall success；
- Python 699 passed；
- Web build success；
- Playwright 21 passed；
- browser evidence upload success。
