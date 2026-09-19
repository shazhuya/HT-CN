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


## D-023 — 用户本机只用于不可替代的本地数据采集

**状态：Frozen engineering workflow**

HT-CN 后续开发默认不得把用户电脑当作常规测试机。

决定：

1. 代码静态核查、单元测试、回归测试、浏览器验收、文件分析、状态迁移计算、报告生成，只要当前 assistant/tool 环境能够完成，就必须由 assistant 自行完成；
2. 不允许为了方便、节省 assistant 工具调用或重复确认，把可自行完成的测试转交给用户本机；
3. 用户电脑只允许承担 assistant 客观无法访问的本地资源步骤，例如用户私有 M1 DuckDB/Parquet、未连接的本地服务、仅存在本机的凭据/硬件/数据源；
4. 即使确实需要本机，也必须最小化为“不可替代的数据采集动作”，不得顺带要求用户重复执行 Python/Web/Playwright 等 assistant 可自行完成的验收；
5. 用户上传本地采集结果后，后续分析、质量检查、代码修复、统计与报告由 assistant 接管；
6. 同一个本地动作不得因为 assistant 自己的测试迭代而反复要求用户重跑；应先穷尽 assistant 侧测试，再在确实需要新本地证据时调用一次；
7. 若未来可以通过连接器、上传一次数据集、自动 artifact 或其他非侵入方式替代人工本机运行，应优先采用替代方式。

原因：

用户已经明确要求“非必要不要调用我的电脑，所有能由 assistant 完成的测试都由 assistant 自己完成”。此前 M3/M4 closeout 将真实 M1 数据验证扩张成了反复本机 QA，增加了不必要的人工作业，也混淆了“本地私有数据采集”和“代码测试”两个职责。

验证方式：

- 每个需要用户本机动作的任务必须能明确说明其不可替代的本地依赖；
- 普通代码提交不得默认附带“请用户运行完整测试”；
- 本地 snapshot 一旦上传，后续处理必须在 assistant 环境完成。


## D-024 — Prospective outcome cohort 采用严格 pre-terminal enrollment gate

**状态：Frozen M4 outcome-enrollment contract**

`prospective_new` 只表示 candidate 在 T0 之后首次出现，不自动等于可以进入未来胜率/收益 outcome cohort。

正式 outcome enrollment 必须同时满足：

1. candidate 属于 `prospective_new`；
2. 首次达到 outcome eligibility 时 geometry 仍为 `forming`；
3. canonical Source lifecycle 处于 terminal 之前：
   - `approaching_source_prz`；
   - `entered_source_prz`；
   - `waiting_terminal`；
4. Source Raw PRZ 已解决且 low <= high；
5. Source Terminal 尚未在该记录之前发生；
6. 5-0 不允许进入；
7. Alternate Bat 在 source conflict 解除前不允许进入。

如果 candidate 在首次出现时 Source PRZ 尚未解决，可以继续保留为 `prospective_new` observability evidence；只有后续在 terminal 之前首次满足上述条件的交易日，才冻结 `outcome_enrollment_trade_date`。

一旦 candidate 正式进入 prospective outcome cohort，后续 lifecycle 即使进入 terminal / Type-I / Type-II / invalidated，cohort membership 继续保留，用于真实前瞻路径追踪。

T0 的 `baseline_existing` 永久 `prospective_outcome_eligible=false`，不能因为后续继续出现而升级成 outcome cohort。

原因：

只按“首次在 T0 后出现”入组仍可能把 late-discovered completed geometry、Source clock unavailable、Source PRZ unresolved 或 Alternate Bat fail-closed 候选错误纳入 outcome 统计，重新引入 hindsight / source-fidelity 污染。

验证方式：

- Alternate Bat outcome gate regression；
- completed-at-first-observation regression；
- unresolved -> later resolved pre-terminal enrollment regression；
- baseline never-upgrades regression；
- outcome enrollment date persistence regression。


## D-025 — Snapshot manifest 是 M4 捕获时间轴的权威来源

**状态：Frozen M4 chronology contract**

M4 的 lifecycle journal 只记录 candidate 行，因此不能单独证明某个交易日是否完成过全市场 snapshot。正式 capture chronology 必须由独立 append-only snapshot manifest 提供。

决定：

1. 每次完整 M4 capture 无论 candidate_count 为 0 或大于 0，都必须写入一条 manifest；
2. manifest 固定记录 code_head、as_of_trade_date、instrument coverage、candidate_count、clean-worktree 与边界字段；
3. 同一 as-of date 只能有一个 code_head；
4. 同日同 head 重跑只有在 capture facts 完全一致时才允许幂等；
5. manifest candidate_count 必须等于同日 journal row count；
6. manifest 激活以后，journal 出现某个日期却没有对应 manifest 时 fail closed；
7. manifest 激活前的旧 T0 journal 允许作为 `legacy_pre_manifest_dates`；
8. transition / prospective observation 必须使用 manifest chronology，而不是从 candidate 行猜测“哪天采过”；
9. `captured_snapshot_index` 只是已捕获快照序号，不等于完整交易日序号；
10. scanner absence 只表示在一个确认已采集的 snapshot 中候选未出现，不等于 invalidated。

原因：

如果没有独立 capture manifest，candidate_count=0 的完整采集日会在 journal 中完全消失，无法区分“候选真的缺席”与“当天根本没采集”，会污染 disappearance/reappearance 与 outcome window。

验证方式：

- zero-candidate manifest regression；
- manifest/journal code-head cross-check；
- manifest/journal candidate-count cross-check；
- post-activation missing-manifest fail-closed；
- zero-candidate gap -> scanner_disappeared -> scanner_reappeared regression。


## D-026 — Committed capture transaction 是 M4 Phase 2.5 之后的权威证据单元

**状态：Frozen M4 atomic-evidence contract**

从 Phase 2.5 起，未来 M4 snapshot 不再把 lifecycle journal 与 snapshot manifest 的两次独立 append 当作正式原子证据。

正式决定：

1. 每个完整 capture 先构造一个 deterministic `transaction_id`；
2. transaction identity 由 code head、as-of date、完整 instrument coverage 与 canonical candidate facts 决定，不由 capture wall-clock time 决定；
3. 一次 capture 的 journal rows 与 capture metadata 被封装进单个 immutable committed-capture JSON；
4. committed capture 使用 temp file + flush + fsync + `os.replace` 原子落盘；
5. 只有最终 committed JSON 才是正式 future evidence；临时文件与 compatibility mirror 不进入 transition / observation；
6. 第一次 future transaction 前，将旧 T0 journal 原子冻结成 immutable legacy baseline；
7. future reports 正式读取：
   **frozen legacy baseline + committed capture transactions**；
8. lifecycle_journal.jsonl 与 snapshot_manifest.jsonl 从此是兼容/人工检查镜像；镜像缺失、半写或损坏不得改变已经 committed 的正式证据；
9. 同一交易日只能存在一个 committed transaction；
10. 相同事实、不同 capture 时间的重跑必须幂等；
11. 同日事实漂移、transaction 文件改名、transaction-id/row-id 篡改、instrument coverage 不完整全部 fail closed；
12. transaction 日期必须严格晚于 frozen legacy baseline cutoff；
13. committed transactions 禁止历史 backfill；
14. transaction store 激活后，不允许用新代码重新生成/覆盖 frozen T0。

原因：

两个独立 JSONL append 无法获得真正跨文件原子性。单一 immutable transaction file 可以把“完整 capture 是否存在”缩成一个原子文件事实，并允许兼容镜像在中断后自行恢复，而不污染正式研究时间轴。

验证方式：

- deterministic transaction-id test；
- same-facts/different-capture-time idempotency；
- zero-candidate committed capture；
- temp partial-file ignored；
- frozen baseline immutability；
- same-day fact drift rejection；
- baseline-day overwrite rejection；
- committed-transaction backfill rejection；
- transaction filename / row transaction-id tamper rejection；
- frozen baseline + committed captures coexistence。


## D-027 — 确认全天停牌保留 lifecycle continuity，但不是 traded observation

**状态：Frozen M4 suspension-continuity contract**

A 股全天停牌日通常没有新的日 K 线。M4 不允许因此把已有 harmonic candidate 误记为 `scanner_disappeared`，也不允许把停牌前最后一根 K 线伪装成停牌日价格。

正式决定：

1. 只有 `security_daily_event` 对目标交易日存在**正面事件记录**且 `trading_status='suspended'` 时，才允许 stale daily bar 作为“确认全天停牌”豁免；
2. 当前 AKShare event feed 是 positive-evidence-only，记录本身足以证明该证券发生全天停牌；不要求 `resolution_complete=true`；
3. `intraday_suspended` 不属于全天停牌豁免，仍要求目标交易日实际 bar；
4. 无 event row 不等于正常交易；stale + 无 confirmed full-day suspension 继续 hard fail；
5. confirmed suspended event 与目标交易日真实 bar 同时存在属于 evidence conflict，hard fail；
6. 全天停牌 carry-forward：
   - candidate 仍为 scanner present；
   - capture `as_of_trade_date` 记目标交易日；
   - `underlying_last_trade_date` 保留最后真实成交日；
   - `market_observation_status='confirmed_full_day_suspended'`；
   - execution gate 强制 `blocked_suspended`；
   - 当日 OHLC/volume 必须为 null；
   - lifecycle / Source Raw PRZ 只做无新价格情况下的连续性延续，不被 A 股规则层修改；
7. confirmed suspension carry-forward 不是 traded observation；
8. candidate 若首次在 suspended carry-forward snapshot 中出现，不允许在该日首次进入 prospective outcome cohort；
9. 已经在此前 traded snapshot 正式 outcome-enrolled 的 candidate，停牌日继续保留 cohort membership；
10. prospective observation 单独统计 suspended snapshot count，不把它与 scanner absence 或可交易观察混为一谈。

原因：

将合法全天停牌误判为 scanner disappearance 会破坏 prospective identity；将旧 bar 复制成停牌日 bar 则会制造不存在的价格路径。D-027 同时避免这两类污染。

验证方式：

- full-day suspended vs intraday event query regression；
- stale bar + confirmed suspension carry-forward regression；
- fake OHLC prohibition；
- execution blocked_suspended regression；
- first-seen suspended outcome-enrollment rejection；
- already-enrolled candidate continuity across suspension；
- suspension event + current-day bar conflict fail closed。


## D-028 — Prospective committed evidence is bound to one deterministic methodology fingerprint

**状态：Frozen M4 methodology-provenance contract**

M4 前瞻证据不能只依赖 `code_head` 判断方法是否相同。普通文档或基础设施提交会改变 commit SHA，而真正需要防止的是 harmonic identity、Source Raw PRZ、Source lifecycle、BAMM evidence、特殊形态 source handling 或 prospective enrollment 规则发生变化后继续把新旧样本混在一个 cohort。

正式决定：

1. 新的 authoritative committed capture 使用 transaction schema v2；
2. 每个 transaction 必须携带 `methodology_contract_version` 与 64 位 SHA-256 `methodology_fingerprint`；
3. methodology fingerprint 由固定、有序的核心方法文件清单逐文件 SHA-256 后再次聚合得到；
4. methodology identity 进入 transaction identity，因此方法变化必须改变 transaction ID；
5. 同一个 active M4 committed-capture chain 只允许一个 methodology identity；
6. 已有 committed capture 与新 capture fingerprint 不一致时 fail closed，禁止静默混样；
7. pre-fingerprint schema-v1 transaction 可以读取用于显式迁移审计，但不能继续追加到 active fingerprinted chain；
8. evidence-health 必须将当前代码 fingerprint 与 authoritative chain fingerprint 对比；不一致为 hard blocker；
9. mismatch 不会篡改或否定旧 committed evidence，只表示当前代码不能继续该证据链；
10. 若确需改变核心方法，必须建立显式 versioned methodology epoch / 新 protocol，而不是覆盖旧 transaction；
11. frozen T0 baseline 不补写 fingerprint，因为它是既有 baseline inventory，且永久不进入 prospective outcome inference；
12. compatibility manifest 与 derived reports 暴露 fingerprint，但 mirror 仍不是权威证据；
13. methodology identity 只证明研究规则 provenance，不证明 alpha / 胜率 / 盈利能力。

原因：

前瞻研究最危险的污染之一不是文件损坏，而是研究规则在样本积累中途改变却仍按同一个 cohort 统计。D-028 将“使用了哪一套方法”提升为 authoritative evidence 的一部分，使规则漂移像数据篡改一样可检测、可阻断。

验证方式：

- methodology fingerprint deterministic regression；
- core-method file changed -> fingerprint changes；
- missing fingerprint source file fail closed；
- transaction ID changes when methodology changes；
- committed chain methodology drift rejection；
- pre-fingerprint schema-v1 explicit migration regression；
- evidence-health current-vs-chain mismatch hard blocker；
- compatibility manifest methodology drift detection / repair regression。


## D-029 — 私有 M1 前瞻采集必须在更新数据前通过本地 checkout preflight

**状态：Frozen M4 private-capture preflight contract**

用户电脑只用于 assistant 无法访问的私有 M1 数据采集，不承担常规测试。第一次及后续 prospective capture 在触碰 M1 数据前，必须先证明本地 checkout 满足冻结协议。

正式决定：

1. `运行M4真实A股生命周期快照.bat` 在任何 M1 update 前执行 preflight；
2. 必须位于 `m4/real-a-share-validation-workflow`；
3. 当前 HEAD 必须包含最低安全 checkpoint `3bd0c236d5f1318caf0b6125f9f99ef1f113e0af`；
4. detached HEAD、错误分支、缺少最低 checkpoint 或与冻结协议分叉均 fail closed；
5. worktree 必须 clean，dirty/untracked 改动在 M1 update 前阻断；
6. preflight 失败时不得运行 M1 update，不得写 authoritative capture；
7. 该规则只保护采集入口与 provenance，不修改 harmonic identity、Source Raw PRZ、Source lifecycle、BAMM 或 outcome enrollment 语义；
8. 用户本机仍不作为常规 QA runner；除私有 M1 数据不可替代外，测试/审计由 assistant 侧完成。

原因：

M4 的第一批真实 prospective evidence 一旦写入 immutable transaction chain，就不应由过旧、错误分支或本地修改过的 checkout 启动。仅检查 capture 时的 `worktree_clean` 不足以证明用户启动前所处协议版本正确，因此入口必须先 fail closed。

验证方式：

- wrapper static contract regression；
- branch/checkpoint preflight 位于 M1 update 之前；
- dirty-worktree preflight 位于 M1 update 之前；
- failure path 明确声明未启动 M1 update / authoritative capture。


## D-030 — Evidence bundle 必须先验证再原子发布，blocked evidence 仍可诊断传输

**状态：Frozen M4 transport-integrity contract**

M4 evidence bundle 是非权威运输层，但它必须可靠地把 frozen baseline、immutable captures 与 derived reports 交给 assistant。运输层损坏不能被误认为 evidence failure，也不能覆盖掉一个原本完好的 bundle。

正式决定：

1. bundle manifest 对每个成员记录 `size_bytes` 与 SHA-256；
2. verifier 必须拒绝重复成员、未列入 manifest 的额外成员、不安全路径、缺失成员、size/SHA mismatch；
3. verifier 必须检查 `alpha_inference_allowed=false`、`is_trade_instruction=false`、`authoritative_evidence_modified=false`；
4. `transport_bundle_ready` 不得同时携带 evidence-health blocker 或 committed-capture read error；
5. `evidence_health_blocked` 可以是**运输完整**的诊断包：它通过 transport integrity，但明确产生 warning，不被解释为 evidence ready；
6. exporter 先写临时 ZIP，先验证临时 ZIP；只有验证通过才原子替换正式 `m4-evidence-bundle.zip`；
7. 原子替换后再验证正式路径，防止发布阶段发生不可见变化；
8. bundle verifier 不修改 authoritative evidence，不修复 transaction，不参与 harmonic methodology fingerprint；
9. 用户无需额外执行验证动作；必要的私有 M1 一键采集流程内部完成 bundle 生成与验证，上传后 assistant 也可独立复验。

原因：

运输层不是权威证据，但如果运输层无法证明自身完整性，assistant 无法可靠地区分“原始 evidence 有问题”和“ZIP 在交接过程中损坏”。先验证临时包再原子发布，可以在不增加用户操作的前提下把这两类故障分离。


## D-031 — T1/Tn 交接必须从 authoritative evidence 重算，不信任 ZIP 内派生报告

**状态：Frozen M4 evidence-intake contract**

运输完整只说明 ZIP 没有在交接层损坏，不等于其中的研究状态已经通过。收到 T1/Tn handoff 后，assistant 必须从 frozen baseline + immutable committed transactions 重新验证并重新计算 lifecycle / prospective observation，再与 bundle 中的 derived reports 对账。

正式决定：

1. intake 第一层先执行 D-030 transport verification；
2. 只有 transport-valid 的 authoritative members 才进入隔离临时目录；
3. committed captures 必须重新经过 transaction validator，不能只信 manifest；
4. frozen baseline identity / cutoff 必须重新验证；当前 T0 cutoff 固定为 `2026-09-17`；
5. capture timeline 必须从 authoritative evidence 重建；
6. lifecycle transitions 必须重新计算；
7. prospective observations / outcome enrollment facts 必须重新计算；
8. ZIP 中 transition / observation reports 只作为派生缓存；与重算结果不一致为 hard blocker；
9. bundle-level methodology、capture count、latest date、transaction ID、code head、clean-worktree provenance 必须与 committed chain 一致；
10. `evidence_health_blocked` 即使运输完整，intake 仍必须 `not_ready`；
11. 缺失 derived report 可以从 authoritative evidence 重算并 warning，不因此否定 transaction 本身；
12. intake 只报告事实观测，不计算 return / MFE / MAE / win rate / alpha / 买卖评分；
13. intake 属于 evidence-consumption 层，不改变 harmonic identity、Source Raw PRZ、Source lifecycle、BAMM 或 prospective enrollment，因此不进入 methodology fingerprint。

原因：

如果直接信任 ZIP 内的 derived reports，就可能出现“transaction 是新的，但 report 是旧的”或“外层 manifest 与内层 authoritative chain 不一致”而未被发现。前瞻研究必须以 immutable authoritative evidence 为唯一事实源，派生报告随时可以重算。



## D-032 — Outcome-enrolled candidate scanner 缺席后必须继续独立市场 follow-up；methodology contract 升级为 v2

**状态：Frozen M4 cohort-followup / methodology-v2 contract**

M4 的 prospective outcome cohort 一旦正式入组，后续不能因为 scanner 不再返回该 harmonic candidate 就停止观察该证券的真实市场路径。否则最终 outcome 样本会系统性偏向“持续被 scanner 看见”的候选，形成 survivorship / informative-censoring 污染。

正式决定：

1. 已正式 `prospective_outcome_eligible=true` 的 candidate，后续完整 capture 日若 scanner 不再返回该 candidate，仍必须记录独立 `cohort_followup_row`；
2. follow-up 永远保持 `scanner_presence='absent'`，不得伪装成 candidate 仍存在；
3. follow-up 不拥有 `source_lifecycle_state`、`action_state`、Source PRZ 或 pattern identity，不延长/恢复 harmonic lifecycle；
4. traded follow-up 必须来自目标 capture 日真实 bar，`underlying_last_trade_date == as_of_trade_date`，并记录 OHLC/volume；execution gate 固定为 `followup_observation_only`；
5. confirmed full-day suspension follow-up 必须有正面 suspension evidence，保留 prior underlying trade date，OHLC/volume 必须为 null，execution gate 为 `blocked_suspended`；
6. schema v3 committed transaction 同时封装 scanner-present `journal_rows` 与 scanner-absent `cohort_followup_rows`；
7. follow-up rows 进入 deterministic transaction identity；篡改 follow-up 必须改变/破坏 transaction identity；
8. 对 schema v3，每个 capture 的 follow-up keys 必须严格等于：
   **prior outcome-enrolled cohort keys − current scanner-present keys**；
   少一条或多一条均 fail closed；
9. follow-up candidate 必须在此前已经 outcome-enrolled；instrument identity 与 frozen enrollment date 不得漂移；
10. previously enrolled instrument 若从 initialized listed universe 消失，在没有明确 listing-end protocol 前 hard fail，不允许静默丢失 follow-up；
11. prospective observation report 对 scanner-absent follow-up 使用真实 market facts，但 lifecycle/action 保持 null；
12. scanner absence 仍不等于 invalidated；market follow-up 也不等于 scanner reappearance；
13. Phase 2 仍不计算 return / MFE / MAE / win rate / alpha；follow-up 只是先把未来 outcome 所需的无偏市场路径保存下来；
14. methodology contract 从 v1 升级为 **v2**；fingerprint 组件由 32 扩为 **37**，新增：
    - `capture_transaction.py`
    - `cohort_followup.py`
    - `lifecycle_transitions.py`
    - `prospective_observations.py`
    - `snapshot_manifest.py`
15. 第一笔 post-T0 committed capture 尚未产生，因此 v2 升级发生在 prospective evidence chain 启动前，不需要迁移/重写历史 future evidence；
16. frozen T0（2026-09-17）保持不变，仍只是 baseline inventory；
17. 私有 T1 一键采集最低安全 checkpoint 提升到 `084ddf649e031e8169a761fd3b8578f73b31b5c2`。

原因：

只记录 scanner 是否仍返回 candidate，不足以支撑未来 outcome 研究。candidate 的 scanner identity 可以消失，但证券的真实价格路径仍然继续。D-032 将“形态存在性”和“入组后市场路径”永久分离，并把这组语义纳入 methodology fingerprint，防止样本积累过程中偷偷改变 censoring / follow-up 规则。



## D-033 — 第一笔 T1 前 methodology v2 采用精确组件代码冻结，不只检查 ancestry

**状态：Frozen M4 pre-T1 methodology code-freeze contract**

methodology contract v2 / 37 个组件已经在提交 `084ddf649e031e8169a761fd3b8578f73b31b5c2` 完成冻结。仅要求当前 HEAD “包含这个提交”仍不够，因为后续提交仍可能修改 methodology 组件后继续通过 ancestry 检查。

正式决定：

1. 当前 T1 methodology freeze commit 固定为 `084ddf649e031e8169a761fd3b8578f73b31b5c2`；
2. 第一笔以及后续同一 methodology epoch 的私有 M1 authoritative capture 前，必须运行 `m4_methodology_freeze_guard.py`；
3. guard 必须验证 methodology contract version = 2；
4. guard 必须验证 fingerprint component count = 37；
5. frozen commit 必须是当前 HEAD 的 ancestor；
6. 37 个 component path 必须全部存在；
7. `git diff 084ddf... HEAD -- <37 methodology paths>` 必须为空；
8. 任一 methodology component 在冻结点之后发生任何改动，都必须在 M1 update 之前 fail closed；
9. guard 失败时不得更新私有 M1、不得创建 authoritative transaction；
10. guard JSON 作为非权威 provenance report 随 `m4-evidence-bundle.zip` 交接；
11. docs/tests/intake/transport 等明确不在 37 个 methodology component 内的改动可以继续，不触发 methodology drift；
12. 若未来确需修改 methodology component，必须显式开启新的 methodology decision/epoch；不得仅提高 minimum-safe commit 来绕过冻结；
13. 当前从 freeze commit 到 D-033 冻结时的仓库差异已审计，37 个 methodology component 改动数为 0。

原因：

methodology fingerprint 可以在 transaction 生成时记录“实际用了哪套规则”，但第一笔 future capture 之前还没有旧 transaction 可供 current-vs-chain 比较。D-033 增加一个**事前冻结锚点**，确保第一笔 T1 本身就是经过审计的 methodology v2，而不是某个后来悄悄修改过的版本。



## D-034 — Prospective evidence 必须冻结价格基准 provenance；schema v4 / methodology v3 取代 pre-T1 v2 freeze

**状态：Frozen M4 price-basis provenance contract**

在第一笔 post-T0 authoritative future capture 产生之前，审计发现一个会污染未来 outcome 统计的价格标尺缺口：

HT-CN 正式谐波分析使用 QFQ 连续价格；但此前 M4 journal / follow-up 未保存分析时的价格基准身份，且 raw fallback 理论上仍可能进入 prospective enrollment。若候选入组后发生除权除息或上游 QFQ 因子历史重标，后续 OHLC 与入组时 PRZ/目标可能处于不同标尺，直接计算 target hit / MFE / MAE 会产生错误。

正式决定：

1. 正式 prospective harmonic evidence 仅接受 `price_mode in {qfq, qfq_carry_forward}`；
2. `raw` fallback 仍可用于展示/诊断，但：
   - `eligible_for_validation=false`；
   - 不得进入 strict prospective outcome cohort；
   - authoritative full-universe capture 遇到任何 non-formal price basis 时整轮 fail closed；
3. 每次正式 analysis 输出 `price_basis_id`；
4. QFQ `price_basis_id` 是对按日期排序的 **QFQ factor change-point sequence** 做确定性 SHA-256：
   - 仅新增相同 factor 的 carry-forward 日期，不改变 basis ID；
   - 新增/修订 factor regime 时改变 basis ID；
5. M4 `LifecycleJournalEntry`、scanner-absent `cohort_followup_rows` 均保存 `price_mode + price_basis_id`；
6. committed capture schema 从 v3 升级为 **v4**；
7. schema v4 journal/follow-up row 缺失合法 QFQ basis 时 hard fail；
8. v1-v3 transaction 仍可用于历史读取/审计，但不得静默续接 v4 active chain；
9. D-024 prospective enrollment 增加正式价格基准 gate；
10. prospective observation schema 升级为 v3，并冻结：
    - enrollment price mode；
    - enrollment price basis ID；
    - 每个 observation 当前 price basis；
    - `price_basis_matches_enrollment`；
    - basis drift count / first drift date；
11. 已入组 candidate 后续 scanner-present 或 scanner-absent follow-up 只要有真实 observation，就必须带 price basis provenance；
12. basis drift 是事实 evidence，不等于 candidate invalidated，也不等于 scanner disappearance；
13. Phase 2 不自动 rebase PRZ/target，也不在不同 basis 间直接计算 return/MFE/MAE；
14. 发生 basis drift 时 intake 给出 warning：
    `price_basis_drift_present_future_outcome_rebase_required`；
15. 未来 outcome protocol 若要跨 basis 计算，必须另行预注册显式 rebasing 规则；在此之前相关 outcome 保持 unresolved；
16. methodology contract 从 v2 升级为 **v3**，component count 保持 37；
17. v3 exact methodology freeze commit：
    `2b0aa92d292410098d9678a3bfd3102f3df1ed4b`；
18. D-033 的 v2 exact freeze 是有效的历史 pre-T1 checkpoint，但已在第一笔 future capture 之前被 D-034 显式 supersede；
19. 第一笔 post-T0 committed future capture 仍未产生，因此 v3 升级没有迁移、重写或混合任何 future evidence；
20. QFQ price-basis provenance 不改变 Carney harmonic identity / Fibonacci ratios / Source Raw PRZ source definitions；它只冻结 A 股数据层用于 prospective evidence 的价格标尺身份。

原因：

未来 outcome 研究必须先保证“比较的是同一个价格标尺”。在没有 provenance 的情况下，除权除息后的 QFQ 重标可能把真实市场路径与入组时的 harmonic price levels 放到不同坐标系。D-034 选择 fail-safe 记录 basis drift，而不是在看到样本后临时选择 rebasing 方法。



## D-035 — Outcome enrollment 必须冻结可重建 Source execution clock 的最小 seed；schema v5 / methodology v4

**状态：Frozen M4 source-clock reconstruction contract**

在 Phase 2.11 price-basis provenance 收口后，对未来 outcome protocol 做数据充分性审计时发现：

scanner-absent follow-up 虽然可以继续保存真实 OHLC，但如果 candidate 在 Source Terminal 出现之前从 scanner 消失，仅有 direction + frozen Source Raw PRZ + future OHLC 仍不足以无损重建现有 `observe_source_execution()` 时钟。该函数还需要：

- forming projection 的 observable signal time；
- reaction anchor price。

如果这些事实不在 enrollment 时冻结，未来 Type-I / Type-II source-event 研究会对“持续被 scanner 看见”的 candidate 产生 informative censoring。

正式决定：

1. strict prospective outcome enrollment 必须冻结最小 Source-clock seed：
   - `source_signal_trade_date`
   - `source_signal_clock_basis`
   - `source_reaction_anchor_label`
   - `source_reaction_anchor_price`
2. 当前 signal clock basis 固定为：
   `last_frontier_pivot_confirmed_at=index+scale`；
3. reaction anchor 使用现有 Source execution 规则：
   - Shark / `0XABC`：B；
   - XABCD / standalone AB=CD：A；
4. 这些字段直接来自 forming payload 已有 `execution_clock`，不重新推导、不发明新的 harmonic identity；
5. candidate 若缺任一 seed 字段，D-024 outcome enrollment fail closed，reason：
   `source_clock_seed_unresolved`；
6. signal trade date 晚于当前 observation 时 fail closed，reason：
   `source_clock_seed_after_observation`；
7. journal row 可完全没有 seed（例如非 enrollment candidate），但不得只保存部分 seed；
8. committed capture schema 从 v4 升级为 **v5**：
   - seed 四项要么全有、要么全无；
   - partial seed hard fail；
   - v1-v4 只保留历史读取兼容，不得静默续接 v5；
9. prospective observation schema 从 v3 升级为 **v4**；
10. outcome enrollment candidate summary 永久冻结 `enrollment_source_clock_seed`，包含：
    - pattern_id / schema / direction / scale；
    - enrollment lifecycle；
    - frozen Source Raw PRZ；
    - signal trade date / signal clock basis；
    - reaction anchor label / price；
11. candidate 入组后 scanner 消失：
    - scanner presence 仍为 absent；
    - follow-up 不拥有 lifecycle；
    - frozen enrollment seed 不被删除；
    - future source-event evaluator 可用 frozen seed + authoritative market observations 重建 Source execution clock；
12. candidate 后续变 completed 时，不要求 completed payload 重复携带 forming execution_clock；enrollment seed 已经冻结；
13. seed 不修改 harmonic identity、Fibonacci ratios、Source Raw PRZ、BAMM 或 candidate key；
14. seed 不构成交易指令、胜率或 alpha；
15. 若 price basis 后续 drift，D-034 继续优先：在显式 rebasing protocol 冻结前，不允许跨 basis 直接计算 target hit / return / MFE / MAE；
16. methodology contract 从 v3 升级为 **v4**，component path count 保持 37；
17. methodology-v4 exact freeze commit：
    `c774c54928c33361952bf1a612a8555633449625`；
18. D-034 的 methodology-v3 freeze 是有效历史 checkpoint，但在第一笔 T1 之前已被 D-035 显式 supersede；
19. 第一笔 post-T0 future committed capture 仍未产生，因此 v4 升级没有迁移、重写或混合任何 future evidence。

原因：

Prospective research 不能让 scanner visibility 决定一个已入组 candidate 是否继续拥有可计算的 source outcome。D-035 把 forming 时已经可观察的 source-clock 起点冻结下来，使 scanner presence 和 future source-event reconstruction 永久解耦。



## D-036 — M4 Outcome Protocol v1 在第一笔真实 outcome 前预注册；Source-event 与 market-path 分层

**状态：Historical preregistration — superseded by D-037 before first real prospective outcome**

在 T0 之后尚未产生第一笔真实 future committed capture、尚未看到任何 prospective outcome 的前提下，冻结 M4 第一版 outcome protocol。

正式决定：

1. outcome protocol 与 capture methodology 分开版本化：
   - capture methodology：v4 / schema v5；
   - outcome protocol：`m4-outcome-v1`；
2. outcome cohort 只接受 authoritative evidence 中 `prospective_outcome_eligible=true` 的 candidate；
3. T0 baseline、pre-enrollment historical Source Terminal、5-0、fail-closed Alternate Bat 不得进入 outcome cohort；
4. outcome market path 不以 `captured_snapshot_index` 代替交易日序列；
5. source-event reconstruction 使用本地 M1 **base + daily_delta logical daily history** 的完整 traded-bar path，以解决用户没有每天运行 capture 时的 observation gap；
6. outcome path 只允许与 enrollment `price_basis_id` 相同的正式 QFQ basis；若 basis drift：
   - drift 前可成熟的 source facts 保留；
   - drift 后需要价格比较的 metric 记 unresolved；
   - v1 不自动 rebase；
7. outcome evaluator 必须复用现有：
   - `observe_source_execution()`
   - `derive_source_lifecycle()`
   禁止复制一套略有差异的 Terminal / Type-I / Type-II 公式；
8. frozen enrollment Source-clock seed 是 reconstruction 起点；
9. 若重建发现 Source Terminal 早于 outcome enrollment，记为 evidence contradiction，禁止把它当正常 outcome；
10. full-day suspension 不计为 traded bar；固定 bar window 只按真实 traded bars 计数；
11. Phase 3.0 primary source-event facts：
    - Source Terminal observed / not yet observed；
    - terminal trade date / terminal price；
    - Type-I 38.2% target 是否在 T+1...T+5 traded bars 内命中；
    - 38.2% / 61.8% first-hit traded-bar offset；
    - reaction-only later 38.2%；
    - first Source PRZ exit；
    - Type-II re-entry；
    - strict Type-II terminal-side retest；
    - post-Type-II reversal-direction exit；
12. 对 Shark：
    - generic 38.2% / 61.8% 仅作为 canonical Type-I reaction classification；
    - **不得**把它称为 Shark-specific management target；
    - Shark 专属 “50% vs Reciprocal AB=CD first target” 不进入 outcome-v1，除非后续单独冻结完整 target input protocol；
13. Type-II price path 只标为 `type_ii_price_structure_evidence`；
    未同时满足单独 indicator-confirmation protocol 时，不得写成完整 Carney Type-II reversal proof；
14. market-path descriptive metrics 只在 Source Terminal 后计算：
    - 5 traded bars：primary source-aligned window；
    - 10 / 20 traded bars：预注册 secondary descriptive windows；
15. 每个窗口记录：
    - MFE；
    - MAE；
    - MFE / MAE 占 `abs(reaction_anchor_price - terminal_price)` 的 span units；
    - MFE / MAE 占 terminal price 的百分比；
16. post-terminal window 不包含 T-Bar 本身，从 T+1 开始；
17. 5/10/20-bar metric 只有在对应 traded bars 全部可观察、价格 basis 未中断时才成熟；不足时标 immature，不用部分窗口冒充完整窗口；
18. v1 不定义 stop-loss、entry price、position size、fees、T+1 execution P&L，因此不计算交易收益；
19. v1 不定义“盈利/亏损”“胜/负”二元标签，不输出 win rate；
20. v1 不做 alpha、benchmark excess return、p-value、显著性、策略排名；
21. terminal 未出现或 Type-II 尚未完成的 candidate 保持 right-censored / ongoing，不机械记失败；
22. 每次 outcome extraction 必须记录：
    - candidate key；
    - enrollment methodology fingerprint；
    - outcome protocol ID；
    - outcome as-of trade date；
    - M1 price basis ID；
    - reconstructed traded-date path；
    - canonical path SHA-256；
23. 同一 candidate + same outcome as-of 若 canonical market-path hash 变化，必须报告 data drift，不得静默覆盖旧 outcome evidence；
24. outcome-v1 的机器可读协议冻结在 `research/m4-outcome-protocol-v1.json`；
25. 第一版 evaluator 必须逐字段服从该协议；任何 metric/window/denominator 变化都需要新的 outcome protocol version，不能改写 v1；
26. outcome-v1 是 descriptive prospective validation，不是盈利证明。

Source 对齐：

- Carney Volume III：Type-I first PRZ test、Terminal Price Bar、3-5 bars immediate confirmation、38.2%/61.8% automatic objectives；
- Type-II 是 secondary PRZ retest，且完整 reversal 需要价格与 indicator confirmation；
- HT-CN 的完整 M1 path、QFQ basis、path hash、5/10/20 secondary windows 属于 A-share research engineering，不冒充 Carney 原文。

## D-037 — Outcome evidence 使用独立 protocol + engine epoch；v2 在第一笔真实 outcome 前取代 v1

**状态：Frozen M4 Phase 3.1 outcome-evidence contract**

在第一笔真实 post-T0 prospective outcome 产生之前，对 D-036 outcome-v1 实现做可执行审计，发现两个必须先收口的问题：

1. v1 的直接 MFE/MAE 差值在 post-terminal price 未越过 Terminal 时理论上可产生负 excursion，而标准 excursion 应是非负幅度；
2. 只冻结“算什么”的 protocol fingerprint 与“候选怎么产生”的 capture methodology fingerprint 仍不足以证明未来 outcome 使用了同一版 evaluator 实现。

正式决定：

1. `m4-outcome-v1` 保留为有效历史 preregistration，不改写；
2. 在尚无任何真实 prospective outcome result 时创建 `m4-outcome-v2`，显式 supersede v1；
3. v2 canonical SHA-256 固定为：
   `5822b302e11d197682dc4bb6d835fb0a3b2d62fc97f788c7a323ecda2770555b`；
4. v2 的 MFE/MAE 定义为 nonnegative magnitude，并 zero-floor：
   - bullish MFE = max(0, max high - terminal)；
   - bullish MAE = max(0, terminal - min low)；
   - bearish MFE = max(0, terminal - min low)；
   - bearish MAE = max(0, max high - terminal)；
5. v1 validator 保留，历史协议可重放；active protocol 切换为 v2；
6. outcome evaluator 必须复用：
   - `observe_source_execution()`
   - `derive_source_lifecycle()`
   禁止复制第二套 Terminal / Type-I / Type-II 实现；
7. outcome path 使用 M1 base + daily_delta logical history 的真实 traded bars；
8. 5/10/20 traded-bar windows 从 T+1 开始，不包含 Terminal bar；
9. Terminal 未出现属于 right-censored ongoing，不机械记失败；
10. basis drift 不自动重基准；跨 basis 价格比较保持 unresolved；
11. 每个 outcome result 必须保存 canonical `market_path_rows`，不再只保存 path hash；
12. canonical market path 包含 trade_date + OHLCV + price_basis_id，并保存 SHA-256；
13. evidence bundle 离开私有 M1 后必须能使用 snapshot OHLCV + frozen enrollment seed 离线重跑 evaluator；
14. outcome snapshot 升级为 **schema v2**；
15. snapshot v2 绑定：
    - outcome protocol ID/fingerprint；
    - capture methodology fingerprint；
    - outcome engine contract/fingerprint；
16. 同 as-of 同事实可幂等；同 as-of fact drift fail closed；
17. outcome snapshot 禁止 historical backfill；
18. 同一 outcome evidence chain 禁止混用不同：
    - outcome protocol；
    - capture methodology；
    - outcome engine；
19. Outcome Engine contract v1 的组件固定为 4 个：
    - `outcome_protocol.py`
    - `outcome_evaluator.py`
    - `outcome_snapshot.py`
    - `outcome_engine_identity.py`
20. Outcome Engine v1 exact code anchor：
    `9cbc0d3d30ac5f0a87748a39788cbee04a44bcc8`；
21. `m4_outcome_engine_freeze_guard.py` 必须在 M1 update 前检查：
    - engine version = 1；
    - component count = 4；
    - anchor ancestry；
    - 4 component 相对 anchor 零 diff；
    - active protocol v2 canonical fingerprint；
22. outcome-engine guard 失败时：
    - 不更新私有 M1；
    - 不创建 authoritative capture；
    - 不创建 outcome snapshot；
23. one-click Phase 3.1 minimum-safe workflow checkpoint 固定为：
    `c34026755b3b8c491759eaacdb45376d4e1db485`；
24. minimum-safe workflow checkpoint 不取代 capture methodology exact freeze：
    - capture methodology 仍固定 D-035 / `c774c549...` / 37 components；
25. minimum-safe workflow checkpoint 也不取代 outcome engine exact freeze：
    - engine 仍固定 `9cbc0d3d...` / 4 components；
26. bundle intake 必须进行 semantic recomputation，而不只校验 ZIP SHA；
27. 即使篡改者重新生成 snapshot ID 与 transport hashes，stored outcome 与 frozen evaluator 重算结果不一致时仍 fail closed；
28. Type-II price structure 不得写成完整 Carney Type-II reversal proof；
29. Shark generic Type-I 38.2%/61.8% 不得写成 Shark-specific management target；
30. outcome-v2 仍不定义 P&L / win-loss / win rate / alpha / ranking；
31. D-037 冻结时仍没有第一笔真实 post-T0 future capture、真实 outcome cohort 或真实 outcome snapshot，因此该修正不涉及看结果后改规则。

原因：

Prospective validation 不只要冻结“研究问题”，还要冻结“输入坐标系、计算实现和可独立复算的原始路径”。D-037 把 enrollment authority、outcome protocol、outcome engine 与 transport report 四层彻底分开，避免未来代码演进或数据修订悄悄改变旧 cohort 的 outcome 口径。

## D-038 — 首次真实 T1 私有采集必须包含 hosted-CI-green checkpoint

**状态：Frozen M4 T1 acquisition safety gate**

在 Phase 3.1 hosted CI 恢复后，真实 runner 依次暴露并修复了：

- stale test-contract / fixture 不一致；
- outcome protocol bundle filename mapping 错误。

最终 hosted-CI-green checkpoint 为：

`d29870d3a2ef7b60dec4fd8f0dbef2d7a8f0b5a7`

该 checkpoint 已证明：

- Python deterministic suite：590 passed；
- Node / npm install：pass；
- Web build：pass；
- capture methodology 自 `c774c549...` 起 37/37 component 零漂移；
- Outcome Engine 自 `9cbc0d3d...` 起 4/4 component 零漂移。

正式决定：

1. 第一次真实 post-T0 T1 私有 M1 capture，不得从早于
   `d29870d3a2ef7b60dec4fd8f0dbef2d7a8f0b5a7`
   的 checkout 启动；
2. `运行M4真实A股生命周期快照.bat` 的
   `M4_MIN_SAFE_COMMIT` 提升到上述 checkpoint；
3. 本地 checkout 若不包含该 ancestor：
   - 在 M1 update 前 fail closed；
   - 不创建 authoritative capture；
   - 不创建 outcome snapshot；
4. 该 minimum-safe checkpoint 只是**采集流程/transport/testing 安全门**，
   不成为 harmonic methodology authority；
5. capture methodology exact freeze 仍由 D-035：
   `c774c54928c33361952bf1a612a8555633449625`
   + 37 components 单独拥有；
6. Outcome Engine exact freeze 仍由 D-037：
   `9cbc0d3d30ac5f0a87748a39788cbee04a44bcc8`
   + 4 components 单独拥有；
7. 后续若只修改 documentation / test / transport / local-wrapper，
   不得因此宣称 methodology 或 Outcome Engine 新版本；
8. D-023 继续有效：用户电脑只承担不可替代的私有 M1 capture，
   不作为常规测试机；
9. D-038 冻结时仍无 post-T0 real future capture，
   因此该 gate 不涉及任何 outcome 观察后调参。

原因：

第一次真正进入 prospective evidence chain 的本地运行，应至少包含已经被真实 hosted CI 验证过的完整 Phase 3.1 transport/intake 修复。仅依赖更早的功能 checkpoint 会允许不同本地 checkout 产生不同质量的 handoff evidence，即使 harmonic methodology 本身未漂移。

## D-039 — 第一次正式 T1 capture 前必须先完成 strict full-universe QFQ readiness

**状态：Frozen M4 acquisition-data readiness gate**

首个用户私有 M4 evidence bundle（code head
`276de795cbbf13c33d7aca563e225b02ece5f0c0`）暴露出一个 acquisition-pipeline 缺口：

- M1 raw daily update：55 / 55 初始化标的更新成功；
- bulk snapshot 网络请求失败后，slow-path historical repair 55 / 55 成功；
- formal capture：仅 3 / 55 通过；
- 52 / 55 被正式 QFQ gate 拒绝；
- 通过的 3 个标的恰好是历史 QFQ pilot：
  - SSE.600519
  - SSE.688256
  - SZSE.300820
- 失败原因统一为：
  `formal prospective capture requires QFQ price basis: mode=raw basis=raw`；
- authoritative capture 未提交；
- journal/manifest 未追加 T1；
- committed_capture_count = 0；
- outcome_snapshot_count = 0；
- T0 legacy baseline evidence 未被改写。

根因：

D-034 已将正式 prospective evidence 收紧到
`qfq / qfq_carry_forward` price basis，但原 one-click acquisition chain 只负责 raw daily update，没有在正式 capture 前把 QFQ factor layer 从历史 3-symbol pilot 扩到当前 initialized universe。

正式决定：

1. one-click M4 acquisition 新增独立 strict-QFQ readiness stage；
2. 顺序固定为：
   - M1 raw update；
   - strict formal-QFQ universe readiness；
   - authoritative lifecycle capture；
3. 正式 capture 只有在 initialized listed SSE/SZSE 全部可提供
   `qfq` 或 `qfq_carry_forward`
   且 basis ID 为 `qfq:...` 时才允许启动；
4. 已有 formal QFQ view 直接复用，不重复联网；
5. 仅对：
   - factor 缺失；
   - factor 历史内部缺口；
   - formal QFQ view 无法形成；
   的标的进行 build/repair；
6. build/repair provider 顺序：
   - AkShare adjusted history；
   - BaoStock adjusted history fallback；
7. 新建 factor candidate 必须满足：
   - price_factor finite；
   - price_factor > 0；
   - raw/factor overlap >= 95%；
   - factor 起点不晚于 raw 起点；
   - latest factor date 之前不存在 raw trading-date 内部缺口；
8. factor 最新日期之后的少量 raw 日期继续由已经冻结的
   `qfq_carry_forward` 规则处理；
9. factor 文件按 instrument 独立落盘，因此网络中断后可续跑，不重做已经 formal-ready 的标的；
10. 任一 initialized instrument 最终仍不是 formal QFQ：
    - QFQ stage 非零退出；
    - authoritative capture 不启动；
    - 旧 evidence 不覆盖；
11. QFQ readiness 诊断写入：
    - `artifacts/reports/m4-qfq-readiness.json`
    - `artifacts/reports/m4-qfq-readiness.log`
12. handoff bundle 包含上述 QFQ 诊断；
13. strict QFQ preparation 是 acquisition/data provisioning gate，不拥有 harmonic identity；
14. capture methodology contract 仍为 v4 / 37 components；
15. Outcome Engine 仍为 v1 / 4 components；
16. 新增 QFQ acquisition stage 后审计：
    - methodology drift = 0 / 37；
    - Outcome Engine drift = 0 / 4；
17. GitHub Actions run #1431 对该版本：
    - Python deterministic tests：success；
    - Web build：success；
    - overall：success；
18. D-039 冻结时仍无真实 post-T0 committed future capture，因此该修复没有修改任何已观察 outcome。

原因：

正式 prospective validation 已把 price coordinate system 作为 evidence identity 的一部分，就不能允许 acquisition pipeline 在 QFQ factor 尚未建立时直接进入 capture。QFQ readiness 必须成为 raw freshness 与 authoritative capture 之间的显式 fail-closed gate。

## D-040 — QFQ provider-calendar 内部微缺口只允许稳定 regime 下的安全修复

**状态：Frozen M4 acquisition compatibility rule**

第二个用户私有 evidence bundle 显示：

- initialized instruments：55；
- existing formal QFQ：3；
- 本轮成功 build/repair：50；
- formal QFQ ready：53 / 55；
- failed：2；
- authoritative capture 未启动；
- committed capture 仍为 0。

仅剩失败：

1. `SSE.600057`
   - BaoStock QFQ 缺 `2007-04-24`；
2. `SZSE.000001`
   - BaoStock QFQ 缺若干 1991 年周六历史交易日；
   - 例如 `1991-04-06 / 04-13 / 04-20 / 05-04 / 05-11`。

AkShare 对这两只仍出现 RemoteDisconnected。

正式决定：

1. 不放宽 formal-QFQ requirement；
2. 不允许任意 forward-fill 历史内部 factor gap；
3. acquisition 层允许修复 provider-calendar tiny internal gap，但必须同时满足：
   - gap 被真实 factor observation 前后夹住；
   - gap <= 10 个 raw trading sessions；
   - 前后 factor relative drift <= 0.5%；
4. 修复值采用两侧稳定 factor 的线性插值；
5. 若前后 factor drift > 0.5%，视为可能跨 corporate-action regime，继续 fail closed；
6. leading gap 不修；
7. trailing freshness 不由该规则处理，继续由冻结的 `qfq_carry_forward` 规则拥有；
8. synthetic row source 标为 `safe_internal_calendar_gap_fill`；
9. report 必须记录 gap 起止、前后 factor、relative drift 和 fill method；
10. 该规则只属于 acquisition/data-provider compatibility，不改变 harmonic identity、Source Raw PRZ、Source lifecycle 或 outcome evaluator；
11. GitHub Actions run #1446 对该版本：
    - Python deterministic tests：success；
    - Web build：success；
    - overall：success；
12. freeze audit：
    - capture methodology drift = 0 / 37；
    - Outcome Engine drift = 0 / 4；
13. D-040 冻结时仍无任何 post-T0 committed future capture，因此没有重写真实 prospective evidence。

原因：

不同 A-share 历史供应商对早期周六交易和个别历史 session 的覆盖不完全一致。只要缺口处于同一稳定 factor regime，就可以在 acquisition 层做可审计、受限的 calendar-gap repair；但不能跨潜在除权 regime 自动补值。

## D-041 — Early-A-share historical Saturday QFQ gaps require raw pre-close continuity before repair

**状态：Frozen M4 acquisition compatibility rule**

Third private M4 bundle advanced formal QFQ readiness to 54/55. The only remaining blocked instrument was `SZSE.000001`, with provider-calendar gaps on 1991 historical Saturday trading sessions.

Formal rule:

1. Generic internal factor-gap repair remains capped at <=0.5% bracketing factor drift.
2. A separate historical-Saturday path may be used only when every missing raw session:
   - is Saturday;
   - year <= 1992;
   - is bracketed by real factor observations.
3. Raw `pre_close` continuity is mandatory:
   - each missing session's pre_close must match the previous raw session close within 1%;
   - the next observed raw session's pre_close must match the last missing session close within 1%.
4. This raw-price continuity is independent evidence that the gap does not cross a corporate-action regime boundary.
5. Even then, bracketing factor drift must remain <=5%.
6. If any continuity check is missing or fails, repair is refused.
7. Repair remains linear interpolation bounded by real bracketing factors and is audit-labelled `historical_saturday_raw_preclose_continuity`.
8. Leading gaps and trailing freshness are unaffected; trailing freshness remains owned by `qfq_carry_forward`.
9. This is acquisition/data-provider compatibility only; harmonic methodology and Outcome Engine remain unchanged.
10. GitHub Actions run #1459 passed after the rule and fail-closed tests were added.
11. Freeze audit at code head `af1124dcd32bd1d719877e7d88ff74d26c6deebf`:
    - capture methodology drift = 0/37;
    - Outcome Engine drift = 0/4.
12. No post-T0 authoritative future capture existed when D-041 was frozen.

## D-042 — M5 作为只读实战产品层与 M4 prospective evidence 并行推进

**状态：Frozen M5 Phase 1 product boundary**

正式决定：

1. 新建独立分支：
   `m5/a-share-operator-workbench`；
2. M5 不继续堆在 M4 PR #13 上；
3. M5 Phase 1 的目标是 Daily Operator Queue，不是新的 harmonic engine；
4. Queue 只能消费已有：
   - source_lifecycle；
   - decision_narrative；
   - execution/context integrity；
5. Queue 不拥有 lifecycle；
6. Queue 不修改 harmonic identity；
7. Queue 不修改 Source Raw PRZ；
8. Queue 不修改 M4 enrollment 或 outcome evidence；
9. Queue 的固定工作流顺序：
   - execution_evaluation
   - reaction_observation
   - waiting
   - evidence_insufficient
10. 该顺序只表示人工观察优先级，不是预测收益排名；
11. Queue 禁止使用：
   - win rate；
   - alpha；
   - MFE/MAE outcome；
   - buy/sell score；
   - composite predictive score；
12. Queue 默认只显示 primary identity；
13. secondary identity 仍留在单票 audit；
14. 单一 instrument 失败不得拖垮整个 operator queue；
15. 首页产品结构变为：
   - 今日观察队列；
   - 单标的深度工作台；
16. M5 CI 必须执行 Playwright browser acceptance；
17. M4 prospective validation 可以继续独立积累，M5 不等待单个历史数据边角问题才开始产品化；
18. 未来若要把真实 outcome statistics 接入 queue 排序，必须另行预注册，D-042 不授权。

原因：

HT-CN 已经具备较强的单标的 source-aligned 解释能力，但缺少日常操作入口。继续扩识别规则的边际价值低于把已冻结能力组织成“全市场 -> 观察队列 -> 单票深挖”的实战工作流。

## D-043 — Operator Delta 仅为产品观察变化，不得冒充 M4 authoritative transition

**状态：Frozen M5 Phase 2 product-observation boundary**

正式决定：

1. M5 Phase 2 增加“今日变化 / Operator Delta”；
2. Queue product identity 必须优先使用 harmonic point trade_date，避免滚动窗口 index 漂移；
3. Queue snapshot schema 升级为 v2，显式记录 as_of_trade_date / observed_trade_dates / observation_integrity；
4. 只有 single_as_of snapshot 可参与日间比较；
5. mixed-as-of 不比较；
6. reverse chronology 不比较；
7. 同一交易日刷新不生成 delta；
8. 允许展示：
   - new_candidate
   - disappeared_candidate
   - action_state_changed
   - lifecycle_state_changed
   - pattern_state_changed
   - next_key_changed
   - execution_gate_changed
   - context_cautions_changed
9. 当前 instrument 分析失败时，必须抑制该 instrument 的 disappeared_candidate；
10. 浏览器只保存最近两份 product Queue snapshot；
11. localStorage snapshot 不是 research evidence，可重置；
12. Queue 始终保存完整 candidate 集；UI 的 evidence-insufficient filter 不得改变 comparison universe；
13. POST /api/operator/delta 是纯函数式比较，不持久化 evidence；
14. Operator Delta contract 永久声明：
   - authoritative_transition=false
   - writes_m4_evidence=false
   - predictive_score_used=false
   - historical_outcome_used=false
   - alpha_inference_allowed=false
   - is_trade_instruction=false
   - mutates_harmonic_identity=false
   - mutates_source_raw_prz=false
   - owns_lifecycle=false
15. 不允许用 M4 outcome statistics 在 Phase 2 中排序 change；
16. Hosted CI run #1503：
   - overall success
   - Python 619 passed
   - Web build success
   - Playwright 19 passed
17. M4 frozen methodology diff=0；
18. Outcome Engine diff=0。

原因：

实战工作台需要知道“今天发生了什么”，但产品状态差异和研究证据链不是一回事。D-043 将两者硬分离，既提升日常使用价值，又避免产生第二套伪 authoritative lifecycle history。

## D-044 — M5 每日 Queue 缓存属于产品加速层，freshness 不满足时禁止落盘为当日缓存

**状态：Frozen M5 Phase 3 product-cache boundary**

正式决定：

1. M5 可缓存完整 Operator Queue，以避免同交易日重复逐只运行 M3；
2. cache identity 必须至少绑定：
   - expected trade date
   - bars
   - scales
   - universe hash
   - cache contract version；
3. product cache 永久声明：
   - authoritative_evidence=false
   - writes_m4_evidence=false；
4. cache 不拥有 lifecycle；
5. cache 不修改 harmonic identity；
6. cache 不修改 Source Raw PRZ；
7. cache 不进入 M4 enrollment/outcome；
8. 只有 single_as_of Queue 可缓存；
9. 若有 expected local trade date，则 Queue as-of 必须与其一致；
10. 新交易日下旧 Queue 只能 live_not_cached，禁止错存成新交易日快照；
11. cache corruption / schema mismatch / universe mismatch 不得阻断 live rebuild；
12. cache 写入使用 temp + fsync + atomic replace；
13. UI filter 只能作用于 presentation copy，不得改变完整 cached universe；
14. 普通页面打开默认 cache-first；
15. 用户显式“刷新队列”使用 refresh=true 强制重算；
16. 允许每日 M1 更新后通过独立脚本预热产品 Queue；
17. 预热结果不属于 research evidence；
18. Hosted CI run #1525：
   - overall success
   - Python 628 passed
   - Web build success
   - Playwright 19 passed
   - browser evidence upload success。

原因：

HT-CN 实战工作台未来必须面对几百到几千只 A 股。重复全 universe 扫描会把产品性能变成主要瓶颈。D-044 允许产品层做可验证、可失效、可回退的每日缓存，同时明确禁止把缓存升级成研究证据或 methodology state。

## D-045 — UI 展示范围永远不得定义 HT-CN Operator Queue 的扫描 universe

**状态：Frozen M5 Phase 4 full-universe boundary**

正式决定：

1. Operator Queue scan/cache universe 固定为所有当前本地已初始化 instrument；
2. UI page size、搜索、筛选不得缩小 scan/cache universe；
3. legacy `limit` query 参数只做兼容，后端必须忽略其 scan 语义；
4. `operator_index.universe_scope=all_initialized_local_instruments`；
5. presentation_does_not_define_universe=true；
6. search/filter/pagination 只作用于浏览器展示；
7. presentation 操作不得改变 localStorage Delta snapshot；
8. presentation 操作不得触发新的 harmonic scan；
9. instrument picker 上限放宽到 10,000；
10. Phase 4 不引入 predictive ranking、win rate、alpha、trade instruction；
11. Phase 4 不修改 harmonic identity / Source Raw PRZ / lifecycle；
12. Phase 4 不写 M4 evidence store；
13. Hosted CI run #1583：
    - overall success
    - Python 629 passed
    - Web build success
    - Playwright 21 passed
    - browser evidence upload success。

原因：

当 HT-CN 从几十只标的扩展到全 A 股后，任何由 UI limit 决定 scan universe 的设计都会产生静默漏扫。D-045 将“扫描完整性”与“展示性能”彻底分离。

## D-046 — M5 并行构建只能优化吞吐，禁止改变 Queue 语义或共享未知 service 实例

**状态：Frozen M5 Phase 5 parallel-build boundary**

正式决定：

1. Operator Queue 允许使用有界线程池加速完整 universe build；
2. 默认 workers=4；
3. `HTCN_OPERATOR_WORKERS` 仅允许 1..16；
4. 只有提供 service_factory 时才允许 parallel mode；
5. parallel worker 必须使用线程本地独立 M3 service；
6. 不允许多个线程直接共享一个未知状态的 M3 service 实例；
7. 请求 parallel 但缺 service_factory 时必须自动回退 sequential；
8. 并发完成顺序不得拥有 Queue 排序语义；
9. Queue 最终排序仍由 frozen workflow bucket + instrument + deterministic display key 决定；
10. parallel / sequential 对相同输入必须产生相同 candidate/state 语义；
11. 单 instrument failure 继续隔离，不能中断其他标的；
12. progress callback 只用于产品观测，异常不得影响 build；
13. cache hit 不得创建 worker service；
14. worker count 不进入 candidate identity；
15. worker count 不进入 cache identity；
16. worker count 不进入 Operator Delta identity；
17. precompute 永远覆盖完整初始化 universe，删除 subset limit；
18. build_execution 永久声明：
    - changes_queue_semantics=false
    - authoritative_evidence=false
    - writes_m4_evidence=false；
19. Phase 5 不修改 harmonic identity / Source Raw PRZ / lifecycle；
20. Phase 5 不写 M4 evidence；
21. Hosted CI run #1601：
    - overall success
    - Python 634 passed
    - Web build success
    - Playwright 21 passed
    - browser evidence upload success。

原因：

全 A 股首次日内构建需要吞吐优化，但任何性能优化都不能获得修改研究语义的权力。D-046 将并发严格限定在 product execution layer。

## D-047 — 同一 Operator cache identity 的并发 rebuild 必须 single-flight 合并

**状态：Frozen M5 Phase 6 concurrency boundary**

正式决定：

1. 同一 Operator cache identity 同时只允许一个 rebuild owner；
2. identity 绑定：
   - cache root
   - expected trade date
   - bars
   - scales
   - universe hash
   - cache contract version；
3. worker count 不进入 single-flight identity；
4. follower 不得再次运行 full-universe scan；
5. follower 必须等待并复用 owner result；
6. follower status 固定为 `coalesced_wait`；
7. follower 必须记录 `coalesced_from_status`；
8. 普通 valid cache hit 不进入 single-flight；
9. 非-force owner 获得 ownership 后必须再次检查 cache，防止 race 重算；
10. 同时的 force refresh 也必须 coalesce；
11. single-flight scope 仅为 `process_local_cache_identity`；
12. D-047 不声称提供跨进程或分布式锁；
13. owner failure 后 registry 必须清理，禁止永久锁死；
14. single-flight 不拥有 Queue semantics；
15. single-flight 不修改 harmonic identity / Source Raw PRZ / lifecycle；
16. single-flight 不写 M4 evidence；
17. Hosted CI run #1613：
    - overall success
    - Python 637 passed
    - Web build success
    - Playwright 21 passed
    - browser evidence upload success。

原因：

全 A 股 daily cache miss 的成本较高。React 双请求或多客户端并发如果触发重复 full-universe build，会把 CPU / IO 负担成倍放大。D-047 将重复请求合并，但不赋予协调层任何研究语义。



## D-048 — Operator cache 必须绑定当前数据输入身份与分析代码身份

**状态：Frozen M5 Phase 7 cache-input-identity boundary**

正式决定：

1. M5 product cache 的有效性不能只由交易日 / bars / scales / universe / cache contract 决定；
2. 同一交易日内，只要底层数据输入发生变化，旧 cache 必须失效；
3. 同一交易日内，只要能够改变 Queue 输出的分析代码发生变化，旧 cache 必须失效；
4. Data Input Identity contract v1 覆盖当前 Operator Queue 的本地正式输入：
   - `catalog.duckdb`；
   - `catalog.duckdb.wal`；
   - `daily/**/*.parquet`；
   - `daily_delta/**/*.parquet`；
   - `adjustment/qfq/**/*.parquet`；
   - `benchmarks/**/*.parquet`；
5. Data Input Identity 使用 relative path + size + mtime_ns；它是产品 cache invalidation identity，不是研究证据 hash；
6. Analysis Code Identity contract v1 使用内容 SHA-256，覆盖：
   - Operator / context / source service 相关 app 文件；
   - 对应 data 层文件；
   - `src/htcn/harmonic/**/*.py`；
7. Operator Cache Input Identity contract v1 必须合并 data fingerprint 与 analysis-code fingerprint；
8. Operator snapshot contract 升级到 v2，并持久化完整 input identity provenance；
9. cache read 必须校验：
   - trade date；
   - bars；
   - scales；
   - universe hash；
   - snapshot contract；
   - operator input identity；
   - data fingerprint；
   - analysis-code fingerprint；
10. single-flight key 必须包含 operator input fingerprint；
11. 不同 input identity 的 concurrent request 不允许被错误合并为同一 single-flight；
12. API 进程启动时冻结 analysis-code identity；运行中的进程不得把磁盘上后续热改源码当成自己已加载的代码身份；
13. API 每次 Queue 请求重新计算 data identity；
14. precompute 进程同样冻结本进程 analysis-code identity；
15. full-universe build 完成后必须再次读取当前 data identity；
16. 若 build 前后 combined input identity 不一致：
    - `input_identity_stable_during_build=false`；
    - status=`live_not_cached_input_changed`；
    - 禁止写 product cache；
17. cache hit 明确记录 `input_identity_stable_during_build=true`；
18. input identity / cache / single-flight 永久属于 product execution layer：
    - authoritative_evidence=false；
    - writes_m4_evidence=false；
    - methodology_identity=false；
19. Phase 7 不修改 harmonic identity / Source Raw PRZ / Source lifecycle / M4 enrollment / Outcome Engine；
20. D-047 的 single-flight scope 仍只是 process-local；D-048 不虚构跨进程锁语义；
21. validated checkpoint：
    `7d1de7a81b7b2efc2a149eecd5a6c41b865123cd`；
22. Hosted CI run `35378357267` / #1634：
    - overall success；
    - Python 650 passed；
    - Web build success；
    - Playwright 21 passed；
    - browser evidence upload success；
23. run `35378145254` / #1632 的 cancelled 结论来自后续 push supersede，不得解释成 Phase 7 测试失败。

原因：

M5 已经进入全 universe、并行、缓存和 single-flight 的实战产品阶段。若 cache identity 不绑定实际数据与实际分析代码，同一交易日内的数据更新或代码升级可能静默复用旧 Queue，直接破坏“当前看到的结果对应当前输入”的基本产品可信度。D-048 将这一点冻结为显式、可测试的产品一致性边界，同时继续与 M4 authoritative evidence 完全隔离。


## D-049 — 同一 Operator cache slot 的跨进程 rebuild 必须由 OS advisory lock 串行协调

**状态：Frozen M5 Phase 8 cross-process coordination boundary**

正式决定：

1. D-047 的 process-local single-flight 继续保留；
2. M5 还必须协调独立 API / precompute 进程对同一 Operator cache slot 的 rebuild；
3. coordination key 以 cache slot 为边界：
   - cache root；
   - expected trade date；
   - bars；
   - scales；
4. lock 不按 input identity 分裂，因为不同 identity 仍可能写同一个 cache 文件；
5. 不同 input identity **不得 coalesce 成同一个 Queue result**，但必须串行写同一 cache slot；
6. 跨进程协调采用 OS advisory file lock：
   - POSIX：`fcntl.flock`；
   - Windows：`msvcrt.locking`；
7. lock file 只是协调 inode，不是“锁状态真相”；真正 ownership 绑定打开的文件描述符；
8. 进程异常退出由 OS 释放锁；不得依赖“成功删除 lock 文件”才能恢复；
9. lock file 位于产品 runtime tree，不进入任何 M4 evidence / methodology identity；
10. process-local follower 继续使用 `coalesced_wait`；
11. filesystem-lock waiter 可记录：
    - `cross_process_coordination_scope=filesystem_advisory_cache_slot_lock`；
    - waited；
    - wait seconds；
12. 非 force 请求取得跨进程锁后必须再次检查 cache；
13. force refresh 若确实等待过另一个 owner，也可复用该 owner 刚产生的、对自身当前 input identity 有效的 cache；
14. 任何 cache hit 返回前必须重新检查当前 input identity；
15. 等待跨进程锁后必须再次读取当前 input identity；
16. 若请求起始 identity 已不是当前 identity，不得复用仅匹配旧 identity 的 cache；
17. full build 后 Phase 7 的 input-identity recheck 继续生效；
18. 输入在等待或构建过程中变化时，最终不得把漂移结果写入正式 product cache；
19. real multiprocessing regression 必须证明第二进程在相同 lock slot 上阻塞，并在第一进程释放后获取锁；
20. `data/product/**` 与 `data/research/**` 必须被 Git ignore，runtime cache / lock / local evidence 不得污染 source clean-worktree gate；
21. Phase 8 coordination 永久属于 product execution layer：
    - authoritative_evidence=false；
    - writes_m4_evidence=false；
    - owns_lifecycle=false；
    - mutates_harmonic_identity=false；
    - mutates_source_raw_prz=false；
22. M4 capture methodology 37 components 不变；
23. Outcome Engine 4 components 不变；
24. validated code checkpoint：
    `08f51e28f60840cfb6a85b85fbceb091c9392825`；
25. Hosted CI run `35380339931` / #1641：
    - overall success；
    - Python 658 passed；
    - Web build success；
    - Playwright 21 passed；
    - browser evidence upload success。

原因：

全 universe rebuild 成本已经足以让 API、多客户端和预计算脚本之间的重复扫描成为真实产品问题。只做 process-local single-flight 无法阻止两个独立进程同时扫描并原子替换同一个 cache 文件。Phase 8 用最小、跨平台、崩溃可恢复的 OS advisory lock 关闭该竞态，同时仍把所有研究语义留在既有 M3/M4 冻结层。


## D-050 — 每日收盘流水线必须把 M5 产品 lane 与 M4 research lane 解耦，并在研究侧 QFQ 后最终重验产品 cache

**状态：Frozen M5 Phase 9 daily-close product boundary**

正式决定：

1. M1 fresh market data 是 M5 product 与 M4 research 的共享硬前置；
2. M3 context sync 对 M5 是 best-effort，不是 hard product gate；
3. M5 initial Operator cache 必须在 M4 research lane 之前构建；
4. M4 source preflight 只约束 M4 research lane；
5. M4 methodology / Outcome guards 只约束 M4 research lane；
6. M4 strict-QFQ readiness 只约束 M4 research lane；
7. 单一历史 provider/QFQ 边角问题不得把已经满足产品条件的 M5 Queue 判为不可用；
8. M4 research lane 运行后必须执行 M5 final **non-force** cache revalidation；
9. final revalidation 的原因是 `adjustment/qfq` 属于 Phase 7 Data Input Identity，M4 QFQ 写入可能使初始 M5 cache 失效；
10. 若 M4 未改变产品输入，final step 应退化为廉价 cache hit；若改变，则按当前 identity 自动 rebuild；
11. final product-ready 必须基于 current / single-as-of / persisted cache / stable input identity；
12. 单票 instrument failures 保持隔离；只要系统级 readiness 成立即可 `ready_with_instrument_failures`，但错误明细必须显式输出；
13. M5 initial failure 可以在 final validation 恢复；最终 persistent M5 failure 才是产品失败；
14. M5 failure 不得抹掉一个独立有效的 M4 research result；
15. M4 degraded 不得把一个独立有效的 final M5 product 改写成 product failure；
16. daily subprocess 必须 unbuffered 并实时 tee stdout，同时保存 per-step logs；
17. context sync 必须暴露阶段进度，避免长时间“无反应”；
18. M5 precompute report 必须携带 instrument_errors，而不只给失败数量；
19. Phase 9 永久属于 product orchestration：
    - authoritative_evidence=false；
    - writes_m4_evidence=false；
    - mutates_harmonic_identity=false；
    - mutates_source_raw_prz=false；
    - owns_lifecycle=false；
20. 不使用 win rate / alpha / predictive score 进行 Queue 排序，不输出 trade instruction；
21. Phase 8 → Phase 9 changed files 未触碰冻结的 M4 methodology / Outcome Engine；
22. M4 capture methodology drift：0 / 37；
23. Outcome Engine drift：0 / 4；
24. validated code checkpoint：
    `dec76022098574537333e8d3abd56bcc3b928a99`；
25. Hosted CI run `35381269831` / #1646：
    - overall success；
    - Python 682 passed；
    - Web build success；
    - Playwright 21 passed；
    - browser evidence upload success。

原因：

每日产品入口的第一职责是稳定地产出“当前输入对应的当前 Queue”。M4 research 有更严格的 evidence/source/QFQ 约束，这些约束不能反向变成 M5 的总开关；同时，M4 QFQ 又确实可能改变 Phase 7 已纳入 identity 的产品输入，所以必须在 research lane 后做一次轻量、非 force 的最终 revalidation。D-050 将“解耦”与“最终一致性”同时冻结。


## D-051 — 每日交接包必须精确绑定 Phase 9 最终产品快照，且 transport failure 不得改写产品/研究就绪状态

**状态：Frozen M5 Phase 10 daily handoff transport boundary**

正式决定：

1. Daily Handoff Bundle v2 是 transport artifact，不是 research authority；
2. 外层 handoff 永久声明：
   - `transport_only=true`；
   - `authoritative_evidence=false`；
   - `writes_m4_evidence=false`；
   - `is_trade_instruction=false`；
   - `alpha_inference_allowed=false`；
3. `m5_product_ready=true` 时，current product snapshot 不得通过“扫描目录后选择最新文件”推断；
4. current snapshot 必须从最终 `m5-operator-snapshot.json` 的 `product_cache.cache_path` 精确绑定；
5. final M5 report 必须满足：
   - schema v2；
   - product_ready=true；
   - single-as-of；
   - persisted cache status；
   - freshness=current；
   - input identity stable；
   - expected/queue/as-of trade date 一致；
   - report identity 与 cache identity 一致；
6. exact cache path 必须被限制在 `data/product/m5/operator_queue/`；
7. exact current snapshot 文件名必须符合 canonical trade-date/bars/scales slot；
8. current snapshot 必须满足 Operator snapshot schema v1 / contract v2；
9. current snapshot 的 trade date / bars / scales / queue integrity 必须与 final report 一致；
10. current snapshot 的完整 input identity 必须与 final report 完全相同；
11. current snapshot 必须继续声明：
    - authoritative_evidence=false；
    - writes_m4_evidence=false；
12. optional previous snapshot 只能作为历史产品上下文，不能参与 current 选择；
13. previous snapshot 也必须满足 canonical contract/date/single-as-of/non-authoritative 约束；
14. handoff 必须携带实际 Phase 9 pipeline report，传入 payload 与磁盘文件内容必须一致；
15. manifest 必须记录 pipeline / final M5 report / current snapshot 的 SHA-256 与 product binding；
16. verifier 必须独立解析 pipeline / final M5 report / current snapshot，交叉核对 ready flags、overall status、trade date、cache readiness 与 input identity；不能只相信 manifest 自述；
17. ZIP member 必须使用安全 relative arcname，每个 member 记录 size + SHA-256，manifest member set 必须与实际 archive 精确一致；
18. manifest 中的 source/cache path 使用 repository-relative 表达，不携带本机绝对路径；
19. `m4_research_ready=true` 时，handoff 必须存在且验证通过当前 `m4-evidence-bundle.zip`；
20. research degraded 时，可携带验证通过的 existing M4 evidence bundle，但 role 必须明确为 existing，而不是 current research success；
21. research degraded 且旧 M4 bundle 无效时，省略该 bundle 并记录 warning；
22. 所有嵌套 M4 bundle 必须继续使用现有 `verify_evidence_bundle` 验证；
23. 外层 handoff 不获得 nested M4 capture chain 的 authority；M4 authority 永远留在原 evidence chain；
24. handoff ZIP 必须临时写入、原子替换前 verify、替换后再次 verify；
25. handoff runner 必须把 transport 状态写入独立 `m5-daily-handoff.json`；
26. runner 必须记录 Phase 9 pipeline report 构建前后 SHA-256，证明 pipeline 未被修改；
27. output/report/pipeline 三条路径不得互相覆盖；
28. transport build 失败只影响 handoff transport exit/status，不得编辑 Phase 9 pipeline report；
29. transport failure 不得把既有 `m5_product_ready` 或 `m4_research_ready` 重新写值或重新解释；
30. `运行HT-CN每日交接包.bat` 只运行 handoff builder，不偷偷重跑 Phase 9 daily pipeline；
31. Phase 10 仍不改变 Queue semantics、harmonic identity、Source Raw PRZ 或 lifecycle；
32. Phase 10 不写 M4 evidence，不使用胜率/alpha/predictive score，不输出交易指令；
33. Phase 9 governance checkpoint → Phase 10 validated code checkpoint 仅新增 7 个 handoff/product/test/BAT 文件；
34. M4 capture methodology drift：0 / 37；
35. Outcome Engine drift：0 / 4；
36. validated code checkpoint：
    `99e3bf7aba1e656601bdcf4831d4b215eede4e8d`；
37. Hosted CI run `35382676878` / #1665：
    - overall success；
    - Python 699 passed；
    - Web build success；
    - Playwright 21 passed；
    - browser evidence upload success；
38. draft PR #22 只是 Phase 10 hosted-CI / diff audit carrier，不代表已经合并到 Phase 9 或 main。

原因：

每日交接包的价值在于把“这次收盘流水线实际得到的最终产品状态”可靠搬走，而不是再做一次“哪个文件看起来最新”的推断。Phase 7 已把 input identity 纳入产品缓存，Phase 9 又在 M4 research/QFQ 后执行最终 revalidation；因此 Phase 10 只能精确绑定那一个最终结果。与此同时，运输层的失败不应倒灌到产品/研究语义。D-051 把 exact binding、portable verification、M4 authority isolation 与 transport-failure isolation 一次冻结。


## D-052 — Daily Operator History 必须是 append-only 产品观察链，记录最终产品状态且与 M4 authority 永久隔离

**状态：Frozen M5 Phase 11 daily operator history boundary**

正式决定：

1. M5 Daily Operator History 是 product observation journal，不是 M4 authoritative prospective evidence；
2. history 只能在 Phase 9 final non-force Operator cache revalidation 成功后写入；
3. history 只记录最终 product state，不记录 initial cache 或 M4/QFQ 可能改变产品 input identity 前的中间态；
4. history failure 只影响 `m5_history_ready`，不得把已成立的 `m5_product_ready=true` 改为 false；
5. history failure 不得改写或重新解释 `m4_research_ready`；
6. append 前必须验证最终 `m5-operator-snapshot.json`：
   - schema v2；
   - product_ready=true；
   - single-as-of；
   - persisted cache；
   - freshness=current；
   - stable input identity；
   - as-of / expected / queue trade date 一致；
   - report identity 与 cache identity 一致；
7. exact product snapshot 必须限制在 `data/product/m5/operator_queue/`，并满足 snapshot schema v1 / contract v2；
8. snapshot trade date / input identity / queue integrity 必须与最终 report 一致；
9. snapshot 继续声明 authoritative_evidence=false / writes_m4_evidence=false；
10. observation identity 使用 SHA-256 绑定：
    - trade date；
    - source generated-at；
    - Operator Input Identity fingerprint；
    - final M5 report SHA-256；
    - exact snapshot SHA-256；
    - canonical Queue SHA-256；
11. 完全相同 observation 重跑必须幂等，不新增重复文件；
12. history 物理结构固定为：
    `data/product/m5/operator_history/<trade_date>/<observation_id>.json`；
13. history 永久采用 append-only，不允许覆盖已有 observation；
14. 同一交易日 source/input identity 真变化时必须追加 revision，而不是覆盖上一 revision；
15. 同日 revision ordinal 必须连续 1..N；
16. incoming source generated-at 早于已存在的同日最新 revision 时必须拒绝；
17. 已存在较新 trade date 后，禁止对更早 trade date 做历史 backfill；
18. history append 使用跨进程 OS advisory lock 串行化；
19. 每条 history record 必须自包含完整 Queue snapshot，不依赖未来仍保留 cache 文件才能查询；
20. 跨日 Delta baseline 固定使用“上一已记录交易日的最新有效 revision”，不得使用同日上一 revision 冒充跨日变化；
21. 首个 history 日 delta status 固定为 `baseline_no_previous_observation`；
22. Phase 2 的 current-analysis-error disappearance suppression 继续生效；当前分析失败不得被误记为候选消失；
23. 每条 record 必须保存 `record_integrity_sha256`；
24. 每条 record 必须保存 `previous_same_day_observation_id`；
25. 每条 record 必须保存 `previous_recorded_trade_date` 与 `previous_observation_id`；
26. history load/query 必须 fail closed 验证：
    - record schema/contract；
    - Queue hash；
    - observation id；
    - record self-integrity hash；
    - 文件名与 observation id；
    - 目录名与 trade date；
    - revision ordinal 连续性；
    - same-day revision link；
    - previous trade-date link；
    - previous observation 必须是上一已记录交易日的最新 revision；
27. observation/revision/baseline 文件删除、篡改或断链时，不允许返回“部分看似正常”的 history，必须报告 `operator_history_integrity_failure`；
28. query 默认每交易日只返回最新 revision；审计时可显式请求全部 revisions；
29. query 支持 instrument / display key / start-end date / summary-only / limit；
30. GET `/api/operator/history` 只暴露 product history；integrity failure 必须显式返回错误，不得静默跳过坏记录；
31. Workbench“跨日产品观察历史”与 Phase 2 browser-local “今日变化”是两个不同产品层，不能混成 authority；
32. CLI / BAT / API / UI 都必须显式声明该 history：
    - 不是 M4 evidence；
    - 不用于胜率统计；
    - 不用于 alpha；
    - 不用于 predictive ranking；
    - 不输出 trade instruction；
33. Phase 11 不拥有 lifecycle，不修改 harmonic identity / Source Raw PRZ；
34. Phase 11 不写 M4 evidence；
35. runtime history 位于已 Git-ignore 的 `data/product/**`；
36. validated code checkpoint：
    `504cc063d93e999dcbac1b131e14f475beacd4d0`；
37. Hosted CI run `35384764795` / #1699：
    - overall success；
    - Python 718 passed；
    - Web build success；
    - Playwright 22 passed；
    - browser evidence upload success；
38. 首轮 run `35384383540` / #1693 的 browser failure 来自新增 history test locator 同时命中两个日期卡片；原有 21 Playwright 全过，属于测试 strict-mode ambiguity，不是产品逻辑失败；
39. locator 已在 `b49d1468a243f0a129def63b6ee3984170d1ceb8` 收窄到 latest-day card；
40. draft PR #23 只是 hosted-CI / diff audit carrier，不代表已合并；
41. M4 capture methodology drift：0 / 37；
42. Outcome Engine drift：0 / 4。

原因：

Phase 2 已能回答“今天相对上一快照变了什么”，但浏览器 localStorage 不能承担长期、可审计的跨日产品历史。Phase 11 将每天最终产品状态保存为 append-only observation，并让同日 input-identity 更新形成 revision 而非覆盖；同时用 hash 和链关系对删除/篡改 fail closed。它提升的是产品复盘与可追溯性，不获得 M4 的研究证据权力，也不允许从历史观察直接推导胜率、alpha 或交易排序。


## D-053 — Daily Review Digest 必须是完整 Phase-11 Delta 的透明产品复盘，不得把历史变化转成预测排名

**状态：Frozen M5 Phase 12 daily review digest boundary**

正式决定：

1. Daily Review Digest 是 Phase 11 Operator History 的 product review derivative，不是新的 evidence authority；
2. digest 唯一 source 是 latest valid Phase-11 history revision；
3. history integrity failure 时 digest 必须 fail closed，不允许从剩余文件拼一个“部分正常”的摘要；
4. digest 只能从未过滤、完整的 latest Delta 构建；
5. `delta_total_change_count`、observation `change_count` 与实际 `changes[]` 长度必须完全一致；
6. 任何 count mismatch 必须拒绝生成 digest；
7. digest 永久保留所有变化 item 与每个 item 的完整 `change_types[]`；
8. 固定 review workflow order：
   - execution_evaluation；
   - reaction_observation；
   - waiting；
   - evidence_insufficient；
   - disappeared_candidate；
9. 上述顺序只是产品工作流导航，不是预期收益、成功率、alpha、买卖优先级或机会质量排名；
10. contract 必须声明 `ordering_is_product_workflow_not_expected_return=true`；
11. change-type vocabulary 固定为：
   - new_candidate；
   - disappeared_candidate；
   - action_state_changed；
   - lifecycle_state_changed；
   - pattern_state_changed；
   - next_key_changed；
   - execution_gate_changed；
   - context_cautions_changed；
12. digest 必须输出 `change_count` / `change_type_counts` / `workflow_bucket_counts`；
13. current-analysis-error disappearance suppression 继续沿用 Phase 2/11，不得因为 digest 层重新制造候选消失；
14. comparison-incomplete instruments 必须独立显示为 analysis gaps；
15. analysis gap 不得被解释为看空、恶化、退出或候选消失；
16. digest status 允许：
   - no_history；
   - baseline；
   - no_changes；
   - no_changes_with_analysis_gaps；
   - changes_ready；
   - changes_ready_with_analysis_gaps；
17. baseline 表示首个产品观察日，没有上一交易日 Delta baseline，不是失败；
18. 每日流水线中 Phase 12 只能运行在 Phase 11 history append 成功之后；
19. `m5_daily_review_digest` failure 不得改写 `m5_product_ready`；
20. digest failure 不得改写 `m5_history_ready`；
21. digest failure 不得改写 `m4_research_ready`；
22. digest failure 只影响 `m5_review_digest_ready`；
23. API presentation filter 只允许改变 `filtered_change_count` / `filtered_workflow_sections`；
24. 原始 source `change_count` 必须保持不变并显式暴露 `source_change_count_unchanged`；
25. 未知 workflow bucket / change type 必须显式报参数错误，不得静默返回 0 条；
26. instrument filter 只是展示过滤，不改变 source digest；
27. Workbench 必须同时显示“源变化总数”和“当前筛选命中”，避免把筛选结果误当成当天全部变化；
28. Workbench 必须显示 trade date / previous trade date / revision；
29. Workbench 必须可展示 lifecycle/action/next-key before -> after；
30. Workbench item 可以跳转单票深度工作台，但不得生成买卖按钮/交易指令；
31. one-click `运行HT-CN每日变化复盘.bat` 只构建 review digest，不重跑 daily pipeline；
32. report 固定为 `artifacts/reports/m5-daily-review-digest.json`；
33. Phase 10 handoff v2 冻结不变；未来若运输 Phase 11/12 artifacts 必须建立新 versioned handoff contract；
34. Phase 12 contract 永久声明：
    - semantics=product_change_triage_only；
    - authoritative_transition=false；
    - authoritative_evidence=false；
    - writes_m4_evidence=false；
    - predictive_score_used=false；
    - historical_outcome_used_for_ranking=false；
    - alpha_inference_allowed=false；
    - is_trade_instruction=false；
    - mutates_harmonic_identity=false；
    - mutates_source_raw_prz=false；
    - owns_lifecycle=false；
35. 首轮 hosted CI #1725 / `35413513169`：
    - Python 733 passed；
    - Web build success；
    - Playwright 23 passed；
36. final validated code checkpoint：
    `84c7d8a0f2d46cd8ed9b79dcd638cb727d165465`；
37. final code CI #1733 / `35413656027`：
    - overall success；
    - Python 736 passed；
    - Web build success；
    - Playwright 23 passed；
    - browser evidence upload success；
38. draft PR #24 只是 hosted-CI / diff audit carrier，不代表已经合并；
39. M4 capture methodology drift：0 / 37；
40. Outcome Engine drift：0 / 4。

原因：

Phase 11 解决了“跨日产品状态如何可靠保存”，Phase 12 解决的是“每天打开工具后如何快速看清到底变了什么”。这个阶段最容易出现的错误，是把历史变化偷偷转化为胜率、机会评分或买卖优先级。D-053 因此把完整 Delta、透明 workflow order、源总数不变、presentation-only filter 和 no-alpha/no-ranking 边界一次冻结。


## D-054 — Review Session / Follow-up Journal 必须与 canonical lifecycle/action 完全隔离，并用 append-only 事件表达人工复盘工作流

**状态：Frozen M5 Phase 13 review workflow boundary**

正式决定：

1. Phase 13 只记录用户复盘工作流，不是 harmonic/research/lifecycle/action authority；
2. 固定 review states 为 `unseen` / `reviewed` / `follow_up`；
3. 对新的 `source_observation_id + display_key`，没有 event 时默认 `unseen`，默认未看不需要写事件；
4. `reviewed` 只表示用户已复核该产品变化，不等于看多/看空/通过/失败/买入/卖出；
5. `follow_up` 只表示需要继续人工复盘，不得改变 Queue 排序或 lifecycle/action；
6. 每个写 event 必须绑定精确 `source_observation_id + display_key`；
7. 写入前必须从 Phase 11 validated history 证明 observation 存在且 display key 是该 observation 的真实 Delta change；
8. 不存在的 source binding 必须拒绝；
9. 当前交易日 review state 按 observation binding 计算；昨天 reviewed 不得让今天的新变化自动变 reviewed；
10. active follow-up 按 display key 的 latest review event 计算；
11. latest event=follow_up 时 active follow-up 可以跨 observation / trade date 持续；
12. 第二天即使没有新 Delta，active follow-up 仍必须出现在独立持续跟踪清单；
13. latest display-key event 变为 reviewed 或 unseen 后，active follow-up 结束；
14. 结束跟踪必须追加新 event，不删除旧 follow-up event；
15. runtime root 固定为 `data/product/m5/review_journal/`；
16. event path 固定为 `<trade_date>/<binding_id>/<event_id>.json`；
17. `binding_id=SHA256(source_observation_id + display_key)`；
18. event store 永久 append-only，不覆盖旧 event；
19. append 使用跨进程 OS advisory lock；
20. 所有写请求必须带 `client_request_id`；
21. 同 request id + 相同 payload 返回 `idempotent_existing`；
22. 同 request id + 不同 payload 必须报 replay conflict；
23. note 可为空、换行正规化、trim、最大 1000 字符；
24. note 只是人工文本，不做 sentiment / alpha / outcome 解析；
25. 每个 event 必须保存 self-integrity SHA-256；
26. 每个 event 必须保存 binding event ordinal 与 previous binding event link；
27. 每个 event 必须保存 display-key event ordinal 与 previous display-key event link；
28. journal load/query 必须 fail closed 验证 schema / boundary / binding / state / note / request id / event id / filename / directory / self hash / ordinal / chain；
29. client request id 必须在 journal 中唯一；
30. 中间 event 删除、链断裂或内容篡改必须报告 `review_journal_integrity_failure`；
31. Workbench 必须区分“今天这条变化是否已看”和“该结构是否仍在持续跟踪”，不能合并为一个字段；
32. 同日 follow-up 显示“跟踪中”；来源交易日早于当前交易日时才显示“跨日跟踪中”；
33. Workbench 必须提供独立持续跟踪清单，不能要求标的当天必须重新出现 Delta；
34. active follow-up item 必须可进入单票工作台；
35. active follow-up 必须可显式“结束跟踪”；
36. GET `/api/operator/review-session` 是 enriched product review session，不修改 Phase 12 digest contract；
37. review-session filter 支持 workflow/change-type/instrument/review-state/follow-up-only；
38. review filter 只能改变 filtered sections/count，不得改写源 change count / review counts / active follow-up count；
39. POST `/api/operator/review-session/event` 是唯一产品写入口；
40. write API 不得向前端暴露本地 filesystem path；
41. GET `/api/operator/review-journal` 是只读审计查询；
42. `scripts/m5_query_review_journal.py` 与 `运行HT-CN复盘跟踪查询.bat` 只读；
43. Phase 13 不加入 daily-close pipeline；
44. 没有用户明确操作时，系统不得自动制造 reviewed/follow_up event；
45. Phase 13 failure 不得改写 Phase 9 product、Phase 11 history、Phase 12 digest 或 M4 research readiness；
46. review state / follow-up state 永久禁止用于 Queue 排序；
47. review state / follow-up state 永久禁止用于 win rate / alpha / predictive score / quality score；
48. review state / follow-up state 永久禁止生成 trade instruction；
49. contract 必须保持：
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
    - mutates_harmonic_identity=false；
    - mutates_source_raw_prz=false；
50. Phase 10 handoff v2 冻结不变；若未来运输 Phase 11/12/13 artifacts 必须创建新的 versioned handoff contract；
51. 首轮 hosted CI #1766 / `35415053453`：
    - Python 757 passed；
    - Web build success；
    - 原有 23 Playwright passed；
    - 新 Phase-13 browser test 仅 locator strict ambiguity 失败；
52. locator 已在 `4b015dfc0e72db0f1275e1e570d85959254550fa` 收窄到具体 follow-up row；
53. final validated code checkpoint：
    `4b015dfc0e72db0f1275e1e570d85959254550fa`；
54. final code CI #1768 / `35415145067`：
    - overall success；
    - Python 757 passed；
    - Web build success；
    - Playwright 24 passed；
    - browser evidence upload success；
55. draft PR #25 只是 hosted-CI / diff audit carrier，不代表已经合并；
56. M4 capture methodology drift：0 / 37；
57. Outcome Engine drift：0 / 4。

原因：

Phase 12 已经能回答“今天变了什么”，但如果没有独立 review workflow，用户仍然无法可靠记录“哪些已经看过、哪些要继续跟踪”。Phase 13 用 append-only event journal 把人工复盘进度保存下来，同时把当天 review state 与跨日 follow-up 连续性拆开，避免昨天的“已看”污染今天的新变化，也避免“后续跟踪”因为第二天没有新 Delta 而消失。整个层级只服务复盘流程，不获得任何 lifecycle、研究或交易权力。


## D-055 — Daily Handoff v3 必须把 Phase 11–13 作为可验证 transport extension，且不得修改冻结的 v2 语义

**状态：Frozen M5 Phase 14 handoff v3 boundary**

正式决定：

1. Phase 14 必须新建 schema/versioned v3，不修改 Phase-10 handoff v2；
2. v3 外层基础 member 必须是现场临时重建、并通过冻结 v2 verifier 的 `base/htcn-daily-handoff-v2.zip`；
3. v3 不得覆盖用户已有的 `htcn-daily-handoff-v2.zip` 或 v2 report；
4. v3 verifier 必须再次调用冻结 v2 verifier，不能只相信外层 manifest；
5. v3 manifest 必须绑定 nested-v2 schema/status/product-binding/bundle SHA；
6. nested-v2 manifest 声明与真实 v2 不一致必须 invalid；
7. v3 pipeline SHA 必须校验 nested-v2 中原始 pipeline member bytes，禁止用重新序列化 JSON 代替原始 bytes；
8. v3 继承 pipeline 的 product/history/digest/M4 readiness，不重新定义 readiness；
9. digest-ready 必须蕴含 history-ready；
10. history-ready 必须蕴含 product-ready；
11. readiness 关系不一致时 build/verifier 必须 fail closed；
12. v3 transport failure 不得改写任何 pipeline readiness；
13. 当 history-ready=true，v3 current history 必须是 nested-v2 product trade date 的 latest Phase-11 observation；
14. current history source report SHA 必须等于 nested-v2 product-binding report SHA；
15. current history source snapshot SHA 必须等于 nested-v2 product-binding snapshot SHA；
16. current history trade date 必须等于 nested-v2 product trade date；
17. history transport 必须有界，不运输全部长期 history；
18. history 只运输 current observation、直接上一交易日 observation，以及必要的直接上一同日 revision；
19. current history 有 previous-trade-date baseline 时，v3 verifier 必须用 previous/current queues 独立重算 Operator Delta；
20. 重算 delta 必须与 current history 保存的 delta 完全相同；
21. 无上一交易日时不得带 previous-history member，且 delta 必须为 baseline_no_previous_observation；
22. 当 digest-ready=true，必须运输精确 Phase-12 daily review digest；
23. digest 必须由 transported current history 重新构建并逐字段一致，不能只检查 source id；
24. digest 的 generated_at_utc/history_root/report_path 只作为 transport metadata，不参与 Phase-12 semantic core；
25. Phase-13 review-session snapshot 只能在 digest-ready 时运输；
26. review-session snapshot 必须在 handoff build 时从 validated history + review journal 即时导出；
27. session 导出与 journal event 选择必须拿 Phase-13 的同一个 review-journal process lock，避免撕裂快照；
28. 移除 Phase-13 专属字段和 item review 后，session 必须精确投影回 transported Phase-12 digest；
29. v3 不得整库打包 review journal；
30. journal root event ids 固定来自 current_event_id / active_follow_up_event_id / active_follow_ups[].event_id；
31. 必须递归携带每个 root 的 previous_binding_event_id 与 previous_display_key_event_id 直到链首；
32. included review-event ids 必须严格等于 root closure；
33. 少 predecessor 必须 invalid；
34. 多一个不相关 event 也必须 invalid；
35. 每个 transported review event 必须继续通过 Phase-13 event verifier；
36. current review event 必须与 session item 的 observation/display-key/state/note 交叉一致；
37. active follow-up event 必须为 follow_up 且 source display-key/instrument/observation/trade-date 与 session 完全一致；
38. 外层 v3 永久声明：
    - transport_only=true；
    - authoritative_evidence=false；
    - writes_m4_evidence=false；
    - is_trade_instruction=false；
    - alpha_inference_allowed=false；
    - predictive_score_used=false；
    - historical_outcome_used_for_ranking=false；
    - review_state_changes_product_ranking=false；
39. M4 authority 仍只存在 nested v2 内部的冻结 authoritative capture chain；
40. reviewed/follow_up 被 transport 后不得获得任何 lifecycle/action/ranking/trade 语义；
41. v3 status 允许：
    - complete_review_transport；
    - history_transport_review_degraded；
    - product_transport_history_degraded；
    - base_transport_product_failed；
42. M4 readiness 与这些 product-review transport status 继续独立；
43. v3 写入必须 temp ZIP -> full verify -> atomic replace -> final verify；
44. pre-replace verify 失败不得留下最终 v3 ZIP；
45. v3 runner 必须独立写 `m5-daily-handoff-v3.json`；
46. runner 必须比较 pipeline report build 前后 SHA；
47. runner 必须声明 transport failure does not rewrite readiness；
48. one-click `运行HT-CN每日交接包v3.bat` 只能运行 v3 build script；
49. v3 one-click 不得重跑 daily-close pipeline；
50. v3 one-click 不得调用旧 v2 entrypoint；
51. Phase-10 v2 入口/代码/manifest/verifier 保持原样；
52. 首轮 code CI #1788 / `35416245508`：
    - Python 771 passed；
    - Web build success；
    - Playwright 24 passed；
53. final hardening 增加 review-event predecessor closure、伪造 nested-v2 binding、伪造 pipeline hash 三类测试；
54. final validated code checkpoint：
    `c9de28d959b64043663a2bceccb17cc87b8f3756`；
55. final code CI #1790 / `35416336734`：
    - overall success；
    - Python 774 passed；
    - Web build success；
    - Playwright 24 passed；
    - browser evidence upload success；
56. draft PR #26 只是 hosted-CI / diff audit carrier，不代表已经合并；
57. Phase-10 handoff v2 changed files：0；
58. M4 capture methodology drift：0 / 37；
59. Outcome Engine drift：0 / 4。

原因：

Phase 10 的 v2 已经正确解决“最终产品快照 + M4 nested evidence 如何安全交接”，后续不能为了加入 Phase 11–13 而重写 v2。Phase 14 因此把 v2 当成冻结的可验证基础层，再在外层新增 history/digest/review-state 的绑定链。通过 bounded history、digest 独立重建、session->digest 投影以及 review-event closure，v3 可以证明这些状态确实来自同一个最终产品观察，而不是把几个看起来相关的 JSON 粗暴拼在一起。


## D-056 — Phase 15 portable inspector is a verified read-only consumer

日期：2026-09-19

决定：

1. Phase 15 v1 consumes only the frozen Phase-14 `htcn-daily-handoff-v3.zip`.
2. The existing v3 verifier is a mandatory gate. Invalid or tampered transport fails closed before inspection.
3. The inspector must not depend on the local M1/market database and must not scan local product stores to fill transport gaps.
4. Transported Queue/History/Review state is display-only and is never imported or merged into local stores.
5. Generating the JSON/HTML presentation artifacts is allowed; those artifacts are not product authority or research evidence.
6. The inspector cannot create `reviewed` / `follow_up` events and exposes no review-write surface.
7. Instrument/display-key drill-down is presentation filtering only and cannot affect Queue ranking, lifecycle or harmonic identity.
8. No predictive score, historical-outcome ranking, alpha inference or trade instruction is permitted.
9. Any future import/merge workflow requires a separate versioned contract with explicit provenance, conflict and idempotency semantics.

验证：
- implementation checkpoint `4534e4ed16a9b5aabca9245ceeab271a561b5f4b`;
- Actions #1805 / `35419145630`: success;
- Python 779 passed;
- Web build success;
- Playwright 24 passed.


## D-057 — Portable chart detail requires a new v4 transport; v3 remains frozen

日期：2026-09-19

决定：

1. Phase14 handoff v3 remains frozen and unmodified.
2. Phase15 v3 Inspector remains a pure v3 consumer and is not allowed to consult the local market DB to fill missing geometry.
3. Because v3 Queue records intentionally contain product summaries rather than full bars/pattern.points, portable visual drill-down must use a new versioned transport: v4.
4. v4 nests the exact verified v3 bytes and adds portable detail only for the exhaustive current Queue display-key set.
5. No top-N, score, expected-return or user-follow-up state may define the detail inclusion set.
6. Each current Queue display key must be represented by either exact matched detail or an explicit error; silent omission is invalid.
7. Detail analysis is accepted only when local input identity matches the v3 current product snapshot identity and the analysis trade date matches v3.
8. Pattern binding is exact: the verifier re-derives the Queue display key from transported pattern points.
9. Forming structures must never fabricate a future D/potential leg. The only dashed future-facing visual allowed in v1 is a clearly labelled next-key-price guide, which is not pattern geometry.
10. Portable detail and visualization remain product-presentation artifacts: no methodology authority, no M4 evidence writes, no Queue/history/review mutation, no review events, no alpha/ranking/trade instruction.

验证：
- implementation checkpoint `348fd5b47341fbc01e74085530c4fd8dec9aed28`;
- hosted CI #1822 / `35419647193`: success;
- Python 784 passed;
- Web build success;
- Playwright 24 passed.
