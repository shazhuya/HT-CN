# HT-CN Project Blueprint — 项目总蓝图

blueprint_schema: `6`
status: `authoritative`

## 1. 项目使命

HT-CN 是面向中国 A 股的谐波研究与人工辅助决策系统。方法论以 Scott M. Carney 的 Harmonic Trading Volume One / Two / Three 为 Source Truth，工程层在不篡改 Source Identity、Source Raw PRZ、Source Clock 与 Reaction/Reversal 语义的前提下，完成 A 股数据、交易制度、研究证据、交互图表和中文决策辅助的产品化。

**最终目标不是一个需要用户每天跑命令、上传 ZIP、等待 AI 验证的研究脚本集合，而是一个成熟的自动化应用：自动更新市场数据、自动运行谐波分析、自动维护生命周期、自动记录 prospective evidence、自动处理常规异常，并通过 TradingView 类工作台向用户提供可审计的中文人工决策辅助。**

HT-CN 不是自动交易执行器；不以历史回看后的漂亮形态冒充实时可得信息，不用产品评分反向修改谐波身份，也不在前瞻证据不足时宣称胜率、alpha 或盈利能力。

## 1.1 最高级产品有效性门：谐波识别引擎

**谐波识别引擎是 HT-CN 整个项目的最高优先级与产品有效性前提。**

如果系统不能从原始 K 线中稳定找到应当存在的谐波主结构，或者大量识别错误节点、错误形态、错误完成时点，那么后续的 PRZ、Terminal、Type-I/II、Outcome、胜率、AI 解读、UI、自动化和产品包装全部失去可信输入，整个项目在实战层面没有意义。

永久规则：

1. **Recognition correctness 优先于一切外围产品能力。** 当识别可信度存在重大未解决问题时，UI、胜率、Outcome、AI 解释、新指标、包装等工作必须让位。
2. 识别引擎必须同时证明：应识别结构的 Recall、错误结构的 Precision/FP 控制、节点正确性、no-lookahead、历史不可被未来数据重写。
3. 不允许用“候选更多”“图上有东西”“测试数量更多”“UI 更完整”代替识别正确性。
4. 不允许为了提高 Recall 而放宽或篡改 Carney Source Identity / Source Raw PRZ；应先修 Pivot/Swing/Candidate/Time-of-Knowledge/Completion semantics。
5. 任何 AI / Agent 接手项目时，必须先确认当前 Recognition Gate 与 blocker；若识别引擎尚未达到可信 production gate，默认下一项开发必须继续解决识别问题，除非存在阻止识别验证本身的更高层基础设施故障。

当前长期目标链路为：

`Raw OHLC -> confirmed Pivot Events -> Hierarchical XABC -> frozen Source Raw PRZ -> validity/invalidation clock -> event-sourced Source Terminal completion -> dedupe/false-positive audit`

右确认 D Pivot / 精确 D-XA 可作为 retrospective geometry audit，但不得再次取代 observable Source Terminal 作为唯一完成语义。
## 1.2 当前执行顺序：正确性先于容量与产品接入（D-092）

**当前识别总门未通过；Gate 4B 的工程通过不代表识别可靠。** 当前唯一核心任务为 CR-0090。

按 `specs/m9-recognition-gate4c-correctness-first.md` 顺序推进：

1. 明确投影出生、PRZ 接触、Terminal、反转确认和失效的独立语义，隔离出生时证据与后续证据。
2. 优先逐例审查宽 PRZ、同 ABC 多 X、Pine 分歧和跳空返回；核对全部测量及 Source 依据。
3. 建真实标签与全新封存验收集，调参前冻结指标和门槛；旧 holdout 已参与选参，只作验证/回归。
4. 再比较搜索容量，依据正确率、漏检率、节点/时间误差及实际计算成本，而非候选数或参数乘积。
5. 独立验收后，以单一版本化识别接口最小接入应用，并验证引擎、API、图表一致。

此前容量优先的 next-action 文字属于历史检查点，由此顺序替代。ABCD、Shark、多周期须明确各自覆盖，不能继承标准 XABCD 日频成绩。PRZ 接触不等于反转确认；空结果允许，但要能诊断原因。

保留数据、图表和冻结研究基础；停止外围扩展及全仓重写。冻结不证明实现永远正确：若独立证据确认 Source 错误，必须另立 Source Decision、版本化修订并保护旧 M4，禁止为出图私自放宽规则。

## 2. 永久架构边界

1. Source Harmonic Truth 与 A-share Execution Context 永久分层。
2. Identity 先于 quality/score；非法身份不得被评分救回。
3. Source Raw PRZ 与工程 Ideal Core / Component Envelope / PEZ 分层。
4. Confirmed Pivot Clock 与 observable Source Execution Clock 分层。
5. PRZ 只代表潜在反转区域，不等于 reversal。
6. Type-I Reaction 与 Type-II Reversal 分层。
7. ordinary Wilder RSI 不等于 RSI BAMM。
8. Shark 使用 0-X-A-B-C 拓扑，不发明 D。
9. 5-0 保持 production quarantine，直到 Source conflict 被正式解决。
10. Alternate Bat 保持 fail-closed，直到独立 Source contract 完整冻结。
11. 前瞻研究禁止历史回填、美化 cohort 或重写已消费 evidence。
12. 产品层不得拥有或改写 M2/M3/M4 authoritative harmonic/research state。
13. 工具只辅助人工决策，不执行证券交易。
14. **长期 evidence accumulation 不得被解释为“产品尚未完成”的无限等待条件。**
15. **ISSUE-0066 只限制统计/胜率/alpha/盈利能力结论，不得阻塞 M9 产品开发或 Stable Product Release。**
16. **用户电脑不是 HT-CN 的日常开发基础设施；能够由托管 CI、仓库 fixture、agent-controlled runtime 或自动化服务完成的工作，不得要求用户电脑重复执行。**
17. **D-091：识别引擎是项目最高级产品有效性门。识别不可靠时，任何外围产品完成状态都不能被解释为 HT-CN 已具备实战意义。**

## 3. 项目总里程碑与双轨关系

| Milestone | 目标 | 角色 / 状态 |
| --- | --- | --- |
| M0 | 仓库、工程、测试与规范基座 | complete |
| M1 | A 股数据引擎、DuckDB/Parquet、复权/数据 provenance | established |
| M2 | Carney Source Fidelity / Harmonic Core | core frozen |
| M3 | Canonical Source Lifecycle + A 股 Context + Workbench | integrated |
| M4 | Prospective Evidence / Outcome research architecture | architecture frozen |
| M5 | Daily Operator / Review / Portable Delivery | integrated |
| M6 | Operational Closeout & Integrity | complete |
| M7 | Prospective Evidence Accumulation | **后台长期证据轨，持续运行但不阻塞产品完成** |
| M8 | Evidence-based Decision Calibration | **证据足够后启用；只决定统计校准/声明，不阻塞 M9** |
| M9 | Stable Research/Product Release | **开发主线：自动化、产品化、打包与稳定发布** |

从本 Blueprint v5 起，里程碑不再被解释为必须严格串行的 `M7 完成 -> M8 完成 -> M9 才能开始`。正确依赖关系是：

- M7：持续产生未回看的真实 prospective evidence；
- M8：当预注册证据条件满足时，基于 M7 数据做统计/决策校准；
- M9：在 M7 后台继续积累的同时推进产品自动化与 Stable Release；
- M9 产品可以发布时，即使 ISSUE-0066 仍 open，也必须把统计能力标记为“证据不足/暂不可用”，而不是阻塞整个产品。

## 4. 最终产品交互目标 — TradingView 类同步图表工作台

HT-CN 的最终主图必须是接近 TradingView 的交互式研究工作台，而不是只生成静态谐波截图或固定 SVG。M6.6 已建立 Lightweight Charts + HT-CN overlay 的生产基础，M9 必须把它纳入完整端到端产品工作流。

### 4.1 交互与计算边界

1. K 线支持平移、缩放、价格轴/时间轴操作、crosshair、focus/reset。
2. XABCD / ABCD / 0XABC 节点、腿线、比例、标签绑定 canonical bar/time/price。
3. Raw PRZ、Ideal Core、Component Envelope、PEZ、T1/T2、Terminal、T+1、Type-I/II 与 K 线共用坐标身份。
4. pan/zoom 只是 viewport transform，不得触发谐波重新识别或改写 Source Truth。
5. 只有新 K 线、历史窗口、复权/数据版本、标的或参数变化时才触发受控增量/重新计算。
6. forming pattern 随新数据演化，未来节点不得提前绘制；已冻结历史 evidence 不得回看重写。
7. hover/crosshair 必须把 OHLC、节点、比例、PRZ、生命周期映射到同一 identity。
8. 自动化浏览器测试必须验证 pan/zoom/recompute 后 overlay 不漂移。

## 5. 已完成基础

### M6.1 — Project OS v2 / Cross-Conversation Lossless Continuity
项目状态由仓库、Project State、Decision/Issue/Attempt/Spec 驱动，聊天不是权威状态。

### M6.2 — Real Private-M1 Closeout
真实 Private-M1 current-market closeout 已完成并有 acceptance receipt。

### M6.3 — Universe Coverage Contract
listed / initialized / formal-QFQ-ready / scanner / operator / candidate-set 语义已分层。

### M6.4 — Repository Governance
Project OS、CI、warning/Ruff baseline、正式 release 与 post-merge closeout 已建立。

### M6.5 — Source Coverage Freeze
三卷书关键能力已归档 Supported / Quarantined / Unsupported 并绑定 Source/spec/code/test/decision。

### M6.6 — Interactive Harmonic Chart Foundation
交互 K 线、canonical overlay 坐标、PRZ/lifecycle 同步和浏览器无漂移门禁已建立。

### M7.1–M7.6 — Prospective Evidence Control Plane
首笔真实 M7 prospective capture 已提交并验收；QFQ、capture、Outcome、bundle acceptance、same-day idempotency、append precheck 和 self-contained handoff 已建立。**这些工作证明 evidence pipeline 可运行，不代表用户必须每天人工运行它。**

## 6. 双轨推进模型（永久）

### 6.1 产品完成线 — M9，是当前开发主线

M9 的目标是把已经成立的研究能力封装为成熟应用。开发工作不得因为 M7 需要更多自然时间积累样本而停住。

固定阶段：

1. **M9.0 — Product Completion Policy & Roadmap**  
   冻结本双轨模型、完成定义、用户电脑调用边界和 AI 交接约束。
2. **M9.1 — Automated Market Data & Scheduling Service**  
   自动市场日历、增量行情、QFQ、provider failover/retry、运行调度、健康检查；用户不再运行日常 BAT。
3. **M9.2 — Automated Harmonic Analysis Runtime**  
   新数据到达后自动增量扫描/计算，forming pattern 演化，生命周期与 Source Truth 同步；viewport 操作不重算。**首要验收不是“能运行”，而是识别正确性通过 Ground Truth、真实市场、no-lookahead 与 false-positive gates；未通过时不得用外围产品能力替代。**
4. **M9.3 — End-to-End Product Workbench**  
   股票选择、K 线、谐波 overlay、节点比例、PRZ、状态、关键价位、中文解释和审计信息在同一工作台闭环。
5. **M9.4 — Background Evidence / Calibration Service & Observability**  
   M7 evidence、Outcome、health、cohort、审计后台自动维护；M8 未解锁时产品显示“证据不足”，不生成伪统计。
6. **M9.5 — Reliability, Packaging & Zero-CLI Operation**  
   自动启动/恢复、数据迁移、中文错误、日志、备份、升级、异常恢复；普通使用不依赖命令行、ZIP 或 AI 陪跑。
7. **M9.6 — Stable Product Release Acceptance**  
   完成真实端到端验收、发布包/版本、文档和用户工作流；达到本 Blueprint 的“产品完成定义”。

### 6.2 长期证据线 — M7，后台持续

M7 继续积累 prospective cohort、Source Terminal、Type-I/II、right-censoring、5/10/20 traded-bar MFE/MAE 与市场环境分层，但它是**运行期后台轨**：

- 不要求用户每天人工启动；
- 不要求用户每天上传 ZIP；
- 不作为 M9 开发或 stable release 的自然时间等待门槛；
- 证据服务未自动化之前，不得用“每天人工跑用户电脑”代替产品化工作。

### 6.3 校准线 — M8，证据成熟后启用

M8 负责 evidence-based calibration。ISSUE-0066 open 时：

- 禁止真实胜率、alpha、盈利能力和统计显著性结论；
- 可以继续完成所有不依赖这些统计结论的产品能力；
- UI/报告必须明确显示“证据不足/统计能力未解锁”；
- 不得为了进入 M8 而历史回填或降低 sample/evidence gate。

## 7. 用户电脑调用边界（永久）

### 7.1 默认原则

**用户电脑不是测试农场、CI runner 或日常 evidence 采集机。**

默认测试顺序：

1. agent-controlled / hosted 单元与集成测试；
2. GitHub CI / browser / freeze gates；
3. 仓库内 deterministic fixture / portable evidence；
4. 自动化服务运行环境；
5. 只有前四项无法替代且确实依赖用户私有状态时，才请求用户电脑。

### 7.2 允许请求用户电脑的情况

仅限：

- 无法在托管/fixture 环境重现、且问题明确依赖用户私有 M1 数据；
- 一次性数据迁移/升级必须读取用户已有私有数据库；
- 最终用户验收（UAT）或用户主动要求本地预览；
- 明确的本地环境兼容性故障。

每次请求前 AI 必须能说明：**为什么托管测试不能替代、需要用户执行什么、只需执行几次、产生什么唯一证据。**

### 7.3 明确禁止

不得因为以下原因要求用户电脑：

- 普通代码回归；
- 每日 M7 evidence accumulation；
- 同一交易日重复验证；
- 普通 QFQ/provider 测试；
- 浏览器/图表回归；
- Project OS/CI/冻结门禁；
- “为了多积累一天样本”而人工运行。

## 8. Stable Product 完成定义

HT-CN v1 Stable Product 在以下产品能力全部成立时即可宣告“开发完成”，**不要求 ISSUE-0066 已关闭**。

**前置硬门：自动谐波识别必须达到 D-091 的可信标准。若原始 K 线上的结构识别、完成时钟或误报控制仍存在重大缺陷，则即使 UI、安装、后台服务和发布流程全部成熟，也只能称为 runtime/product engineering 成熟，不能称为具备有效谐波研究能力。**

1. 市场数据和交易日更新可自动运行，失败有重试/降级/健康状态；
2. 复权与数据 provenance 自动维护；
3. 新数据能自动触发谐波扫描、生命周期更新和受控增量计算；
4. TradingView 类交互工作台可完整展示 K 线、节点、比例、PRZ、目标、生命周期与中文解释；
5. 后台 evidence/Outcome 自动维护，不需要用户每日介入；
6. M8 尚未解锁时，统计能力明确显示“证据不足”，且不伪造结论；
7. 常见故障有自动恢复或明确中文诊断；
8. 安装、启动、升级和日常使用不要求用户命令行；
9. 日常使用不要求 ZIP handoff 或 AI 人工验收；
10. 正式 browser/integration/freeze/release gates 全绿；
11. Source Truth、37-component M4 methodology、4-component Outcome Engine 和不可变边界继续受保护；
12. 产品仍只做人工决策辅助，不执行证券交易。

**产品发布后的 M7/M8 继续运行属于产品运营与研究校准，不代表产品开发尚未结束。**

## 9. AI 交接硬规则

任何新 AI / 新对话恢复项目时必须明确回答：

1. **当前 Recognition Gate、识别引擎最大 blocker 与可信度状态是什么？如果尚未 green，当前任务为什么直接服务于识别正确性？**
2. 当前产品开发主线是什么？答案必须来自 Project State / Product Completion Policy，而不是从 M7 样本数量猜测。
3. M7 是开发阻塞线还是后台长期证据线？
4. ISSUE-0066 阻塞什么、明确不阻塞什么？
5. 当前是否真的需要用户电脑？若需要，为什么托管/自动化不能替代？
6. 当前 M9 phase 与 Stable Product 剩余 exit gates 是什么？

禁止把“继续积累 M7”当作默认的下一项开发工作，除非当前任务明确是 evidence 服务本身的产品化或出现真实 evidence blocker。

## 10. 项目事实权威顺序

1. canonical Git history / current source / tests；
2. formal release & CI evidence；
3. `governance/PROJECT_STATE.json`；
4. `governance/PRODUCT_COMPLETION_POLICY.json`；
5. 本 Blueprint；
6. active Change / Decision / Issue / Source Coverage ledgers；
7. active specs；
8. historical PROJECT_CONTEXT / DECISIONS / SESSION_LOG / PR / commit history；
9. 聊天记忆、旧对话、截图。

任何低层信息不得覆盖高层事实。重要事实不得只存在于聊天中。
