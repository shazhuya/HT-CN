import { expect, test } from '@playwright/test'

const bars = [
  { index: 0, trade_date: '2026-09-01', open: 100, high: 101, low: 99, close: 100, volume: 1000 },
  { index: 1, trade_date: '2026-09-02', open: 119, high: 121, low: 118, close: 120, volume: 1000 },
  { index: 2, trade_date: '2026-09-03', open: 108, high: 109, low: 107.4, close: 107.64, volume: 1000 },
  { index: 3, trade_date: '2026-09-04', open: 116, high: 117.1, low: 115.5, close: 116.91, volume: 1000 },
  { index: 4, trade_date: '2026-09-07', open: 112, high: 113, low: 110, close: 111, volume: 1000 },
  { index: 5, trade_date: '2026-09-08', open: 108, high: 109, low: 105, close: 106, volume: 1000 },
]

const discovery = {
  pattern_id: 'gartley',
  schema: 'XABCD',
  direction: 'bullish',
  state: 'forming',
  channel: 'discovery',
  discovery_only: true,
  scale: 10,
  geometry_score: 82.5,
  points: [
    { label: 'X', index: 0, price: 100, trade_date: '2026-09-01' },
    { label: 'A', index: 1, price: 120, trade_date: '2026-09-02' },
    { label: 'B', index: 2, price: 107.64, trade_date: '2026-09-03' },
    { label: 'C', index: 3, price: 116.91, trade_date: '2026-09-04' },
  ],
  pivot_support: [],
  identity_conflicts: ['discovery:gartley@S10'],
  is_primary_identity: true,
  prz: {
    price_low: 104.1,
    price_high: 104.5,
    width: 0.4,
    component_price_low: 103.8,
    component_price_high: 105.0,
    source_prz_low: 104.0,
    source_prz_high: 104.6,
    source_prz: {
      available: true,
      price_low: 104.0,
      price_high: 104.6,
      width: 0.6,
      status: 'frozen',
    },
    components: [
      { name: 'XA completion', price_low: 104.28, price_high: 104.28, ratio_low: 0.786, ratio_high: 0.786 },
    ],
  },
  metrics: { b_xa: 0.618, c_ab: 0.75 },
  discovery: {
    authoritative_identity: false,
    path_kind: 'minor_swing_skip',
    skipped_pivots: 2,
    known_from_bar: 4,
    prz_status: 'tested',
    first_prz_test_bar: 5,
    c_family_target: 0.786,
    c_family_relative_error: 0.0458,
    source_family_aligned: false,
    distance_to_source_prz_xa: 0.07,
    mutates_source_identity: false,
    owns_lifecycle: false,
    fabricates_d: false,
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
  discovery_scales: [5, 10, 20],
  bars,
  completed: [],
  forming: [],
  discovery: [discovery],
  pivot_counts: { '3': 0, '5': 0, '8': 0, '13': 0 },
  discovery_pivot_counts: { '5': 4, '10': 4, '20': 4 },
  recognition_diagnostics: {
    authoritative_completed: 0,
    authoritative_forming: 0,
    discovery_candidates: 1,
  },
  engine_note: '发现层与权威身份分离。',
}

test('Stable renders discovery-only XABC when authoritative channels are empty', async ({ page }) => {
  await page.route('**/api/health', async (route) => {
    await route.fulfill({ json: { status: 'ok', service: 'ht-cn-api', version: '1.0.0' } })
  })
  await page.route('**/api/instruments?**', async (route) => {
    await route.fulfill({ json: { count: 1, items: [{ instrument_id: 'SSE.688256', has_qfq_factor: true }] } })
  })
  await page.route('**/api/harmonic/SSE.688256?**', async (route) => {
    await route.fulfill({ json: analysis })
  })

  await page.goto('/')
  const input = page.locator('#global-symbol-search')
  await input.fill('SSE.688256')
  await input.press('Enter')

  await expect(page.getByRole('heading', { name: 'Gartley · 发现候选' })).toBeVisible()
  const note = page.getByTestId('discovery-candidate-note')
  await expect(note).toContainText('尚非权威身份')
  await expect(note).toContainText('不虚构 D')
  await expect(page.getByLabel('形态候选')).toContainText('发现候选 · S10')
  await expect(page.getByTestId('lifecycle-compass')).toHaveCount(0)

  await page.getByRole('button', { name: '打开结构明细' }).click()
  const audit = page.getByTestId('discovery-audit')
  await expect(audit).toContainText('非权威身份')
  await expect(audit).toContainText('结构区间有效 · 未达3%离散门槛')
  await expect(page.getByTestId('pattern-audit-panel')).toContainText('D/XA')
  await expect(page.getByTestId('pattern-audit-panel')).toContainText('未生成')

  await page.getByLabel('股票详情页签').getByRole('button', { name: 'Source 时钟' }).click()
  await expect(page.getByText('Source 生命周期未启动')).toBeVisible()
  await expect(page.getByTestId('lifecycle-compass')).toHaveCount(0)
})
