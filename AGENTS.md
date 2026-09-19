# HT-CN Agent Protocol v2 — Repository-State-Driven Continuity

本文件是任何 ChatGPT / Codex / Agent 继续 HT-CN 前的强制入口。核心规则：**聊天不是项目状态；仓库才是。**

## 1. 权威顺序

1. canonical Git history、当前源码与测试；
2. formal release / GitHub CI evidence；
3. `governance/PROJECT_STATE.json`；
4. `PROJECT_BLUEPRINT.md`；
5. active Change / Decision / Issue / Source Coverage ledgers；
6. `PROJECT_STATE.required_specs` 指向的当前规范；
7. historical `PROJECT_CONTEXT.md` / `DECISIONS.md` / `SESSION_LOG.md` / PR / commit；
8. 聊天记忆、旧对话、截图。

低层信息不得覆盖高层事实。D-065 起，`PROJECT_CONTEXT.md` 是历史深层材料，不再拥有 current-state authority。

## 2. Blank-session Bootstrap（强制）

收到“继续 HTCN”后，在任何实现前：

1. refresh canonical Git `main` / 当前工作分支 / latest formal release；
2. 运行 `python scripts/project_state.py`；
3. 读取 `governance/PROJECT_STATE.json` 与 `PROJECT_BLUEPRINT.md`；
4. 读取 active Change；
5. 读取 Decision Index、Open Issues、Source Coverage；
6. 只读取 `required_specs` 中与当前 Gate 相关的规范；
7. 查看 latest CI / PR / release；
8. 能准确说明：current phase、active change、Gate、blocker、freeze、next task、最近成功/失败 attempt；
9. 若 state/Git/ledger 任一不一致，先修 Project OS，禁止继续 Source/Product 核心开发。

本地可运行：

```text
检查HT-CN续接状态.bat
生成HT-CN续接包.bat
```

Resume Pack 是动态索引，不再整包复制所有历史长文档。

### 普通 ChatGPT / 其他 AI 的便携续接

当新对话不能直接读取仓库或没有 GitHub 连接时：

1. 用户在最新、干净的工作区运行 `生成HT-CN续接包.bat`；
2. 上传 `artifacts/reports/htcn-chat-continuation-bundle.zip`；若目标 AI 不能读取
   ZIP，则上传 `logs/context/HTCN_CHAT_HANDOFF.md`；
3. 把 `logs/context/HTCN_NEW_CHAT_PROMPT.md` 作为新聊天第一条任务消息；
4. Agent 必须按 `CHAT_CONTINUATION.md` 先返回完整 Bootstrap Receipt，之后才能改代码；
5. 没有在线 GitHub 能力时必须明确标注“未在线核对”，不得假装已核对；
6. 不要求通读全部旧聊天。只有本次任务依赖某个未落库的具体用户选择时，才定向
   检索对应旧对话，并在 closeout 前把恢复事实写回治理台账。

ZIP、standalone Markdown 和 prompt 都是可再生视图，不能覆盖 canonical Git / CI /
Project State。详细格式、校验和隐私边界见 `CHAT_CONTINUATION.md`。

## 3. No Important Fact Only in Chat

以下任何事实出现后，必须在本工作单元结束前进入 Change / Decision / Issue / Attempt / State 至少一个 ledger：

- 用户修改或否定需求；
- 新 bug / Source conflict / data issue；
- 测试或 CI 成功/失败；
- 失败方案与失败原因；
- 新约束、defer、quarantine；
- Gate / Phase / next action 变化；
- merge / release / real-M1 验收结果。

没有落库的信息视为**未完成交接**。

## 4. Change-driven Execution

任何非琐碎修改必须有 CR ID。CR 至少记录 baseline、目标、非目标、验收标准、状态。

标准状态：
`planned -> implementing -> validation_failed|validation_green -> ready_to_merge -> merged -> postmerge_pending -> closed`，以及 `blocked`。

每个有意义的实现/CI/运行尝试写入 append-only Attempt Ledger；失败不得只在聊天里解释后消失。

## 5. Source / Research 永久禁区

- 禁止 score rescue identity；
- 禁止改写 Source Raw PRZ 迎合 A 股；
- 禁止用 retrospective D 冒充 observable Source Terminal；
- Shark 不得发明 D；
- 5-0 production quarantine 保持，除非新 Source Decision 明确解除；
- Alternate Bat fail-closed 保持；
- ordinary RSI 不得冒充 RSI BAMM；
- M4 frozen methodology / Outcome Engine 不得因产品开发漂移；
- 前瞻证据不足时禁止胜率/alpha/盈利能力结论；
- 不执行证券交易。

## 6. 工作单元 Closeout（强制）

结束、切换对话、接近上下文上限、Gate 改变或 milestone 完成前：

1. 实现与测试有可定位 commit；
2. Attempt Ledger 记录结果；
3. CR 状态更新；
4. 新长期规则写 Decision + Index；
5. 新 blocker 写 Open Issues；
6. Gate/next task 变化更新 PROJECT_STATE；
7. 运行 `python scripts/project_state.py --resume`；
8. 重新运行 `生成HT-CN续接包.bat`，使下一个普通聊天获得最新 HEAD；
9. CI Project OS gate 通过；
10. merge 后必须做 post-merge state closeout，不能让 PROJECT_STATE 永久停在 feature-branch 状态。

## 7. 无损恢复验收

一个完全空白的新对话，不读取旧聊天全文，仅凭项目必须能回答：

- canonical release/HEAD 是什么？
- current Milestone/Phase 是什么？
- active CR 及其状态是什么？
- 当前 Gate / blocker / next task 是什么？
- 哪些 Source/Methodology freeze 不可变？
- 最近一次成功/失败 attempt 是什么？
- latest CI 与 state 是否一致？
- 哪些能力是 supported/quarantined/unsupported？

任何一项回答不了，都不得宣称“无缝续接”。
