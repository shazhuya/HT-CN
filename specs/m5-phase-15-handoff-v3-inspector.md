# M5 Phase 15 — Handoff v3 Inspector / Portable Review Workspace v1

状态：**implementation in progress**

## 1. 目标

Phase 15 把 Phase 14 已冻结的 `htcn-daily-handoff-v3.zip` 变成一个可离线打开、只读浏览的便携复盘工作区。

核心原则：

- Inspector 只消费 v3 transport；
- 读取前必须先通过现有 `verify_daily_handoff_bundle_v3()` 全链验证；
- 不依赖本机 M1 / market database；
- 不把 transport 内容导入本机 Queue / Operator History / Review Journal；
- 不创建 `reviewed` / `follow_up` 事件；
- 不修改 M4 evidence；
- 不生成预测评分、胜率、alpha 或买卖排序；
- 不把 review/follow-up 状态解释成新的 harmonic/lifecycle/trade meaning。

## 2. 输入

唯一正式输入：

`artifacts/reports/htcn-daily-handoff-v3.zip`

Inspector 消费 Phase 14 已冻结的 transport 内容：

1. nested Phase-10 v2 handoff；
2. current Operator product snapshot；
3. optional previous product snapshot；
4. current Phase-11 history observation；
5. optional previous trade-date history observation；
6. optional previous same-day revision；
7. Phase-12 daily review digest；
8. Phase-13 review-session snapshot；
9. review-journal predecessor closure；
10. nested M4 verification summary。

Inspector 不扫描本地 market/data 目录来补资料。ZIP 内没有的内容必须显示为缺失/降级，不得从本机“补齐”。

## 3. 验证顺序

```
v3 ZIP
  -> verify_daily_handoff_bundle_v3()
  -> nested v2 verifier
  -> nested M4 verifier (由 v2/v3 verifier 负责)
  -> history / digest / review-session / event-chain semantic checks
  -> only then build portable inspection model
```

验证失败：

`handoff_v3_invalid:<errors>`

Inspector 必须 fail closed，不得展示未经验证的 transport 内容。

## 4. Portable inspection model

新模块：

`src/htcn/app/handoff_v3_inspector.py`

Schema version：1。

主要输出：

- source verification；
- transport summary；
- current / previous Operator snapshot；
- current / previous Queue；
- current / previous history；
- daily review digest；
- review session；
- transported review events；
- current Queue searchable index；
- digest searchable index；
- active follow-up searchable index；
- instrument/display-key drill-down。

固定 contract：

- `requires_market_database=false`
- `imports_product_state=false`
- `writes_operator_queue=false`
- `writes_operator_history=false`
- `writes_review_journal=false`
- `writes_m4_evidence=false`
- `creates_review_events=false`
- `predictive_score_used=false`
- `historical_outcome_used_for_ranking=false`
- `alpha_inference_allowed=false`
- `is_trade_instruction=false`

## 5. Portable HTML workspace

Inspector 可把同一 inspection model 渲染为**单文件 HTML**：

`artifacts/reports/m5-handoff-v3-workspace.html`

特点：

- 中文优先；
- 无外部 JS/CSS/网络依赖；
- inspection JSON 直接嵌入 HTML；
- 支持按证券代码 / display key / 形态 / lifecycle / action 搜索；
- 当前 Queue 一屏显示：
  - 证券；
  - 形态；
  - action/lifecycle；
  - 当前判断；
  - 先看什么；
  - 下一关键价；
  - blocker/context caution；
- 显示 daily digest；
- 显示 active follow-ups；
- 显示 current/previous history observation 及 M4 nested status；
- 不提供任何写入按钮或 API 调用。

HTML 是 presentation artifact，不是新的 product/evidence authority。

## 6. CLI / 一键入口

CLI：

`scripts/m5_inspect_daily_handoff_v3.py`

默认输出：

- `artifacts/reports/m5-handoff-v3-inspector.json`
- `artifacts/reports/m5-handoff-v3-workspace.html`

支持：

- `--bundle`
- `--json-output`
- `--html-output`
- `--instrument`
- `--display-key`
- `--query-only`

Windows 一键入口：

`运行HT-CN便携复盘工作区.bat`

## 7. 安全边界

Phase 15 v1 是严格只读 Inspector。

明确禁止：

- 自动 import/merge；
- 写回 Operator Queue；
- 写回 Operator History；
- 写回 Review Journal；
- 创建 review event；
- 修改 M4 authoritative evidence；
- 根据 follow-up 调整 Queue 顺序；
- 根据历史 observation 生成胜率/alpha；
- 把 portable workspace 当成交易执行器。

未来若需要 import/merge，必须单独建立新 phase / versioned contract，并明确处理：

- source identity；
- conflict；
- idempotency；
- predecessor chain；
- local-vs-transport ownership。

不得在 Phase 15 v1 内偷偷增加写入。

## 8. Acceptance

Phase 15 v1 最低验收：

- [ ] valid v3 可构建 inspection model；
- [ ] invalid/tampered v3 在解析前 fail closed；
- [ ] current Queue 可离线浏览；
- [ ] current/previous history 可离线浏览；
- [ ] digest 可离线浏览；
- [ ] review-session / active follow-up 可离线浏览；
- [ ] instrument/display-key drill-down；
- [ ] 单文件中文 HTML；
- [ ] HTML 无网络 fetch、无 review write action；
- [ ] inspector 不访问 market database；
- [ ] Python regression green；
- [ ] existing Web build / Playwright gates 不回归；
- [ ] M4 methodology 0 drift；
- [ ] Outcome Engine 0 drift。

## 9. 后续候选

Phase 15 v1 完成后再评估：

- 更丰富的离线图形化 drill-down；
- transport 内 XABCD/PRZ/lifecycle mini-chart；
- explicit import/merge contract（独立 phase）；
- Git 主线 integration plan。

以上均不得阻塞当前只读 Inspector closeout。
