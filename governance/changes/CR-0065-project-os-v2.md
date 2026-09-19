# CR-0065 — HT-CN Project OS v2 / 跨对话无损续接

status: validation_failed
baseline_ref: m5/phase23-postmerge-closeout
baseline_head: 29c88c41aa024a4ac00fecdf7e43a61a51e50ad1
target: main
milestone: M6.1

## 用户问题

项目多次因单个长对话达到上下文上限而新开对话，随后出现阶段恢复过旧、失败经验丢失、下一步偏离真实项目进度的问题。项目必须依赖固定蓝图和实际仓库进展，而不是依赖某一段聊天。

## 必须解决

1. 每次修改、成功或失败的详细信息可恢复；
2. 整体推进依赖长期 Blueprint/Milestones；
3. current state 与历史长日志分离；
4. active specs 不再在 context-pack 脚本里硬编码；
5. superseded decisions 不得被旧对话重新激活；
6. Source support/quarantine/unsupported 有机器 ledger；
7. Open issues 有唯一索引；
8. blank-session bootstrap 可仅凭项目恢复；
9. state drift 在 CI 中 fail closed；
10. 旧 PROJECT_CONTEXT / SESSION_LOG 保留历史价值但不再覆盖机器 current state。

## 验收标准

- Project Blueprint 存在且定义 M0–M9 和 M6 exit gates；
- PROJECT_STATE 为 machine-readable current truth；
- Milestone / Decision / Source / Issue / Release / Attempt ledgers 存在；
- context pack v2 动态读取 state，不含硬编码 ACTIVE_SPECS；
- project-state checker 验证 Git ancestry、active change、required specs、ledger references；
- CI 显式运行 Project OS integrity gate；
- automated tests 覆盖 stale/missing/superseded reference；
- PR→main formal release gate green；
- merge 后更新 state 为 M6.1 closed / M6.2 next；
- historical stacked draft PRs 被清理或记录明确 blocker。

## 非目标

本 Change 不修改 harmonic identity、Source Raw PRZ、Source lifecycle、M4 methodology、Outcome Engine，不执行 private-M1 更新，不引入预测评分或交易执行。