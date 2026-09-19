# D-069 — TradingView-class chart foundation is an M6.6 gate before M7

status: `active`

## Decision

HT-CN 将 TradingView 类交互主图基础正式安排为 **M6.6 — Interactive Harmonic Chart Foundation**，执行顺序固定为：

`M6.4 Repository Governance → M6.5 Source Coverage Freeze → M6.6 Interactive Harmonic Chart Foundation → M7 Prospective Evidence Accumulation`

不得把这项能力拖到 M9 再整体迁移，也不得在 M6.4/M6.5 尚未完成时提前打乱当前治理与 Source 收口顺序。

## Rationale

当前生产主图仍主要依赖固定 SVG 坐标渲染。随着 PRZ、生命周期、Source Clock、Type-I/II、更多形态和 prospective evidence 继续累积，如果到 M9 才切换到 TradingView 类统一时间/价格坐标体系，迁移面会显著扩大。

因此先在 M6.6 固定 chart interaction / coordinate / overlay architecture，再让 M7 长期证据积累建立在稳定主图与 identity 映射之上。

## M6.6 implementation order

1. 交互 K 线底座：pan / zoom / time scale / price scale / crosshair / viewport。
2. 谐波 overlay 锚定：XABCD / ABCD / 0XABC 节点、腿线、标签、比例绑定 canonical time + price。
3. PRZ 与生命周期：Source Raw PRZ、Ideal Core、Component Envelope、PEZ、T1/T2、Terminal、T+1、Type-I/II 使用同一坐标体系。
4. 数据驱动更新与验收：新数据或参数变化触发增量/重新分析；viewport 操作只做坐标变换；自动化验证交互后无漂移、forming 不提前画未来节点。

## Non-goals

- 不复制 TradingView 的指标商城、脚本编辑器、社交、多窗口或大量人工画图工具。
- 不让 chart library 拥有或改变 harmonic Source truth。
- 不把鼠标 pan/zoom 当成谐波重算触发器。
- 不改变 M2/M3/M4 已冻结的方法论、Source identity 或 evidence clock。

## Completion constraint

M9 Stable Research/Product Release 不得在主图仍仅以静态 SVG snapshot 为核心生产交互时宣称完成。
