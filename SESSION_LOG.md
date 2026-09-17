# HT-CN Session Log — 会话交接记录

本文件只记录每个开发 Session 最后停在哪里。详细技术事实仍以源码、测试、`PROJECT_CONTEXT.md`、`DECISIONS.md`、`specs/` 为准。

## 2026-09-17 — M2.30 Shark Source Raw PRZ / v6 收口

### 基线

- 起始 main：`6d36dfe4c9e2b597df80596ad1bb1c08d286e9f0`（M2.29 merge）
- 结束功能/研究检查点：`e0f5d9334544944d00b232752ea0e8cdbf5c5bc8`
- 分支：`m2/shark-terminal-source-freeze`
- CI：run #603 / `35186542998`，deterministic + Playwright + 45-symbol real-A-share v6 全链 **success**

### 完成

- Shark Source Raw PRZ 冻结为 `0B 0.886–1.13` corridor 与 `AB 1.618–2.24` corridor 的几何 overlap；
- 新增 Shark source contract / Book Golden evidence / negative regression；
- source-aligned Terminal Price Bar 支持 Shark；
- Shark reaction management 使用 first encountered of `50% BC` / `Reciprocal AB=CD`；61.8% BC 保持 wider prospective 5-0 level；
- 5-0 M2.29 structural semantics 保持，production quarantine 未解除；
- research definition 升至 `m2-source-prz-v6`；
- 新增 v6 sealed research guard；
- 修复旧 `specs/m2-shark-five-zero.md` 的 5-0 50–61.8 universal-band 漂移；
- CI 修复 Actions artifact 权限、snapshot bootstrap、即时 cache、长研究 concurrency、90 分钟安全 timeout、实时无缓冲进度输出。

### 真实研究验收

- cache：45 hit / 0 miss；
- 45 股 calibration：约 85 秒；
- forming signals：8244；
- mature Source-Raw-PRZ Terminal events：1499；
- Train / Validation / sealed Holdout：871 / 265 / 328；purged 35；
- Shark Terminal events：76 / 26 / 40；
- Type-I visible robustness：`full_prz_exit_by_t3`、`full_prz_exit_by_t5`；
- completed-reaction robustness：none；
- v6 confirmatory inference：false；
- historical v1/v3/v4/v5 / Holdout / external replication 未重算、未 relabel。

### 关键决定

- D-015：Shark Source Raw PRZ = published source corridors geometric overlap；
- D-016：真实 A 股长研究必须 snapshot-first、resumable、observable，不能被普通小提交反复浪费。

### 未解决

- RSI BAMM 独立多步骤状态机；
- 5-0 V3 label conflict，production quarantine 继续；
- standard XABCD per-pattern AB=CD hard-gate refinement；
- M3 live execution-clock overlay migration。

### 下一步唯一主任务

**M2.31 — RSI BAMM Dedicated Source State Machine。**

### 新会话特别注意

- 不得把 Wilder RSI 极值反转称为 RSI BAMM；
- 不得把 v6 visible robustness 写成确认性交易结论；
- 5-0 默认生产隔离继续；
- M3 旧 retrospective D-based overlay 不得恢复为 live execution semantics。

---

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
- 历史 v1/v3/Holdout/external replication 均保持不可变。

### 真实研究验收

- forming signals：8085；
- mature Source-Raw-PRZ Terminal events：1233；
- Train / Validation / sealed Holdout：730 / 222 / 258；purged 23；
- `source_prz_unresolved`：6547（v3）-> 1724（v4）；
- mature T-Bar：166（v3）-> 1233（v4）；
- standalone AB=CD：Train 627 / Validation 198 / sealed Holdout 226。

### 下一步

后续已由 M2.29 / M2.30 继续推进。

---

## 2026-09-17 — 建立跨对话无损续接机制

### 基线

- 仓库：`shazhuya/HT-CN`
- 默认分支：`main`
- 功能/研究检查点：`612c0dc01ecbbadfe763bbe9a78c9acd9cee5014`

### 本 Session 完成

- 新增 `AGENTS.md`、`PROJECT_CONTEXT.md`、`DECISIONS.md`、本 `SESSION_LOG.md`；
- 新增 context pack 与 Windows 一键检查/生成入口；
- 后续任何新会话必须检查 `context_checkpoint..HEAD`，禁止仅依赖旧聊天记忆。

---

## Closeout 模板

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
