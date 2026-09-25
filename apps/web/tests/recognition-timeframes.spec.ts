import { expect, test } from '@playwright/test'

const dailyBars = [
  { index: 0, trade_date: '2026-09-23', open: 100, high: 103, low: 99, close: 102, volume: 1000 },
  { index: 1, trade_date: '2026-09-24', open: 102, high: 104, low: 101, close: 103, volume: 1200 },
]

const intradayBars = [
  {
    index: 0, trade_date: '2026-09-24 14:00', time: 1790258400,
    open: 100, high: 102, low: 99, close: 101, volume: 1000,
  },
  {
    index: 1, trade_date: '2026-09-24 15:00', time: 1790262000,
    open: 101, high: 103, low: 100, close: 102, volume: 1500,
  },
]

const pineCandidate = {
  pattern_id: 'abcd',
  schema: 'ABCD',
  direction: 'bullish',
  state: 'forming',
  channel: 'discovery',
  discovery_only: true,
  scale: 5,
  geometry_score: 0,
  points: [
    { label: 'A', index: 0, price: 100, trade_date: '2026-09-24 14:00' },
    { label: 'B', index: 1, price: 90, trade_date: '2026-09-24 14:15' },
    { label: 'C', index: 2, price: 96.18, trade_date: '2026-09-24 14:30' },
  ],
  pivot_support: [],
  identity_conflicts: ['pine_r34:abcd@S5'],
  is_primary_identity: true,
  prz: {
    price_low: 86.18,
    price_high: 86.20,
    width: 0.02,
    component_price_low: 86.18,
    component_price_high: 86.20,
    components: [
      { name: 'R3.4 M1', price_low: 86.18, price_high: 86.18, ratio_low: 0, ratio_high: 0 },
      { name: 'R3.4 M2', price_low: 86.20, price_high: 86.20, ratio_low: 0, ratio_high: 0 },
    ],
  },
  metrics: {
    m1: 86.18,
    m2: 86.20,
    m3: 86.18,
    structural_limit: 83.48,
    distance_to_prz: 15.8,
    distance_to_prz_atr: 2.1,
  },
  discovery: {
    source: 'pine_r34',
    behavioral_baseline: true,
    authoritative_identity: false,
    path_kind: 'pine_r34',
    skipped_pivots: 0,
    known_from_bar: 7,
    prz_status: 'projected',
    first_prz_test_bar: null,
    c_family_target: 0.618,
    c_family_relative_error: 0.002,
    source_family_aligned: true,
    distance_to_source_prz_xa: 0.4,
    research_only: false,
    qualified: true,
    precise: true,
    projected_label: 'D',
    structural_limit: 83.48,
    pine_source_sha256: '84e1eb2267c9b80891e0ffb64a6d4abf5712fc5e756be81815e536f2fca4c3f5',
    mutates_source_identity: false,
    owns_lifecycle: false,
    fabricates_d: false,
  },
}

function analysis(timeframe: '1d' | '60m') {
  const intraday = timeframe === '60m'
  const bars = intraday ? intradayBars : dailyBars
  return {
    instrument_id: 'SSE.688256',
    timeframe,
    price_mode: 'qfq',
    warning: null,
    bars_requested: 420,
    bars_returned: bars.length,
    first_trade_date: bars[0].trade_date,
    last_trade_date: bars.at(-1)?.trade_date,
    scales: intraday ? [] : [3, 5, 8, 13],
    bars,
    completed: [],
    forming: [],
    discovery: intraday ? [pineCandidate] : [],
    pivot_counts: {},
    discovery_scales: [5, 10, 20],
    discovery_pivot_counts: { '5': 3, '10': 0, '20': 0 },
    recognition_diagnostics: {
      authoritative_completed: 0,
      authoritative_forming: 0,
      pine_r34_live: intraday ? 1 : 0,
      extended_graph_candidates: 0,
      discovery_candidates: intraday ? 1 : 0,
    },
    data_provenance: intraday
      ? {
          kind: 'intraday_research',
          provider: 'akshare_eastmoney',
          timeframe,
          adjustment: 'qfq',
          authoritative_source_lifecycle: false,
        }
      : { kind: 'canonical_daily', price_mode: 'qfq' },
    engine_note: intraday ? '分钟级研究通道。' : '日线权威通道。',
  }
}

test('research workspace switches 1D -> 60m and labels Pine R3.4 candidates', async ({ page }) => {
  const requested: string[] = []

  await page.route('**/api/health', async (route) => {
    await route.fulfill({ json: { status: 'ok', service: 'ht-cn-api', version: '1.0.0' } })
  })
  await page.route('**/api/instruments?**', async (route) => {
    await route.fulfill({ json: { count: 1, items: [{ instrument_id: 'SSE.688256', has_qfq_factor: true }] } })
  })
  await page.route('**/api/harmonic/SSE.688256?**', async (route) => {
    const url = new URL(route.request().url())
    const timeframe = (url.searchParams.get('timeframe') ?? '1d') as '1d' | '60m'
    requested.push(timeframe)
    await route.fulfill({ json: analysis(timeframe) })
  })

  await page.goto('/')
  const input = page.locator('#global-symbol-search')
  await input.fill('SSE.688256')
  await input.press('Enter')

  await expect(page.getByLabel('K线周期')).toHaveValue('1d')
  await expect(page.getByText('QFQ · 日K')).toBeVisible()

  await page.getByLabel('K线周期').selectOption('60m')

  await expect.poll(() => requested.at(-1)).toBe('60m')
  await expect(page.getByLabel('K线周期')).toHaveValue('60m')
  await expect(page.getByText('QFQ · 60分钟')).toBeVisible()
  await expect(page.getByText('2026-09-24 15:00 最近K线 · 分钟研究')).toBeVisible()
  await expect(page.getByRole('heading', { name: 'AB=CD · 发现候选' })).toBeVisible()
  await expect(page.getByLabel('形态候选')).toContainText('R3.4')
  await expect(page.getByTestId('discovery-candidate-note')).toContainText('R3.4 行为基线候选')
  await expect(page.getByTestId('lifecycle-compass')).toHaveCount(0)
})
