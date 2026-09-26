# HT-CN 架构与识别主线审计

日期：2026-09-27（Asia/Shanghai）  
归属：CR-0090；只读源码审计及方案建议，未修改生产规则。  
基准：续接 Artifact 10910643162，分支 m9/recognition-trustworthiness-v1，HEAD 1c44d2062d699c2666d7554f7572fefcef8e4e78。  
结论：方向已纠正，但识别总门仍未通过。保留分层 Swing Graph 与事件时钟；Gate 4C 必须优先完成语义、真实标签和独立验收，再选择容量、接入应用。不得将候选数、CI、PRZ 接触数替代正确率。

## 1. 恢复及证据边界

- 续接包 83/83 文件大小和 SHA-256 均通过。
- 在线 main 为 04aa35737f7d58c2ab12bca62ba536c3970ce9ef；续接工作尚未合入 main，这是已记录的分支差异，不是包损坏。
- `python scripts/project_state.py` READY；历史 PROJECT_CONTEXT 陈旧文字警告仍在。
- 续接 HEAD 的托管 CI 36256682915 success；台账阶段检查点为 36252453523 / 110089e。
- last_integrated_release 台账为 c8322ebb；GitHub releases 列表返回空。台账集成状态不等于独立核实的 GitHub Release。
- 下载并读取实际 Gate 4B Artifact 10909996357，而非只引用续接文字。未重新运行整个 45 标的市场扫描。
- 本地 pytest 不存在；改为直接执行现有 test_source_completion.py 中 7 个无参数测试函数，7/7 通过。这不是全套 pytest 或受支持 Python 3.13 环境认证。
- 未调用用户电脑，未改 Source Raw PRZ、Carney 身份、M4 或 Outcome。

## 2. 总体架构评估

现有分层值得保留：数据与复权、谐波 Source/生命周期、研究证据、应用编排、图表展示。问题不只是代码多，而是产品成熟度先于核心准确性证据，以及并行识别路径没有收敛到统一权威输出。

抽样目录规模（递归文件/文本行，仅表明维护规模）：harmonic 33/10,218；app 50/20,583；research 41/14,403；scripts 116/21,568；tests 204/29,469；web/src 45/9,158。不能据此推断多少代码无用，也不建议全仓推倒重写。

当前路径：

| 路径 | 实际职责 | 审计判断 |
|---|---|---|
| HarmonicService -> engine.scan_frame | 既有权威扫描 | 需要兼容保留，不能用旧验收替代 V2 |
| RecognitionDiscoveryService -> Pine R3.4 / discover_frame | 可视发现及补充候选 | 比较器，不是独立真值 |
| source_completion.scan_source_completion_events | V2 XABC/PRZ/完成事件 | 当前 src/app 无调用，主要由审计脚本调用 |
| frozen M4 execution / Source lifecycle | 既有证据及执行语义 | 需版本兼容，不能默默改历史 |

最终应由一个版本化 RecognitionResult/Event 接口输出节点、出生时刻、规则证据、PRZ、状态和失效原因；应用、图表和未来统计只消费接口。旧路径作为显式 legacy/comparison adapter，不再永久增加平行“真相”。不要求立即删除被冻结模块。

## 3. 已有工作确实解决了什么

- Gate 0 将受控漏检归因于连续五拐点候选窗口：100 个小波动干扰案例旧窗口全部漏掉，图搜索恢复。应保留。
- Gate 3 分层图加端点支配条件，在注入真实市场纹理的 72+18 个已知真值案例恢复全部节点。证明受控恢复能力，不证明真实市场精度。
- 事件记录避免未来同类拐点替换抹去过去形态；C 极值失效、180-bar 到期、同柱冲突保守处理、完全跳空越过 PRZ 不当场记完成均有测试。
- D-091 已正确写入 Blueprint、policy、续接协议。外围冻结是正确约束。
- 快速识别工作流降低重复跑完整产品 CI 的成本；不应恢复反复全仓验证作为日常推进方式。

## 4. 优先级最高的发现

### A. 新完成语义需要独立的真值，不能沿用旧 XABCD 分数

旧 benchmark 目标为精确 XABCD；V2 为 first-knowable XABC -> PRZ -> Terminal。研究对象已变。
recognition_oracle.py 是独立编码的标准 XABCD 规则快照；它不能直接证明新的 PRZ/Terminal 事件语义。

应分别验收：结构是否合法、PRZ 是否形成有效汇聚、当时能否知道、完成事件是否合法、之后是否确认反转。PRZ 接触不是反转确认；事件完成也不自动证明所有终点比例成立。

### B. PRZ 汇聚异常必须先于容量选优

实际 Gate 4B：45 标的、111,272 bars，4,424 projections、991 completed、3,222 invalidated、165 expired、46 active。
所有完成事件 PRZ 宽度/XA 中位数 9.24%，P90 69.57%。Crab 的全部 1,871 个投影中，宽度/XA 中位数 67.37%，最小值 30.20%。分母是 XA 波幅，不是股价。

source_prz.py 从允许比例中选择测量，再以 min/max 建区间；project_forming_xabcd 主要校验 B、C 及 C 比例族。SourcePRZProfile 自身说明不负责决定完整谐波身份。
“有 source_prz”因此不能未经验证就当作“有效汇聚充分”。宽区间可以是待审对象，不能单凭本审计判错或私自缩区间。

必须抽查按形态/宽度分层的具体节点和全部测量，核对书例和独立计算。若是候选质量问题，增加独立 qualification；若证实冻结实现有误，走新的 Source Decision 修订、版本化并保留旧 M4，不可因冻结而永久固化错误，也不可为了数量放宽规则。

### C. Gate 4B 不是 Precision Gate

脚本检查数据加载、生命周期记账、exact duplicate。没有真实 TP/FP 标签或语义 precision 门槛，报告也明确承认这一点。
991 个完成事件聚合到 828 个市场 Terminal；存在 135 个市场终点碰撞组、66 个同 ABC 不同 X 组。零完全重复不等于没有重复解释；碰撞也不能全部判误报，可能包含合理嵌套。
828 是统计分组数量，不能宣称最终生产去重策略已经完成。

### D. “盲测”已成为参数选择集

m9_recognition_synthetic_real_gate.py::_skip_ablation 将 development 和 holdout 同时用于 28 个容量组合的 reliable 筛选；后续容量决策也引用 holdout 结果。
当前 18 例可以保留为回归/验证集，但不能继续当作从未使用的最终盲验。需要新股票或新时间段的封存验收集，先冻结方案再揭盲。18/18 本身也不足以推断全市场可靠。

### E. 搜索容量不是精度指标

7/8 的已知真值恢复为 65/72 + 18/18；5/10 为 68/72 + 18/18；7/12 为 72/72 + 18/18（台账事实，未本地重跑 Gate 3）。
两参数定义允许跨越的拐点范围，并非形态比例。5/10 与 7/8 并非严格包含关系；脚本用 leg_step * skips 排“最小”，不等于真实候选空间、计算量或误报风险。
比较应看实际扩展路径数、耗时、正确率、漏检位置，并保留 Pareto 取舍。不能先指定 5/10 胜出，也不能只以候选更少选优。

### F. 事件时间及穿越边界仍有可复现缺口

使用现有 Gartley 测试路径补充只读探针：

1. 截取前 75 bars：同结构 known_at=73，scales=(3,)；全 111 bars：known_at 仍 73，scales=(3,5,8)。这是后续证据合并，并未证明节点/Terminal 回看重写；但若把最终 scales 用作出生时评分，就会引入未来证据。需冻结 birth evidence，后续支持以独立事件记录。
2. PRZ=[119.57,121.40]；bar80 完全跳空到 high=95/low=85，bar81 返回 high=125/low=115；系统仍将原投影在 bar81 记 completed。当前“禁止复活”只覆盖 C 极值/到期。PRZ 外穿越、跳空返回是否应退休及如何处理，尚需明确规则与独立标注，不应擅自写死本审计假设。

### G. 当前覆盖不能代表全产品

新真值主线集中于 Gartley/Bat/Butterfly/Crab/Deep Crab。ABCD、Shark 需要明确单列验收，不能继承标准 XABCD 分数；5-0、Alternate Bat 的隔离继续有效。45 标的日频历史也不能替代 15m/60m 的完整 V2 链路验收。

## 5. 建议调整的执行顺序

保持 CR-0090，不另起 UI/平台重构大项目。正式 Gate 4C 仍 open；以下为待执行审计建议，不声称已完成。

1. 冻结版本化事件合同：projection、PRZ contact、Terminal、reaction confirmation、invalidation 分开；出生和后续证据分开；列出跳空、穿区、同柱顺序及到期边界。
2. 核查真实高信息案例：优先 Crab 宽区间、同 ABC 多 X、V2/Pine 分歧、跳空返回；每例给原始 bars、节点、比例、PRZ 分量、首次可知时刻和判定理由。疑难例保留 uncertain，不强行算 TP。
3. 建真实标签集：困难案例用于找错；另以可复现随机/分层抽样衡量 precision，不能用刻意挑选的争议集估计全体精度。固定时间窗口完整枚举目标结构以估计 recall，避免只审算法输出而漏掉 FN。
4. 开发/验证/全新封存验收三分离；预先规定逐形态、方向、周期的最低覆盖和阈值。指标报告分母、置信区间、错误类别；不临时移动门槛。
5. 在同一标签数据上比较 7/8、5/10、必要邻域容量；记录实际成本与精度，确定事件去重和嵌套规则。独立 Oracle 增补 XABC/PRZ/Terminal 语义，不仅复刻现有规则表。
6. 合格后最小接入生产：同一数据/参数下审计 CLI、应用 API、图表 payload 的 event_id/节点/时刻/PRZ/状态一致；验证重启、追加和多周期。Gate green 后再讨论外围优化。

目标不是保证每支股票每刻都有形态。合法空结果必须附可诊断的阶段原因；非法形态不得为了出图获准。

## 6. 停止与保留

保留数据基础设施、必要图表、冻结研究证据、分层图和事件架构；暂停 UI 美化、AI 解读、胜率、安装器、新指标、全仓清理。没有必要全仓重写。

本次审计只更新评估与交接记录，不更改活动 Gate 的通过状态、不推广 V2 到生产。下一动作应为语义/PRZ 高信息样本审计及全新验收集定义，然后容量选择；不是重复更多候选计数报告。

## 7. 可定位证据

- `src/htcn/harmonic/source_completion.py`：projection 合并、PRZ 接触及有效期。
- `src/htcn/harmonic/scanner.py::project_forming_xabcd`：候选条件。
- `src/htcn/harmonic/source_prz.py`：测量选择与区间边界。
- `scripts/m9_recognition_gate4b_source_completion.py`：计数与实际 gate。
- `scripts/m9_recognition_synthetic_real_gate.py::_skip_ablation`：holdout 筛选和容量排序。
- `src/htcn/app/recognition_discovery_service.py`、`harmonic_service.py`：应用调用链。
- Hosted Artifact 10909996357；续接 Artifact 10910643162；CI run 36256682915。

对 Carney 理论正确性的最终判断仍需逐书例核对。本审计核查了项目实现与现有证据，不宣称重新读完三本原书。
