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

只发生 secondary overlap 不足以叫 Type-II。必须先完整 retest 原 PRZ terminal side，再进入 Type-II Terminal Bar 与后续确认。Source PRZ 未解决时 fail closed。

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

**状态：Frozen engineering policy**

M2.30 起，GitHub CI 的真实 A 股研究采用以下工程约束：

- 允许读取历史 Actions artifact；
- research snapshot cache miss 时优先恢复冻结 45 股 artifact；
- artifact 恢复成功后立即持久化到 cache，不等待整轮研究结束；
- deterministic short tests 可 `cancel-in-progress`；
- long research 使用独立 concurrency 且不自动取消旧 run；
- calibration 使用无缓冲输出，逐股打印真实进度；
- timeout 是防失控保险，不得拿增加 timeout 代替性能诊断。

原因：真实研究结果依赖冻结数据边界。重复联网抓取既浪费时间，也会把 provider availability 与 harmonic 逻辑错误混在一起。run #603 证明恢复 45 股快照后完整校准约 85 秒，因此此前 40 分钟超时主要是缓存恢复链路失效，而非 Shark 计算本身不可接受。

## 后续新增格式

```text
## D-XXX — 决策标题

状态：Proposed / Active / Frozen / Superseded by D-YYY

决定：

原因：

影响范围：

验证方式：
```
