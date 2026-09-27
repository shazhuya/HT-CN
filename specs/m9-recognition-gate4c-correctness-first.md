# CR-0090 Gate 4C — Correctness before capacity and production integration

status: implementing
decision: D-092
effective_date: 2026-09-27

## Authority and objective

This plan supersedes the capacity-first next-action text in earlier CR-0090 checkpoints.
Those checkpoints remain historical evidence, not promotion approval.
The only product-development objective is trustworthy harmonic recognition. If structures,
nodes or observable events are unreliable, HT-CN has no meaningful harmonic-research value.
D-091 remains the highest product-validity gate. No UI expansion, AI explanation, win-rate,
Outcome changes, installer work, new indicators or broad cleanup may displace this work.

## Current status

Gate 4B is an engineering checkpoint, not a semantic precision pass. V2 is experimental and
not integrated into the application. Counts, Pine agreement, CI success and PRZ contacts cannot
establish correctness. Existing main/release maturity cannot override this open recognition gate.

## Ordered work and finite deliverables

| Stage | Required work | Reviewable exit evidence |
|---|---|---|
| 4C.1 Semantics | Version projection birth, PRZ entry, Terminal, reaction confirmation and retirement separately. Freeze birth evidence; record later scale support as later events. Specify gap-through/return, C breach, expiry and same-bar ambiguity. | Event contract plus independently calculated boundary cases; no implementation promotion based on quantity. |
| 4C.2 Confluence audit | Audit Crab wide PRZ, same ABC/different X, Pine disagreements and gap-return cases first. | Frozen case register with raw-data identity, node prices/times, all ratios and PRZ components, first-knowable time, source reference, valid/invalid/uncertain ruling and reason. |
| 4C.3 Labels and preregistration | Separate diagnostic challenge set, representative labelled validation and a fresh sealed final test. | Dataset hashes, complete-window truth enumeration, sampling protocol, matching/dedupe rules, per-family/timeframe coverage and numerical thresholds committed BEFORE capacity selection or final-test access. |
| 4C.4 Capacity and selection | Compare 7/8, 5/10 and only necessary neighbors on the same labelled validation data. | Precision/recall/node error/event-timing error, uncertainty, actual path count/runtime and semantic collisions. No parameter-product proxy for smallest capacity. |
| 4C.5 Sealed acceptance | Freeze code and parameters; run untouched final set once. | Predeclared thresholds passed, every hard safety invariant passed, no unsupported family promotion. If used to tune, retire it to validation and obtain a fresh final set. |
| 4C.6 Production equivalence | Introduce one versioned recognition result/event interface and the minimum application adapter. | Same input yields identical event IDs, nodes, PRZ, time and state across audit runner, API and chart payload; incremental/restart replay and 1D/60m/15m checked. |

4C.1 is implemented with hosted regression evidence; the initial eleven-case 4C.2 register exists.
The immediate task is ISSUE-0078 measurement membership and unresolved multi-X adjudication,
followed by case-driven detector corrections and complete-window labels, not another broad count report.
One work unit must deliver concrete cases/contracts or corrected core behavior plus its evidence.
Do not wait for new calendar months, user-PC runs or longitudinal profitability samples.

## Non-negotiable acceptance rules

- A projected structure, PRZ contact, Terminal and confirmed reversal are different claims.
- Independent XABCD-rule agreement does not validate the new XABC/PRZ/Terminal chain.
- Complete labels on fixed windows are required to measure false negatives. Auditing only emitted
  candidates cannot measure recall. Challenge-set precision is not representative market precision.
- Every reported metric exposes denominators, family/direction/timeframe split, label uncertainty
  and interval uncertainty. An uncertain case is neither silently correct nor silently discarded.
- Thresholds for semantic quality must be justified and fixed in 4C.3, before tuning. Until then,
  semantic acceptance is NOT defined and promotion is prohibited; do not invent a passing score.
- Zero future-born historical signals, zero mutation of frozen birth evidence, zero revival of
  explicitly retired events, zero forbidden-family promotions and zero exact duplicate event IDs
  are hard requirements. Legitimate nested structures need explicit relationships, not blanket removal.
- Existing 18-case holdout has participated in capacity selection; classify it as validation/regression,
  never untouched final blind evidence. Keep its historical results intact with that qualification.
- ABCD and Shark require separate contracts and acceptance; standard XABCD results do not cover them.
  Five-Zero/Alternate Bat stay quarantined/fail-closed. Unsupported features remain unsupported.
- Empty results are legitimate when no qualified structure exists; expose stage rejection reasons.

## Architecture and Source boundary

Retain market data, adjusted-price provenance, hierarchical swing graph and event timing.
Converge application consumers on one versioned RecognitionResult/Event interface; old scan/Pine
paths remain explicit legacy/comparison adapters during migration, not competing authorities.
Version identity includes data/adjustment, timeframe, detector/rule/policy configuration and event
provenance. Preserve immutable M4 records and their original evaluator identity.

Source Raw PRZ must not be narrowed or Carney identity relaxed to improve a score. A wide PRZ is
a diagnostic trigger, not proof of an error. Verify book cases and independent measurements first.
If qualification is deficient, make it explicit outside frozen math. If frozen Source implementation
is demonstrably wrong, open a new Source Decision with exact evidence and versioned migration;
do not silently change historical M4/Outcome or treat freeze as proof of correctness.

## Progress reporting

Report concrete failures recovered, new failures found, remaining semantic blockers and next case
to resolve. Test counts and file counts are supporting engineering facts only. Run focused checks
during iteration and required hosted gates at integration; avoid repeated unrelated historical audits.

## Evidence

Architecture audit: governance/reviews/2026-09-27-recognition-architecture-audit.md.
Baseline: 1c44d206 / Artifact 10910643162; actual Gate 4B report: Artifact 10909996357.
The audit is not a new full-market accuracy study or complete re-verification of the three books.

## 识别修复闭环与防跑偏约束（2026-09-27 用户复核）

当前唯一交付目标是：从原始 OHLC 可靠地识别谐波结构，并正确记录其首次可知时间和状态。
审计、规范、测试、续接包只服务于这个目标，不构成识别能力提升本身。

- 每个实现工作单元先明确一个具体错例或漏例、预期结构/节点/时间及依据，再定位到 pivot、候选搜索、身份/PRZ、时钟或去重层；交付修复前后差异和针对性回归。
- Source 争议无法裁定时，交付具体争议证据、受影响范围和下一项可证伪核查；只阻塞相关形态/规则的通过，继续不依赖该争议的识别修复。禁止凭空解决争议，也禁止无限重复同一审计。
- 误报与漏报必须一起评估。全部拒绝、永久 unverified 或只减少候选不算成功；应识别的正例必须可恢复，不应识别的反例必须被拒绝。当前 qualification 全部不授予身份仅是诊断边界，不是最终引擎。
- 标签必须覆盖完整固定行情窗口，独立于引擎输出；同时包含有效结构、相似但无效结构及无形态窗口。调试案例不能冒充代表性准确率。
- 每次收尾写明：修好了什么识别行为、仍错在哪里、下一例是什么。仅更新文档的工作应明确标记为方向/交接修正，不能计为引擎进展。除用户明确要求或新冲突外，不重复开展总架构审计。
- 文档只做与本次变化相关的最小同步；CI 只证明相应工程检查。不得为文档闭环再造无关框架，或把重复报告/打包当作主任务。

当前可执行队列：
1. ISSUE-0078：核对 Crab 原书图例的节点与测量成员，产出可复算案例和明确裁定；确认实现错误后另立 Source Decision 并版本化修复，否则保留争议和范围。
2. 裁定已选恒瑞同 ABC 多 X 案例，给出合法嵌套/重复/错误节点的依据；仅对已证实错误增加回归和修改识别逻辑。Crab 资料不足不阻塞本项。
3. 在完整行情窗口建立独立标签和失败归因，修复 pivot/候选搜索漏检及身份/时钟/去重误报；按 4C.3 预注册指标，随后才选择容量和最终盲验。
4. 已验收能力通过同一版本化接口最小接入应用并验证一致性；不扩大 UI 或其他产品功能。

最终完成条件仍为 D-092 的独立验收及生产一致性；某个家族未解决时不得宣称全引擎可信。
