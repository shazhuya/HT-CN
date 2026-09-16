# HT-CN Session Log — 会话交接记录

本文件只记录“每个开发 Session 最后停在哪里”，避免把长聊天当项目数据库。详细技术事实仍以源码、测试、`PROJECT_CONTEXT.md`、`DECISIONS.md`、`specs/` 为准。

## 2026-09-17 — M2.28 Standalone AB=CD Source Raw PRZ 收口

### 基线

- 起始功能检查点：`612c0dc01ecbbadfe763bbe9a78c9acd9cee5014`（M2.27 merge）
- 结束功能/研究检查点：`07fde2b1d69664e421b1cb86e3af45a6e26b1093`
- 同步 main 双父 merge：`2a8bbdf318c28a5fce9f350d88abc849f8e37203`
- 分支：`m2/source-prz-abcd`
- CI：run #555 / `35127486034`，deterministic + real 45-symbol A-share research 全链 success

### 完成

- standalone AB=CD Source Raw PRZ：equivalent `AB=CD x1` defining completion + reciprocal BC；
- Volume Three BC layering 固定为 execution-only，不进入 identity / Raw PRZ；
- SourceAligned API 升至 semantics v3 / source profile v2；
- 新增 AB=CD Book Source ledger / Golden regression；
- research definition 升至 `m2-source-prz-v4`；
- 新增 v4 sealed research boundary guard；
- 历史 v1/v3/Holdout/external replication 均保持不可变；
- main 在本 Session 中新增的 9 个“跨对话续接协议”提交已安全以双父 merge 合入当前分支，无文件冲突、无 force-push。

### 真实研究验收

- forming signals：8085；
- mature Source-Raw-PRZ Terminal events：1233；
- Train / Validation / sealed Holdout：730 / 222 / 258；purged 23；
- `source_prz_unresolved`：6547（v3）-> 1724（v4）；
- mature T-Bar：166（v3）-> 1233（v4）；
- standalone AB=CD：Train 627 / Validation 198 / sealed Holdout 226；
- v4 visible robustness：仅 `full_prz_exit_by_t5` robust，Train lift +6.33 pct、Validation lift +10.84 pct；
- nested T+3/T+5 timing：not ready，selected hypothesis none；
- v4 confirmatory inference：false；不得解释为当前个股概率/机械规则。

详细见 `specs/m2-28-source-prz-abcd-closeout.md`。

### 工程观察

- run #555 snapshot cache miss，历史 artifact bootstrap 因 GitHub integration 权限不可访问，导致 45 股重新从 BaoStock 拉取；本轮结束后新 cache 已成功保存；
- source-resolved events 大幅增加后，per-record frame sort / linear target scan 的成本更明显；未来如优化，必须保证结果完全等价并与 source definition change 分开提交。

### 关键决定

- 新增 D-014：Standalone AB=CD Source Raw PRZ 与 V3 BC Layering 永久分层。

### 未解决

- 5-0 V2 structural PRZ vs V3 execution refinement；
- Shark terminal-side Source PRZ / 5-0 transition final source freeze；
- RSI BAMM 独立状态机；
- standard XABCD per-pattern AB=CD family hard gate refinement；
- M3 retrospective D-based overlays 尚未迁移到 live execution clock。

### 下一步唯一主任务

**M2.29 — 5-0 Volume Two / Volume Three Source Reconciliation。**

### 新会话特别注意

- 不得把 v4 visible `full_prz_exit_by_t5` robustness 写成确认性结论或当前标的概率；
- 不得恢复旧 M3 D-based Type-I overlay；
- 5-0 在 source conflict 关闭前继续 production quarantine；
- 新会话先核对 `PROJECT_CONTEXT.md` 的 checkpoint 与当前 HEAD/CI。

---

## 2026-09-17 — 建立跨对话无损续接机制

### 基线

- 仓库：`shazhuya/HT-CN`
- 默认分支：`main`
- 功能/研究检查点：`612c0dc01ecbbadfe763bbe9a78c9acd9cee5014`
- 检查点标题：`M2.27: freeze source PRZ golden profiles`
- 该检查点 GitHub CI：success

### 本 Session 完成

- 新增 `AGENTS.md`：定义新会话 Bootstrap 与 Session Closeout 强制协议；
- 新增 `PROJECT_CONTEXT.md`：保存当前阶段、Gate、冻结约束、未解决问题、唯一主任务和验收入口；
- 新增 `DECISIONS.md`：把关键架构/方法论决定从聊天中迁移为可追溯账本；
- 新增本 `SESSION_LOG.md`；
- 新增一键续接包生成器与 Windows 入口（见同批提交）；
- 后续任何新会话必须检查 `context_checkpoint..HEAD`，禁止仅依赖旧聊天记忆。

### 当前下一步

继续关闭 Source Fidelity Gate：围绕 Book Golden Set、剩余 Source PRZ / Shark / 5-0 source conflict 与 source-aligned execution-clock 语义收口；Gate 关闭后再恢复 M3 正常扩张。

---

## Closeout 模板

复制下面模板追加到文件顶部（最新 Session 放最上面）：

```text
## YYYY-MM-DD — Session 标题

### 基线
- 起始 HEAD：
- 结束功能/研究检查点：
- 分支：
- CI：

### 完成
- 

### 关键决定
- 无 / 见 D-XXX

### 验收
- 

### 未解决
- 

### 下一步唯一主任务
- 

### 新会话特别注意
- 
```
