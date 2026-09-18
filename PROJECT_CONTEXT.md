# HT-CN Project Context — 跨对话权威状态

context_schema: `1`
context_checkpoint: `4922cca8c9dea41551d3cbeeb8e722eafbf2589f`
context_checkpoint_title: `M4 Phase 1: prospective real-A-share lifecycle journal baseline`
context_snapshot_date: `2026-09-18`
default_branch: `main`
repository: `shazhuya/HT-CN`

> 本文件用于恢复“项目现在到底做到哪里”。若本文件与当前 HEAD 冲突，必须先检查 `context_checkpoint..HEAD`，再继续开发。

## 当前阶段

正式 `main` 已合入 **M3 Source-Clock Lifecycle + A-share Context + Action-State Product Orchestration**。

- M3 merge commit：`edec5e21fb9e873daf8fb77fceaa0d89dbbd5b25`
- M3 PR：#12，已于 2026-09-18 合并
- 最终本机验收：current-head READY（known warnings only），hard blocker = 0
- 当前开发分支：`m4/real-a-share-validation-workflow`

M4 当前原则：

**先建立从真实当前交易日开始的 prospective、append-only、no-backfill 生命周期证据，再讨论统计规律、机会排序或执行优先级。**

M3 的 source-clock 规则继续作为不可回退基线：

**live/current state 必须由可观察的 Source execution clock 驱动；historical D/C / reaction audit 只保留诊断兼容。**

## 正式 main 基线 — M3

M3 已正式合入 `main`，冻结以下产品基线：

- canonical Source lifecycle；
- Source-first chart overlay；
- A 股 execution context；
- 科创50 / 创业板指 / 沪深300 / 上证指数 market context；
- 行业 / 概念分层相对强弱；
- context integrity；
- Decision Narrative；
- execution feasibility gate；
- product payload contract；
- real-M1 metadata/product smoke；
- local API / Workbench / Playwright 正式验收；
- merge-readiness anti-false-green chain。

M3 最终 READY 只代表代码与真实 M1 验收满足主线合并条件，不代表 alpha / 胜率证明。

固定边界继续保持：

- 5-0 production quarantine；
- Alternate Bat fail-closed；
- BSE deferred；
- daily-event positive-evidence-only 仍需显式标示。

## M4 Phase 1 — Prospective Lifecycle Journal

M4 第一阶段不做历史回填式“验证”，而是从当前真实已收盘交易日起建立 append-only 日志。

已完成：

- 稳定 candidate key：使用 pattern anchor 的 **trade_date**，不使用 rolling-window bar index；
- XABCD key 使用 X/A/B/C；
- standalone AB=CD 使用 A/B/C；
- Shark 0XABC 使用 0/X/A/B，不发明 C/D；
- 5-0 不进入 M4 production validation journal；
- journal entry 保留 source lifecycle、action state、next key price/role、execution gate、Source Raw PRZ 与 context integrity；
- 同 code_head / as-of / candidate key 重复运行保持幂等；
- 默认禁止 incoming as-of 早于既有 journal max date，历史 backfill fail closed；
- 一键入口：`运行M4真实A股生命周期快照.bat`；
- 全体 initialized listed SSE/SZSE 必须对齐同一 closed trade date；任一分析失败则本轮不追加 journal。

当前 M4 证据仍是 observability / lifecycle evolution evidence，`alpha_inference_allowed=false`。

## Source Fidelity before M3 expansion

该 gate 名称作为跨对话连续性哨兵永久保留。其含义是：M3 产品扩展不得越过已冻结的 M2.31 Source Fidelity、Source Raw PRZ、Source Terminal Price Bar、5-0 quarantine 与 Alternate Bat fail-closed 边界。

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


## M3 Phase 3.3 — Industry / Relative-Strength Context

已建立证券→行业→核心指数的分层证据链。

行业映射：

- 来源：AKShare / Eastmoney `stock_board_industry_name_em` + `stock_board_industry_cons_em`；
- 全量刷新采用 **all-or-nothing 原子替换**；
- 任一行业成分抓取失败时，旧完整映射保留；
- 同一来源一只证券出现多个行业时返回 `membership_ambiguous`，禁止自动挑选。

行业强弱不是直接使用外部行业指数，而是基于本地 M1 成分股重算：

- 1 / 5 / 20 交易日成分股复合收益；
- 等权均值 + 中位数；
- MA20 上方占比；
- 当日上涨 / 下跌广度；
- 成分股 20 日平均量比；
- 个股相对行业中位数的 5 / 20 日超额强弱。

兼容性：

- `pct_change` 存在时优先按本地日涨跌幅复利；
- 旧库/异构数据缺少 `pct_change` 时退回本地 close-to-close；
- 停牌交易日按价格不变处理；
- 普通分析读路径不得创建 DuckDB 表或 benchmark 目录。

工作台已挂载 **行业环境与分层相对强弱** card；浏览器门禁 `sector-context.spec.ts` 已加入 CI 命令。

同步入口：`运行M3行业环境同步.bat`。默认行业映射七天内复用缓存，只重算本地行业快照，避免每天大量联网请求。

固定边界：行业层 `owns_lifecycle=false`，`mutates_harmonic_identity=false`，`mutates_source_raw_prz=false`。


## M3 Phase 3.4 — Concept / Theme Context

概念/题材与行业采用不同语义：

- 概念天然多对多；一只股票属于多个概念是正常状态，不标 ambiguous；
- 来源：AKShare / Eastmoney `stock_board_concept_name_em` + `stock_board_concept_cons_em`；
- 周级 membership 刷新使用有界并发，默认 8 workers、每概念重试；
- 全量抓取全部成功后才原子替换旧映射；任一概念失败保留旧完整映射；
- 概念强弱/广度/量能继续只由本地 M1 成分股重算；
- 工作台默认展开最多 8 个概念，按透明的 5 日中位收益降序，不生成“题材评分”；
- 输出个股相对每个概念的 5 / 20 日强弱。

no-backdating：行业/概念 `mapping_observed_on > analysis.as_of` 时返回 `mapping_after_as_of`，禁止未来 membership 回填历史分析。

同步入口：`运行M3概念题材同步.bat`。

## M3 Phase 3.5 — Context Integrity / One-Click Sync

已新增非评分的 `context_integrity`：

- execution；
- market；
- industry；
- concept。

每层只报告：`current / partial / stale / missing / conflicted / future_observation / unresolved`，同时带 evidence date / source / coverage / reason。

规则：

- 四指数未全部对齐分析日 → partial / stale；
- 行业映射冲突 → conflicted；
- future membership → future_observation；
- 行业/概念 membership 默认超过 7 天未刷新 → stale；
- execution 特殊事件源仍不完整 → unresolved；
- 完整性总览 `is_score=false`，不生成投资评分或买卖信号。

一键入口：`运行M3上下文数据同步.bat`。

它连续同步：

1. 当日停牌正向证据；
2. 科创50 / 创业板指 / 沪深300 / 上证指数；
3. 行业 membership + 本地行业快照；
4. 概念 membership + 本地概念快照；

并输出 `artifacts/reports/m3-context-sync-summary.json`。某一层失败不会隐藏其他层已完成结果。

当前 AKShare 源码已核实行业/概念成分接口均接受 `BKxxxx` 板块代码。


## M3 Phase 4 — Action-State Narrative / Product Orchestration

Phase 4 已把 canonical Source lifecycle 组织成唯一实战导航，但仍不输出买卖指令或综合评分。

冻结四类 action state：

- `waiting`：等待 Source gate；
- `reaction_observation`：T-Bar 后 Type-I 反应观察；
- `execution_evaluation`：source lifecycle 已进入可做执行层评估的阶段；
- `evidence_insufficient`：Source PRZ / Source clock 等证据不足。

固定关系：

- action state 只由 `source_lifecycle.state` 决定；
- execution / market / industry / concept / BAMM 只能形成约束或注意项；
- context 再强也不能把 `waiting_terminal` 升级成 `execution_evaluation`；
- narrative 不拥有 lifecycle，不改 harmonic identity / Source Raw PRZ。

Decision Narrative 现在统一回答：

1. 现在在哪；
2. 先看什么；
3. 到了再看什么；
4. 什么条件不能升级；
5. 下一关键价和角色；
6. execution context gate；
7. 非 current context 注意项。

执行可行性与 lifecycle 分离：

- `tradable`；
- `blocked_suspended`；
- `tradability_unresolved`；
- `execution_unresolved / stale / missing / future_observation`。

例如 lifecycle 可以是 `type_i_confirmed -> execution_evaluation`，但当日停牌时 execution gate 明确显示 `blocked_suspended`，不把停牌错误写成 lifecycle 失败。

## M3 Phase 4.1 — Product Contract + Real M1 Acceptance

已新增 `htcn.app.product_contract`，逐 pattern 审计：

- narrative lifecycle state == canonical source lifecycle；
- action state 可由 lifecycle 确定性重建；
- next key price / role 一致；
- pattern execution context copy == top-level execution context；
- 非 current context 全部进入 narrative cautions；
- narrative 边界 flag 必须为 false；
- 5-0 保持 quarantine。

真实 M1 smoke：`scripts/m3_product_contract_smoke.py`。

正式 `运行M3工作台验收.bat` 已升级为：

1. 全量 Python regression；
2. TypeScript + Web build；
3. 真实 M1 metadata / tradability 严格只读 smoke；
4. 真实 M1 product contract smoke；
5. 本地 API + Workbench；
6. 全量 Playwright。

正式验收要求代表性 MAIN / STAR / CHINEXT parquet 可真实读取；早期迁移时期的 `security_master_pass_parquet_unavailable` 不再被正式验收接受。

联网行业/概念刷新仍独立运行 `运行M3上下文数据同步.bat`，不和确定性代码验收混在一起。

## M3 Phase 4.2 — UI Consolidation

正式 source-driven pattern 的 UI 已收敛：

- `DecisionNarrative` 是唯一“现在 / 先看 / 下一步 / 升级阻断”导航；
- `LifecycleCompass` 在 source-driven 路径降级为紧凑 **Source Clock 证据条**；
- Source 证据条只显示 canonical state、PRZ/PEZ 边界、Signal、PRZ Entry、T-Bar、T+1、T1/T2、Type-II、BAMM；
- historical / retrospective compatibility 路径继续保留旧诊断 UI；
- A 股 execution card 已去重，顶层只显示一次。

selected-pattern browser gate 已冻结：从一个候选切换到另一个候选时，Decision Narrative 必须同步切换到该 pattern 自己的 source lifecycle / next key price，禁止残留前一个候选的状态。


## M3 Phase 4.4 — Acceptance Evidence / Real-M1 Closeout

验收不再依赖人工解释零散日志。当前正式证据链：

- `m3-workbench-acceptance.json`；
- `m3-metadata-tradability-smoke.json`；
- `m3-product-contract-smoke.json`；
- `m3-context-sync-summary.json`。

四份报告全部带 `code_head`；任何旧 commit 报告都是 hard blocker。

新增：

- `scripts/m3_pr_readiness.py`；
- `运行M3合并就绪检查.bat`；
- `运行M3最终收口.bat`；
- `m3-pr-readiness.json`；
- `m3-pr-readiness.md`。

Ready 判定区分 blocker / warning：

硬阻断包括 deterministic acceptance 失败、真实 MAIN/STAR/CHINEXT parquet 缺失、product contract issue、无成功真实分析、context 结构性 failure、证据来自旧 HEAD。

warning 包括 positive-evidence-only 停牌源、可 fail-safe 保留旧快照的 context degraded、真实小样本恰好没有谐波候选等。

`运行M3最终收口.bat` 一次执行：工作台严格验收 → 四层真实同步 → 当前 HEAD Ready/Not Ready。即使前一步失败，也继续生成最终 blocker 报告。

`m3_sync_all_contexts.py` 已修复成功状态名与退出码不一致问题；`all_steps_completed` 现在真实返回 0。


## M3 Phase 4.5 — Anti-False-Green Readiness Hardening

Phase 4.5 继续收紧“Ready”的证据含义，不新增谐波逻辑。

新增三层强绑定：

1. **同 commit**：所有正式验收报告继续要求 `code_head == current HEAD`；
2. **clean worktree**：报告生成时和最终 readiness 评估时都必须 `worktree_clean=true`，未提交源码/配置修改直接 hard blocker；
3. **同最新已收盘交易日**：provider-confirmed closed-trade clock、local `trade_calendar`、base+daily_delta 逻辑行情、metadata smoke 样本、product smoke 样本必须一致。

新增共享 `htcn.data.trading_clock.latest_closed_trade_clock`：

- 上海时钟 16:30 前只接受上一已收盘交易日；
- 16:30 后允许当日成为 target；
- 通过 provider trade calendar 处理周末/节假日，不用工作日猜测。

M1 日更现在会把 provider 确认的 target / previous trade day 写回本地 `trade_calendar`。

正式 metadata smoke 已从“只读 base parquet”改为 **base + daily_delta logical history**，避免增量架构本身造成假 stale。

Context sync 新增 `market_data_freshness`：

- `expected_trade_date`；
- `local_trade_calendar_latest`；
- `logical_market_latest`；
- initialized/current/stale/ahead dataset count；
- stale/ahead sample。

所有已初始化、仍上市 SSE/SZSE daily dataset 必须追到 expected trade date；任何 stale dataset 或 ahead-of-closed-clock dataset 都是 Ready hard blocker。

`运行M3最终收口.bat` 当前顺序：

1. M1 智能日更；
2. 严格工作台验收；
3. 四层 context 真实同步；
4. 当前 HEAD readiness 判定。

最终 READY 因而要求：代码身份正确、工作树干净、全市场本地日线新鲜、代表样本新鲜、产品 contract 通过、浏览器验收通过、context 无结构性 failure。


## M3 Phase 4.6 — Real-Run Blocker Fixes

用户本机首次运行 `运行M3最终收口.bat` 暴露出三类真实问题，已修复：

1. **Generated artifacts polluted clean-worktree evidence**
   - 真实日志中 `artifacts/` 作为 untracked 路径导致 QA 在 gate 1 前直接退出；
   - `.gitignore` 现加入 `artifacts/**`；
   - 生成的验收/Playwright/context/readiness 文件不再让 worktree 自己变脏。

2. **Windows CMD parser corruption**
   - 原最终收口 wrapper 的中文标题行在部分 Windows CMD 环境被误解析，出现 `'ase' is not recognized` / `'HEAD' is not recognized`；
   - `运行M3最终收口.bat` 控制行改为 ASCII-safe 文本；
   - 不影响 Python/报告中的中文优先产品规范。

3. **External context outage semantics**
   - 首次真实运行时 M1 已 55/55 更新到最新收盘日，market-data freshness 全部 current；
   - 外部 Eastmoney/AkShare 连接断开导致四指数、行业、概念拉取失败；
   - 规则现冻结为：
     - 本地 schema / DB / aggregate / program error → `failed` → hard blocker；
     - 可识别的 remote connection / timeout / proxy / SSL failure → `external_unavailable` → warning；
     - 有旧完整 mapping 时继续 fail-safe preserve；
     - 无旧 mapping 时明确 unavailable，不伪造 current evidence。

Context sync exit semantics 同步调整：

- `all_steps_completed` → exit 0；
- `degraded`（仅外部不可达 / fail-safe 降级）→ exit 0；
- `partial_failure`（本地结构性失败）→ non-zero。

Readiness 回归测试冻结：
`market=partial + industry/concept=external_unavailable` 可成为 READY-with-warnings；
`industry/concept=failed` 仍然 NOT READY。

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

**M4 Phase 1 — 生成第一份真实 prospective 生命周期快照并建立 transition baseline。**

执行顺序：

1. 用户本机切换到 `m4/real-a-share-validation-workflow`；
2. 运行 `运行M4真实A股生命周期快照.bat`；
3. 核查全部 initialized SSE/SZSE 是否同一最新交易日、零失败；
4. 将第一日 journal 作为 prospective T0，不做历史补录；
5. 第二个真实交易日开始，建立 candidate lifecycle transition 对比；
6. 在至少积累若干真实交易日之前，不把状态频数解释成胜率/alpha。


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
