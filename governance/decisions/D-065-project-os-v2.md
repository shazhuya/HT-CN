# D-065 — Project OS v2 / Repository-State-Driven Continuity

status: active
change: CR-0065
date: 2026-09-19

## Decision

HT-CN 从本决策起正式由“对话上下文驱动”切换为“仓库项目状态驱动”。

### 权威状态

当前项目状态必须首先由 `governance/PROJECT_STATE.json` 表达。聊天记忆、旧对话、截图和人工摘要不得作为 current state authority。

### 信息必须落库

任何会影响后续工作的事实，包括用户调整、需求否定、bug、失败尝试、Source interpretation、defer、验收结果、blocker，都必须进入 Change / Decision / Issue / Attempt / State 至少一个 ledger。重要事实不得只存在于聊天。

### Current 与 History 分离

- PROJECT_STATE：现在是什么；
- PROJECT_BLUEPRINT：最终往哪里走；
- Change：本轮为什么改、验收什么；
- Attempt：每次成功/失败尝试；
- Decision：为什么采用/禁止某个长期规则；
- Issue：尚未解决的 blocker/risk；
- Source Coverage：三卷书能力覆盖状态；
- PROJECT_CONTEXT / SESSION_LOG / legacy DECISIONS：历史深层材料，不再拥有 current state。

### Fail-closed

Project bootstrap/state validation 检测到 release anchor、active change、active decision、required spec、ledger reference 或 Git ancestry 不一致时必须失败，禁止继续修改核心代码。

### Dynamic context

Resume Pack 不得继续硬编码旧 M2/M3 active specs。它必须从 PROJECT_STATE 和 ledgers 动态选择当前工作所需信息。

## Rationale

过去已经实际发生“项目已推进到更晚 Phase，但新对话恢复到旧 M4/M5 checkpoint”的偏差。人工长文档随着项目增长也会产生 current/history 混杂和 stale top-level 状态。结构化、可测试、fail-closed 的 Project OS 是解决问题的必要条件。
