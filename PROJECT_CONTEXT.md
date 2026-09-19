# HT-CN Project Context — 跨对话权威状态

context_schema: `1`
context_checkpoint: `c9de28d959b64043663a2bceccb17cc87b8f3756`
context_checkpoint_title: `M5 Phase 14 Daily Handoff Bundle v3 green`
context_snapshot_date: `2026-09-19`
default_branch: `main`
repository: `shazhuya/HT-CN`

> 本文件用于恢复“项目现在到底做到哪里”。若本文件与当前 HEAD 冲突，必须先检查 `context_checkpoint..HEAD`，再继续开发。

## 当前阶段

正式 `main` 仍以 **M3 Source-Clock Lifecycle + A-share Context + Action-State Product Orchestration** 为已合并基线；M4 prospective evidence 与 M5 只读产品层继续在独立分支演进。

当前实际开发现场已经完成 **M5 Phase 14 — Daily Handoff Bundle v3 / Review-State Transport**：

- 当前分支：`m5/daily-handoff-bundle-v3`
- Phase 14 validated code checkpoint：`c9de28d959b64043663a2bceccb17cc87b8f3756`
- hosted CI：run `35416336734` / #1790，overall success
- Python：774 passed
- Web build：success
- Playwright：24 passed
- browser evidence upload：success
- Phase-10 handoff v2 changed files：0
- M4 capture methodology drift：0 / 37
- Outcome Engine drift：0 / 4

M5 Phase 1–14 当前主线：

1. Daily Operator Queue；
2. Operator Delta / 今日变化；
3. Daily Operator Cache；
4. Full-Universe Operator Index；
5. bounded parallel build；
6. process-local single-flight；
7. cache input identity（数据 + 分析代码身份）；
8. filesystem advisory cache-slot lock；
9. Daily Close Product Pipeline；
10. Daily Handoff Bundle v2；
11. append-only Daily Operator History / Change Journal；
12. Daily Review Digest / Change Triage；
13. Review Session / Follow-up Journal；
14. Daily Handoff Bundle v3：以冻结 v2 为嵌套基础，把 current history、review digest、review-session snapshot 与其引用的 journal event closure 绑定成新的可离线验证 transport。

M5 仍是**只读实战产品层 + 人工复盘工作流 + transport 层**，不拥有 harmonic identity、Source Raw PRZ、canonical lifecycle 或 action state，不写 M4 authoritative evidence，不使用 win rate / alpha / predictive score 进行排序。Phase 14 只运输这些状态，不改变它们的语义。

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

## M4 Phase 1.6 — T0 Baseline Audit

用户上传的真实 T0 snapshot/journal 已由 assistant 离线完整审计，不要求用户重复运行。

真实 T0：

- trade date：2026-09-17；
- initialized instruments：55；
- successful：55；
- failed：0；
- candidates：87；
- candidate-bearing instruments：44；
- zero-candidate initialized instruments：11；
- unique candidate keys：87；
- hard blockers：0；
- warnings：6；
- `transition_ready=true`；
- `prospective_outcome_ready=false`。

候选结构：

- standalone AB=CD：56（64.4%）；
- Shark：15；
- Crab：7；
- Bat：4；
- Alternate Bat：4；
- Gartley：1；
- bullish：39；
- bearish：48；
- scale 3/5/8/13 = 25/14/18/30。

Lifecycle：

- approaching_source_prz：50；
- waiting_terminal：13；
- source_clock_unavailable：9；
- source_prz_unresolved：4；
- reversal_evidence：4；
- type_i_confirmed：3；
- type_i_failed：2；
- type_i_early_reaction：1；
- t_plus_1：1。

真实 warnings：

1. AB=CD 占 64.4%，总样本不能解释成 shape-balanced；
2. 87/87 execution gate 为 `execution_unresolved`；
3. 87/87 context integrity 为 `issues_present`；
4. 4 个 Alternate Bat 仅作为 fail-closed observability evidence；
5. 11 个 T0 候选已存在 Source Terminal 历史，其中 5 个超过 20 天，最老 583 天；
6. 13 个候选存在 Source observability gap（9 source_clock_unavailable + 4 source_prz_unresolved）。

内部一致性审计全部通过：

- lifecycle -> action state：0 mismatch；
- lifecycle -> next-key role：0 mismatch；
- Source PRZ contract：0 error；
- Source Terminal date contract：0 error；
- 5-0 / Alternate Bat / alpha / trade-instruction boundary：0 violation；
- snapshot 与 journal 的 head/date/count/lifecycle/action/schema 完全一致。

M4 outcome enrollment 已由 D-024 收紧：
`prospective_new` 不自动 outcome-eligible；必须在 terminal 前、forming、Source PRZ resolved 且不触碰冻结 source-fidelity 边界。

## M4 Phase 2 — Transition / Observation Protocol

M4 Phase 2 已建立不依赖 outcome 评分的事实观察层。

### Raw market facts

未来 journal row 新增：

- as_of_open；
- as_of_high；
- as_of_low；
- as_of_close；
- as_of_volume。

旧 T0 不回填、不重跑；raw market facts 从未来 snapshot 自然开始。

### Prospective observation

对 D-024 严格入组的 outcome cohort，按**实际 capture snapshot**生成：

- captured_snapshot_index；
- scanner present / absent；
- consecutive_absent_snapshots；
- lifecycle / action；
- execution/context；
- next-key price/role；
- Source Terminal trade date；
- raw OHLC/volume；
- first lifecycle-state observation；
- first scanner absence / reappearance。

固定边界：

- 不把 captured_snapshot_index 当完整交易日序号；
- scanner absent 不等于 invalidated；
- Source Terminal 早于 outcome enrollment 直接 fail closed；
- 不计算 return / profit / win rate / alpha；
- 不定义盈利阈值或买卖评分。

### Snapshot manifest

D-025 冻结 manifest-authoritative capture chronology：

- candidate_count=0 的完整 capture 日也必须存在；
- manifest 激活后 journal 日期必须有 manifest；
- journal/manifest 同日 code_head 与 candidate_count 必须一致；
- legacy T0 可在 manifest 激活前保留；
- transition/observation 统一使用同一 capture timeline resolver。

## M4 Phase 2.5 — Atomic Capture Transactions

D-026 已冻结。

未来 capture 正式证据链：

```
frozen legacy T0 baseline
        +
immutable committed capture transactions
        ↓
authoritative transition / observation view
```

兼容镜像：

- `lifecycle_journal.jsonl`
- `snapshot_manifest.jsonl`

只用于兼容/人工检查，不再是 transaction 激活后的权威下游输入。

核心规则：

- deterministic transaction ID 不含 wall-clock capture time；
- candidate rows 在 transaction identity 中 canonical-sort；
- committed JSON 单文件 temp + fsync + os.replace；
- .tmp 不读取；
- first future transaction 前冻结旧 T0；
- future transaction 必须晚于 frozen T0 cutoff；
- transaction dates append-only / no backfill；
- same-date fact drift fail closed；
- same facts rerun idempotent；
- transaction file / row-id tamper fail closed；
- full instrument coverage required；
- downstream reports 在 transaction 存在时不读取 live compatibility mirrors。

Assistant-side executable validation 已完成：

- core transaction module compile / execution smoke：PASS；
- same facts + different capture time：PASS；
- frozen baseline immutable/idempotent：PASS；
- T0 overwrite rejection：PASS；
- T1 commit + rerun：PASS；
- T2 commit：PASS；
- T2 后历史 T1 backfill rejection：PASS；
- temp partial ignored：PASS。

GitHub-hosted Actions 仍为 runner-allocation anomaly：最新 run #914 deterministic-tests 为 steps=null / logs=null，因此不计入通过或失败证据。

## M4 Phase 2.6 — Mirror Recovery / T0 Closeout

Compatibility mirrors are now explicitly non-authoritative and self-healing.

Implemented:

- transaction ID stamped into future lifecycle journal mirror rows；
- transaction ID stamped into future snapshot manifest mirror rows；
- post-capture mirror integrity inspection；
- corrupt/missing/drift mirror can be rebuilt from frozen baseline + committed transactions；
- repair uses atomic temp + fsync + os.replace；
- repair never mutates committed transaction files；
- transaction store inactive => repair no-op，避免误改 legacy-only T0。

Assistant-side recovery execution:

- journal corrupt + manifest corrupt -> rebuilt：PASS；
- both mirrors missing -> rebuilt：PASS；
- authoritative evidence remains unchanged：PASS。

真实上传 T0 在当前 Phase 2.6 规则下重新计算：

- baseline audit = pass_with_warnings；
- blocker = 0；
- warning = 6；
- transition_ready = true；
- prospective_outcome_ready = false；
- transition = baseline_only；
- baseline_existing = 87；
- prospective_new = 0；
- prospective_outcome_eligible = 0；
- prospective observation status = no_outcome_cohort；
- observation rows = 0；
- 55/55 instruments successful；
- 44 candidate-bearing instruments / 11 zero-candidate instruments；
- Source Terminal already observed = 11；
- oldest Source Terminal age = 583 calendar days。

Testing evidence boundary:

- assistant container executed transaction / chronology / mirror-recovery synthetic scenarios：PASS；
- full private-repo pytest NOT claimed，because assistant container has no GitHub private-repo credential；
- GitHub-hosted CI run #914 still has deterministic-tests steps=null / logs=null，so runner did not execute tests。

## M4 Phase 2.7 — Closed-Day / Suspension Correctness

Prospective capture 时间与无交易日语义已进一步 fail-closed。

### Provider-backed closed day

M4 authoritative capture 复用 M3 `latest_closed_trade_clock`：

- AkShare → Sina → BaoStock failover；
- provider-confirmed latest closed trade day 必须等于本地 M1 trade_calendar latest；
- 每只正常交易标的 analysis last_trade_date 必须等于该日期；
- provider clock unavailable 不猜日期，authoritative capture fail closed；
- `--max-symbols` 只允许 diagnostic，不产生 transaction/journal/manifest。

### Confirmed full-day suspension — D-027

只有本地 `security_daily_event` 中目标日明确存在 `trading_status='suspended'` 的 positive evidence 才允许 stale-bar carry-forward。

carry-forward row：

- candidate = present；
- as_of = capture date；
- underlying_last_trade_date = 最后真实 K 线日期；
- market_observation_status = confirmed_full_day_suspended；
- execution gate = blocked_suspended；
- OHLC/volume = null；
- event source/reason 显式保存。

固定排除：

- intraday_suspended 不豁免当日 bar；
- unknown stale 不豁免；
- suspended event + current-day bar = evidence conflict；
- suspended first observation 不允许首次 prospective outcome enrollment；
- 已入组 candidate 在停牌日继续保留 cohort。

## M4 Phase 2.8 — Deterministic Methodology Identity

D-028 已冻结：未来 authoritative prospective evidence 必须绑定确定性的 methodology identity。

已完成：

- capture transaction schema 从 v1 升到 v2；
- 每个新 committed capture 保存 `methodology_contract_version` / `methodology_fingerprint`；
- methodology fingerprint 进入 transaction identity；
- fingerprint 覆盖 candidate / ratios / Source PRZ / Source lifecycle / RSI BAMM / Shark / 5-0 source handling / M4 capture-enrollment 关键文件；
- 同一个 active committed chain 只允许一个 methodology fingerprint；
- 方法漂移 append fail closed；
- pre-fingerprint schema-v1 transaction 保持可读，但只能进入显式 migration 审计，不能和 v2 active chain 静默混合；
- evidence-health 比较 current methodology 与 authoritative chain，mismatch 为 hard blocker；
- compatibility manifest 与 mirror-integrity 纳入 methodology identity；
- transition / prospective-observation derived reports 暴露 authoritative fingerprint；
- frozen T0 baseline 不回写 fingerprint，继续仅作为 baseline / continuity evidence，且永久不进入 prospective outcome inference。

当前 GitHub-hosted CI 状态仍是 runner-allocation anomaly：最新 push / PR deterministic-tests `steps=null`，没有真实执行 pytest，不能计为代码测试失败或通过。

## M4 Phase 2 Closeout

Phase 2 evidence-integrity closeout 已冻结：`specs/m4-phase-2-closeout.md`。

当前定性：

- authoritative evidence 已完成 atomic transaction / frozen baseline / no-backfill / tamper guard；
- transition / observation chronology 已完成；
- confirmed full-day suspension continuity 已完成；
- D-024 strict prospective outcome enrollment 已完成；
- D-028 methodology provenance schema v2 已完成；
- methodology component tree 静态审计：37 / 37 路径存在；
- production capture 与已修改 research fixtures 均已传入 methodology identity；
- schema-v1 只保留 migration readability，不能静默续接 schema-v2；
- Phase 2 现在是 **structurally ready for first fingerprinted future capture**；
- `运行M4真实A股生命周期快照.bat` 已收敛为一次运行完成 M1 智能日更 → capture → health → transition → observation → evidence bundle；
- M1 日更失败时禁止尝试新 authoritative capture，防止 stale market data 进入 T1；
- M1 更新日志自动进入 evidence bundle；
- 单一交接文件：`artifacts/reports/m4-evidence-bundle.zip`；
- bundle 只是运输层；即使 authoritative evidence 损坏也原样打包诊断，不会修复/改写权威证据；
- 该 ready 只指证据架构，不是 alpha / 胜率 / 盈利验证。

仍开放的外部 gate：

1. GitHub-hosted deterministic job 必须出现真实 steps/logs；当前 runner 仍在 steps=null 阶段终止；
2. 用户私有 M1 数据产生首个 post-T0 fingerprinted future capture；
3. 真正出现至少一个 strict prospective_outcome_eligible candidate；
4. 在任何 return / MFE / MAE / win-rate / alpha 统计前，另行冻结 future outcome protocol。









## M4 Phase 2.12 — Frozen Source-clock seed / D-035

在第一笔真实 T1 之前继续做 outcome 数据充分性审计，发现 scanner 消失前若还没有 Source Terminal，仅保存 future OHLC 仍不足以重建现有 Source execution clock。

当前正式 T1 协议升级为：

- committed capture schema：**v5**；
- prospective observation schema：**v4**；
- methodology contract：**v4**；
- fingerprint components：**37**；
- exact methodology freeze commit：`c774c54928c33361952bf1a612a8555633449625`；
- strict outcome enrollment 必须冻结四项 Source-clock seed：
  - `source_signal_trade_date`
  - `source_signal_clock_basis`
  - `source_reaction_anchor_label`
  - `source_reaction_anchor_price`
- signal clock basis 固定为 `last_frontier_pivot_confirmed_at=index+scale`；
- reaction anchor：Shark/0XABC 用 B，XABCD/ABCD 用 A；
- seed 四项要么全有、要么全无；partial seed 在 schema v5 hard fail；
- 缺 seed 的 candidate 可以作为普通 evidence 保存，但不能进入 strict prospective outcome cohort；
- enrollment candidate summary 冻结完整 `enrollment_source_clock_seed`；
- scanner 后续消失仍保持 absent，follow-up 不拥有 lifecycle，但 frozen seed + authoritative OHLC 允许未来重建 Source Terminal / Type-I / Type-II facts；
- D-034 price-basis 规则继续有效；basis drift 时仍禁止自动跨标尺 outcome 计算；
- 第一笔 post-T0 future committed capture 仍未产生，所以 methodology-v4 没有迁移或混合既有 future evidence。

D-034 的 v3 freeze 与 D-033 的 v2 freeze 都保留为历史 checkpoint，但当前唯一可用于第一笔 T1 的 exact freeze 是 D-035 / `c774c549...`。

## M4 Phase 2.11 — Price-basis provenance / D-034

第一笔真实 post-T0 future capture 之前，发现并修复价格标尺 provenance 缺口。

当前正式 T1 协议：

- committed capture schema：**v4**；
- methodology contract：**v3**；
- fingerprint components：**37**；
- exact methodology freeze commit：`2b0aa92d292410098d9678a3bfd3102f3df1ed4b`；
- formal prospective price mode 仅允许 `qfq / qfq_carry_forward`；
- raw fallback 只能诊断展示，`eligible_for_validation=false`，且 authoritative capture 整轮 fail closed；
- 每个正式 analysis / journal / follow-up 保存 `price_mode + price_basis_id`；
- `price_basis_id` 对 QFQ factor **change-point sequence** 做 SHA-256，同 factor 仅延长日期不会改变 ID；
- schema v4 journal / follow-up 缺 basis 直接 hard fail；
- prospective observation schema v3 冻结 enrollment basis，并记录后续 basis drift；
- basis drift 不自动重基准，不改 scanner/lifecycle，不计算跨 basis return / MFE / MAE；
- intake 在 drift 存在时输出 warning：
  `price_basis_drift_present_future_outcome_rebase_required`；
- 未来若计算跨 basis outcome，必须单独预注册 rebasing protocol。

D-033 的 v2 exact freeze 仍作为历史审计 checkpoint 保留，但在第一笔 T1 之前已被 D-034 显式 supersede。

## M4 pre-T1 exact methodology freeze — D-033

第一笔 T1 不能只依赖“HEAD 包含 methodology-v2 commit”。

历史 D-033 精确冻结（已被 D-034 supersede）：

- frozen methodology commit：`084ddf649e031e8169a761fd3b8578f73b31b5c2`；
- methodology contract：v2；
- component count：37；
- 一键私有采集在 M1 update 之前运行 `m4_methodology_freeze_guard.py`；
- guard 要求 37 个 methodology path 相对 frozen commit **零差异**；
- 任意 methodology component 改动都会在触碰私有 M1 前阻断；
- guard 结果写入 `artifacts/reports/m4-methodology-freeze-guard.json` 并进入 evidence bundle；
- 从 frozen commit 到当前审计点，37 个 methodology component 实际改动数 = 0。

非 methodology 的 intake / transport / tests / docs 可以继续维护；若要修改 37 个方法组件，必须显式开启新 methodology epoch，不得静默续接。

## M4 Phase 2.10 — Cohort follow-up / D-032

在第一笔 post-T0 fingerprinted committed capture 产生之前，M4 又修正了一个会污染未来 outcome 研究的 censoring 缺口：

**candidate 可以从 scanner 消失，但已正式入组 cohort 的证券市场路径不能因此消失。**

当前冻结：

- committed capture schema：**v3**；
- methodology contract：**v2**；
- fingerprint components：**37**；
- scanner-present candidate 继续写 `journal_rows`；
- 已 outcome-enrolled、但当前 scanner absent 的 candidate 写独立 `cohort_followup_rows`；
- follow-up 只记录真实 market observation，不拥有 harmonic lifecycle / action state / Source PRZ；
- schema v3 强制：
  `followup_keys == prior enrolled cohort - current scanner-present keys`；
- traded follow-up 必须保存当前日 OHLC/volume；
- confirmed full-day suspension follow-up 不允许伪造 OHLC；
- prospective observation 与 intake 已消费 follow-up market facts；
- intake 对 `normalized_rows / transitions / observations` 做完整 payload 重算对账；
- methodology v2 新增 fingerprint：
  `capture_transaction.py / cohort_followup.py / lifecycle_transitions.py / prospective_observations.py / snapshot_manifest.py`；
- T0 cutoff 仍为 `2026-09-17`，未被重写；
- 当前仍没有第一笔 post-T0 committed future capture，因此 methodology-v2 freeze 没有迁移或污染既有 future evidence。

Phase 2.10 仍不计算 return / MFE / MAE / win-rate / alpha。

## M4 Phase 2.9 — Evidence intake / D-031

收到 T1/Tn `m4-evidence-bundle.zip` 后，不能只相信 bundle manifest 或派生报告。

当前 intake 链：

1. transport integrity；
2. isolated authoritative extraction；
3. frozen baseline / committed transaction revalidation；
4. authoritative capture timeline rebuild；
5. transition recompute；
6. prospective observation recompute；
7. derived report full-payload cross-check（normalized_rows / transitions / observations）；
8. methodology / capture-count / latest-date / transaction-id / code-head provenance cross-check；
9. structured ready / ready_with_warnings / not_ready。

当前 T0 expected baseline cutoff：`2026-09-17`。

`evidence_health_blocked` 可以是运输完整的诊断 ZIP，但 intake 必须 `not_ready`。

缺失 derived report 可以从 authoritative evidence 重算并 warning；authoritative transaction 不依赖这些 report 才成立。

该层不进入 methodology fingerprint，不改变 harmonic / PRZ / Source lifecycle / enrollment 规则。

## M4 transport bundle integrity — D-030

- `m4-evidence-bundle.zip` 不是 authoritative evidence，只是运输层；
- 每个成员由 manifest 记录 size + SHA-256；
- duplicate / extra / unsafe-path / missing / size-SHA mismatch 均 fail closed；
- exporter 先验证临时 ZIP，再原子发布正式 ZIP，发布后再次验证；
- `evidence_health_blocked` 允许作为完整诊断包交接，但不会被解释为 evidence ready；
- 用户不需要额外运行 bundle QA；必要采集仍保持一个动作，assistant 收到 ZIP 后可独立复验。

## M4 T1 本机采集 preflight — D-029

在任何私有 M1 更新或 authoritative capture 之前，一键入口现在先验证：

- 当前分支必须为 `m4/real-a-share-validation-workflow`；
- HEAD 必须包含最低安全 checkpoint `c774c54928c33361952bf1a612a8555633449625`；
- detached / wrong branch / stale-or-diverged protocol 均 fail closed；
- worktree 必须 clean；
- preflight 失败时明确保证 **M1 update 和 authoritative capture 均未启动**。

该 preflight 只保护本机采集入口，不进入 methodology fingerprint，不改变 harmonic / Source PRZ / lifecycle / enrollment 语义。

## 本机调用规则 — D-023

用户电脑不是 HT-CN 常规测试环境。

- assistant 能完成的静态、单元、回归、浏览器、文件分析与统计全部自行完成；
- 用户本机只承担 assistant 无法访问的私有 M1 数据采集；
- 本地结果一经上传，后续由 assistant 接管；
- 不得因 assistant 自身迭代反复要求用户重跑完整 QA。

## 下一步唯一主任务

**生成并审计首个 post-T0 fingerprinted future capture（T1）。**

Phase 2 assistant-side 结构收口已完成。下一次用户本机参与只用于 assistant 无法访问的私有 M1 数据：

1. 更新本地项目到当前 M4 分支；
2. 在新的已收盘 A 股交易日运行一次 `运行M4真实A股生命周期快照.bat`；
3. 不做重复 QA，不要求人工截图；
4. 只需交给 assistant：`artifacts/reports/m4-evidence-bundle.zip`；
5. assistant 从 bundle 中审计 authoritative capture、evidence-health、methodology fingerprint、transition、prospective enrollment、suspension 与 mirror；
6. 若尚无 strict outcome-eligible candidate，则继续积累事实快照，不提前定义收益阈值或做 alpha 推断。


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

- `main` 是否仍包含 M3 merge `edec5e21...`，以及是否已有 M4 后续正式 merge；
- `m4/real-a-share-validation-workflow` HEAD 与本 `context_checkpoint` 的差异；
- PR #13 当前状态；
- Actions runner 是否恢复真实 `steps/logs`，不得把 runner_id=0 当代码失败；
- `specs/m4-phase-2-8-methodology-identity.md`、`m4-phase-2-9-evidence-intake.md`、`m4-phase-2-10-cohort-followup.md`、`m4-phase-2-11-price-basis-provenance.md`、`m4-phase-2-12-source-clock-seed.md` 与当前代码是否一致；
- 当前 authoritative schema / observation schema / methodology contract / fingerprint component count 是否仍为 v5 / v4 / v4 / 37；
- 是否已经产生第一笔 post-T0 authoritative capture；若有，必须先从 evidence bundle / transaction chain 恢复，不得猜测。

完成上述检查后，才能宣称“已恢复 HT-CN 当前现场”。

## M4 Phase 3.1 — Outcome evidence v2 / D-037

当前跨对话权威状态已经从 Phase 2 的“只积累生命周期证据”推进到 **Phase 3.1 outcome evidence implementation frozen, waiting for first real post-T0 future capture**。

三层 provenance 永久分离：

1. **Capture methodology**
   - contract v4；
   - committed capture schema v5；
   - prospective observation schema v4；
   - 37 components；
   - exact freeze commit：`c774c54928c33361952bf1a612a8555633449625`；
   - 从该 freeze 到本 checkpoint 的 37-component diff = **0**。

2. **Outcome protocol**
   - historical v1 保留、不改写；
   - active = `m4-outcome-v2`；
   - v2 SHA-256：
     `5822b302e11d197682dc4bb6d835fb0a3b2d62fc97f788c7a323ecda2770555b`；
   - v2 在第一笔真实 prospective outcome 前修正 MFE/MAE 为 zero-floor nonnegative magnitude。

3. **Outcome engine**
   - contract v1；
   - 4 components；
   - exact code anchor：
     `9cbc0d3d30ac5f0a87748a39788cbee04a44bcc8`；
   - 从该 anchor 到本 checkpoint 的 4-component diff = **0**；
   - 每个 outcome result / snapshot 绑定 engine fingerprint。

Phase 3.1 已完成：

- deterministic outcome evaluator；
- 复用 `observe_source_execution()` / `derive_source_lifecycle()`；
- Source Terminal / Type-I / Type-II price-structure facts；
- 5/10/20 traded-bar descriptive MFE/MAE；
- MFE/MAE 从 T+1 开始、不包含 Terminal bar；
- right-censoring；
- price-basis drift fail-safe；
- canonical `market_path_rows` + SHA-256；
- immutable outcome snapshot schema v2；
- same-date fact drift detection；
- historical outcome backfill rejection；
- protocol / capture methodology / outcome engine chain-identity consistency；
- bundle 携带 frozen protocol、outcome snapshots 与 engine-freeze provenance；
- intake 使用 frozen enrollment seed + bundled OHLCV path **离线重跑 evaluator**；
- semantic tamper 即使重新生成 snapshot ID / ZIP SHA 仍必须 fail closed；
- `m4_outcome_engine_freeze_guard.py` 在私有 M1 update 之前执行；
- one-click workflow 已扩展为：
  capture-methodology guard → outcome-engine guard → M1 update → capture → health → transition → observation → outcome-v2 → bundle；
- Phase 3.1 minimum-safe workflow checkpoint：
  `c34026755b3b8c491759eaacdb45376d4e1db485`。

仍然没有改变：

- 5-0 production quarantine；
- Alternate Bat fail-closed；
- BSE deferred；
- Type-II price structure 不能冒充完整 Carney indicator-confirmed reversal；
- Shark generic Type-I 不能冒充 Shark-specific management target；
- `alpha_inference_allowed=false`；
- outcome-v2 不定义 entry / stop / fees / execution P&L / win-loss / win rate / alpha / ranking。

### 当前真实证据状态

- frozen T0 cutoff：2026-09-17；
- T0 candidates：87；
- T0 prospective outcome eligible：0；
- **尚无 post-T0 real authoritative future capture**；
- **尚无真实 prospective-new outcome cohort**；
- **尚无真实 outcome snapshot**；
- 因此尚不能报告真实 MFE/MAE 分布、win rate、alpha 或盈利能力。

### 下一真实 gate

代码侧 pre-T1 架构的下一步不再是扩功能。

下一步是：

1. 核对 hosted CI 当前 runner 状态；
2. 保持 capture methodology 与 outcome engine exact freeze；
3. 在需要私有 M1 数据时，仅运行一次现有 `运行M4真实A股生命周期快照.bat`；
4. 将生成的单一 `m4-evidence-bundle.zip` 交回 assistant；
5. assistant intake 独立复验 capture + outcome evidence。

D-023 继续有效：用户电脑不是常规测试机，只承担不可替代的私有 M1 数据采集。

## M4 Phase 3.1 hosted-CI closeout — 2026-09-18

GitHub-hosted runner allocation has recovered. The prior `steps=null` infrastructure anomaly is no longer the current testing boundary.

Current validated code checkpoint:

`8833d1d78bc266fc26efff92bd0a89204cb5ec12`

GitHub Actions:

- workflow: `HT-CN CI`;
- run: **#1406** / id `35358993415`;
- overall conclusion: **success**;
- deterministic-tests job: **success**;
- Python: **590 passed**, 1162 warnings;
- Node 22 setup: pass;
- `npm ci`: pass, 0 vulnerabilities;
- Web build: pass;
- Playwright steps: intentionally skipped because current workflow only enables deterministic browser acceptance on `m3/*` and specified `m2/*` source branches; M4 did not satisfy that branch predicate;
- autonomous real-A-share research job: skipped by design because M4 push/PR does not satisfy the M2 `[research]` / workflow-dispatch condition.

The CI recovery also exposed real test failures in earlier runs; those were fixed without changing frozen methodology or outcome engine:

- run #1398: 4 failed / 586 passed;
- run #1404: 1 failed / 589 passed;
- run #1406: 590 passed.

Fixes were confined to stale test fixtures/assertions and transport/intake mapping:

- chronology backfill test isolated from cohort-followup semantics;
- wrapper assertion aligned to Phase 3.1 minimum-safe wording;
- manifest fixture now respects positive candidate-count/journal-row consistency;
- snapshot outcome protocol ID now maps to canonical bundle filename
  `m4-outcome-protocol-v2.json`.

Post-fix freeze audit remains:

- capture methodology: **0 / 37 changed** since
  `c774c54928c33361952bf1a612a8555633449625`;
- outcome engine: **0 / 4 changed** since
  `9cbc0d3d30ac5f0a87748a39788cbee04a44bcc8`.

PR #13 at this checkpoint:

- open;
- Draft;
- mergeable=true;
- mergeable_state=clean;
- review threads=0.

Draft remains intentional because **no first post-T0 private-M1 future capture exists yet**. Code-side Phase 3.1 is ready; empirical M4 acceptance still requires irreducibly private future evidence.

Next required real action is not another feature change. It is one clean run of:

`运行M4真实A股生命周期快照.bat`

on the user's private M1 checkout after updating to a HEAD containing the Phase 3.1 minimum-safe checkpoint. The single handoff artifact remains:

`artifacts/reports/m4-evidence-bundle.zip`

After that bundle is supplied, assistant-side intake must independently verify capture authority + prospective enrollment + outcome evidence. D-023 remains active: no routine user-PC QA.

## M4 T1 acquisition gate — D-038

第一次真实 post-T0 private-M1 capture 的本地 minimum-safe gate 已提升。

必须包含的 hosted-CI-green ancestor：

`d29870d3a2ef7b60dec4fd8f0dbef2d7a8f0b5a7`

wrapper/test implementation checkpoint：

`106c53da04dab0c3fcc9d03d6b2148106128ff77`

GitHub Actions run #1414 已验证该 wrapper gate 本身：

- Python deterministic tests：success；
- Node setup：success；
- web dependencies：success；
- Web build：success；
- M4 Playwright：按现有 M2/M3-only predicate 预期 skip。

freeze audit：

- capture methodology changed components：0 / 37；
- outcome engine changed components：0 / 4。

这意味着：

- 本地如果还停留在旧 checkout，脚本会在触碰 M1 前直接拒绝；
- 用户不需要手工判断“这个版本够不够新”；
- 这不是 methodology version bump；
- 这不是 Outcome Engine version bump；
- T1 真正剩下的唯一不可替代动作仍是 private-M1 one-click capture。

### 当前下一步

更新本地 `m4/real-a-share-validation-workflow` 到包含 D-038 gate 的最新版本，保持 worktree clean，然后仅运行一次：

`运行M4真实A股生命周期快照.bat`

成功后只需要保留/上传：

`artifacts/reports/m4-evidence-bundle.zip`

其余验收继续由 assistant 完成。

## M4 first private bundle diagnosis — D-039

用户首次成功上传 `m4-evidence-bundle.zip` 后，assistant-side 完成独立检查。

Bundle transport integrity：

- manifest listed members：12；
- SHA-256 mismatches：0；
- methodology freeze guard：`frozen_match`；
- outcome-engine freeze guard：`frozen_match`；
- worktree_clean=true。

真实 capture 结果：

- code head：`276de795cbbf13c33d7aca563e225b02ece5f0c0`；
- target closed trade date：2026-09-18；
- initialized instruments：55；
- M1 raw update：55 / 55 成功；
- bulk snapshot provider unavailable，自动转 slow-path repair；
- slow-path repair：55 / 55 成功；
- formal capture successful instruments：3；
- formal capture failed instruments：52；
- candidate rows calculated before fail-close：2；
- authoritative journal append：**未发生**；
- committed captures：0；
- outcome snapshots：0。

3 个成功标的：

- SSE.600519
- SSE.688256
- SZSE.300820

它们正好是历史 `m1_adjustment_pilot.py` 的 3 个 QFQ pilot。

52 个失败的统一根因：

`formal prospective capture requires QFQ price basis: mode=raw basis=raw`

因此这不是 harmonic scanner 故障，也不是 T1 evidence 失败，而是 **formal-QFQ acquisition provisioning 缺失**。

修复：

- 新增 `scripts/m4_prepare_qfq_universe.py`；
- one-click 顺序变为：
  M1 raw update → strict QFQ readiness → authoritative capture → health → transitions → observations → outcome-v2 → bundle；
- existing formal QFQ 直接复用；
- 缺失/破损 factors 使用 AkShare → BaoStock fallback 建立；
- per-symbol factor write 可续跑；
- 只有 55/55 formal QFQ ready 才能启动 authoritative capture；
- QFQ failure 不会写 authoritative T1；
- bundle 增加：
  - `m4-qfq-readiness.json`
  - `m4-qfq-readiness.log`。

GitHub Actions run #1431：

- overall success；
- Python tests success；
- Web build success。

Freeze audit：

- capture methodology drift：0 / 37；
- Outcome Engine drift：0 / 4。

### 当前下一步

用户只需要更新本地 M4 branch 后重新运行同一个 one-click BAT。

下一次首次 QFQ expansion 可能需要对约 52 个缺 factor 标的进行网络拉取，因此会比普通日更慢；这是一次性/resumable 工作。完成后后续已有 formal-ready 标的不会重复抓取。

仍然不需要用户手工运行 `m2_qfq_expand.py`、pytest 或其他脚本。

## M4 second private bundle — D-040

第二个 `m4-evidence-bundle.zip` 已完成 assistant-side audit。

Transport：

- ZIP members：15；
- manifest-listed members：14；
- size/SHA-256 mismatches：0；
- worktree_clean=true。

QFQ readiness：

- initialized：55；
- already formal-ready：3；
- newly built/repaired：50；
- formal-ready after：53；
- failed：2；
- provider builds：BaoStock QFQ 50。

仅剩失败：

- `SSE.600057`：BaoStock adjusted history 缺 2007-04-24；
- `SZSE.000001`：BaoStock adjusted history 缺若干 1991 historical Saturday sessions；
- AkShare 对两只仍 RemoteDisconnected。

因此 authoritative capture 在 QFQ stage 后被阻断：

- committed_capture_count=0；
- outcome_snapshot_count=0；
- transition 仍为 2026-09-17 T0 baseline-only；
- prospective_outcome_cohort=0。

注意：bundle 中的 `m4-lifecycle-snapshot.json` 是上一次 failed capture 的旧诊断 artifact；本轮 QFQ stage 在 capture 之前停止，所以没有新 lifecycle snapshot。这不构成 authoritative evidence。

D-040 修复：

- tiny internal provider-calendar factor gaps 可在稳定 factor regime 下安全补齐；
- gap <=10 raw sessions；
- bracketing factor relative drift <=0.5%；
- 超阈值继续 fail closed；
- leading gaps 不补；
- trailing gap 仍由 qfq_carry_forward 管；
- synthetic rows 可审计标注 source。

GitHub Actions run #1446：

- overall success；
- Python success；
- Web build success。

Freeze audit：

- capture methodology：0/37 drift；
- Outcome Engine：0/4 drift。

下一次本地运行预计只需要重新处理剩余 2 个缺 factor 标的；已完成的 53 个会直接 READY，不重复整批下载。

## M4 third private bundle — D-041

Latest bundle audit:
- formal QFQ ready: 54/55;
- newly repaired in that run: SSE.600057;
- only remaining blocked instrument: SZSE.000001;
- remaining missing provider-calendar sessions are all 1991 Saturdays;
- committed_capture_count=0;
- outcome_snapshot_count=0;
- no authoritative T1 was written.

D-041 adds a separate early-Saturday compatibility path that requires raw pre-close continuity on both sides before any repair. It does not relax the generic 0.5% factor-regime rule.

Validation:
- GitHub Actions run #1459: success;
- capture methodology drift 0/37;
- Outcome Engine drift 0/4.

Next local run should reuse 54 already-ready instruments and only attempt SZSE.000001 before entering authoritative T1 capture.

## M5 Phase 1 — A股实战工作台 / Daily Operator Queue

M5 已从 M4 evidence branch 独立：

`m5/a-share-operator-workbench`

目标不是继续改 harmonic engine，而是把已经冻结的 Source lifecycle / Decision Narrative 组织成日常可用的全市场工作流。

已实现：

- `src/htcn/app/operator_queue.py`
- `GET /api/operator/queue`
- API version 0.4.0
- 首页“今日观察队列”
- action-state workflow buckets
- next key price / role
- first_watch / next_watch / upgrade_blocker
- execution gate / context cautions
- Queue -> 单票输入框联动
- Python operator queue tests
- Playwright operator queue acceptance
- M5 branch browser CI gate

D-042 永久边界：

- read-only over existing lifecycle；
- no predictive score；
- no historical outcome ranking；
- no alpha；
- no trade instruction；
- no identity/PRZ/lifecycle mutation；
- no writes into M4 evidence store。

M4 继续独立积累 prospective evidence；M5 不再因单一历史 provider-calendar 边角问题停止产品主线。

## M5 Phase 1 closeout — Operator Queue green

M5 Phase 1 code checkpoint:

`4df6baa42cd308287796561245e2c6293bb6356d`

GitHub Actions:

- workflow run #1485 / id `35370628695`；
- overall: **success**；
- Python deterministic tests: success；
- Web build: success；
- Playwright Chromium install: success；
- M5 deterministic browser acceptance: success；
- browser evidence upload: success。

冻结边界复核：

- M5 相对 M4 frozen methodology components：**0 changed**；
- M5 相对 Outcome Engine components：**0 changed**。

Phase 1 已实现并验收：

- 全本地 universe Operator Queue；
- workflow buckets；
- next key price / role；
- first_watch / next_watch / upgrade_blocker；
- execution/context cautions；
- primary identity only；
- per-instrument error isolation；
- Queue -> 单票工作台联动；
- API 0.4.0；
- M5 browser CI gate。

Phase 1 仍不包含：

- 胜率；
- alpha；
- outcome-based ranking；
- 买卖评分；
- trade instruction；
- 对 M4 evidence store 的写入。

### M5 下一步

Phase 2 转向 **Operator Delta / 今日变化**：

- 新出现候选；
- 候选消失；
- action_state 变化；
- lifecycle_state 变化；
- next-key 变化；
- context caution 变化。

该变化层属于 product observation，不能冒充 M4 authoritative prospective evidence。

## M5 Phase 2 closeout — Operator Delta green

Phase 2 validated checkpoint:

`791cbdb18322a9fc00e771b9bcb79529d8e63277`

Actions run #1503:

- overall success；
- Python 619 passed；
- Web build success；
- Playwright 19 passed；
- browser evidence upload success。

Implemented:

- stable trade-date-based product display key；
- Queue snapshot schema v2；
- single-as-of integrity；
- pure Operator Delta comparator；
- new/disappeared/state/next-key/context changes；
- current-error disappearance suppression；
- POST /api/operator/delta；
- two-snapshot browser localStorage；
- UI-only evidence-insufficient filtering；
- “今日变化” panel；
- Queue/Delta -> single-symbol deep dive。

D-043 boundary:

- product observation only；
- not authoritative transition；
- no M4 evidence writes；
- no outcome-based ranking；
- no predictive score/alpha/trade instruction。

Frozen M4 methodology and Outcome Engine remain unchanged.

## M5 Phase 3 closeout — Daily Operator Snapshot Cache green

Validated checkpoint:

`3f666c53fa4856eb5ef973e27679583ffa604435`

Actions run #1525:

- overall success；
- Python 628 passed；
- Web build success；
- Playwright 19 passed；
- browser evidence upload success。

Implemented:

- daily full-Queue product cache；
- trade-date/bars/scales/universe-hash/contract cache identity；
- atomic writes；
- cache hit；
- force refresh；
- stale Queue current-date cache rejection；
- automatic invalidation on universe/date/contract change；
- presentation-only filters；
- UI cache provenance；
- `scripts/m5_precompute_operator_snapshot.py`。

D-044 freezes the cache as product acceleration only:
- not authoritative evidence；
- no M4 writes；
- no harmonic/PRZ/lifecycle mutation。

## M5 Phase 4 closeout — Full-Universe Operator Index green

Validated checkpoint:

`41700e02bff874f7498c51bfbad6d8c5e708d4b2`

Actions run #1583:

- overall success；
- Python 629 passed；
- Web build success；
- Playwright 21 passed；
- browser evidence upload success。

Implemented:

- full initialized local universe scan/cache；
- legacy UI limit ignored for scan scope；
- explicit operator_index provenance；
- code/pattern/lifecycle/action search；
- action/lifecycle/pattern/direction filters；
- local presentation pagination；
- 10,000-instrument symbol picker。

D-045 freezes the rule that presentation never defines the scan universe.

## M5 Phase 5 closeout — Parallel Daily Operator Build green

Validated checkpoint:

`96417f63d40d844b5d9d560fde5b47176b90aded`

Actions run #1601:

- overall success；
- Python 634 passed；
- Web build success；
- Playwright 21 passed；
- browser evidence upload success。

Implemented:

- bounded parallel Queue build；
- default 4 workers / env override 1..16；
- per-thread independent M3 service；
- no-factory sequential fallback；
- deterministic final sorting；
- product progress callback；
- precompute live progress；
- precompute full-universe only；
- cache hit skips worker creation。

D-046 freezes parallelism as throughput-only:
- no Queue semantic changes；
- no methodology changes；
- no M4 evidence writes。

## M5 Phase 6 closeout — Single-Flight Operator Rebuild green

Validated checkpoint:

`ad76b7e62de49f7dbafb6898fbfdd055d096d338`

Actions run #1613:

- overall success；
- Python 637 passed；
- Web build success；
- Playwright 21 passed；
- browser evidence upload success。

Implemented:

- process-local single-flight rebuild registry；
- cache-identity keyed owner/follower；
- cache miss coalescing；
- force-refresh coalescing；
- hit-after-race recheck；
- follower `coalesced_wait` provenance；
- failure cleanup。

D-047 freezes single-flight as product concurrency coordination only.



## M5 Phase 7 — Operator Cache Input Identity

Phase 7 修复了“同一交易日内，底层数据或分析代码发生变化但旧 Queue cache 仍可能被复用”的产品一致性缺口。

当前冻结实现：

- Data Input Identity contract v1：
  - `catalog.duckdb` / WAL；
  - `daily`；
  - `daily_delta`；
  - `adjustment/qfq`；
  - `benchmarks`；
  - 使用 relative path + size + mtime_ns 构建产品缓存失效 fingerprint。
- Analysis Code Identity contract v1：
  - app 层与 data 层显式依赖；
  - `src/htcn/harmonic/**/*.py`；
  - 使用文件内容 SHA-256。
- Operator Cache Input Identity contract v1 合并 data + analysis-code fingerprint。
- Operator snapshot contract 已升至 v2，并持久化 input identity。
- cache read 必须同时匹配 trade date / bars / scales / universe / contract / input identity。
- single-flight key 绑定 input identity；不同 identity 不允许错误 coalesce。
- API 进程冻结 analysis-code identity，但每次请求刷新 data identity。
- precompute 同样冻结本进程 analysis-code identity，并在 full build 完成后再次读取 data identity。
- 构建过程中若 input identity 改变：
  - 返回 `live_not_cached_input_changed`；
  - 禁止把本次结果写成正式 product cache。
- Phase 7 不改变 Queue semantics，不进入 M4 methodology / outcome evidence。

Validated checkpoint：

`7d1de7a81b7b2efc2a149eecd5a6c41b865123cd`

Hosted CI：

- run `35378357267` / #1634：success；
- Python 650 passed；
- Web build success；
- Playwright 21 passed；
- browser evidence artifact uploaded。

Phase 7 governance：D-048 / `specs/m5-phase-7-operator-cache-input-identity.md`。

### 下一步

Phase 7 代码已经 green；下一阶段不应再回到 M4 QFQ 或重复做同一缓存 identity 修复。

优先进入 M5 下一产品可靠性阶段：处理 **跨进程 / precompute 与 API 并发 rebuild 的协调边界**，因为 D-047 明确只保证 process-local single-flight。任何新协调层仍只能优化产品执行，不得改变 Queue semantics 或 M4 evidence。


## M5 Phase 8 — Cross-Process Operator Rebuild Coordination

Phase 8 关闭了 D-047 明确留下的 process-local-only 并发缺口。

冻结实现：

- 保留 Phase 6 process-local single-flight；
- 新增 cache-slot scoped filesystem advisory lock；
- POSIX 使用 `fcntl.flock`；
- Windows 使用 `msvcrt.locking`；
- lock file 位于 `data/product/m5/operator_queue/.locks/`，它只是协调 inode，不是 cache/evidence；
- 锁由 OS 文件描述符拥有，进程异常退出后由 OS 释放，不依赖删除 lock file 解锁；
- 同一 cache slot（trade date + bars + scales + cache root）的跨进程 rebuild 串行；
- 不同 input identity 仍**不 coalesce**，只是不能并发写同一个 cache slot；
- 等待另一进程后，force refresh 可复用对方刚完成、且对自己当前 identity 仍有效的 cache；
- cache fast hit 与 cross-process wait 后的 hit 都重新核对当前 input identity；
- build 结束后的 Phase 7 identity recheck 继续保留；
- 输入在等待/构建中漂移时不得把结果写为正式 cache；
- 真实 multiprocessing 回归验证第二个进程确实阻塞并在第一个进程释放后取得锁；
- `data/product/**` 与 `data/research/**` 已明确 Git ignore，runtime cache/lock/evidence 不污染 source worktree。

Validated checkpoint：

`08f51e28f60840cfb6a85b85fbceb091c9392825`

Hosted CI：

- run `35380339931` / #1641：success；
- Python 658 passed；
- Web build success；
- Playwright 21 passed；
- browser evidence uploaded。

Frozen boundary audit：

- M4 capture methodology：0 / 37 changed；
- Outcome Engine：0 / 4 changed。

Governance：D-049 / `specs/m5-phase-8-cross-process-operator-rebuild.md`。

### 下一步

进入 M5 下一产品阶段：**Daily Close Product Pipeline**。

旧的 `m5/daily-close-pipeline` / `m5/daily-handoff-bundle` 是早期从共同祖先分叉的实验线，不能直接切回或整分支合并。可择优移植，但必须修正旧设计中的阻塞关系：

- M1 fresh market data 是 M5/M4 可共享的基础；
- M5 Operator 产品不得被 M4 strict-QFQ readiness 的单票历史供应商问题阻塞；
- M4 methodology/outcome guards 只约束 M4 research lane，不得成为 M5 product lane 的总前置门；
- context sync 可 best-effort 更新并把 degraded 状态带入 Queue，而不是把产品入口锁死。


## M5 Phase 9 — Daily Close Product Pipeline

Current lineage completed Phase 9 on branch `m5/daily-close-product-pipeline`.

Validated code checkpoint:
`dec76022098574537333e8d3abd56bcc3b928a99`

Hosted CI run `35381269831` / #1646:
- overall success；
- Python 682 passed；
- Web build success；
- Playwright 21 passed；
- browser evidence upload success。

Frozen design:
- M1 fresh market data is the shared hard prerequisite；
- M3 context sync is best effort for M5；
- M5 initial product cache runs before M4 research；
- M4 source/methodology/outcome/QFQ gates constrain only the research lane；
- M4 degraded does not invalidate an otherwise ready M5 product；
- after M4 research, M5 always runs a final non-force cache revalidation because research-side QFQ can mutate `adjustment/qfq`, which is part of Phase 7 Data Input Identity；
- per-instrument failures remain isolated while explicit `instrument_errors` are surfaced；
- subprocess output streams live and each step has a log。

Freeze audit:
- M4 capture methodology: 0 / 37 changed；
- Outcome Engine: 0 / 4 changed。

Governance:
- D-050；
- `specs/m5-phase-9-daily-close-product-pipeline.md`。

### 下一步

进入 **M5 Phase 10 — Daily Handoff Bundle v2**。
不要切回或整体合并旧 `m5/daily-handoff-bundle` 实验分支；只择优移植思想。新交接包必须绑定 Phase 9 最终 product snapshot / input identity，并把任何嵌套 M4 evidence bundle 明确标成独立 authoritative research evidence，而不是把整个 handoff ZIP 本身升级成 authority。


## M5 Phase 10 — Daily Handoff Bundle v2

Current branch:
`m5/daily-handoff-bundle-v2`

Validated code checkpoint:
`99e3bf7aba1e656601bdcf4831d4b215eede4e8d`

Hosted validation:
- draft PR #22 used only as CI/diff carrier；
- Actions run `35382676878` / #1665：success；
- Python 699 passed；
- Web build success；
- Playwright 21 passed；
- browser evidence upload success。

Frozen implementation:
- current M5 product snapshot is bound from the final Phase 9 `m5-operator-snapshot.json` exact cache path, never guessed by scanning for the latest JSON；
- final M5 report and snapshot are cross-checked for contract v2, trade date, single-as-of state and Phase 7 input identity；
- cache path is confined to the Operator cache root and canonical date/bars/scales filename；
- manifest paths are repository-relative/portable, not local absolute paths；
- outer ZIP remains transport-only/non-authoritative；
- optional previous M5 snapshot is context only, never current identity；
- current M4 evidence is required only when the Phase 9 research lane says ready；
- degraded research may carry a separately verified existing M4 bundle without calling it current research success；
- all nested M4 bundles use the frozen evidence-bundle verifier；
- each member has size/SHA-256 and exact manifest membership；
- ZIP is verified before and after atomic replace；
- pipeline/M5 report/current snapshot are independently parsed and cross-verified by the handoff verifier；
- handoff runner writes a separate `m5-daily-handoff.json` and proves the Phase 9 pipeline report hash is unchanged；
- output/report/pipeline path collisions are forbidden；
- handoff transport failure never rewrites `m5_product_ready` or `m4_research_ready`；
- one-click `运行HT-CN每日交接包.bat` only builds the handoff and does not rerun Phase 9。

Artifacts:
- `artifacts/reports/htcn-daily-handoff-v2.zip`
- `artifacts/reports/m5-daily-handoff.json`

Freeze audit:
- M4 capture methodology: 0 / 37 changed；
- Outcome Engine: 0 / 4 changed。

Governance:
- D-051；
- `specs/m5-phase-10-daily-handoff-bundle-v2.md`。

### 下一步

Phase 10 已解决“每日结果如何可靠交接/搬运”。下一阶段应继续留在 M5 产品主线，优先做 **Daily Operator History / Change Journal v1**：把每天 final Operator snapshot 的产品级变化长期留档并提供跨日检索，但仍必须与 M4 authoritative prospective evidence 隔离。禁止用该 history 直接生成胜率/alpha/预测排序。


## M5 Phase 11 — Daily Operator History / Change Journal v1

Current branch:
`m5/daily-operator-history`

Validated code checkpoint:
`504cc063d93e999dcbac1b131e14f475beacd4d0`

Hosted validation:
- draft PR #23 is only a CI/diff carrier；
- final code CI run `35384764795` / #1699：success；
- Python 718 passed；
- Web build success；
- Playwright 22 passed；
- browser evidence upload success。

Frozen implementation:
- history is written only after Phase 9 final cache revalidation；
- a history failure never rewrites an otherwise valid `m5_product_ready` or M4 research result；
- append source is the exact final M5 report/snapshot, validated for current/single-as-of/persisted/stable input identity；
- observation id binds trade date, source generated-at, input identity, final report SHA, product snapshot SHA and canonical Queue SHA；
- storage is append-only under `data/product/m5/operator_history/<trade_date>/<observation_id>.json`；
- exact rerun is idempotent；
- same-day changed input/source appends a new revision instead of overwriting；
- older same-day revision and historical backfill are forbidden；
- append is cross-process serialized by OS advisory lock；
- each record contains a self-contained Queue snapshot；
- cross-day Delta baseline is the latest revision of the previous recorded trade date；
- current instrument-analysis errors retain Phase 2 disappearance suppression；
- each record has a self-integrity SHA；
- same-day revision links and previous-trade-date links are explicit；
- missing/tampered/deleted records break the chain and queries fail closed with `operator_history_integrity_failure`；
- default query returns the latest revision per day；all revisions remain auditable；
- GET `/api/operator/history` supports instrument/display-key/date/revision/summary filters；
- Workbench adds **跨日产品观察历史** alongside the existing browser-local **今日变化**；
- CLI: `scripts/m5_query_operator_history.py`；
- recorder: `scripts/m5_record_operator_history.py`；
- one-click query: `运行HT-CN历史变化查询.bat`；
- daily report: `artifacts/reports/m5-operator-history.json`；
- CI now includes `apps/web/tests/operator-history.spec.ts`。

Boundary:
- product observation only；
- authoritative_transition=false；
- authoritative_evidence=false；
- writes_m4_evidence=false；
- historical_outcome_used_for_ranking=false；
- predictive_score_used=false；
- alpha_inference_allowed=false；
- is_trade_instruction=false；
- no harmonic identity / Source Raw PRZ / lifecycle mutation。

Development note:
- run #1693 exposed only an ambiguous Playwright locator in the new history test; the existing 21 browser gates passed；
- locator was scoped to the latest-day card in `b49d1468a243f0a129def63b6ee3984170d1ceb8`；
- run #1695 then passed 715 Python + 22 Playwright；
- chain hardening increased final regression to 718 Python, with run #1699 fully green。

Freeze audit:
- M4 capture methodology: 0 / 37 changed；
- Outcome Engine: 0 / 4 changed。

Governance:
- D-052；
- `specs/m5-phase-11-daily-operator-history.md`。

### 下一步

Phase 11 已建立可靠的跨日产品观察底座。下一阶段优先进入 **M5 Phase 12 — Daily Review Digest / Change Triage v1**：基于已冻结的 product history，把“新出现 / 消失 / lifecycle / action / next-key / context 变化”整理成每日复盘摘要与可钻取工作流。

Phase 12 仍只能做透明的变化归类和复盘导航，不得把历史 observation 转换为胜率、alpha、预测评分或买卖排序。若后续需要把 Phase 11 history 带入每日交接包，应通过新的 versioned handoff contract 实现，不修改 Phase 10 已冻结的 v2 语义。


## M5 Phase 12 — Daily Review Digest / Change Triage v1

Current branch:
`m5/daily-review-digest-v1`

Validated code checkpoint:
`84c7d8a0f2d46cd8ed9b79dcd638cb727d165465`

Hosted validation:
- draft PR #24 is only a CI/diff carrier；
- first code CI run `35413513169` / #1725：success；
- Python 733 passed；
- Web build success；
- Playwright 23 passed；
- final hardening CI run `35413656027` / #1733：success；
- Python 736 passed；
- Web build success；
- Playwright 23 passed；
- browser evidence upload success。

Frozen implementation:
- digest source is the latest valid Phase-11 history revision；
- Phase-11 record/revision/previous-day chain integrity is inherited and remains fail-closed；
- digest requires an exhaustive unfiltered Delta：declared total, observation change count and actual changes length must match；
- all changes and all change_types are retained；
- fixed review workflow order is execution_evaluation → reaction_observation → waiting → evidence_insufficient → disappeared_candidate；
- that order is product workflow navigation only, explicitly not expected-return/win-rate/trade ranking；
- transparent change types cover new/disappeared/action/lifecycle/pattern/next-key/execution-gate/context-caution changes；
- current analysis gaps are shown separately and are not reinterpreted as candidate disappearance；
- digest status distinguishes baseline/no-changes/changes-ready and analysis-gap variants；
- Phase 12 runs only after Phase-11 history append in the daily close pipeline；
- digest failure does not rewrite product/history/research readiness；
- GET `/api/operator/review-digest` supports workflow/change-type/instrument filters；
- filters only affect filtered sections/count and never alter source change totals；
- invalid workflow/change-type filters are rejected explicitly；
- Workbench adds **每日变化复盘** before **跨日产品观察历史**；
- UI shows source total and filtered hit count side by side；
- each item can drill into the single-symbol workbench；
- report: `artifacts/reports/m5-daily-review-digest.json`；
- one-click: `运行HT-CN每日变化复盘.bat`；
- CI includes `apps/web/tests/daily-review-digest.spec.ts`。

Boundary:
- product_change_triage_only；
- exhaustive_changes=true；
- authoritative_transition=false；
- authoritative_evidence=false；
- writes_m4_evidence=false；
- historical_outcome_used_for_ranking=false；
- predictive_score_used=false；
- alpha_inference_allowed=false；
- is_trade_instruction=false；
- no harmonic identity / Source Raw PRZ / lifecycle mutation。

Freeze audit:
- M4 capture methodology: 0 / 37 changed；
- Outcome Engine: 0 / 4 changed。

Governance:
- D-053；
- `specs/m5-phase-12-daily-review-digest.md`。

### 下一步

Phase 12 已把“长期历史”变成每天可执行的复盘导航。下一阶段优先进入 **M5 Phase 13 — Review Session / Follow-up Journal v1**：给 review item 增加独立的产品工作流状态，例如“未看 / 已看 / 后续跟踪”和可选笔记，并稳定绑定 source observation / display key。

Phase 13 只能记录用户复盘工作流，不得修改 canonical lifecycle/action state，不得变成仓位/交易执行层，也不得因为用户 pin/follow-up 就改变 Queue 排序、胜率、alpha 或预测评分。若未来需要把 Phase 11/12 artifacts 带入交接包，仍需另建 versioned handoff contract，不修改冻结的 Phase 10 handoff v2。


## M5 Phase 13 — Review Session / Follow-up Journal v1

Current branch:
`m5/review-followup-journal-v1`

Validated code checkpoint:
`4b015dfc0e72db0f1275e1e570d85959254550fa`

Hosted validation:
- draft PR #25 is only a CI/diff carrier；
- initial CI run `35415053453` / #1766：Python 757 + Web green；原有 23 Playwright green；新增 Phase-13 test 仅因 locator 同时命中 follow-up header/item 失败；
- locator 在 `4b015dfc0e72db0f1275e1e570d85959254550fa` 收窄到具体 row；
- final code CI run `35415145067` / #1768：success；
- Python 757 passed；
- Web build success；
- Playwright 24 passed；
- browser evidence upload success。

Frozen implementation:
- review workflow state is separate from canonical lifecycle/action；
- fixed states: unseen / reviewed / follow_up；
- no event means unseen for the exact current observation/display-key binding；
- every write binds a validated Phase-11 source observation + real Delta display key；
- journal root is `data/product/m5/review_journal/`；
- event storage is append-only and cross-process locked；
- client_request_id makes retries idempotent and conflicting replays fail；
- note is optional, normalized and capped at 1000 chars；
- each event has self-integrity SHA plus binding/display-key ordinal chains；
- chain gaps/tampering fail closed with `review_journal_integrity_failure`；
- current-day review state never inherits yesterday's reviewed state；
- active follow-up is derived from the latest event per display key and can persist across trade dates；
- a follow-up stays visible even when the current day has no new Delta；
- ending follow-up appends reviewed rather than deleting history；
- Workbench shows current review counts plus a separate persistent follow-up list；
- same-day follow-up says “跟踪中”；older source date says “跨日跟踪中”；
- GET `/api/operator/review-session` returns the enriched current review session；
- POST `/api/operator/review-session/event` is the explicit write surface；
- GET `/api/operator/review-journal` is read-only audit；
- CLI: `scripts/m5_query_review_journal.py`；
- one-click query: `运行HT-CN复盘跟踪查询.bat`；
- Phase 13 is deliberately not part of daily-close pipeline, so no user action means no automatic review event；
- Phase 12 `/api/operator/review-digest` contract remains available/frozen；
- Phase 10 handoff v2 remains frozen/unmodified。

Boundary:
- product_review_workflow_only；
- append_only=true；
- authoritative_transition=false；
- authoritative_evidence=false；
- writes_m4_evidence=false；
- predictive_score_used=false；
- historical_outcome_used_for_ranking=false；
- alpha_inference_allowed=false；
- is_trade_instruction=false；
- mutates_operator_queue=false；
- mutates_operator_history=false；
- mutates_action_state=false；
- mutates_lifecycle=false；
- no harmonic identity / Source Raw PRZ mutation。

Freeze audit:
- M4 capture methodology: 0 / 37 changed；
- Outcome Engine: 0 / 4 changed。

Governance:
- D-054；
- `specs/m5-phase-13-review-followup-journal.md`。

### 下一步

Phase 13 已把“每天看什么”推进到“哪些看过、哪些要持续跟踪”，并且形成可审计的人工复盘 journal。下一阶段优先进入 **M5 Phase 14 — Daily Handoff Bundle v3 / Review-State Transport**。

Phase 14 应建立新的 versioned transport contract，把 Phase 11/12/13 的当前产品状态安全加入交接包：
- current validated Operator product snapshot；
- latest current-day Phase-11 history observation；
- Phase-12 review digest；
- Phase-13 review-session snapshot / active follow-up context；
- 必要的 hashes / source binding / portable paths。

Phase 14 不得修改 Phase 10 handoff v2，不得把 mutable review journal 伪装成 M4 authoritative evidence，也不得因 follow-up/reviewed 状态改变产品排序或交易含义。


## M5 Phase 14 — Daily Handoff Bundle v3 / Review-State Transport

Current branch:
`m5/daily-handoff-bundle-v3`

Validated code checkpoint:
`c9de28d959b64043663a2bceccb17cc87b8f3756`

Hosted validation:
- draft PR #26 is only a CI/diff carrier；
- first code CI run `35416245508` / #1788：success；
- Python 771 passed；
- Web build success；
- Playwright 24 passed；
- final hardening CI run `35416336734` / #1790：success；
- Python 774 passed；
- Web build success；
- Playwright 24 passed；
- browser evidence upload success。

Frozen implementation:
- v3 is a new schema/versioned transport and does not modify Phase-10 v2；
- v3 builds a verified v2 only inside a temporary directory and nests it as `base/htcn-daily-handoff-v2.zip`；
- existing v2 ZIP/report are never overwritten；
- outer manifest cross-checks nested-v2 schema/status/product binding/bundle SHA；
- outer pipeline hash is checked against the exact raw pipeline member inside nested v2；
- product/history/digest/M4 readiness are inherited from the same pipeline report；
- digest-ready requires history-ready；history-ready requires product-ready；
- current Phase-11 history record must bind to the exact nested-v2 product report/snapshot hashes and trade date；
- history transport is bounded to current + direct previous trade-date observation + direct previous same-day revision when needed；
- current delta is independently rebuilt from previous/current queues when a previous trade-date baseline exists；
- Phase-12 digest is recomputed from transported current history and must exactly match semantic core；
- Phase-13 review-session snapshot is captured under the existing review-journal process lock；
- removing Phase-13-specific review fields from session must project exactly back to the Phase-12 digest；
- only journal events referenced by current session roots are transported；
- previous binding/display-key event links are recursively included until chain start；
- included event set must exactly equal the root closure：no missing predecessor and no unrelated extra event；
- each event is revalidated with Phase-13 event verifier；
- current review event and active-follow-up source/state/note are cross-checked against the session snapshot；
- v3 write is temp -> verify -> atomic replace -> verify again；
- v3 runner/report are fully isolated from pipeline readiness；
- new outputs:
  - `artifacts/reports/htcn-daily-handoff-v3.zip`
  - `artifacts/reports/m5-daily-handoff-v3.json`
- one-click: `运行HT-CN每日交接包v3.bat`；
- old v2 entrypoints remain frozen and separate。

Boundary:
- schema_version=3；
- transport_only=true；
- authoritative_evidence=false；
- writes_m4_evidence=false；
- is_trade_instruction=false；
- alpha_inference_allowed=false；
- predictive_score_used=false；
- historical_outcome_used_for_ranking=false；
- review_state_changes_product_ranking=false；
- M4 authority remains nested in the frozen v2 capture chain；
- reviewed/follow_up gain no new ranking/lifecycle/trade meaning from transport。

Freeze audit:
- Phase-10 handoff v2 files: 0 changed；
- M4 capture methodology: 0 / 37 changed；
- Outcome Engine: 0 / 4 changed。

Governance:
- D-055；
- `specs/m5-phase-14-daily-handoff-bundle-v3.md`。

### 下一步

Phase 14 已经解决“如何把当前产品观察 + history + 每日 digest + 人工 review/follow-up 状态完整、安全地带走”。下一阶段优先进入 **M5 Phase 15 — Handoff v3 Inspector / Portable Review Workspace v1**。

Phase 15 应做到：
- 只读打开一个 v3 ZIP；
- 先完成 v3/v2/nested-M4 全链验证；
- 不依赖本机 market database 就能浏览 transported current Operator snapshot、current/previous history、daily digest、review-session 和 active follow-ups；
- 提供中文优先的 portable summary / drill-down；
- 可以按 instrument/display-key 浏览 transport 内的当前状态；
- 不把 v3 内容自动导入本地 Queue/history/review journal；
- 不产生新的 reviewed/follow_up event；
- 不修改 M4 evidence；
- 不做收益、胜率、alpha 或交易排序。

如果未来要支持显式 import/merge，必须是 Phase 15 之后独立的新 contract，并处理冲突/幂等/来源身份，不能把“只读 inspector”偷偷变成写入器。
