import crypto from 'node:crypto'
import fs from 'node:fs'
import path from 'node:path'
import { expect, test } from '@playwright/test'


const screenshotDir = '../../artifacts/screenshots'
const evidenceDir = '../../artifacts/reports/playwright'


function sha256(filePath: string): string {
  const digest = crypto.createHash('sha256')
  digest.update(fs.readFileSync(filePath))
  return digest.digest('hex')
}


async function selectInstrument(
  page: import('@playwright/test').Page,
  instrumentId: string,
) {
  await page.getByRole('button', { name: new RegExp(instrumentId.replace('.', '\\.')) }).click()
  await expect(page.getByRole('heading', { name: new RegExp(instrumentId.replace('.', '\\.')) })).toBeVisible()
}


async function capture(
  page: import('@playwright/test').Page,
  filename: string,
) {
  fs.mkdirSync(screenshotDir, { recursive: true })
  const target = path.join(screenshotDir, filename)
  await page.screenshot({ path: target, fullPage: true })
  expect(fs.statSync(target).size).toBeGreaterThan(10_000)
  return {
    file: target,
    size_bytes: fs.statSync(target).size,
    sha256: sha256(target),
  }
}


test('M5 Phase18 portable visual workspace renders frozen semantics in a real browser', async ({ page }) => {
  await page.goto('/portable-visual-fixture.html')

  await expect(page.getByRole('heading', { name: 'HT-CN v4 便携图形复盘' })).toBeVisible()
  await expect(
    page.locator('.shell > .muted').filter({ hasText: 'Visual Semantics v2' }),
  ).toBeVisible()
  await expect(page.locator('#verify')).toContainText('验证：valid')
  await expect(page.getByText('Queue候选', { exact: true }).locator('..')).toContainText('5')
  await expect(page.getByText('完整覆盖', { exact: true }).locator('..')).toContainText('是')

  const screenshots: Array<Record<string, unknown>> = []
  const checks: string[] = []

  // 1) Completed XABCD: full observed geometry, three-layer PRZ semantics,
  // Source Clock events and non-geometry guides.
  await selectInstrument(page, 'SSE.600001')
  const chart = page.locator('.chart')

  for (const label of ['X', 'A', 'B', 'C', 'D']) {
    await expect(chart.locator(`[data-node-label="${label}"]`)).toBeVisible()
  }
  for (const leg of ['XA', 'AB', 'BC', 'CD']) {
    await expect(chart.locator(`[data-leg-name="${leg}"]`)).toBeVisible()
  }

  await expect(chart.locator('[data-layer-id="source_raw_prz"]')).toBeVisible()
  await expect(chart.locator('[data-layer-id="ideal_core"]')).toBeVisible()
  await expect(chart.locator('[data-layer-id="component_envelope"]')).toHaveCount(0)

  await page.getByLabel('全组件 Envelope').check()
  await expect(chart.locator('[data-layer-id="component_envelope"]')).toBeVisible()
  await page.getByLabel('Source Raw PRZ').uncheck()
  await expect(chart.locator('[data-layer-id="source_raw_prz"]')).toHaveCount(0)
  await page.getByLabel('Source Raw PRZ').check()
  await expect(chart.locator('[data-layer-id="source_raw_prz"]')).toBeVisible()
  await page.getByLabel('全组件 Envelope').uncheck()

  await expect(chart.locator('[data-event-field="source_terminal_bar"]')).toBeVisible()
  await expect(chart.locator('[data-event-field="execution_start_bar"]')).toBeVisible()
  await expect(chart.locator('[data-event-field="type_ii_terminal_bar"]')).toBeVisible()
  await expect(chart.locator('[data-guide-field="target_382"]')).toBeVisible()
  await expect(chart.locator('[data-guide-field="target_618"]')).toBeVisible()
  await expect(chart.locator('[data-guide-field="next_key_price"]')).toBeVisible()

  await expect(page.getByText('同几何身份冲突：', { exact: false })).toBeVisible()
  await expect(page.getByText(/当前图只画 Queue 选中的 primary identity/)).toBeVisible()
  checks.push(
    'completed_xabcd_nodes_and_legs',
    'layer_toggle_source_ideal_envelope',
    'source_clock_events',
    'non_geometry_price_guides',
    'identity_conflict_disclosure',
  )
  screenshots.push(await capture(page, 'm5-phase18-xabcd-complete.png'))

  // 2) Forming XABCD: D is explicitly missing and never rendered.
  await selectInstrument(page, 'SSE.600002')
  await expect(chart.locator('[data-node-label="X"]')).toBeVisible()
  await expect(chart.locator('[data-node-label="C"]')).toBeVisible()
  await expect(chart.locator('[data-node-label="D"]')).toHaveCount(0)
  await expect(chart.locator('[data-leg-name="CD"]')).toHaveCount(0)
  await expect(page.getByText(/尚未发生：D（只列出，不绘制）/)).toBeVisible()
  checks.push('forming_xabcd_missing_d_not_rendered')
  screenshots.push(await capture(page, 'm5-phase18-xabcd-forming.png'))

  // 3) Standalone AB=CD: no X node, independent topology and ratio vocabulary.
  await selectInstrument(page, 'SSE.600003')
  await expect(chart.locator('[data-node-label="X"]')).toHaveCount(0)
  for (const label of ['A', 'B', 'C', 'D']) {
    await expect(chart.locator(`[data-node-label="${label}"]`)).toBeVisible()
  }
  for (const leg of ['AB', 'BC', 'CD']) {
    await expect(chart.locator(`[data-leg-name="${leg}"]`)).toBeVisible()
  }
  await expect(page.getByText('C reciprocal 目标', { exact: true })).toBeVisible()
  await expect(page.getByText('BC reciprocal 目标', { exact: true })).toBeVisible()
  checks.push('standalone_abcd_topology_and_ratios')
  screenshots.push(await capture(page, 'm5-phase18-abcd-complete.png'))

  // 4) Shark: schema is 0-X-A-B-C and D is forbidden.
  await selectInstrument(page, 'SSE.600004')
  for (const label of ['0', 'X', 'A', 'B', 'C']) {
    await expect(chart.locator(`[data-node-label="${label}"]`)).toBeVisible()
  }
  await expect(chart.locator('[data-node-label="D"]')).toHaveCount(0)
  await expect(chart.locator('[data-leg-name="0X"]')).toBeVisible()
  await expect(chart.locator('[data-leg-name="BC"]')).toBeVisible()
  await expect(page.getByText(/Shark 专属管理/)).toBeVisible()
  await expect(page.getByText(/Shark 终点是 C，不虚构 D/)).toBeVisible()
  checks.push('shark_0xabc_without_d')
  screenshots.push(await capture(page, 'm5-phase18-shark.png'))

  // 5) 5-0: 61.8 is visible only as execution refinement, never Raw PRZ membership.
  await selectInstrument(page, 'SSE.600005')
  await expect(page.getByText(/5-0 production quarantine/)).toBeVisible()
  const refinementRow = page.getByRole('row').filter({
    hasText: 'BC 61.8% V3 execution boundary',
  })
  await expect(refinementRow).toBeVisible()
  await expect(refinementRow.getByText('执行 refinement', { exact: true })).toBeVisible()
  await expect(refinementRow.getByText('Raw PRZ 成员', { exact: true })).toHaveCount(0)
  await expect(
    chart.locator('[data-component-role="execution_refinement_not_raw_prz"]'),
  ).toBeVisible()

  await page.getByLabel('PRZ 组件线').uncheck()
  await expect(chart.locator('[data-component-name]')).toHaveCount(0)
  await page.getByLabel('PRZ 组件线').check()
  await expect(chart.locator('[data-component-name]')).toHaveCount(3)
  checks.push(
    'five_zero_618_refinement_not_raw_prz',
    'component_layer_toggle',
  )
  screenshots.push(await capture(page, 'm5-phase18-five-zero.png'))

  // Write auditable semantic evidence next to the Playwright HTML report.
  fs.mkdirSync(evidenceDir, { recursive: true })
  const evidencePath = path.join(
    evidenceDir,
    'phase18-portable-visual-browser-evidence.json',
  )
  fs.writeFileSync(
    evidencePath,
    JSON.stringify(
      {
        schema_version: 1,
        phase: 'M5 Phase 18',
        source_fixture: 'portable-visual-fixture.html',
        visual_semantics_version: 2,
        transport_schema_version: 4,
        browser: 'chromium',
        checks,
        screenshots,
        screenshot_count: screenshots.length,
        no_market_database_required: true,
        writes_m4_evidence: false,
        mutates_harmonic_identity: false,
        mutates_source_raw_prz: false,
        mutates_source_lifecycle: false,
        future_pattern_points_rendered: false,
        is_trade_instruction: false,
      },
      null,
      2,
    ) + '\n',
    'utf-8',
  )

  expect(fs.statSync(evidencePath).size).toBeGreaterThan(500)
})
