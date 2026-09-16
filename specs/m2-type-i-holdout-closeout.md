# M2.22 Type-I 一次性 Holdout 验证收口

## 目的

本文件冻结 `m2-type-i-holdout-v1` 的一次性确认性检验结果，并明确该 Holdout 已被消费，后续不得继续用于迭代调参或替换主检验。

## 冻结对象

- 数据集：`a-share-research-v2-45`
- 快照截止：`2026-09-15`
- 预注册 commit：`286eead8b3fa1afa1e716161366b8edcf2c555b2`
- 一次性执行 commit：`5ed9ed50aae2e64a5d80e74fbdaf0ff71ab65736`
- 主检验：`full_prz_exit_by_t5` 对比 `no_full_exit_by_t5`
- 研究人群：Terminal Price Bar 后，到 T+5 仍未达到 T2 的 Holdout 案例
- Endpoint：T+6 到 T+20 首次达到 T2
- 统计规则：每组至少 20 个样本；使用 95% Newcombe 两比例差区间；仅当下界严格大于 0 才确认。

## 一次性结果

Holdout 共 355 条 M2.17 Terminal-Bar 记录，其中 313 条在 T+5 时仍待 T2：

- T+5 前完整脱离 PRZ：115 条，40 条在 T+6..T+20 达到 T2，比例 `0.34782608695652173`。
- T+5 前未完整脱离 PRZ：198 条，39 条在 T+6..T+20 达到 T2，比例 `0.19696969696969696`。
- 绝对比例差：`0.15085638998682477`。
- 95% Newcombe 区间：`[0.049612411917687296, 0.2541290679331789]`。
- 预注册结果：`confirmed`。

完整 CI Artifact 的 SHA256 为 `36d8e3dc2f5bb12814c0132940c205e2240b365c7ba532d9e3708b598bbc2d99`；其中原始 `m2-type-i-holdout-evaluation.json` SHA256 为 `836f54af3c68db796b43dc9e2c5d9e1f9324fb04923b16ca5b62e48b941f5c04`。

## 允许的解释

该结果支持一个有限但实战上重要的结论：对于已经出现 Terminal Price Bar、且 T+5 时尚未到达 T2 的历史案例，**在前 5 根 K 线内完整脱离 PRZ** 与随后 T+6..T+20 更高的 T2 progression 比例相关。它可作为 HT-CN 的“完成后 Type-I 早期确认”证据层。

它不是：Carney 几何身份规则、收益率预测、个股买卖指令、全 A 股无条件成功率，也不能证明“越早离开 PRZ 越好”。M2.20 已表明 T+3 相比 T+4..T+5 没有稳定的额外速度优势，因此冻结语义必须是 `by T+5`，不能偷换成 `by T+3`。

## Holdout 消费规则

本数据集的该 Type-I Holdout 从本次验证后永久视为 **consumed**：

- CI 不再重新计算这次 Holdout；只校验冻结结果及 SHA256。
- 不得因看到结果后修改阈值、endpoint、family、方向、scale 或子组，再把同一 Holdout 当作新的确认性证据。
- 后续若要确认更细的 Type-I 规则，必须使用新的冻结数据集/向前推进的独立快照，并先完成新的预注册。
- 当前 `confirmed` 结果只进入独立 lifecycle/evidence 层，不修改 Carney pattern identity。
