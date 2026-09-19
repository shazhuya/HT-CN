# M6 Phase 1 — Project OS v2 / Cross-Conversation Lossless Continuity

## Scope

本 Phase 只修改项目治理、恢复协议、上下文生成和相应 CI/tests，不修改谐波算法、M4 evidence semantics 或 M5 product semantics。

## Data model

权威文件：

- `PROJECT_BLUEPRINT.md`
- `governance/PROJECT_STATE.json`
- `governance/MILESTONES.json`
- `governance/DECISION_INDEX.json`
- `governance/SOURCE_COVERAGE.json`
- `governance/OPEN_ISSUES.json`
- `governance/changes/CR-*.md`
- `governance/attempts/*.jsonl`
- `governance/releases/*.json`

Legacy deep-history files `PROJECT_CONTEXT.md`, `DECISIONS.md`, `SESSION_LOG.md` 保留但降级为历史资料。

## Bootstrap contract

新会话在实现前必须：

1. refresh canonical Git state / latest formal release；
2. read PROJECT_STATE + Blueprint；
3. validate all ledger references；
4. read active Change；
5. read only required specs / active decisions / open blockers；
6. compare last integrated release anchor to current Git history；
7. state drift => stop and repair state before product/source changes；
8. only then continue implementation。

## Closeout contract

任何重要事实不得只存在于聊天。每个工作单元必须把结果写入至少一个 structured ledger，并在 Gate 变化时更新 PROJECT_STATE。

## CI contract

Project OS integrity check must be an explicit deterministic and formal-main-release step. Tests must not merely check file existence; they must validate semantic references and forbid the legacy hard-coded active-spec list.

## No-mutation boundary

M6.1 does not alter M2 Source Truth, M3 lifecycle semantics, M4 methodology/outcome engine, M5 delivery semantics or private-M1 data.
