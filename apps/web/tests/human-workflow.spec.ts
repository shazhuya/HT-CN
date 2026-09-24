import { expect, test } from '@playwright/test'

const bars = [
  { index: 0, trade_date: '2026-09-16', open: 100, high: 102, low: 99, close: 101, volume: 1000 },
  { index: 1, trade_date: '2026-09-17', open: 118, high: 121, low: 117, close: 120, volume: 1100 },
  { index: 2, trade_date: '2026-09-18', open: 108, high: 110, low: 107, close: 108.5, volume: 950 },
  { index: 3, trade_date: '2026-09-21', open: 114, high: 117, low: 113, close: 116, volume: 1050 },
  { index: 4, trade_date: '2026-09-22', open: 104, high: 106, low: 103.8, close: 104.3, volume: 1250 },
  { index: 5, trade_date: '2026-09-23', open: 106, high: 109.5, low: 105, close: 109.2, volume: 900 },
]

const pattern = {
  pattern_id: 'gartley',
  schema: 'XABCD',
  direction: 'bullish',
  state: 'completed',
  scale: 5,
  geometry_score: 98.7,
  points: [
    { label: 'X', index: 0, price: 100, trade_date: '2026-09-16' },
    { label: 'A', index: 1, price: 120, trade_date: '2026-09-17' },
    { label: 'B', index: 2, price: 107.64, trade_date: '2026-09-18' },
    { label: 'C', index: 3, price: 116.64, trade_date: '2026-09-21' },
    { label: 'D', index: 4, price: 104.28, trade_date: '2026-09-22' },
  ],
  prz: {
    price_low: 104.2,
    price_high: 104.4,
    width: 0.2,
    source_prz_low: 103.9,
    source_prz_high: 104.5,
    source_prz: {
      available: true,
      price_low: 103.9,
      price_high: 104.5,
      width: 0.6,
      status: 'frozen',
    },
    components: [
      { name: 'XA completion', price_low: 104.28, price_high: 104.28, ratio_low: 0.786, ratio_high: 0.786 },
    ],
  },
  metrics: {
    b_xa: 0.618,
    c_ab: 0.728,
    bc_projection: 1.373,
    d_xa: 0.786,
    cd_ab: 1,
  },
  source_lifecycle: {
    state: 'type_i_confirmed',
    state_reason: '38.2 reached inside five bars.',
    clock_source: 'source_terminal_price_bar',
    current_bar: 5,
    signal_bar: 2,
    source_prz_entry_bar: 4,
    source_terminal_bar: 4,
    execution_start_bar: 5,
    bars_since_terminal: 1,
    type_i_t1_bar: 5,
    type_i_t2_bar: null,
    first_source_prz_exit_bar: 5,
    type_ii_retest_entry_bar: null,
    type_ii_terminal_bar: null,
    reversal_exit_after_type_ii_bar: null,
    source_prz_low: 103.9,
    source_prz_high: 104.5,
    pez_low: 103.8,
    pez_high: 104.5,
    target_382: 107,
    target_618: 109.2,
    next_key_price: 109.2,
    next_key_price_role: 'type_i_61_8_target',
    strict_type_ii_full_retest: true,
    retrospective_geometry_clock_used: false,
  },
  decision_narrative: {
    lifecycle_state: 'type_i_confirmed',
    action_state: 'reaction_observation',
    current_position: 'Source T-Bar 已形成，T+1 已开始，38.2% 已确认。',
    first_watch: '先看价格能否保持在 Source PRZ 之外。',
    next_watch: '随后观察 61.8% 目标 109.20；未到达前不提前升级。',
    upgrade_blocker: '未完整回测 Source PRZ 前，不得升级为 Type-II。',
    next_key_price: 109.2,
    next_key_price_role: 'type_i_61_8_target',
    execution_context_gate: 'tradable',
    context_cautions: [],
    is_trade_instruction: false,
    uses_score: false,
    mutates_harmonic_identity: false,
    mutates_source_raw_prz: false,
    owns_lifecycle: false,
  },
}

const analysis = {
  instrument_id: 'SSE.688256',
  price_mode: 'qfq',
  warning: null,
  bars_requested: 420,
  bars_returned: bars.length,
  first_trade_date: bars[0].trade_date,
  last_trade_date: bars.at(-1)?.trade_date,
  scales: [3, 5, 8, 13],
  bars,
  completed: [pattern],
  forming: [],
  pivot_counts: { '3': 8, '5': 5, '8': 3, '13': 2 },
  type_i_t5_events: [],
  engine_note: 'geometry_score 仅衡量几何贴合度，不代表胜率、预期收益或交易建议。',
}

test('Stable application separates home, research, discovery and system destinations', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 })
  let harmonicRequestCount = 0

  await page.route('**/api/health', async (route) => {
    await route.fulfill({ json: { status: 'ok', service: 'ht-cn-api', version: '1.0.0' } })
  })
  await page.route('**/api/instruments?**', async (route) => {
    await route.fulfill({ json: { count: 1, items: [{ instrument_id: 'SSE.688256', has_qfq_factor: true }] } })
  })
  await page.route('**/api/product/status', async (route) => {
    await route.fulfill({ json: { status: 'healthy', healthy: true, children: {} } })
  })
  await page.route('**/api/market-data/status', async (route) => {
    await route.fulfill({ json: { status: 'idle_current', healthy: true, last_success_trade_date: '2026-09-23' } })
  })
  await page.route('**/api/harmonic/runtime/status', async (route) => {
    await route.fulfill({ json: { status: 'idle_current', healthy: true, last_success_trade_date: '2026-09-23' } })
  })
  await page.route('**/api/evidence/status', async (route) => {
    await route.fulfill({ json: { status: 'healthy', healthy: true, evidence_insufficient: true, calibration_state: 'disabled_insufficient_evidence' } })
  })
  await page.route('**/api/operator/queue?**', async (route) => {
    await route.fulfill({ status: 503, json: { detail: 'fixture intentionally unavailable' } })
  })
  await page.route('**/api/harmonic/SSE.688256?**', async (route) => {
    harmonicRequestCount += 1
    await route.fulfill({ json: analysis })
  })

  await page.goto('/')

  await expect(page.getByRole('heading', { name: '今天想研究什么？' })).toBeVisible()
  await expect(page.getByLabel('应用导航')).toBeVisible()
  await expect(page.getByLabel('operator-queue')).toHaveCount(0)

  await page.getByLabel('应用导航').getByRole('button', { name: '机会发现', exact: true }).click()
  await expect(page.getByRole('heading', { name: '机会发现' })).toBeVisible()
  await expect(page.getByLabel('operator-queue')).toBeVisible()

  await page.getByLabel('应用导航').getByRole('button', { name: '首页', exact: true }).click()
  const symbol = page.locator('#global-symbol-search')
  await symbol.fill('SSE.688256')
  await symbol.press('Enter')

  const workbench = page.getByTestId('product-workbench')
  const chart = page.getByLabel('harmonic-chart')
  const narrative = page.getByTestId('decision-narrative')

  await expect(page.getByRole('heading', { name: 'SSE.688256' })).toBeVisible()
  await expect(workbench).toBeVisible()
  await expect(chart).toBeVisible()
  await expect(narrative).toBeVisible()
  await expect(narrative).toContainText('现在在哪')
  await expect(narrative).toContainText('先看什么')
  await expect(narrative).toContainText('到了再看什么')
  await expect(narrative).toContainText('下一关键价')
  await expect(narrative).toContainText('109.20')
  expect(harmonicRequestCount).toBe(1)

  await page.getByRole('button', { name: '形态与价位' }).click()
  await expect(page.getByTestId('pattern-audit-panel')).toBeVisible()
  await page.getByRole('button', { name: '市场环境' }).click()
  await expect(page.locator('[data-research-tab="context"]')).toBeVisible()
  await page.getByRole('button', { name: '审计' }).click()
  await expect(page.locator('[data-research-tab="audit"]')).toBeVisible()
  expect(harmonicRequestCount).toBe(1)

  await page.getByLabel('应用导航').getByRole('button', { name: '系统状态', exact: true }).click()
  await expect(page.getByRole('heading', { name: '系统状态' })).toBeVisible()
  await expect(page.getByTestId('market-data-runtime-card')).toBeVisible()
})

test('chart workspace keeps watchlist, inspector and viewport interactions in one research surface', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 })
  let requests = 0
  await page.route('**/api/health', async (route) => {
    await route.fulfill({ json: { status: 'ok', service: 'ht-cn-api', version: '1.0.0' } })
  })
  await page.route('**/api/instruments?**', async (route) => {
    await route.fulfill({ json: { count: 3, items: [
      { instrument_id: 'SSE.688256', has_qfq_factor: true },
      { instrument_id: 'SSE.688300', has_qfq_factor: true },
      { instrument_id: 'SZSE.300394', has_qfq_factor: true },
    ] } })
  })
  await page.route('**/api/harmonic/**', async (route) => {
    requests += 1
    const instrumentId = decodeURIComponent(new URL(route.request().url()).pathname.split('/').at(-1) ?? '')
    await route.fulfill({ json: { ...analysis, instrument_id: instrumentId } })
  })

  await page.goto('/')
  await page.keyboard.press('Control+k')
  await expect(page.locator('#global-symbol-search')).toBeFocused()
  await page.locator('#global-symbol-search').fill('SSE.688256')
  await page.locator('#global-symbol-search').press('Enter')

  await expect(page.getByRole('heading', { name: 'SSE.688256' })).toBeVisible()
  await expect(page.getByLabel('谐波主图')).toBeVisible()
  await expect(page.getByLabel('自选股列表').getByRole('button', { name: '打开 SSE.688300 图表' })).toBeVisible()
  await expect(page.getByLabel('自选股列表')).toContainText('最近收盘')
  await expect(page.getByLabel('自选股列表')).toContainText('其余证券暂不提供实时报价')

  await page.getByRole('button', { name: '添加自选股' }).click()
  await page.getByRole('combobox', { name: '输入代码添加自选股' }).fill('SZSE.300394')
  await page.getByRole('combobox', { name: '输入代码添加自选股' }).press('Enter')
  await expect(page.getByRole('button', { name: '从自选股移除 SZSE.300394' })).toBeVisible()

  await page.getByLabel('股票详情页签').getByRole('button', { name: 'Source 时钟' }).click()
  await expect(page.getByTestId('lifecycle-compass')).toBeVisible()
  await page.getByLabel('股票详情页签').getByRole('button', { name: '当前判断' }).click()
  await page.getByRole('button', { name: '打开结构明细' }).click()
  await expect(page.getByTestId('pattern-audit-panel')).toBeVisible()
  await page.getByRole('button', { name: '收起右侧详情栏' }).click()
  await expect(page.getByLabel('自选股列表')).toHaveCount(0)
  await page.getByRole('button', { name: '打开右侧详情栏' }).click()
  expect(requests).toBe(1)

  await page.getByRole('button', { name: '打开 SSE.688300 图表' }).click()
  await expect(page.getByRole('heading', { name: 'SSE.688300' })).toBeVisible()
  expect(requests).toBe(2)
  await expect(page.getByLabel('自选股列表')).toContainText('SZSE.300394')

  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'SSE.688300' })).toBeVisible()
  expect(requests).toBe(3)
  await expect(page.getByRole('button', { name: '从自选股移除 SZSE.300394' })).toBeVisible()

  await page.setViewportSize({ width: 390, height: 844 })
  await expect(page.getByLabel('harmonic-chart')).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390)
})
