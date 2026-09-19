# M5 Phase 18 — Portable Visual Browser Acceptance / Screenshot Evidence v1

状态：**Frozen / hosted CI green**

## 1. 目标

Phase17 已冻结 Portable Visual Semantics v2，但其新离线 HTML 主要由 Python contract/HTML regression 覆盖。

Phase18 不增加新的谐波算法，也不增加新的产品状态。

Phase18 只回答一个问题：

> **Phase17 的正式 HTML builder 在真实 Chromium 中，是否真的按 Visual Semantics v2 正确渲染和交互？**

因此本阶段建立：

- deterministic browser fixture；
- dedicated Playwright acceptance；
- screenshot evidence；
- machine-verifiable evidence manifest；
- CI artifact upload。

## 2. 测试对象

Phase18 不手写第二份 HTML。

CI 必须先调用：

`scripts/m5_build_portable_visual_browser_fixture.py`

该脚本：

1. 使用正式 `build_pattern_visual_semantics()`；
2. 使用正式 `build_portable_visual_workspace_html_v2()`；
3. 生成：
   - `apps/web/public/portable-visual-fixture.html`
   - `artifacts/reports/playwright/phase18-portable-visual-fixture.json`

Playwright 通过 Vite 打开该正式 builder 生成的 fixture。

## 3. Fixture 场景

固定 5 个场景：

1. completed XABCD；
2. forming XABCD；
3. standalone AB=CD；
4. completed Shark 0XABC；
5. completed FIVE_ZERO。

Fixture 只为 UI/browser regression 提供确定性输入：

- authoritative_evidence=false；
- writes_m4_evidence=false；
- requires_market_database=false；
- is_trade_instruction=false。

Fixture 不是 M4 evidence，不代表真实 A 股样本有效性。

## 4. Browser acceptance

专用 Playwright：

`apps/web/tests/portable-visual-workspace.spec.ts`

至少验收：

### completed XABCD

- X/A/B/C/D 全部可见；
- XA/AB/BC/CD 全部可见；
- Source Raw PRZ 默认显示；
- Ideal Core 默认显示；
- Envelope 默认关闭；
- Envelope 可以打开；
- Source Raw PRZ 可以单独关闭/再打开；
- Source T-Bar / T+1 / Type-II T-Bar 事件存在；
- T1/T2/next-key guide 存在；
- identity conflict 文字可见但没有叠第二套主 geometry。

### forming XABCD

- 只显示 X/A/B/C；
- D 不存在；
- CD leg 不存在；
- UI 显示 D 尚未发生且“不绘制”。

### standalone AB=CD

- 不显示 X；
- 只显示 A/B/C/D；
- AB/BC/CD legs；
- reciprocal ratio vocabulary 可见。

### Shark

- 显示 0/X/A/B/C；
- 不显示 D；
- 0X 和 BC legs 存在；
- Shark 专属管理说明可见；
- 明确“终点是 C，不虚构 D”。

### FIVE_ZERO

- production quarantine 提示可见；
- BC 61.8 V3 execution boundary 可见；
- 该行显示“执行 refinement”；
- 不显示为 Raw PRZ 成员；
- SVG component role 为 `execution_refinement_not_raw_prz`；
- PRZ component 图层开关真实生效。

## 5. Semantic SVG hooks

为 browser acceptance，Phase18 允许给 Visual Semantics v2 SVG 加**presentation-only data attributes**：

- `data-layer-id`
- `data-leg-name`
- `data-node-label`
- `data-component-name`
- `data-component-role`
- `data-event-field`
- `data-guide-field`

这些属性：

- 不修改布局；
- 不修改 transport；
- 不修改 harmonic identity；
- 不修改 Source Raw PRZ；
- 不修改 source lifecycle；
- 只用于浏览器可测试性与可审计性。

## 6. Screenshot evidence

Playwright 必须生成 5 张 full-page screenshot：

- `m5-phase18-xabcd-complete.png`
- `m5-phase18-xabcd-forming.png`
- `m5-phase18-abcd-complete.png`
- `m5-phase18-shark.png`
- `m5-phase18-five-zero.png`

每张截图：

- 必须实际存在；
- size > 10 KB；
- 记录 SHA-256；
- 记录 size_bytes。

## 7. Evidence manifest

Playwright 生成：

`artifacts/reports/playwright/phase18-portable-visual-browser-evidence.json`

必须记录：

- phase；
- fixture；
- visual semantics version；
- transport schema version；
- browser；
- passed semantic checks；
- screenshots；
- screenshot size/hash；
- boundary flags。

固定 boundary flags：

- no_market_database_required=true；
- writes_m4_evidence=false；
- mutates_harmonic_identity=false；
- mutates_source_raw_prz=false；
- mutates_source_lifecycle=false；
- future_pattern_points_rendered=false；
- is_trade_instruction=false。

## 8. Independent evidence verification

新增：

`scripts/m5_verify_portable_visual_browser_evidence.py`

Playwright 完成后再独立验证：

- manifest schema；
- phase/version；
- required checks 全集；
- screenshot 精确集合；
- screenshot 文件实际存在；
- recorded size 与文件一致；
- recorded SHA-256 与文件一致；
- boundary flags 没有被改变。

因此不能只凭“Playwright exit 0”宣布 Phase18 成功。

## 9. CI

M5 CI 增加：

1. existing deterministic browser acceptance；
2. build Phase18 fixture；
3. run Phase18 dedicated Playwright；
4. verify Phase18 evidence manifest；
5. upload screenshots + Playwright report/evidence。

Phase18 dedicated browser test 不替代既有 24 个 Playwright；它是额外 gate。

## 10. 不做的事

Phase18 不：

- 改 handoff v4 transport schema；
- 改 v4 verifier；
- 改 Source Truth；
- 改 PRZ 算法；
- 改 lifecycle；
- 改 Queue；
- 写 M4；
- 证明胜率/alpha；
- 进行真实交易执行。

## 11. Acceptance

- [x] fixture 由正式 Phase17 builder 生成；
- [x] fixture 不读取 market DB；
- [x] completed XABCD browser semantics 通过；
- [x] forming XABCD browser semantics 通过；
- [x] AB=CD browser semantics 通过；
- [x] Shark 无 D browser semantics 通过；
- [x] 5-0 61.8 refinement browser semantics 通过；
- [x] layer toggles 在真实浏览器中生效；
- [x] Source Clock/price guides 在真实浏览器中存在；
- [x] 5 张 screenshot 生成；
- [x] screenshot SHA/size 写入 evidence；
- [x] evidence manifest 独立验证通过；
- [x] existing Python regressions green；
- [x] Web build green；
- [x] existing 24 Playwright green；
- [x] dedicated Phase18 Playwright green；
- [x] browser evidence artifact upload green；
- [x] handoff v4 transport/verifier drift=0；
- [x] M4 methodology drift=0；
- [x] Outcome Engine drift=0。


## 12. Hosted validation closeout — 2026-09-19

Validated implementation checkpoint:

`c3a67a11ba2aa61c3e047d585293a49acd7d11ff`

Hosted CI:

- Actions **#1858 / 35425914613**: success;
- Python: **792 passed**, 1163 warnings;
- Web build: success;
- existing deterministic Playwright: **24 passed**;
- dedicated Phase18 Playwright: **1 passed**;
- browser fixture: **5 cases**;
- required semantic checks: **10 / 10**;
- screenshot evidence: **5 / 5**;
- independent evidence verifier: `status=valid`;
- visual semantics version: 2;
- transport schema version: 4;
- browser evidence artifact upload: success;
- artifact id: **10579180470**.

Development failures retained as useful evidence:

1. CI #1854 failed because one broad text locator matched both subtitle and footer.
   - fixed by scoping the locator;
   - no product/visual semantics change.

2. CI #1856 failed because Playwright `toBeVisible()` treats zero-width/zero-height SVG `<line>` bounding boxes as hidden even when Chromium renders them.
   - vertical/horizontal semantic lines are now asserted by exact DOM/data-hook presence;
   - full-page screenshots remain the independent rendered-visual evidence;
   - semantic coverage was not removed or weakened.

Freeze audit against Phase17:

- handoff v4 transport changed: 0;
- handoff v4 verifier changed: 0;
- portable visual semantics algorithm changed: 0;
- only presentation-only SVG hooks were added to the workspace;
- M4 methodology drift: 0;
- Outcome Engine drift: 0.

Limitation:

Phase18 proves deterministic fixture rendering and interaction in Chromium. It does **not** claim that a real market v4 bundle has been visually audited end-to-end. That is a separate next-stage product integration/real-artifact gate.
