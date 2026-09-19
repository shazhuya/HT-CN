# M5 Phase 9 — Daily Close Product Pipeline

status: frozen
validated_code_checkpoint: `dec76022098574537333e8d3abd56bcc3b928a99`
validated_ci_run_id: `35381269831`
validated_ci_run_number: `1646`
date: `2026-09-19`

## 目标

把 M1 日更、M3 context、M5 Operator cache 与独立 M4 research lane 组织成一个收盘后一键流水线，同时明确：M5 产品可用性不得被 M4 strict-QFQ、methodology guard 或单一历史供应商边角问题总阻塞。

## 冻结顺序

1. M1 fresh market data；
2. M3 context sync（best effort）；
3. M5 initial Operator cache；
4. M4 independent research lane；
5. M5 final non-force cache revalidation。

最后一步是必须项：M4 research lane 可能写入 `data/market/adjustment/qfq`，而 QFQ 属于 Operator Data Input Identity。若该输入在 M4 阶段变化，最终 revalidation 必须让 M5 cache 自动失效并按当前 identity 重建。

## 产品 ready 语义

M5 final product-ready 要求：

- initialized universe 非空；
- 至少一个成功分析；
- analyzed + failed == instrument count；
- observation_integrity == `single_as_of`；
- Queue 日期匹配 expected trade date；
- product cache freshness 为 current；
- cache status 为已持久化状态之一；
- input_identity_stable_during_build == true。

单票失败可以被隔离，不因个别 instrument error 把整个 Queue 判死，但错误必须显式进入报告。

## 分层阻塞边界

- M1 fresh market data 是 M5/M4 的共享硬前置；
- context sync 失败不阻塞 M5，产品可携带 degraded/previous context；
- M4 source preflight 只阻塞 M4 research lane；
- M4 methodology/outcome guard 只阻塞 M4 research lane；
- M4 strict QFQ readiness 只阻塞 M4 research lane；
- M4 degraded 不得把已经满足 final product-ready 的 M5 结果改成产品失败；
- M5 失败也不得掩盖一个本来有效的 M4 research result。

## 可观察性

每日流水线使用 unbuffered child process 与 line-by-line tee：
- 长步骤实时打印进度；
- 每一步同时写独立 log；
- context sync 暴露 [1/4] 到 [4/4] 阶段；
- Operator precompute 报告显式列出 instrument_errors。

## 永久边界

本阶段仍属于 product orchestration：
- authoritative_evidence=false；
- writes_m4_evidence=false；
- mutates_harmonic_identity=false；
- mutates_source_raw_prz=false；
- owns_lifecycle=false；
- 不使用 win rate / alpha / predictive score 排序；
- 不输出 trade instruction。

## 验证

Hosted CI run `35381269831` / #1646：
- overall success；
- Python 682 passed；
- Web build success；
- Playwright 21 passed；
- browser evidence upload success。

Freeze audit：
- M4 capture methodology changed components: 0 / 37；
- Outcome Engine changed components: 0 / 4。

Phase 8 → Phase 9 变更仅覆盖 daily close orchestration、context progress、M5 precompute readiness 与相关 tests，没有触碰被冻结的 M4 methodology / Outcome Engine 组件。
