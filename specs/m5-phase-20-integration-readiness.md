# M5 Phase 20 — Preserve-Ancestry Integration Readiness v1

状态：**implementation in progress**

## 1. 目标

Phase19 已形成可交付的日常产品链，但项目仍有一个长期治理风险：

- `main` 相对最新 M5 lineage 大幅落后；
- M4/M5 的大量工作仍存在于连续 feature lineage；
- 多个历史 phase PR 仍然 open；
- 若用 squash/rebase“清理历史”，会破坏 M4 methodology / Outcome Engine / phase checkpoint 的精确祖先关系。

Phase20 不开发新的交易功能。

Phase20 只解决：

> **如何把当前 M2 → M3 → M4 → M5 lineage 安全地准备为一次 preserve-ancestry 的 main integration。**

## 2. 当前 Git 事实冻结

Phase20 启动时：

- target: `main`;
- main HEAD: `e25fd9584008d35ec464c73f91854d12a66f79ff`;
- merge base: `edec5e21fb9e873daf8fb77fceaa0d89dbbd5b25`;
- latest Phase19 lineage vs main:
  - lineage-only >= 625 commits;
  - main-only = 1 commit;
- main-only commit:
  - `e25fd9584008d35ec464c73f91854d12a66f79ff`;
  - README cleanup only;
- allowed main-only path:
  - `README.md`.

如果 main HEAD 在 integration 前变化，Phase20 必须 fail closed 并重新审计，不能继续沿用旧 readiness。

## 3. Merge method

唯一允许的最终 integration method：

`merge commit`

明确禁止：

- squash；
- rebase；
- force update main；
- 把 625+ lineage commit 压成一个；
- 重新生成 M4 methodology/outcome history。

原因：

M4 source/methodology/outcome provenance 和 M5 phase lineage 依赖精确祖先关系。

## 4. Required ancestor checkpoints

Integration head 必须保留以下祖先：

- M2.31 source fidelity:
  `fbf964fb2230df2dd21138d2d99f037d3b5a382f`
- M3 merge base:
  `edec5e21fb9e873daf8fb77fceaa0d89dbbd5b25`
- M4 methodology freeze:
  `c774c54928c33361952bf1a612a8555633449625`
- M4 Outcome Engine anchor:
  `9cbc0d3d30ac5f0a87748a39788cbee04a44bcc8`
- M5 Phase14:
  `c9de28d959b64043663a2bceccb17cc87b8f3756`
- M5 Phase15:
  `cc6fc7dd230f3229f1882d4fb6c50476515af887`
- M5 Phase16:
  `364835c6661050cdda760c2c45a9488143b9a629`
- M5 Phase17:
  `71093b22c1f6efd4ce7faa740a9dd8b2c554db20`
- M5 Phase18:
  `476acfa239fe67111e87a0adce3bb25e085792a7`
- M5 Phase19:
  `03cd1acdf4c60e5e319a4e6d433d8e3336f8b93d`

任一不是 HEAD 的 ancestor：

integration blocked。

## 5. Real Git history gate

新增：

`src/htcn/app/integration_readiness.py`

`scripts/m5_integration_readiness.py`

它不是只读 GitHub PR metadata，而是在 full-history checkout 中执行真实 Git：

- `git rev-parse HEAD`
- `git rev-parse origin/main`
- `git merge-base origin/main HEAD`
- `git rev-list --left-right --count origin/main...HEAD`
- `git rev-list HEAD..origin/main`
- main-only diff paths
- `git merge-base --is-ancestor <checkpoint> HEAD`
- tracked worktree clean check。

## 6. Main-only change contract

Phase20 当前只允许 main-only：

- commit = frozen README cleanup commit；
- path set = exactly `README.md`;
- main README has one non-empty line。

任何新的 main-only commit/path：

fail closed + re-audit。

这是为了避免 integration PR 在准备期间悄悄跨过新的 main changes。

## 7. Hosted integration job

CI 新增独立 job：

`integration-readiness`

只在 Phase20 integration branch / integration PR 上运行。

要求：

- checkout `fetch-depth: 0`;
- checkout PR head rather than synthetic merge result；
- setup Python；
- install project；
- run integration readiness script；
- run M4 methodology freeze guard；
- run M4 Outcome Engine freeze guard；
- upload readiness report。

普通 deterministic job 保持不变，仍需：

- Python full regressions；
- Web build；
- existing 24 Playwright；
- Phase18 real-browser gate/evidence。

因此 integration readiness 是附加 gate，不替代产品测试。

## 8. Integration carrier PR

Phase20 完成后建立一个新的 carrier PR：

`m5/integration-readiness-v1 -> main`

该 PR 是 main integration 的唯一 carrier。

历史 phase-local PR 保留为 review/audit history，但不再逐个 merge main。

Carrier PR 必须：

- mergeable；
- deterministic job green；
- integration-readiness job green；
- main HEAD 仍等于 frozen expected main HEAD；
- merge method = merge commit。

## 9. README resolution

main 唯一独有 change 是 README cleanup。

因为它位于 main 的独立 parent lineage，最终 merge commit 应保留该 parent。

Phase20 不通过 cherry-pick/rebase 把它伪装进 M5 ancestry。

若 GitHub 报冲突：

不得 force/squash；
必须显式解决后重新跑 readiness，并保持 main commit 作为 merge parent。

## 10. 不做的事

Phase20 不：

- 改 harmonic/source rules；
- 改 v4/v3 transport；
- 改 Phase19 delivery；
- 改 M4 evidence；
- 运行真实交易；
- 声称盈利；
- 清除历史 phase branches；
- 在 readiness 未绿时 merge main。

## 11. Acceptance

- [ ] current main HEAD exact match；
- [ ] merge base exact match；
- [ ] main-only commit exact match；
- [ ] main-only path exact README-only；
- [ ] lineage-only commits >= 625；
- [ ] all required checkpoints are ancestors；
- [ ] tracked worktree clean；
- [ ] merge method contract = merge-only；
- [ ] squash/rebase forbidden；
- [ ] M4 methodology guard green；
- [ ] M4 Outcome Engine guard green；
- [ ] deterministic product CI green；
- [ ] Phase18 browser evidence green；
- [ ] integration-readiness hosted job green；
- [ ] carrier PR to main created and mergeable；
- [ ] no methodology/product implementation drift introduced by Phase20。
