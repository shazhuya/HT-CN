# HT-CN Decision Ledger — 设计决策账本

本文件记录会影响后续实现方向的“为什么”。它采用 append-only 风格：后续若推翻旧决定，应新增 supersede 记录，而不是静默改掉历史原因。

## D-001 — Carney source fidelity 高于工程便利

**状态：Frozen**

Carney Volume One / Two / Three 定义 harmonic identity、source measurement 与 Reaction vs. Reversal 的理论基准。HT-CN 可以增加 A 股执行层、统计层、排名层和 UI，但不得把工程近似包装成原书定义。

## D-002 — 几何时钟与执行时钟永久分离

**状态：Frozen**

历史完成 D Pivot 只属于 retrospective geometry；source-aligned Terminal Price Bar 属于 execution observability。

官方执行序列保持：`forming projection -> source PRZ entry -> Terminal Price Bar -> PEZ -> T-Bar+1 -> Type-I`。

## D-003 — PRZ 采用分层对象，不再用一个 price_low/high 概括

**状态：Frozen**

显式区分 component envelope、Ideal Core、Source Raw PRZ、Terminal extreme、PEZ。legacy `price_low/high` 只能作为兼容别名，不能冒充完整 source PRZ。

## D-004 — Type-II 必须完整 retest 后再确认

**状态：Frozen**

只发生 secondary overlap 不足以叫 Type-II。必须先完整 retest 原 PRZ terminal side 后再进入 Type-II Terminal Bar 与后续确认。Source PRZ 未解决时 fail closed。

## D-005 — Wilder RSI evidence 不等于 RSI BAMM

**状态：Frozen**

当前简单 Wilder RSI 极值区反转只作为 indicator evidence。未来 RSI BAMM 必须作为独立多步骤状态机实现，不能改名冒充。

## D-006 — 5-0 在 source conflict 关闭前默认隔离

**状态：Frozen**

5-0 默认 Engine / Scanner / Workbench 不发出；只允许研究显式 opt-in。M2.29 已冻结 V2 structural Raw PRZ，但 V3 标签冲突仍不足以解除 production quarantine。

## D-007 — Shark 使用专属 first-target contract

**状态：Frozen**

Shark initial target 为从 C/Terminal 出发先遇到的 50% BC 或 Reciprocal AB=CD；61.8% BC 保留为更宽的 prospective 5-0 management level。

## D-008 — Identity 不能被分数或统计“救活”

**状态：Frozen**

source-backed hard identity 先决定 completed/rejected。geometry score、统计、A 股环境、indicator evidence、UI 偏好只能在已经通过 identity 的候选之上排序或解释。

## D-009 — 冻结研究结果不可回写

**状态：Frozen**

已经消费/冻结的 Holdout、external replication、历史 closed result 保持不可变。source repair 改变规则时必须建立新的 research version / prospective protocol。

## D-010 — A 股增强必须在独立执行层

**状态：Frozen**

T+1、涨跌停、流动性、ATR、指数/板块相对强弱、开收盘微观结构等可以影响执行可行性、风险和优先级，但不能改写 Carney pattern identity 或 source PRZ。

## D-011 — 中文优先，但内部标识保持稳定

**状态：Frozen**

界面、表格、状态、审计提示和散户可读解释尽量中文化。内部枚举、API 字段、技术缩写保持稳定英文标识。

## D-012 — 当前默认市场范围为 SSE/SZSE

**状态：Frozen until user reopens scope**

北交所 BSE 暂不进入默认开发与验收范围。

## D-013 — 跨对话项目事实以仓库为准

**状态：Frozen**

新会话必须以当前 HEAD、`PROJECT_CONTEXT.md`、本账本、相关 specs、CI 为权威，并检查 `context_checkpoint..HEAD`。

## D-014 — Standalone AB=CD Source Raw PRZ 与 BC Layering 永久分层

**状态：Frozen**

Standalone AB=CD Source Raw PRZ = equivalent `AB=CD x1` defining completion + reciprocal BC complementary measurement。Volume Three BC layering 只能进入 execution refinement，不能进入 identity / Raw PRZ。

该决定从 M2.28 起形成 `m2-source-prz-v4`。历史 frozen results 不因定义变化而重算。

## D-015 — Shark Source Raw PRZ 采用 published corridors 的几何重叠

**状态：Frozen**

M2.30 起，Shark Source Raw PRZ 明确定义为以下两条 Carney published completion corridors 的几何 overlap/alignment：

- `0B 0.886–1.13 completion corridor`；
- `AB 1.618–2.24 Extreme Harmonic Impulse corridor`。

决定：

- 不使用 synthetic midpoint 作为 Shark completion；
- 不允许 legacy Ideal Core 替代 Shark Source Raw PRZ；
- 若两条 corridor 不重叠，source-aligned execution fail closed；
- `1.13 0B` 是 outer completion / stop reference；
- 50% BC、Reciprocal AB=CD、61.8% BC 均属于 post-completion management，不属于 Shark identity / Source Raw PRZ；
- source-aligned reaction clock 从 observed Terminal Price Bar extreme 开始，不从 later right-confirmed C pivot 开始。

原因：Shark 是独立 0-X-A-B-C contract，不能被 generic XABCD completion/target 逻辑吞并。

验证方式：Shark Book Golden ledger + source-contract tests + Terminal-Bar regression + v6 sealed research guard + 45-symbol real A-share CI。

## D-016 — 长耗时真实 A 股研究必须可恢复、可观察、不可被普通小提交浪费

**状态：Frozen engineering policy; concurrency clause superseded by D-019**

M2.30 起，GitHub CI 的真实 A 股研究采用以下工程约束：

- 允许读取历史 Actions artifact；
- research snapshot cache miss 时优先恢复冻结 45 股 artifact；
- artifact 恢复成功后立即持久化到 cache，不等待整轮研究结束；
- deterministic short tests 可 `cancel-in-progress`；
- calibration 使用无缓冲输出，逐股打印真实进度；
- timeout 是防失控保险，不得拿增加 timeout 代替性能诊断。

M2.30 最初采用 long research `cancel-in-progress: false`。M2.31 closeout 发现普通开发提交会堆积无价值中间研究，因此该并发条款由 D-019 取代；其余 snapshot-first / resumable / observable 原则继续冻结。

原因：真实研究结果依赖冻结数据边界。重复联网抓取既浪费时间，也会把 provider availability 与 harmonic 逻辑错误混在一起。

## D-017 — RSI BAMM 是独立 source-confirmation evidence，不是 Wilder RSI 别名

**状态：Frozen**

M2.31 起，RSI BAMM 必须由独立 no-lookahead 状态机产生，并保持以下边界：

- 14-period Wilder RSI；两次 30/70 extreme test；中间至少一次 RSI 50 midpoint reaction；
- Volume Three Simple/Complex × Confirmation/Divergence 四类结构独立保留；
- Volume Two X-A Confirmation Point 使用 1.13/1.618 source selection，X-A 锚点在第二次 extreme 前冻结；
- standalone AB=CD 使用 M2.28 source resolver；Shark 使用 M2.30 source contract；5-0 在 production quarantine 解除前不得确认 BAMM；
- 1.13 retracement-pattern precedence 只允许原书明确支持的 source-cleared Gartley/Bat，不扩展到 Shark/AB=CD/5-0；
- 不发明 ATR、百分比、tick 或 PRZ-distance 容差来“凑”BAMM 与 harmonic confluence；不满足 source contract 时 fail closed；
- BAMM 只能增加 confirmation/execution evidence，永远不能创建、修改或救活 harmonic identity / Source Raw PRZ。

原因：普通 RSI 极值、RSI divergence 与完整 RSI BAMM 是不同层级的证据；若允许 caller boolean 或工程容差直接制造 `source_confirmed`，会重新破坏 Source Fidelity Gate。

## D-018 — Completed BAMM confluence 必须绑定 Source Terminal Price Bar，而不是历史 D/C

**状态：Frozen**

M2.31 Phase 4 正式区分两个适配器：

- `confirm_rsi_bamm_with_match()`：只保留 geometry-terminal compatibility / golden-test 用途；
- `confirm_rsi_bamm_with_source_execution()`：production lifecycle 的 canonical confluence adapter。

Completed historical match 必须先通过 `observe_source_execution_for_match()`，从 pre-terminal pivot 的可观察时点重建：

`Source Raw PRZ entry -> Source Terminal Price Bar -> PEZ -> T+1`

然后才能把 BAMM 绑定到 execution lifecycle。

进一步冻结：

- historical D/C pivot 不自动等于 Source Terminal Price Bar；
- Source T-Bar 必须在 historical terminal pivot 之前或当根已可观察，禁止后来的 unrelated PRZ touch 回填；
- Source T-Bar 可以形成合法 PEZ overspill；static Raw PRZ interval 仍保持不变；
- BAMM 可用时间 = `max(Source T-Bar, BAMM completion)`；任何晚完成 evidence 禁止 backdate。

原因：Volume Three 的执行语义依赖真正 PRZ terminal-side test。把事后 right-confirmed D/C 当 T-Bar 会制造不可实盘复现的证据时钟。

验证方式：Source T-Bar distinct-from-D/C regression、PEZ overspill regression、no-backdating regression、45-symbol frozen observability、run #643。

## D-019 — 45 股重研究只由明确 closeout 触发，并只保留最新分支 closeout

**状态：Frozen engineering policy**

M2.31 起：

- 普通 push/PR 运行 deterministic + Web build + Playwright；
- 45 股 autonomous research 只在明确 `[research]` closeout 提交运行；
- 同一开发分支的旧中间 research run 允许被更新 closeout 取消；
- latest closeout 使用冻结 snapshot / sealed research guards；
- 已冻结 Holdout / external replication / closed result 仍不可改写。

该决定只优化 CI 资源使用，不改变 research definition、样本边界或 source semantics。

## D-020 — M3 产品 lifecycle 必须由 source execution clock 驱动

**状态：Frozen migration contract**

M3 Workbench 的 live/current state 不得再由 historical D/C pivot 直接派生。统一目标状态链：

`forming -> approaching_source_prz -> entered_source_prz -> waiting_terminal -> source_terminal_complete -> t_plus_1 -> type_i_early_reaction -> type_i_confirmed / type_i_failed / reaction_only -> type_ii_retest_forming -> type_ii_terminal -> reversal_evidence / invalidated`

产品必须优先回答：

- 现在在哪个状态；
- 先看什么证据；
- 下一个关键价格/状态；
- 什么使当前判断失效；
- 当前应该等待、观察还是进入下一层执行评估。

RSI BAMM、普通 RSI、A 股市场环境、ATR、流动性等都只能作为 evidence/context channel；它们不能拥有 lifecycle，也不能修改 Carney identity / Source Raw PRZ。

原因：M2.31 的 45 股 observability 显示 174 个 historical completed match 里只有 128 个能从当时信息重建 source clock，说明 retrospective completed geometry 与 live execution observability 并不等价。

## D-021 — A 股交易制度与波动数据只进入 execution context，不得拥有 lifecycle

**状态：Frozen M3 execution-context contract**

M3 Phase 3 起，A 股制度/波动信息统一进入独立 `a_share_execution_context`：

- 普通 A 股 T+1 / 当日买入不可当日卖出的执行约束；
- SSE/SZSE 板块日常涨跌幅规则；
- 上市前 5 个交易日不套用日常涨跌幅规则的 IPO 例外；
- 主板风险警示股票 2026-07-06 前后的历史规则切换；
- ATR(14) / ATR%、最新日内振幅、前 20 日均量与量比；
- 证券元数据是否足以判断 ST / 上市年龄 / 板块；
- 北交所继续 deferred。

决定：

1. execution context 不生成 harmonic identity，不修改 Source Raw PRZ，也不拥有 source lifecycle state；
2. 不建立“综合可交易性分数”作为黑箱决策器，先暴露原始可审计字段；
3. 元数据不足时 fail safe：只展示板块名义规则，不猜 ST / IPO 例外；
4. 因停复牌、特殊证券等事件元数据尚未完整接入，字段使用 `rule_based_price_limit_pct`，禁止命名为 exact price limit；
5. `special_event_exceptions_unresolved=true` 时，UI 必须明确该规则值不等同于当天精确涨跌停价格；
6. ATR / 成交量只能用于波动与执行背景，不得反向修复、否决或重排 Carney identity。

原因：A 股交易制度会显著改变“同一个谐波 lifecycle 是否具备现实执行条件”，但把这些规则塞回形态识别会污染 Carney source fidelity；把它们压成单一分数又会失去审计性并诱发错误自动化。

验证方式：主板风险警示 2026-07-06 日期切换回归、STAR/ChiNext 20% 板块规则、IPO 前 5 交易日例外、缺 metadata fail-safe、ATR/量比 deterministic tests，以及工作台独立 execution-context 卡片。

## 后续新增格式

```text
## D-XXX — 决策标题

状态：Proposed / Active / Frozen / Superseded by D-YYY

决定：

原因：

影响范围：

验证方式：
```


## D-022 — M4 生命周期验证默认 prospective append-only

**状态：Frozen M4 validation contract**

M4 对真实 A 股 Source lifecycle 的正式验证默认从当前真实已收盘交易日开始，采用 append-only prospective journal。

决定：

1. 不允许为了增加样本量，把已经知道后续结果的历史 completed geometry 重新包装成“当时可见的 prospective lifecycle”；
2. 每个 journal entry 必须带 `code_head`、`as_of_trade_date`、稳定 candidate key、canonical `source_lifecycle` 与 Decision Narrative action state；
3. candidate key 使用 pivot anchor 的交易日期，不使用 rolling analysis window 中会每日漂移的 bar index；
4. 同一 code-head / as-of / candidate key 重复采集必须幂等；
5. 默认禁止早于既有 journal 最大日期的 backfill；
6. 5-0 在 production quarantine 解除前不进入 M4 正式 validation cohort；
7. journal 初期只允许输出 observability、状态分布和真实状态转移；不得把小样本频数包装成 alpha、胜率或交易评分；
8. 后续若要做历史 replay，必须另建显式 versioned research protocol，并证明 prefix/no-lookahead，不得混入 prospective 主账本。

原因：

M2.31/M3 已证明 historical completed geometry 与 live source-clock observability 并不等价。若 M4 再用后验历史重建冒充 prospective 证据，会重新引入最初要消除的 hindsight bias。

验证方式：

- stable candidate-key regression；
- no-backfill regression；
- idempotent append regression；
- real-A-share latest-closed-day snapshot；
- 后续跨交易日 transition ledger。
