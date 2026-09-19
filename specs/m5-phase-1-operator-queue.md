# M5 Phase 1 — A股实战工作台 / Daily Operator Queue

状态：**Product-layer implementation; read-only over frozen harmonic/source lifecycle**

## 1. 目标

M5 不重新发明谐波识别，也不提前做胜率、alpha 或买卖排名。

M5 Phase 1 解决一个实际产品问题：

> M3/M4 已经能够解释“某一只股票现在在哪”，但用户仍需要手工逐只输入代码。  
> M5 要把本地初始化 universe 转成“今天先看什么”的工作流队列。

核心输出：

- 当前有哪些 primary harmonic candidates；
- 每个 candidate 处于哪个 Source lifecycle；
- 当前 action state 是：
  - execution_evaluation
  - reaction_observation
  - waiting
  - evidence_insufficient
- 下一关键价是什么；
- 先看什么；
- 到了再看什么；
- 什么条件不能升级；
- execution/context 是否存在 caution；
- 点击后进入原有单标的深度工作台。

## 2. 单向依赖边界

M5 是 product consumer，不是 research owner。

数据方向只能是：

`M2/M3 frozen harmonic + Source lifecycle -> M5 operator queue`

禁止：

`M5 queue -> harmonic identity / Source Raw PRZ / lifecycle / enrollment / outcome`

M5 Phase 1 contract：

- `source_of_truth=existing_source_lifecycle_and_decision_narrative`
- `ranking_mode=workflow_bucket_only`
- `predictive_score_used=false`
- `historical_outcome_used=false`
- `alpha_inference_allowed=false`
- `is_trade_instruction=false`
- `mutates_harmonic_identity=false`
- `mutates_source_raw_prz=false`
- `owns_lifecycle=false`

## 3. Queue 排序语义

Queue 允许工作流顺序，但禁止把它解释成收益排序。

固定 bucket 顺序：

1. `execution_evaluation`
2. `reaction_observation`
3. `waiting`
4. `evidence_insufficient`

组内只按：

- instrument_id
- deterministic display key

排序。

禁止使用：

- geometry score 作为 queue priority；
- historical win rate；
- outcome MFE/MAE；
- alpha；
- benchmark excess return；
- composite market/sector/theme score；
- 买入/卖出评分。

## 4. Candidate 范围

默认只进入：

`is_primary_identity != false`

同节点 secondary identities 继续保留在单标的深度审计中，不在 daily queue 重复制造“多个机会”的错觉。

5-0 quarantine、Alternate Bat fail-closed 等既有方法学边界完全继承，不由 M5 改写。

## 5. API

新增：

`GET /api/operator/queue`

参数：

- `limit`
- `bars`
- `include_evidence_insufficient`

输出：

- contract；
- universe/analyzed/error counts；
- candidate counts；
- action/lifecycle distributions；
- candidate items；
- per-instrument analysis errors。

单个标的数据错误只在 queue 中记录错误，不使整个 UI 崩溃。

## 6. Queue item

每个 item 至少包含：

- instrument_id
- pattern_id/schema/direction/scale
- pattern_state
- action_state
- lifecycle_state
- state_reason
- current_position
- first_watch
- next_watch
- upgrade_blocker
- next_key_price / role
- execution_context_gate
- context_cautions
- Source PRZ low/high
- bars_since_terminal
- price_mode / last_trade_date

显式边界字段：

- `is_trade_instruction=false`
- `predictive_score_used=false`
- `alpha_inference_allowed=false`

## 7. 前端

首页升级为：

**A股谐波实战工作台**

第一层：

**今日观察队列**

第二层：

**单标的深度工作台**

Queue 点选 instrument 只负责把代码带入单标的工作台，不自动产生买卖动作。

## 8. M4 并行关系

M4 继续负责：

- authoritative prospective evidence；
- candidate enrollment；
- outcome snapshots；
- no-lookahead evidence chain。

M5 可以在 M4 样本积累期间并行迭代，因为 M5 不写 M4 evidence store。

任何未来使用 M4 outcome 统计来排序 M5 queue 的工作，都必须：

1. 等独立 outcome protocol 有足够真实样本；
2. 单独预注册；
3. 不能在 Phase 1 暗中接入。

## 9. 测试

必须有：

- Python unit tests：
  - workflow bucket only；
  - secondary identity filtering；
  - per-instrument error isolation；
  - evidence_insufficient filter；
  - no predictive-score contract。
- Web build；
- Playwright：
  - Queue 可见；
  - workflow bucket 显示；
  - next key price 显示；
  - 点击 queue instrument 能填入单票输入框。

M5 branch 必须执行浏览器验收，不允许只靠 TypeScript build。

## 10. Phase 1 完成标准

Phase 1 可验收需要：

- queue builder tests green；
- API endpoint green；
- Web build green；
- M5 Playwright green；
- 不改 M4 frozen methodology / Outcome Engine；
- 不产生 predictive ranking / trade instruction；
- UI 能从全市场观察队列进入单票深挖。
