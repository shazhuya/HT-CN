import { expect, test } from '@playwright/test'

const bars = [
  { index: 0, trade_date: '2026-09-08', open: 100, high: 102, low: 99, close: 101, volume: 1000 },
  { index: 1, trade_date: '2026-09-09', open: 118, high: 121, low: 117, close: 120, volume: 1100 },
  { index: 2, trade_date: '2026-09-10', open: 109, high: 110, low: 107.5, close: 108, volume: 950 },
  { index: 3, trade_date: '2026-09-11', open: 115, high: 117, low: 114, close: 116.5, volume: 1050 },
  { index: 4, trade_date: '2026-09-14', open: 105, high: 106, low: 103.8, close: 104.3, volume: 1250 },
  { index: 5, trade_date: '2026-09-15', open: 106, high: 108, low: 105, close: 107, volume: 900 },
]

const executionContext = {
  instrument_id: 'SSE.688256',
  symbol: '688256',
  board: 'STAR',
  as_of_trade_date: '2026-09-15',
  metadata_available: true,
  metadata_source: 'test',
  list_date: '2020-07-20',
  is_st: false,
  t_plus_one: true,
  same_day_sell_after_buy: false,
  earliest_sell_offset_sessions_after_buy: 1,
  nominal_price_limit_pct: 20,
  rule_based_price_limit_pct: 20,
  price_limit_status: 'board_rule_profile_resolved_special_events_unresolved',
  ipo_first_five_sessions: false,
  special_event_exceptions_unresolved: true,
  atr_period: 14,
  atr: 6.21,
  atr_pct: 5.8,
  latest_range_pct: 2.86,
  avg_volume_20: 1025000,
  volume_ratio_20: 1.37,
  bse_deferred: false,
  mutates_harmonic_identity: false,
  mutates_source_raw_prz: false,
}

const pattern = {
  pattern_id: 'gartley',
  schema: 'XABCD',
  direction: 'bullish',
  state: 'completed',
  scale: 5,
  geometry_score: 98.7,
  points: [
    { label: 'X', index: 0, price: 100, trade_date: '2026-09-08' },
    { label: 'A', index: 1, price: 120, trade_date: '2026-09-09' },
    { label: 'B', index: 2, price: 107.64, trade_date: '2026-09-10' },
    { label: 'C', index: 3, price: 116.64, trade_date: '2026-09-11' },
    { label: 'D', index: 4, price: 104.28, trade_date: '2026-09-14' },
  ],
  source_lifecycle: {
    state: 'waiting_terminal',
    state_reason: 'waiting for source terminal-side test',
    clock_source: 'source_terminal_price_bar',
    current_bar: 5,
    signal_bar: 2,
    source_prz_entry_bar: 4,
    source_terminal_bar: null,
    execution_start_bar: null,
    bars_since_terminal: null,
    type_i_t1_bar: null,
    type_i_t2_bar: null,
    first_source_prz_exit_bar: null,
    type_ii_retest_entry_bar: null,
    type_ii_terminal_bar: null,
    reversal_exit_after_type_ii_bar: null,
    source_prz_low: 103.9,
    source_prz_high: 104.5,
    pez_low: null,
    pez_high: null,
    target_382: null,
    target_618: null,
    next_key_price: 103.9,
    next_key_price_role: 'source_prz_terminal_side',
    strict_type_ii_full_retest: true,
    retrospective_geometry_clock_used: false,
  },
  a_share_execution_context: executionContext,
  prz: {
    price_low: 104.2,
    price_high: 104.4,
    width: 0.2,
    components: [
      { name: 'XA completion', price_low: 104.28, price_high: 104.28, ratio_low: 0.786, ratio_high: 0.786 },
    ],
  },
  metrics: { b_xa: 0.618, c_ab: 0.728, bc_projection: 1.373, d_xa: 0.786, cd_ab: 1 },
}

test('A-share execution context is separate, auditable, and does not replace source lifecycle', async ({ page }) => {
  await page.route('**/api/health', async (route) => {
    await route.fulfill({ json: { status: 'ok', service: 'ht-cn-api', version: '0.3.0' } })
  })
  await page.route('**/api/instruments?**', async (route) => {
    await route.fulfill({ json: { count: 1, items: [{ instrument_id: 'SSE.688256', has_qfq_factor: true }] } })
  })
  await page.route('**/api/harmonic/SSE.688256?**', async (route) => {
    await route.fulfill({
      json: {
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
        pivot_counts: { '3': 8, '5': 5 },
        a_share_execution_context: executionContext,
        engine_note: 'Execution context is evidence/context only.',
      },
    })
  })

  await page.goto('/')
  await page.getByRole('button', { name: '运行谐波分析' }).click()

  const context = page.getByTestId('a-share-execution-context')
  await expect(context).toBeVisible()
  await expect(context.getByText('科创板 · 2026-09-15')).toBeVisible()
  await expect(context.getByText('买入后最早下一交易日卖出')).toBeVisible()
  await expect(context.getByText('规则值 ±20%')).toBeVisible()
  await expect(context.getByText(/ATR\(14\)/)).toBeVisible()
  await expect(context.getByText(/量比 1\.37/)).toBeVisible()
  await expect(context.getByText(/不会创建、修复或否定谐波身份/)).toBeVisible()

  const compass = page.getByTestId('lifecycle-compass')
  await expect(compass.getByText('Source Clock 证据')).toBeVisible()
  await expect(page.getByTestId('source-clock-state').getByText('waiting_terminal')).toBeVisible()
  await expect(compass.getByText(/历史 reaction_audit 不覆盖 canonical source lifecycle/)).toBeVisible()
})
