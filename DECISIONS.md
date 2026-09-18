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
