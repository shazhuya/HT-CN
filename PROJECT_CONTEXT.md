# HT-CN Project Context — 跨对话权威状态

context_schema: `1`
context_checkpoint: `07fde2b1d69664e421b1cb86e3af45a6e26b1093`
context_checkpoint_title: `M2.28: standalone AB=CD Source Raw PRZ v4`
context_snapshot_date: `2026-09-17`
default_branch: `main`
repository: `shazhuya/HT-CN`

> 本文件用于恢复“项目现在到底做到哪里”。它不是历史聊天摘要，也不是替代源码/测试。若本文件与当前 HEAD 冲突，必须先检查 `context_checkpoint..HEAD` 的提交，再更新本文件。

## 当前阶段

当前有效开发主线仍处于 **M2 Source Fidelity Repair / Source PRZ Golden Set 收口阶段**。

最近已完成并通过真实 A 股 CI 的检查点为 **M2.28**：

- 标准 XABCD 的 M2.27 Source Raw PRZ 保持不变；
- standalone AB=CD 新增 source-backed Raw PRZ：equivalent `AB=CD x1` defining measurement + reciprocal BC complementary measurement；
- Volume Three BC layering 被固定为 execution-only，不属于 identity / Raw PRZ；
- API price-zone contract 升至 semantics v3 / source profile v2；
- research definition 升至 `m2-source-prz-v4`；
- 45-symbol real A-share v4 全链 CI success；
- 历史 Holdout / external replication / v3 结果均保持冻结，不回写、不重算。

M3 Phase 1 的已有产品化成果继续保留，但 **M3 execution overlay 正常扩张仍受 Source Fidelity Gate 约束**。旧 retrospective D-based overlay 不得继续被解释成 live execution semantics。

## M2.28 真实研究检查点

数据集：`a-share-research-v2-45`；snapshot cutoff `2026-09-15`。

- forming signals：8085；
- mature Source-Raw-PRZ Terminal events：**1233**；
- Train / Validation / sealed Holdout：**730 / 222 / 258**；purged 23；
- `source_prz_unresolved`：M2.27 v3 的 6547 -> M2.28 v4 的 **1724**；
- mature T-Bar：v3 的 166 -> v4 的 **1233**；
- 样本扩张主要来自 standalone AB=CD：Train 627、Validation 198、sealed Holdout 226；
- Type-I robustness：当前 visible evidence 中只有 `full_prz_exit_by_t5` robust；Train lift +6.33 pct，Validation lift +10.84 pct；
- nested T+3/T+5 timing 仍 `not_ready`，selected hypothesis = none；
- v4 `confirmatory_inference_allowed = false`，不能把上述结果写成当前个股概率或机械交易规则。

详细冻结见 `specs/m2-28-source-prz-abcd-closeout.md`。

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

原则：**宁可 unresolved / fail closed，也不允许工程近似伪装成原书规则。**

## 已冻结的重要事实与约束

1. **方法论权威**：Scott M. Carney《Harmonic Trading》Volume One / Two / Three 是 harmonic identity、source measurement、Reaction vs. Reversal 执行概念的理论基准。
2. **双时钟**：几何/回溯 D 时钟与执行/Terminal Price Bar 时钟永久分离。
3. **PRZ 分层**：component envelope、Ideal Core、Source Raw PRZ、Terminal extreme、PEZ 不得混称。
4. **standalone AB=CD**：Source Raw PRZ = equivalent AB=CD defining completion + reciprocal BC；V3 BC layering 仅 execution tolerance，不得进入 identity/Raw PRZ。
5. **Type-II**：必须经过完整原 Raw PRZ terminal-side retest 后才进入 Type-II T-Bar 与 price / indicator confirmation。
6. **RSI**：当前 Wilder RSI evidence 只是辅助确认，不是 RSI BAMM。
7. **5-0**：默认从 Engine / Scanner / Workbench 隔离；未完成 V2/V3 figure-level reconciliation 前不得恢复默认生产输出。
8. **Shark**：使用自身 first-target contract；initial target 为从 C 出发先遇到的 50% BC 或 Reciprocal AB=CD，不机械套通用 XABCD T1/T2。
9. **Identity 优先**：geometry score、历史统计、A 股上下文、UI 偏好不能挽救一个不满足 source-backed identity 的候选。
10. **研究边界**：冻结的历史 Holdout / external replication / 已消费结果不得回头篡改；规则变化必须开新 research version。
11. **A 股增强分层**：T+1、涨跌停、流动性、ATR、指数/板块环境等只进入执行/可交易性层，不改写 Carney identity / Source PRZ。
12. **中文优先**：界面、状态、审计提示尽量中文化；内部技术标识保持稳定英文。
13. **市场范围**：当前默认 SSE/SZSE；BSE 暂不处理。
14. **交易边界**：HT-CN 是研究与辅助决策系统，不执行交易。

## 已完成里程碑

- M0 ✅ 工程骨架、本地启动、测试基础设施。
- M1 ✅ A 股数据层、日线、QFQ/HFQ、智能增量、健康检查。
- M2 ✅ Pivot / Fibonacci / 标准 Pattern / AB=CD / Shark / Reaction vs. Reversal / T-Bar 研究资产与历史研究基础。
- M2.26 ✅ 双时钟、PRZ 分层、严格 Type-II、5-0 quarantine、Shark target contract、API v2 等 Source Fidelity Repair 主体。
- M2.27 ✅ 标准 XABCD Source PRZ Golden Profiles、Book Case、source/engineering provenance、v3 research boundary。
- M2.28 ✅ standalone AB=CD Source Raw PRZ、AB=CD Book Gate、BC-layering execution-only、v4 research boundary、真实 45 股 v4 全链验收。
- M3 Phase 1 ✅ 中文 lifecycle navigator / workbench / 浏览器自动验收资产；后续产品扩张仍受当前 Gate 限制。

## 当前仍未完全解决

以下项目不得靠猜测补齐：

- **5-0**：Volume Two structural PRZ 与 Volume Three conditional execution refinement 尚需 figure-level reconciliation；
- Shark source PRZ terminal-side / 5-0 transition 的最终 source freeze；
- RSI BAMM 尚未实现完整独立多步骤状态机；
- standard XABCD per-pattern AB=CD family hard gate 仍需进一步 source-backed refinement，不能只靠宽松 `>=1.0` 永久存在；
- M3 retrospective lifecycle overlay 需要迁移为 source-aligned live execution-clock semantics；
- CI snapshot cache miss 时的历史 artifact bootstrap 当前可能因 GitHub integration 权限失败，属于工程韧性问题；
- M1 全市场覆盖度与核心算法正确性仍分开管理。

## 下一步唯一主任务

**M2.29 — 5-0 Volume Two / Volume Three Source Reconciliation。**

执行顺序：

1. 保持 production quarantine，不因已有 evaluator 存在就恢复默认扫描；
2. 逐图例核对 V2 structural PRZ：50% BC + Reciprocal AB=CD；
3. 独立建模 V3 conditional execution refinement / 61.8 make-or-break；
4. 禁止再次压缩成 universal 50%-61.8 identity band；
5. 建立 Book Golden regression 与 negative cases；
6. 只有 source conflict 真正关闭后，才决定是否恢复 source-certified 5-0 identity/execution output。

之后再收 Shark terminal-side source freeze、RSI BAMM dedicated module；Source Fidelity Gate 关闭后，再恢复 M3 live execution overlays。

## 当前验收入口

- M2 综合验收：`运行M2综合验收.bat`
- M3 Phase 1 工作台保护性验收：`运行M3工作台验收.bat`
- 前瞻 Type-I 登记：`运行M2前瞻Type-I登记.bat`（独立持续研究流程，普通 acceptance 不得修改）

## 新会话恢复必须核对

新会话继续开发前必须核对：

- 当前 HEAD 与 `context_checkpoint` 的差异；
- 最近 CI 是否 success；
- 相关 `specs/` 是否更新；
- 是否出现新的 research version boundary；
- 是否有旧聊天结论被当前源码/测试推翻。

完成上述检查后，才能宣称“已恢复 HT-CN 当前现场”。
