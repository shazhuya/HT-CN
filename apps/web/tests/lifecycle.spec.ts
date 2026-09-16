import { expect, test } from '@playwright/test'

const bars = [
  { index: 0, trade_date: '2026-09-08', open: 100, high: 102, low: 99, close: 101, volume: 1000 },
  { index: 1, trade_date: '2026-09-09', open: 118, high: 121, low: 117, close: 120, volume: 1100 },
  { index: 2, trade_date: '2026-09-10', open: 109, high: 110, low: 107.5, close: 108, volume: 950 },
  { index: 3, trade_date: '2026-09-11', open: 115, high: 117, low: 114, close: 116.5, volume: 1050 },
  { index: 4, trade_date: '2026-09-14', open: 105, high: 106, low: 103.8, close: 104.3, volume: 1250 },
  { index: 5, trade_date: '2026-09-15', open: 106, high: 108, low: 105, close: 107, volume: 900 },
]

const basePattern = {
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
  prz: {
    price_low: 104.2,
    price_high: 104.4,
    width: 0.2,
    source_prz_low: null,
    source_prz_high: null,
    components: [
      { name: 'XA completion', price_low: 104.28, price_high: 104.28, ratio_low: 0.786, ratio_high: 0.786 },
    ],
  },
  metrics: { b_xa: 0.618, c_ab: 0.728, bc_projection: 1.373, d_xa: 0.786, cd_ab: 1 },
}

function reactionAudit(overrides: Record<string, unknown> = {}) {
  return {
    d_index: 4,
    bars_observed: 12,
    target_382: 110.28,
    target_618: 114.0,
    bars_to_382: null,
    bars_to_618: null,
    first_prz_exit_bar: 1,
    secondary_prz_retest_bar: null,
    source_prz_available: false,
    full_prz_retest_bar: null,
    type_ii_terminal_bar: null,
    reversal_exit_after_retest_bar: null,
    bars_to_reversal_exit_after_retest: null,
    third_prz_test_bar: null,
    no_prz_retest_first_3_bars: true,
    no_prz_retest_first_5_bars: true,
    max_favorable_price: 112,
    max_favorable_retracement: 0.49,
    type_ii_candidate: false,
    rsi_period: 14,
    rsi_at_d: 27,
    rsi_extreme_bar: null,
    rsi_extreme_value: null,
    rsi_trigger_bar: null,
    rsi_trigger_value: null,
    rsi_confirmation: false,
    indicator_evidence_kind: 'wilder_rsi_extreme_reversal',
    indicator_evidence_is_rsi_bamm: false,
    type_ii_evidence_state: 'not_candidate',
    ...overrides,
  }
}

function analysisFor(pattern: Record<string, unknown>) {
  const isForming = pattern.state === 'forming'
  return {
    instrument_id: 'SSE.688256',
    price_mode: 'qfq',
    warning: null,
    bars_requested: 420,
    bars_returned: bars.length,
    first_trade_date: bars[0].trade_date,
    last_trade_date: bars.at(-1)?.trade_date,
    scales: [3, 5, 8, 13],
    bars,
    completed: isForming ? [] : [pattern],
    forming: isForming ? [pattern] : [],
    pivot_counts: { '3': 8, '5': 5, '8': 3, '13': 2 },
    engine_note: 'geometry_score 仅衡量几何贴合度，不代表胜率、预期收益或交易建议。',
  }
}

async function openScenario(page: import('@playwright/test').Page, pattern: Record<string, unknown>) {
  await page.route('**/api/health', async (route) => {
    await route.fulfill({ json: { status: 'ok', service: 'ht-cn-api', version: '0.3.0' } })
  })
  await page.route('**/api/instruments?**', async (route) => {
    await route.fulfill({ json: { count: 1, items: [{ instrument_id: 'SSE.688256', has_qfq_factor: true }] } })
  })
  await page.route('**/api/harmonic/SSE.688256?**', async (route) => {
    await route.fulfill({ json: analysisFor(pattern) })
  })

  await page.goto('/')
  await page.getByRole('button', { name: '运行谐波分析' }).click()
  await expect(page.getByTestId('lifecycle-compass')).toBeVisible()
}

test('forming candidate stays explicitly uncompleted and waits for source-aligned T-Bar', async ({ page }) => {
  await openScenario(page, { ...basePattern, state: 'forming' })
  const compass = page.getByTestId('lifecycle-compass')
  await expect(compass.getByText('形成中 · 尚未完成')).toBeVisible()
  await expect(
    compass.getByText(
      '先看价格是否在仍有效的 forming 投影下测试 source PRZ 的最终/极端测量，并形成 Terminal Price Bar。',
      { exact: true },
    ),
  ).toBeVisible()
  await expect(page.getByTestId('type-i-target-t1')).toHaveCount(0)
  await expect(page.getByTestId('type-i-target-t2')).toHaveCount(0)
})

test('retrospective T1 reached remains explicitly separate from source execution clock', async ({ page }) => {
  await openScenario(page, {
    ...basePattern,
    reaction_audit: reactionAudit({ bars_to_382: 2 }),
  })
  await expect(page.getByText('后验 Type-I · 已到 T1，T2 未到')).toBeVisible()
  await expect(page.getByText(/Type-II 仍要求明确 source PRZ/)).toBeVisible()
  await expect(page.getByTestId('type-i-target-t1')).toHaveAttribute('data-state', 'reached')
  await expect(page.getByTestId('type-i-target-t2')).toHaveAttribute('data-state', 'pending')
  await expect(page.getByText(/后验T1 38\.2% · 110\.28 · 已到达/)).toBeVisible()
  await expect(page.getByText(/后验T2 61\.8% · 114\.00 · 待到达/)).toBeVisible()
})

test('retrospective T2 reached is not mislabeled as source-aligned execution or long-term reversal', async ({ page }) => {
  await openScenario(page, {
    ...basePattern,
    reaction_audit: reactionAudit({ bars_to_382: 2, bars_to_618: 5 }),
  })
  await expect(page.getByText('后验 Type-I · 已到 T2（61.8%）')).toBeVisible()
  await expect(page.getByText(/不等于 source-aligned 实时执行完成/)).toBeVisible()
  await expect(page.getByTestId('type-i-target-t1')).toHaveAttribute('data-state', 'reached')
  await expect(page.getByTestId('type-i-target-t2')).toHaveAttribute('data-state', 'reached')
})

test('re-entry cannot become Type-II while source PRZ remains unresolved', async ({ page }) => {
  await openScenario(page, {
    ...basePattern,
    reaction_audit: reactionAudit({
      bars_to_382: 2,
      secondary_prz_retest_bar: 7,
      source_prz_available: false,
      type_ii_evidence_state: 'source_prz_unresolved',
    }),
  })
  await expect(page.getByText('二次重入已见 · Source PRZ 未冻结')).toBeVisible()
  await expect(page.getByText(/禁止把这次重入升级为 Type-II/)).toBeVisible()
})

test('partial secondary source PRZ overlap is not promoted to Type-II Terminal Price Bar', async ({ page }) => {
  await openScenario(page, {
    ...basePattern,
    prz: { ...basePattern.prz, source_prz_low: 104.0, source_prz_high: 104.5 },
    reaction_audit: reactionAudit({
      bars_to_382: 2,
      secondary_prz_retest_bar: 7,
      source_prz_available: true,
      type_ii_evidence_state: 'partial_retest_only',
    }),
  })
  await expect(page.getByText('二次进入 · 尚未完整回测')).toBeVisible()
  await expect(page.getByText(/不是 Type-II Terminal Price Bar/)).toBeVisible()
})

test('full source PRZ retest with price and RSI evidence stays explicitly non-BAMM', async ({ page }) => {
  await openScenario(page, {
    ...basePattern,
    prz: { ...basePattern.prz, source_prz_low: 104.0, source_prz_high: 104.5 },
    reaction_audit: reactionAudit({
      bars_to_382: 2,
      bars_to_618: 5,
      secondary_prz_retest_bar: 7,
      source_prz_available: true,
      full_prz_retest_bar: 8,
      type_ii_terminal_bar: 8,
      reversal_exit_after_retest_bar: 9,
      bars_to_reversal_exit_after_retest: 1,
      type_ii_candidate: true,
      rsi_extreme_bar: 8,
      rsi_extreme_value: 28,
      rsi_trigger_bar: 9,
      rsi_trigger_value: 36,
      rsi_confirmation: true,
      type_ii_evidence_state: 'price_and_rsi_confirmed',
    }),
  })
  await expect(page.getByText('后验 Type-II · 价格 + RSI 辅助证据')).toBeVisible()
  const auditCard = page.locator('.audit-card')
  await expect(auditCard.getByText(/明确不是 RSI BAMM/)).toBeVisible()
  await expect(page.getByTestId('type-i-target-t1')).toHaveAttribute('data-state', 'reached')
  await expect(page.getByTestId('type-i-target-t2')).toHaveAttribute('data-state', 'reached')
})
