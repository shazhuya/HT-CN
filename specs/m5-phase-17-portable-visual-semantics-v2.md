# M5 Phase 17 — Portable Visual Semantics / Chart Fidelity v2

状态：**implementation in progress**

## 1. 目标

Phase 16 已经解决：

- v4 可把当前 Queue 的 exact bars + pattern payload 带到离线环境；
- 节点和 K 线来自真实 transport；
- forming pattern 不补造未来 D。

Phase 17 只解决：

> **同一份已验证 v4 detail 到底应该如何表达，才能不把 Source Raw PRZ、HT-CN 工程层、审计层、生命周期和 schema 身份混为一谈。**

本阶段是纯 presentation semantics，不修改任何算法定义。

## 2. 不升级 transport

Phase 17 **不建立 v5**。

原因：

v4 detail 已包含：

- pattern.points；
- metrics；
- PRZ components；
- Source Raw PRZ；
- Ideal Core；
- Component Envelope；
- source_lifecycle；
- checks / reaction targets / source-specific fields。

因此图形层可以完全从冻结 v4 payload 派生。

固定：

- handoff v4 schema 不变；
- v4 verifier 不变；
- v4 ZIP 内容不因 Phase 17 改写；
- visual semantics 只是 Inspector 内的 deterministic derived view。

## 3. Visual Semantics Contract v2

新增：

`src/htcn/app/portable_visual_semantics.py`

contract：

- version=2；
- semantics=presention_only_from_transported_pattern_payload；
- mutates_harmonic_identity=false；
- mutates_source_raw_prz=false；
- mutates_source_lifecycle=false；
- invents_future_pattern_points=false；
- projected_geometry_is_pattern_identity=false；
- predictive_score_used=false；
- historical_outcome_used_for_ranking=false；
- alpha_inference_allowed=false；
- is_trade_instruction=false。

Inspector schema 升级为 2，但 source transport 仍是 v4。

## 4. Schema topology

视觉层必须尊重四套独立 schema：

### XABCD

完整节点：

`X -> A -> B -> C -> D`

forming 只允许已有 prefix，例如：

`X -> A -> B -> C`

缺失 D 只能报告为：

`missing_future_labels=["D"]`

不得绘制 C-D。

### ABCD

`A -> B -> C -> D`

forming：

`A -> B -> C`

### Shark

`0 -> X -> A -> B -> C`

Shark 不存在普通 XABCD 的 D。

forming Shark：

`0 -> X -> A -> B`

只允许报告 C 尚未发生，不得制造 D。

### FIVE_ZERO

`X -> A -> B -> C -> D`

即便视觉可展示，production quarantine 仍保持，不得因画图而解封。

任何 transport 节点序列不是 schema 合法完整序列或合法 prefix：

- topology status = invalid_non_prefix；
- chart fail closed；
- 不自动重排节点；
- 不补点。

## 5. Geometry

只有 transport 中真实存在的相邻 points 可以成为 pattern geometry。

每条 leg：

- line_style=solid；
- observed_geometry=true；
- 保存 from/to label、bar、price；
- 图上显示 leg name，例如 XA / AB / BC / CD。

禁止：

- 预测 D；
- 预测 C；
- 把下一关键价连成 pattern leg；
- 把 PRZ component 当成 pattern leg。

## 6. Ratio panel

按 schema 独立展示已知 metrics。

### XABCD

- B / XA；
- C / AB；
- CD / BC projection；
- D / XA；
- CD / AB。

形成中结构只显示 payload 已存在的测量，例如 B/XA、C/AB。

### ABCD

- C / AB；
- CD / BC；
- CD / AB；
- reciprocal C target；
- reciprocal BC target。

### Shark

- A / 0X；
- B / XA；
- C / AB；
- C / 0B。

### 5-0

- B / XA；
- C / AB；
- D / BC；
- CD / AB。

Visual layer 不重新计算/修正原 metrics；只展示 transported values。

## 7. PRZ 三层必须视觉分离

### 7.1 Source Raw PRZ

语义：

`source_defined_reversal_zone`

最高视觉优先级。

只有：

`source_prz.available=true`

才允许显示为 Source Raw PRZ。

### 7.2 HT-CN Ideal Core

语义：

`engineering_convergence_selection_not_source_prz`

必须明确不是 Source Raw PRZ。

默认允许显示，但使用不同线型。

### 7.3 Component Envelope

语义：

`audit_envelope_not_source_prz`

只是全部组件的外包络。

默认关闭，用户显式打开才显示。

## 8. PRZ Components

每个 component 都必须展示：

- name；
- ratio_low / ratio_high；
- price_low / price_high；
- 是否属于 Source Raw PRZ；
- visual line style；
- semantic role。

Source membership 只能来自：

`source_prz.component_names`

不得按“靠得近”自行推断。

非 source component：

`audit_measurement_not_raw_prz`

5-0 特例：

`BC 61.8% V3 execution boundary`

当它不是 source member 时必须标记：

`execution_refinement_not_raw_prz`

不得涂进 Raw PRZ。

## 9. Source Clock timeline

视觉层从 `source_lifecycle` 读取，不从 retrospective D/C clock 推断：

- signal；
- Source PRZ entry；
- Source T-Bar；
- T+1；
- Type-I 38.2；
- Type-I 61.8；
- first PRZ exit；
- Type-II retest entry；
- Type-II T-Bar；
- Type-II reversal-direction exit。

时间线只画 transport 已存在事件。

## 10. Price guides

允许的虚线：

- Type-I 38.2 target；
- Type-I 61.8 target；
- next_key_price。

全部必须：

- line_style=dashed；
- is_pattern_geometry=false。

不得把任何虚线 price guide 解释成未来 harmonic leg。

## 11. Identity conflict / overlap policy

当前 portable workspace 一次只画：

**当前 Queue display key 对应的 primary identity。**

其他 `identity_conflicts`：

- 文字列出；
- 不在同一主图叠线；
- 不隐藏其存在；
- 不根据 geometry score 自动替用户选择“最好形态”。

这样避免多形态叠加导致 X/A/B/C/D、PRZ 和时间轴不可读。

后续若需要 overlay，必须单独定义 overlay contract。

## 12. Workspace v2

新增：

`src/htcn/app/portable_visual_workspace_v2.py`

默认 Phase16 一键入口继续使用相同输出文件，但 HTML 升级为 Visual Semantics v2。

图层控制：

- Source Raw PRZ：默认开；
- Ideal Core：默认开；
- Component Envelope：默认关；
- PRZ components：默认开；
- Source Clock：默认开；
- targets / next-key guides：默认开。

页面必须显示：

- schema topology；
- observed vs expected nodes；
- missing future labels；
- ratios；
- PRZ component table；
- raw/source membership；
- identity conflicts；
- schema-specific warning；
- lifecycle state/reason。

## 13. Shark / 5-0 专属边界

### Shark

必须显示：

- schema = 0XABC；
- C 是完整结构终点；
- 不存在 D；
- 50% / 61.8 / Reciprocal AB=CD 作为 Shark management/reaction 信息，不作为 XABCD D。

### 5-0

必须显示：

- production quarantine；
- Raw PRZ members；
- 61.8 V3 execution refinement 单独列出；
- 61.8 不得升级为 Raw PRZ member。

## 14. Acceptance

- [ ] Visual semantics 为纯函数，不读取行情数据库；
- [ ] Inspector schema version=2；
- [ ] v4 transport schema/verifier 0 change；
- [ ] XABCD complete topology 正确；
- [ ] XABCD forming 不画 D；
- [ ] ABCD topology 独立；
- [ ] Shark 只允许 0XABC，不生成 D；
- [ ] 5-0 61.8 refinement 不属于 Raw PRZ；
- [ ] Source Raw PRZ / Ideal Core / Envelope 三层独立；
- [ ] Source membership 只由 source component_names 决定；
- [ ] ratios 按 schema 显示；
- [ ] Source Clock events 按 bar 顺序展示；
- [ ] price guides 明确不是 pattern geometry；
- [ ] identity conflicts 不叠到主图；
- [ ] layer controls 可独立开关；
- [ ] HTML 无 fetch / review write；
- [ ] Python regression green；
- [ ] Web build green；
- [ ] existing Playwright green；
- [ ] M4 methodology drift = 0；
- [ ] Outcome Engine drift = 0。
