# M5 Phase 5 — Daily Close Pipeline

状态：**One-click operational orchestration; M4 research and M5 product remain independent**

## 1. 目标

每日收盘后只执行一次入口：

`M1 update -> QFQ readiness -> M5 Operator cache + M4 prospective evidence`

该流水线只负责协调，不能把 M5 产品状态升级成研究证据，也不能让 M4 失败抹掉有效的 M5 产品结果。

## 2. Preflight

任何数据修改前必须满足：

- Git repository 可解析；
- named branch，可拒绝 detached HEAD；
- HEAD 可解析；
- source worktree clean；
- real M1 catalog 存在；
- M4 methodology freeze guard 通过；
- M4 Outcome Engine freeze guard 通过。

分支名本身不授权或禁止 prospective capture。

跨分支 capture 权限由：

- frozen methodology ancestor/content guard；
- Outcome Engine/active protocol guard；
- capture 内部 methodology fingerprint；
- clean worktree/code identity

共同决定。

## 3. Step order

1. methodology_guard
2. outcome_guard
3. m1_update
4. qfq_readiness
5. m5_operator_cache
6. m4_capture
7. m4_health
8. m4_transition
9. m4_observation
10. m4_outcome（条件满足时）
11. m4_bundle

## 4. Independent failure domains

M1/QFQ 是共享数据前提。

数据 ready 后：

- M5 cache 独立运行；
- M4 capture 独立运行。

规则：

- M5 cache 失败，不抑制 otherwise-valid M4 capture；
- M4 capture 失败，不抹掉 otherwise-valid M5 cache；
- M4 outcome 必须依赖 capture + health + observation；
- health/transition/observation 可审计已有 authoritative chain，即使当天没有新 capture。

最终单独报告：

- data_ready
- m5_product_ready
- m4_research_ready
- overall_status

## 5. M5 handoff readiness

M5 当日产品 snapshot 只有同时满足以下条件才返回 ready/exit 0：

- observation_integrity = single_as_of；
- failed_instrument_count = 0；
- analyzed_instrument_count = instrument_count；
- product_cache.freshness = current；
- as_of_trade_date 已解析。

否则 precompute exit=2，不允许日常流水线伪称 product-ready。

## 6. Runtime Git cleanliness

运行时目录：

- data/product/**
- data/research/**

必须被 Git 忽略。

理由：

- M5 cache 是 runtime product state；
- M4 evidence 是本地 append-only authoritative evidence store；
- 两者都不应被 standard git status 误判为源码变更，导致下一次 capture 自锁。

Git ignore 不改变 evidence 内容、不删除 evidence，也不替代 M4 bundle/hash/health。

## 7. Executables

Python：

`scripts/m5_daily_close_pipeline.py`

Windows：

`运行HT-CN每日收盘流水线.bat`

总报告：

`artifacts/reports/m5-daily-close-pipeline.json`

每一步单独日志写入 artifacts/reports。

## 8. Hosted validation

Validated checkpoint:

`f1b29a02a939160be01e75350373d6fde2af693a`

GitHub Actions run #1564 / id `35374690280`:

- overall: success
- Python: 645 passed
- Web build: success
- Playwright: 20 passed
- browser evidence upload: success

Frozen boundary audit:

- methodology components changed = 0
- Outcome Engine components changed = 0
