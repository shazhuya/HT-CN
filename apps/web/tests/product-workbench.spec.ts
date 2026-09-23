import { expect, test } from '@playwright/test'

const bars = [
  { index: 0, trade_date: '2026-09-16', open: 100, high: 102, low: 99, close: 101, volume: 1000 },
  { index: 1, trade_date: '2026-09-17', open: 118, high: 121, low: 117, close: 120, volume: 1100 },
  { index: 2, trade_date: '2026-09-18', open: 109, high: 110, low: 107.5, close: 108, volume: 950 },
  { index: 3, trade_date: '2026-09-21', open: 115, high: 117, low: 114, close: 116.5, volume: 1050 },
  { index: 4, trade_date: '2026-09-22', open: 105, high: 106, low: 103.8, close: 104.3, volume: 1250 },
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
      { name: 'BC projection', price_low: 103.9, price_high: 104.5, ratio_low: 1.13, ratio_high: 1.618 },
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
  engine_note: 'geometry_score 仅衡量几何贴合度，不代表胜率、预期收益或交易建议。',
}

test('M9.3 end-to-end workbench shares canonical identity across runtime, chart and decision panels', async ({ page }) => {
  let harmonicRequestCount = 0

  await page.route('**/api/health', async (route) => {
    await route.fulfill({ json: { status: 'ok', service: 'ht-cn-api', version: '0.4.0' } })
  })
  await page.route('**/api/instruments?**', async (route) => {
    await route.fulfill({ json: { count: 1, items: [{ instrument_id: 'SSE.688256', has_qfq_factor: true }] } })
  })
  await page.route('**/api/market-data/status', async (route) => {
    await route.fulfill({
      json: {
        status: 'healthy',
        healthy: true,
        last_success_trade_date: '2026-09-22',
        diagnostics_zh: ['自动行情服务正常。'],
      },
    })
  })
  await page.route('**/api/harmonic/runtime/status', async (route) => {
    await route.fulfill({
      json: {
        status: 'idle_current',
        healthy: true,
        target_trade_date: '2026-09-22',
        last_success_trade_date: '2026-09-22',
        diagnostics_zh: ['谐波分析水位已覆盖当前 canonical 数据身份。'],
      },
    })
  })
  await page.route('**/api/harmonic/SSE.688256?**', async (route) => {
    harmonicRequestCount += 1
    await route.fulfill({ json: analysis })
  })

  await page.goto('/')

  await page.getByLabel('应用导航').getByRole('button', { name: '系统状态', exact: true }).click()
  await expect(page.getByTestId('market-data-runtime-card')).toContainText('数据已就绪')
  await expect(page.getByTestId('harmonic-runtime-card')).toContainText('分析已同步')

  const symbolInput = page.locator('#global-symbol-search')
  await symbolInput.fill('SSE.688256')
  await symbolInput.press('Enter')

  await expect(page.getByTestId('product-workbench')).toBeVisible()
  await expect(page.getByRole('heading', { name: 'SSE.688256' })).toBeVisible()
  await expect(page.getByRole('button', { name: '概要' })).toHaveAttribute('aria-selected', 'true')
  await expect(page.getByTestId('decision-narrative')).toContainText('随后观察 61.8% 目标 109.20')
  await expect(page.getByTestId('workbench-context-panel')).toContainText('Gartley')
  await expect(page.getByTestId('workbench-context-panel')).toContainText('type_i_confirmed')
  await expect(page.getByTestId('workbench-context-panel')).toContainText('103.90 – 104.50')
  await expect(page.getByTestId('workbench-context-panel')).toContainText('109.20')
  await expect(page.getByTestId('workbench-context-panel')).toContainText('Source T1 38.2%')
  await expect(page.getByTestId('workbench-context-panel')).toContainText('B/XA')

  const chart = page.getByLabel('harmonic-chart')
  const overlay = chart.getByTestId('harmonic-overlay')
  const dNode = overlay.locator('[data-node-label="D"]')
  await expect(dNode).toHaveAttribute('data-anchor-date', '2026-09-22')

  const stage = chart.getByTestId('interactive-chart-stage')
  await stage.scrollIntoViewIfNeeded()
  const box = await stage.boundingBox()
  expect(box).not.toBeNull()
  if (!box) return

  const cx = Number(await dNode.getAttribute('cx'))
  const cy = Number(await dNode.getAttribute('cy'))
  await page.mouse.move(box.x + cx, box.y + cy)

  const shared = page.getByTestId('workbench-crosshair-context')
  await expect(shared).toContainText('2026-09-22')
  await expect(shared).toContainText('节点 D')
  expect(harmonicRequestCount).toBe(1)

  const beforeVersion = Number(await overlay.getAttribute('data-viewport-version'))
  await page.mouse.wheel(0, -600)
  await expect.poll(async () => Number(await overlay.getAttribute('data-viewport-version'))).toBeGreaterThan(beforeVersion)
  expect(harmonicRequestCount).toBe(1)
})
