# HT-CN Portable Chat Continuation Protocol

本协议用于普通 ChatGPT 新对话、其他 AI、无 GitHub 连接或无旧聊天全文的场景。

核心结论：**不需要每次重新阅读全部旧聊天。**旧聊天只能帮助恢复未落库的用户语义，不能担任当前项目状态。可执行事实必须由仓库、正式 CI 和治理台账恢复。

## 用户唯一流程

1. 在最新、干净的 HT-CN 工作区运行 `生成HT-CN续接包.bat`。
2. 向新聊天上传以下任一文件：
   - 首选：`artifacts/reports/htcn-chat-continuation-bundle.zip`；
   - 若新 AI 不能读取 ZIP：`logs/context/HTCN_CHAT_HANDOFF.md`。
3. 复制 `logs/context/HTCN_NEW_CHAT_PROMPT.md` 的全文作为第一条消息。
4. AI 必须先返回 Bootstrap Receipt；Receipt 合格后才能修改代码或提出下一阶段方案。

生成过程不会读取或打包 `data/`、私有 M1 数据库、运行产物、截图、环境变量、凭据或旧聊天全文。

## 新 AI 的强制恢复顺序

1. 读取 `START_HERE.md`、`MANIFEST.json` 和 `HTCN_RESUME_PACK.md`；
2. 按 manifest 校验文件数量、大小和 SHA-256；
3. 读取 `canonical/AGENTS.md`、`canonical/governance/PROJECT_STATE.json`、`canonical/governance/PRODUCT_COMPLETION_POLICY.json` 和 `canonical/PROJECT_BLUEPRINT.md`；
4. 读取 active Change、active spec、最新 Attempt、Open Issues、Decision Index、Source Coverage；
5. 只在本次任务确实需要时读取其他 required specs；
6. 若可访问 GitHub，核对 manifest HEAD 与 canonical `main`；若不能访问，明确写出“未在线核对”，不得伪称已验证；
7. 先提交 Bootstrap Receipt，发现矛盾则停止核心工作。

## Bootstrap Receipt 必答项

1. repository、branch、HEAD、tree；
2. current milestone / phase / status；
3. active Change / active spec；
4. last integrated release 与 latest formal validation；
5. 当前 Gate、blocker、next major task；
6. 下一项必须由用户执行的动作与 AI 可独立执行的动作；
7. 不可修改的 Source / methodology / Outcome freezes；
8. supported / partial / quarantined / unsupported 边界；
9. 最近成功与失败 Attempt；
10. bundle、GitHub、state、ledger 是否存在矛盾；
11. 本次任务允许修改与禁止修改的范围；
12. 当前产品开发主线与后台 evidence/calibration 轨分别是什么、ISSUE-0066 阻塞什么/不阻塞什么、当前是否真的需要用户电脑。

任何一项无法回答，都不能宣称“已经无损续接”。

## Product Completion 交接硬规则

- 恢复项目时必须把 M9 视为产品开发主线，把 M7 视为后台长期 evidence track。
- M8/ISSUE-0066 只控制统计/胜率/alpha/盈利能力/calibration 声明，不得被解释为 M9 产品发布的等待条件。
- 默认“下一项用户动作”应为无；不得因为 M7 日常积累要求用户每天开电脑、跑 BAT 或上传 ZIP。
- 只有 `PRODUCT_COMPLETION_POLICY.json` 允许的 private/local-only 原因才能请求用户电脑。
- 若统计证据不足，产品应显示“证据不足/能力未解锁”，而不是暂停产品开发。

## 旧聊天的正确用途

- 旧聊天不是每次启动的必读材料。
- 只有当用户提到某个尚未落库的具体选择、反馈或语义时，才定向检索相关旧对话。
- 从旧聊天恢复出的重要事实，必须在本工作单元结束前写入 Change / Decision / Issue / Attempt / State；否则仍视为未交接。
- AI 不得把模糊聊天记忆覆盖到仓库当前状态之上。

## 工作结束前的交接标准

任何 AI 在结束、切换聊天或接近上下文上限前，必须：

1. 提交可定位代码；
2. 记录成功与失败 Attempt；
3. 更新 CR、Decision、Issue、State 中发生变化的事实；
4. 运行 Project OS、测试和相应门禁；
5. 重新生成便携续接包；
6. 不得把下一位 AI 必须知道的事实只留在最后一条聊天回复里。
