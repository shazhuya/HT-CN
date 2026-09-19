# CR-0065 — HT-CN Project OS v2 / 跨对话无损续接

status: closed
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

## 当前验证状态

- Project OS fail-closed gate: green；
- push CI #2019 / 35436109461: success；
- Python: 855 passed / 1163 warnings；
- Web build: success；
- PR→main formal release: pending on final governance HEAD；
- first failed validation #2010 is preserved in Attempt Ledger and was fixed without weakening the gate。
- PR CI #2031 / 35436210906: Project OS gate passed, but one Resume Pack test was over-constrained; failure preserved as A-20260919-0065-006 and test narrowed without allowing legacy body dumps。

## Final Closeout

- PR #37 final head: `fe2a1ba62073c8bdd6deacf81b19a8f198d46392`；
- PR→main formal release run: `35436318390` — success；
- merge commit: `ccf3592a7ea4d2e97e95d367a389e1a10c74aa4f`；
- merge-generated push-main run: `35436435722` — success；
- Python: **855 passed / 1163 warnings**；
- existing browser acceptance: **24 passed**；
- Phase18: **1 passed / evidence valid**；
- Phase21: **1 passed / evidence valid**；
- M4 capture methodology: **frozen_match / 37 components**；
- Outcome Engine: **frozen_match / 4 components**；
- main release artifact: **10581534183**；
- historical stacked M5 draft PRs are closed or explicitly superseded；
- two real failed Project OS validations remain preserved in Attempt Ledger；
- no harmonic / Source / M4 / M5 product semantics were mutated。

All M6.1 acceptance criteria are closed. M6.2 is the next project task but is not started by this closeout.
