# HT-CN Project Context — 跨对话权威状态

context_schema: `1`
context_checkpoint: `0effcaffd033d5398ffa0e0b09ab67188a958e58`
context_checkpoint_title: `M3 Phase 3.2: event ingestion, real execution UI wiring, core benchmark market context`
context_snapshot_date: `2026-09-18`
default_branch: `main`
repository: `shazhuya/HT-CN`

> 本文件用于恢复“项目现在到底做到哪里”。若本文件与当前 HEAD 冲突，必须先检查 `context_checkpoint..HEAD`，再继续开发。

## 当前阶段

正式 `main` 已冻结 **M2.31 Source Fidelity / RSI BAMM Source Terminal Price Bar closeout**。当前开发分支为 `m3/source-clock-lifecycle-migration`，Draft PR #12 正在推进 M3 产品迁移。

M3 当前原则：

**live/current state 必须由可观察的 Source execution clock 驱动；historical D/C / reaction audit 只保留诊断兼容。**

## 正式 main 基线 — M2.31

M2.31 已完成并正式合入 `main`：

- dedicated no-lookahead RSI BAMM state machine；
- Volume Two Trigger / midpoint / X-A Confirmation Point / 1.13 vs 1.618；
- Volume Three Simple/Complex × Confirmation/Divergence 四类 profile；
- completed confluence 绑定 observable Source Terminal Price Bar，而不是 historical D/C；
- PEZ overspill 合法且不修改 Source Raw PRZ；
- evidence available time = `max(Source T-Bar, BAMM completion)`，禁止 backdate；
- Golden Ledger + machine-readable Source Truth 已更新；
- 5-0 quarantine / Alternate Bat fail-closed 保持。

M2.31 冻结验证：GitHub Actions run #643 / `35209013814`，validated commit `0c7799391bc92af46a2b249892dc24e06a6143a0`，45 股全链通过。

正式 observability：

- 45 / 45 symbols；
- 686 complete BAMM sequences；
- 174 completed source-scannable harmonic matches；
- 128 source-clock observable；
- 23 observed Source Terminal Price Bars；
- 2 strict source-confirmed BAMM confluences；
- `confirmatory_inference_allowed=false`，不得写成 alpha / 胜率结论。

M2.31 merge commit：`fbf964fb2230df2dd21138d2d99f037d3b5a382f`。

## M3 Phase 1 — Canonical Source Lifecycle

已实现 canonical `SourceLifecycleState / SourceLifecycleSnapshot`：

`source_clock_unavailable -> source_prz_unresolved -> approaching_source_prz -> entered_source_prz -> waiting_terminal -> source_terminal_complete -> t_plus_1 -> type_i_early_reaction -> type_i_confirmed / type_i_failed / reaction_only -> type_ii_retest_forming -> type_ii_terminal -> reversal_evidence`

`invalidated` 仅保留 vocabulary；当前没有为了填状态而发明新的 Carney source invalidation rule。

核心冻结：

- forming/current lifecycle 使用 observable forming signal / frozen Source PRZ / Source T-Bar；
- completed match 先从 pre-terminal observable state 重建 Source T-Bar；不可重建则 `source_clock_unavailable`，禁止退回 D-clock 冒充 live state；
- Type-I 38.2% in first 5 bars 是 HT-CN execution-state operationalization，不是 identity rule / alpha claim；
- Type-II 生产路径继续 strict full Raw PRZ terminal-side retest；
- BAMM / Wilder RSI / 市场环境只能作为 evidence/context，不拥有 lifecycle。

独立 prefix validation 已验证：

`approaching -> entered -> waiting_terminal -> source_terminal_complete -> t_plus_1 -> type_i_confirmed -> type_ii_retest_forming -> type_ii_terminal -> reversal_evidence`

并验证未来 Type-II/reversal state 不会回填较早 prefix。

## M3 Phase 2 — Source-Clock Chart Overlay

已实现 K 线图 source-first 可视化：

- Source Raw PRZ；
- PEZ；
- Source T-Bar；
- T-Bar+1；
- Source Type-I 38.2% / 61.8% targets；
- Type-II re-entry；
- Type-II Terminal；
- Type-II 后 reversal-direction exit。

source lifecycle 存在时，T1/T2 overlay 标记 `data-clock=source`；旧 retrospective D-clock target 仅作为弱化 fallback。

Playwright source-overlay regression 已加入，但 GitHub-hosted runner 当前未真正执行。

## M3 Phase 3 — A 股 Execution Context

已新增独立 `a_share_execution_context`，输出到 analysis 顶层并复制到 pattern payload 供工作台展示。

当前字段：

- board / listing date / ST metadata availability；
- T+1、same-day sell-after-buy=false；
- board nominal price-limit profile；
- metadata 足够时的 `rule_based_price_limit_pct`；
- `price_limit_status` / `special_event_exceptions_unresolved`；
- IPO first-five-trading-session exception；
- 2026-07-06 主板风险警示规则历史切换；
- ATR(14) / ATR%；
- latest high-low range %；
- prior-20-session average volume / volume ratio；
- BSE deferred；
- `mutates_harmonic_identity=false`；
- `mutates_source_raw_prz=false`。

关键决定：不创建黑箱“综合可交易性分数”；元数据不足时 fail-safe，不猜 ST / IPO；特殊事件元数据未完整接入时不使用 `exact_price_limit_pct` 语义。

工作台已新增 **A 股执行约束与波动背景** card，与 lifecycle 分栏显示。


## M3 Phase 3.1 第二批 — 自动交易事件证据

已把 daily-event contract 推进为自动采集链：

- AKShare `stock_tfp_em` 只作为 **positive suspension evidence**；
- 连续/全天停牌写入 `suspended`，盘中停牌单独写入 `intraday_suspended`；
- 即使上游返回历史旧记录，也按目标交易日重新过滤；
- 空结果绝不合成 `normal`；
- 所有该源记录保持 `resolution_complete=false`；
- `security_daily_event_sync` 记录 success/failure、条数与 `positive_evidence_only` coverage；
- 已有 `resolution_complete=true` 的完整记录不能被后来 partial feed 降级覆盖；
- M1 日更在价格 fast-pass 之前同步事件，事件源失败不阻塞行情更新；
- 独立入口：`运行M3交易事件同步.bat`。

百度停复牌接口存在长期空结果问题，因此当前不作为“完整事件覆盖”第二源，避免虚假解除 fail-safe。

## M3 Phase 3 UI 纠错

发现并修复两层断链：

1. `AShareExecutionContext.tsx` 已存在，但此前 `App.tsx` 未真正挂载；
2. `execution-context.spec.ts` 已存在，但 CI Playwright 命令此前未执行它。

现已正式挂载执行约束卡，并纳入浏览器验收。以后不得再以“文件存在”替代“产品已接通”的完成判定。

## M3 Phase 3.2 — Core Market Context

已新增四大固定基准的本地 evidence 层：

- 科创50：`000688`
- 创业板指：`399006`
- 沪深300：`000300`
- 上证指数：`000001`

输出字段以原始可审计指标为主：

- 1 / 5 / 20 日涨跌幅；
- MA20 距离；
- MA20 五日斜率；
- 简单描述性状态（上方且抬升 / 下方且下行 / 混合 / 历史不足）；
- 个股相对各基准的 5 / 20 日相对强弱。

明确不创建市场综合分数。市场层 `owns_lifecycle=false`，不得修改 harmonic identity 或 Source Raw PRZ。

本地同步入口：`运行M3核心指数同步.bat`。指数数据未同步或源失败时，个股分析继续运行，market context 返回 `unavailable/partial`。

## 当前 CI 基础设施异常

M2.31 后期至当前 M3，GitHub-hosted Actions 出现仓库/平台级调度异常：

- deterministic job 在 runner allocation 之前立即 failure；
- `runner_id=0`；
- zero steps；
- no log blob；
- 同一现象发生在 docs-only、main merge 与 M3 commits，故不能解释为当前 Python/Web 逻辑失败。

开发策略：**不等待、不反复 rerun**。继续做 targeted local checks；仅在有意义的 batch 后查询一次 Actions。恢复后再执行完整 Python/Web/Playwright gate。

## 当前仍未完全解决

- GitHub-hosted full Python / Web / Playwright 尚未恢复真实执行；
- Phase 3 `security_master` 需要在用户已建立的真实 M1 catalog 上做 metadata read smoke test；
- 停复牌、恢复上市、特殊证券等 event metadata 尚未进入精确 daily price-limit resolution，因此保持 `special_event_exceptions_unresolved=true`；
- 5-0 V3 label conflict 未解决，production quarantine 继续；
- Alternate Bat Source Raw PRZ conflict 继续 fail closed；
- standard XABCD per-pattern AB=CD hard-gate refinement 仍可后续 source-backed refinement，但当前不应打断 M3 lifecycle 产品迁移；
- BSE 继续 deferred。

## 下一步唯一主任务

**M3 Phase 3.3 — Sector / Relative-Strength Context。**

执行顺序：

1. 建立证券到行业/概念的可审计映射，不用黑箱标签替代原始来源；
2. 优先接行业/板块相对强弱与量价环境，不把板块强弱用于“救活”失败谐波；
3. 建立个股 vs. 行业 vs. 双创/沪深300的分层相对强弱；
4. 保持市场/行业 context 只做 evidence，不拥有 lifecycle；
5. GitHub-hosted runner 恢复后一次性跑 Python/Web/Playwright 全门禁，不反复 rerun 空 runner。


## 固定 Source / Product 边界

1. Carney Volume One / Two / Three 是 harmonic identity、source measurement、Reaction vs. Reversal 理论基准。
2. geometry clock 与 source execution clock 永久分离。
3. component envelope / Ideal Core / Source Raw PRZ / Terminal extreme / PEZ 永久分层。
4. Identity 不能被 score、统计、A 股环境或 UI“救活”。
5. BAMM 是 evidence-only。
6. A 股 execution context 不拥有 lifecycle，不改 identity / Source Raw PRZ。
7. 已冻结 Holdout / external replication / historical closed result 不回写。
8. 5-0 quarantine 保持；Alternate Bat fail closed。
9. 中文优先；内部 enum/API identifier 稳定英文。
10. 默认市场 SSE/SZSE；BSE 暂不处理。
11. HT-CN 只做研究与辅助决策，不执行交易。

## 当前验收入口

- M2 综合验收：`运行M2综合验收.bat`
- M3 工作台验收：`运行M3工作台验收.bat`
- 前瞻 Type-I 登记：`运行M2前瞻Type-I登记.bat`（独立持续研究流程，普通 acceptance 不得修改）

## 新会话恢复必须核对

- `main` 当前正式 release 是否仍为 M2.31 或已有后续 merge；
- `m3/source-clock-lifecycle-migration` HEAD 与本 `context_checkpoint` 差异；
- PR #12 当前状态；
- Actions runner 是否恢复真正执行；
- `specs/m3-source-clock-lifecycle-migration.md` 与当前代码是否一致；
- execution context 是否已经完成真实 M1 catalog smoke test。

完成上述检查后，才能宣称“已恢复 HT-CN 当前现场”。
