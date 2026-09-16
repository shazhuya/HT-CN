# HT-CN Project Context — 跨对话权威状态

context_schema: `1`
context_checkpoint: `612c0dc01ecbbadfe763bbe9a78c9acd9cee5014`
context_checkpoint_title: `M2.27: freeze source PRZ golden profiles`
context_snapshot_date: `2026-09-17`
default_branch: `main`
repository: `shazhuya/HT-CN`

> 本文件用于恢复“项目现在到底做到哪里”。它不是历史聊天摘要，也不是替代源码/测试。若本文件与当前 HEAD 冲突，必须先检查 `context_checkpoint..HEAD` 的提交，再更新本文件。

## 当前阶段

当前有效开发主线仍处于 **M2 Source Fidelity Repair / Source PRZ Golden Set 收口阶段**。

最近已验收的功能/研究检查点为 M2.27：

- 标准 XABCD 形态建立 source-backed Raw PRZ profiles；
- 新增 Book Case 证据；
- source provenance 与 engineering provenance 分离；
- 建立 source-Raw-PRZ v3 研究语义；
- 历史已关闭研究结果继续保持冻结，不回写；
- 最新 `main` CI 对该检查点为 success。

M3 工作台 Phase 1 的已有产品化成果保留，但 **M3 正常功能扩张仍受 Source Fidelity Gate 约束**。在 source-aligned Terminal Price Bar / Source PRZ / 执行语义没有完成必要冻结前，不应继续把旧的 retrospective overlay 当作 live execution semantics 扩张。

## 当前 Gate

### Gate 名称

`Source Fidelity before M3 expansion`

### Gate 的根因

三卷 Carney 原始方法复核发现，历史实现中存在把以下概念混用的风险：

- 后验 D Pivot 与 source-aligned Terminal Price Bar；
- ideal convergence core 与完整 source Raw PRZ；
- 简化 Wilder RSI 反转与 RSI BAMM；
- 5-0 的 Volume Two 结构 PRZ 与 Volume Three 执行细化；
- Shark 与通用 XABCD T1/T2 管理。

因此当前原则是：**宁可 unresolved / fail closed，也不允许工程近似伪装成原书规则。**

## 已冻结的重要事实与约束

1. **方法论权威**：Scott M. Carney《Harmonic Trading》Volume One / Two / Three 是 harmonic identity、source measurement、Reaction vs. Reversal 执行概念的理论基准。
2. **双时钟**：几何/回溯 D 时钟与执行/Terminal Price Bar 时钟必须分离。
3. **PRZ 分层**：`component envelope`、`ideal convergence core`、`source Raw PRZ`、Terminal extreme、PEZ 不得混称。
4. **Type-II**：必须经过完整原 PRZ terminal side retest 后才进入 Type-II candidate/confirmation 路径。
5. **RSI**：当前 Wilder RSI evidence 只是辅助确认，不是 RSI BAMM。
6. **5-0**：默认从 Engine / Scanner / Workbench 隔离；未完成 Volume Two / Volume Three 图例级 reconciliation 前不得恢复默认生产输出。
7. **Shark**：使用自身 first-target 语义；initial target 为从 C 出发先遇到的 50% BC 或 Reciprocal AB=CD，而不是机械套用通用 XABCD T1/T2。
8. **Identity 优先**：geometry score、历史统计、A 股上下文、UI 偏好不能挽救一个已经不满足 source-backed identity 的候选。
9. **研究边界**：冻结的历史 Holdout / external replication / 已消费结果不得回头篡改；规则变化必须开新版本协议。
10. **A 股增强分层**：T+1、涨跌停、流动性、ATR、指数/板块环境等只能进入执行/可交易性层，不改写 Carney identity / source PRZ。
11. **中文优先**：用户界面、状态解释、审计提示尽量中文化；技术内部标识可保留稳定英文。
12. **市场范围**：当前默认 SSE/SZSE；BSE 暂不处理。
13. **交易边界**：HT-CN 是研究与辅助决策系统，不执行交易。

## 已完成里程碑

- M0 ✅ 工程骨架、本地启动、测试基础设施。
- M1 ✅ A 股数据层、证券主表、日线、QFQ/HFQ、智能增量、健康检查。
- M2 ✅ 已形成 Pivot / Fibonacci / 标准 Pattern / AB=CD / Shark / Reaction vs. Reversal / Terminal Price Bar 研究管线、真实 A 股校准、历史 Holdout / 外部复现等基础资产。
- M2.26 ✅ Source Fidelity Repair 主体：双时钟、PRZ 分层、严格 Type-II、5-0 quarantine、Shark target contract、API v2 price-zone contract 等。
- M2.27 ✅ Source PRZ Golden Profiles：标准 XABCD source-backed Raw PRZ、Book Case 证据、source/engineering provenance、source-Raw-PRZ v3 research semantics。
- M3 Phase 1 ✅ 已有中文实战工作台 / lifecycle navigator / 浏览器自动验收资产，但后续产品扩张暂受当前 Gate 限制。

## 当前仍未完全解决

以下项目不得靠猜测补齐：

- Book Golden Set 还需继续覆盖/核验尚未完全 source-cleared 的形态与执行语义；
- Shark source PRZ terminal-side 的最终 source freeze 仍需保持图例/文本证据驱动；
- 5-0 的 Volume Two 结构 PRZ 与 Volume Three 执行细化仍需完成 figure-level reconciliation；
- RSI BAMM 尚未实现完整独立状态机；
- M3 中历史 retrospective lifecycle overlay 需要逐步迁移为 source-aligned live execution-clock 语义，不能直接继承旧标签含义；
- M1 全市场覆盖度与“核心功能正确性”分开：M2 验收通过不代表本地所有 A 股已全部初始化。

## 下一步唯一主任务

**继续关闭 Source Fidelity Gate，而不是扩张新的 M3 功能。**

执行顺序：

1. 以 Book Golden Set / source evidence 继续核验剩余 Source PRZ 与 pattern-specific execution semantics；
2. 优先完成仍存在 source conflict 的 Shark / 5-0 边界，不允许用通用区间替代原书定义；
3. 对 source-Raw-PRZ v3 研究边界做回归与 CI 保护；
4. 确认 Terminal Price Bar / PEZ / Type-I / Type-II 的 runtime observability 与 source clock 一致；
5. Gate 关闭后，再恢复 M3，把工作台导航迁移到 live execution-clock targets。

若 `context_checkpoint..HEAD` 已经出现新的功能提交，则新会话必须先根据这些提交重新判断“下一步唯一主任务”，不得机械照抄本节。

## 当前验收入口

### M2 综合验收

`运行M2综合验收.bat`

该入口覆盖 deterministic QA、Web build、API、fixture/live browser acceptance、真实本地 QFQ 扫描、Reaction/retest/RSI audit、Pivot robustness、Golden candidate、冻结历史研究完整性、数据集健康检查。

### M3 工作台验收

`运行M3工作台验收.bat`

该资产当前用于保护已完成的 M3 Phase 1，不代表 Source Fidelity Gate 已自动关闭。

### 前瞻 Type-I 登记

`运行M2前瞻Type-I登记.bat`

这是独立持续研究流程，不应被普通 M2 acceptance 自动修改。

## 新会话恢复必须核对

新会话在继续开发前必须核对：

- 当前 HEAD 与 `context_checkpoint` 是否一致；
- 若不一致，列出 `context_checkpoint..HEAD` 的提交；
- 最近 CI 是否 success；
- 与下一步有关的 `specs/` 是否被这些提交更新；
- 是否出现新的 research version boundary；
- 是否有任何旧聊天结论已经被仓库推翻。

完成上述检查后，才能宣称“已恢复 HT-CN 当前现场”。
