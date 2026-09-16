# M2 — A股谐波校准样本与反泄漏契约

## 目标

M2 的几何识别通过自动验收后，下一阶段不是继续放宽识别条件，而是把真实 A 股历史中的**有效形态、后续反应、失败样本、Pivot 稳健性**拆开保存，形成可重复审计的数据集。

这份数据集服务于后续参数研究、Golden Case / Negative Case 人工复核和形成中预测校准；它不是胜率表，也不是自动交易模型。

## 1. 身份与结果必须物理分层

每个样本必须至少分为三个命名空间：

1. `identity`：形态 schema、方向、节点、Carney 比例、几何评分；
2. `quality`：PRZ 宽度、跨尺度 Pivot 支持等 HT-CN 质量诊断；
3. `outcome`：D/C 完成后未来价格是否到达反应目标。

禁止用后续上涨/下跌结果修改以下任何内容：

- 形态身份；
- 节点位置；
- PRZ；
- 几何评分；
- Pivot 选择；
- 同一结构跨尺度去重时的代表样本。

换句话说：**“后来涨了”不能让一个错误几何变成正确形态；“后来没涨”也不能让一个合格几何失去身份。**

## 2. 只接收 deterministic core 已完成主身份

首版校准集只纳入：

- `state = completed`；
- `is_primary_identity != false`；
- 来自 QFQ 连续价格视图；
- 已通过各自 schema 的 source-valid identity gate。

支持的 schema：

- `XABCD`；
- `ABCD`；
- `0XABC`（Shark）；
- `FIVE_ZERO`。

形成中预测必须以后用独立 walk-forward 数据集评估，不能把今天完整历史里看到的旧 XABC/ABC frontier 当成当时实时可见的预测样本。

## 3. Outcome 目标按 schema 分开

### 标准 XABCD / 独立 AB=CD / 5-0

沿用 M2 Reaction vs. Reversal 审计：

- T1 = 从完成点朝 A 的 38.2% 反应；
- T2 = 61.8% 反应；
- Type-II 二次测试与 RSI 证据继续作为后验描述字段。

### Shark

Shark 是反应型结构，不能强塞进标准 Type-I 38.2/61.8 统计。首版校准使用其专属：

- T1 = 50%；
- T2 = 61.8%；
- Reciprocal AB=CD 另列字段。

这与 Volume Three 对 Shark 的主动管理和进入 5-0 PRZ 的目标逻辑一致。

## 4. 固定观察窗口

首版默认观察窗口：**20 根 K 线**。

这是 HT-CN 的研究政策，不是 Carney 的身份规则。输出中必须显式标记 `observation_horizon_is_htcn_policy = true`。

分类：

- `t2_within_horizon`：窗口内到达 T2；
- `t1_only_within_horizon`：窗口内到达 T1，但未到 T2；
- `no_t1_within_horizon`：已有完整观察窗口但未到 T1；
- `immature`：完成后可观察 K 线不足 20 根。

`immature` 绝不能被当成失败/负样本。

## 5. 跨尺度重复结构去重

同一证券、同一 pattern/schema/direction、同一组实际节点，如果被 S3/S5/S8/... 多个 Pivot 尺度重复识别，只算一个物理样本。

代表样本选择只允许使用：

1. 节点最小跨尺度支持数；
2. 平均跨尺度支持；
3. 完成节点支持；
4. 几何评分；
5. source scale。

**禁止把 T1/T2 是否成功加入去重排序。**

同时保留 `observed_scales`，以后研究“跨尺度稳定性是否与反应质量相关”，但它仍然不能改变形态身份。

## 6. PRZ 归一化仅用于研究

为了跨股票、跨价格尺度比较 PRZ 宽度，首版按 schema 使用以下参考跨度：

- XABCD：XA；
- ABCD：AB；
- Shark：0B；
- 5-0：BC。

`prz_width_ratio = PRZ width / reference span` 只是质量特征，不能被提升为新的 Carney 硬规则，除非后续经过独立样本验证并且仍以 HT-CN 研究规则身份存在。

## 7. Golden / Negative Case 的含义

自动脚本只生成**人工复核队列**：

- `strong_reaction_candidates`：T2 在观察窗口内到达；
- `negative_control_candidates`：成熟样本但 T1 未到；
- `immature_holdout`：尚不能判断的近期样本。

这些名称描述后续路径，不代表形态“正确/错误”。正式 Golden Case 必须经过独立复核：节点、比例、PRZ、复权连续性、Pivot 合法性均先通过，然后才能附加 outcome 标签。

## 8. 输出

脚本：`scripts/m2_case_calibration_dataset.py`

默认输出：

- `artifacts/calibration/m2-case-calibration.json`
- `artifacts/calibration/m2-case-calibration.csv`

JSON 保留完整审计结构；CSV 用于统计分析。

## 9. 下一阶段

完成这份 completed-case 校准集后，下一步才进入真正的 **walk-forward forming calibration**：在每个历史截止日只使用当时已经确认的数据/Pivot，记录当时真实存在的 forming PRZ，再观察未来是否触及、完成、失效。该步骤必须避免任何未来数据泄漏。
