# HT-CN Decision Ledger — 设计决策账本

本文件记录会影响后续实现方向的“为什么”。它是 append-only 风格的决策账本：后续若推翻旧决定，应新增一条 supersede 记录，而不是静默改掉历史原因。

## D-001 — Carney source fidelity 高于工程便利

**状态：Frozen**

Carney Volume One / Two / Three 定义 harmonic identity、source measurement 与 Reaction vs. Reversal 的理论基准。HT-CN 可以增加 A 股执行层、统计层、排名层和 UI，但不得把工程近似包装成原书定义。

原因：项目目标是用于实战研究，若 source rule 与工程 rule 混层，后续所有统计、UI、扫描和交易辅助都会在错误语义上继续放大。

## D-002 — 几何时钟与执行时钟永久分离

**状态：Frozen**

历史完成 D Pivot 只属于 retrospective geometry；source-aligned Terminal Price Bar 属于 execution observability。两者不能因为“位置接近”或 UI 需要而合并。

官方执行序列保持：

`forming projection -> source PRZ entry -> Terminal Price Bar -> PEZ -> T-Bar+1 -> Type-I`

## D-003 — PRZ 采用分层对象，不再用一个 price_low/high 概括

**状态：Frozen**

需要显式区分：

- component envelope；
- ideal convergence core；
- source Raw PRZ；
- Terminal extreme；
- PEZ。

legacy `price_low/high` 只能作为 ideal core 的兼容别名，不能称为完整 source PRZ。

## D-004 — Type-II 必须完整 retest 后再确认

**状态：Frozen**

只发生 secondary overlap 不足以叫 Type-II。必须先完整 retest 原 PRZ terminal side，再进入 Type-II Terminal Bar 与后续 price / indicator confirmation。

当 source PRZ 未解决时，Type-II fail closed。

## D-005 — Wilder RSI evidence 不等于 RSI BAMM

**状态：Frozen**

当前简单 Wilder RSI 极值区反转只作为 indicator evidence。未来 RSI BAMM 必须作为独立多步骤状态机实现，不能改名冒充。

## D-006 — 5-0 在 source conflict 关闭前默认隔离

**状态：Frozen**

5-0 的 Volume Two 结构 PRZ 与 Volume Three 执行细化尚需 figure-level reconciliation。此前把 50%-61.8% 简化为通用 band 的解释不再作为生产默认语义。

因此默认 Engine / Scanner / Workbench 不发出 5-0；只允许研究显式 opt-in。

## D-007 — Shark 使用专属 first-target contract

**状态：Frozen**

Shark 不是普通 XABCD T1/T2 管理。当前目标语义为：从 C 出发，50% BC 与 Reciprocal AB=CD 谁先被价格遇到，谁是 initial target；61.8% 保留为后续 5-0 / risk measurement。

## D-008 — Identity 不能被分数或统计“救活”

**状态：Frozen**

source-backed hard identity 先决定 completed/rejected。geometry score、历史统计、A 股环境、indicator evidence、UI 偏好只能在已经通过 identity 的候选之上排序或解释。

## D-009 — 冻结研究结果不可回写

**状态：Frozen**

已经消费/冻结的 Holdout、external replication、历史 closed result 保持不可变。若 source repair 改变候选资格或执行定义，必须建立新的 research version / prospective protocol，不能重算旧结果后覆盖。

## D-010 — A 股增强必须在独立执行层

**状态：Frozen**

T+1、涨跌停、流动性、ATR、指数/板块相对强弱、开收盘微观结构等可以影响执行可行性、风险和优先级，但不能改写 Carney pattern identity 或 source PRZ。

## D-011 — 中文优先，但内部标识保持稳定

**状态：Frozen**

界面、表格、状态、审计提示和散户可读解释尽量使用中文。代码内部枚举、API 字段、技术缩写可保留英文，避免频繁重命名造成兼容性问题。

## D-012 — 当前默认市场范围为 SSE/SZSE

**状态：Frozen until user reopens scope**

北交所 BSE 暂不进入默认开发与验收范围。除非用户明确重新开启，不应因为“全 A”字样自动把 BSE 拉回当前主线。

## D-013 — 跨对话项目事实以仓库为准

**状态：Frozen**

大型项目不依赖聊天连续性。新的 AI 会话必须以当前 HEAD、`PROJECT_CONTEXT.md`、本账本、相关 specs、CI 为权威，并检查 `context_checkpoint..HEAD` 的变化。

原因：模型能力可以保持，但旧聊天的细粒度上下文不能保证逐轮完整继承；把长期事实写入仓库能防止失忆式返工。

## D-014 — Standalone AB=CD Source Raw PRZ 与 BC Layering 永久分层

**状态：Frozen**

Standalone AB=CD 的 Source Raw PRZ 采用：

- equivalent `AB=CD x1` completion 作为 defining measurement；
- reciprocal BC 作为 complementary source measurement。

Volume Three 的 BC layering / extension refinement（例如从 1.618 向 2.0 的执行层观察）只能进入 execution tolerance / execution refinement，明确不属于 harmonic identity，也不属于 Source Raw PRZ membership。

该决定从 M2.28 起形成 `m2-source-prz-v4` research definition。v4 真实 A 股可见研究即使发现 `full_prz_exit_by_t5` 通过当前 robustness gate，也不得把它升级为 source rule、个股概率、机械五日倒计时或 confirmatory policy；冻结历史 Holdout / replication 不因 v4 定义变化而重算。

原因：如果把 BC layering 并入 Raw PRZ，会再次重演 Ideal Core 替代 Source PRZ 的语义污染，并使 Terminal Price Bar、PEZ、Type-I 全部建立在错误边界上。

影响范围：standalone AB=CD runtime payload、Source PRZ registry、Terminal Price Bar research、M3 future overlays、research version governance。

验证方式：AB=CD Book Golden Gate + API contract tests + v4 sealed boundary guard + 45-symbol real A-share CI。

## 后续新增格式

```text
## D-XXX — 决策标题

状态：Proposed / Active / Frozen / Superseded by D-YYY

决定：

原因：

影响范围：

验证方式：
```
