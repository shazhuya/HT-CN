import { expect, test } from '@playwright/test'

test('core market context renders four benchmarks and stays separate from harmonic identity', async ({ page }) => {
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
        bars_returned: 1,
        first_trade_date: '2026-09-17',
        last_trade_date: '2026-09-17',
        scales: [3, 5, 8, 13],
        bars: [{ index: 0, trade_date: '2026-09-17', open: 100, high: 102, low: 99, close: 101, volume: 1000 }],
        completed: [],
        forming: [],
        pivot_counts: {},
        market_context: {
          status: 'complete',
          as_of_trade_date: '2026-09-17',
          mutates_harmonic_identity: false,
          mutates_source_raw_prz: false,
          owns_lifecycle: false,
          benchmarks: [
            { key: 'star50', symbol: '000688', name_zh: '科创50', available: true, as_of_trade_date: '2026-09-17', close: 1200, return_1d_pct: 1.1, return_5d_pct: -2.2, return_20d_pct: -6.5, ma20: 1250, distance_to_ma20_pct: -4, ma20_slope_5d_pct: -2, trend_state: 'below_falling_ma20', instrument_relative_5d_pct: 3.1, instrument_relative_20d_pct: 4.2 },
            { key: 'chinext', symbol: '399006', name_zh: '创业板指', available: true, as_of_trade_date: '2026-09-17', close: 2800, return_1d_pct: .5, return_5d_pct: -1, return_20d_pct: -4, ma20: 2850, distance_to_ma20_pct: -1.75, ma20_slope_5d_pct: -1, trend_state: 'below_falling_ma20', instrument_relative_5d_pct: 1.9, instrument_relative_20d_pct: 1.7 },
            { key: 'csi300', symbol: '000300', name_zh: '沪深300', available: true, as_of_trade_date: '2026-09-17', close: 4100, return_1d_pct: .2, return_5d_pct: .8, return_20d_pct: 1.2, ma20: 4080, distance_to_ma20_pct: .49, ma20_slope_5d_pct: .4, trend_state: 'above_rising_ma20', instrument_relative_5d_pct: .1, instrument_relative_20d_pct: -3.5 },
            { key: 'sse_composite', symbol: '000001', name_zh: '上证指数', available: true, as_of_trade_date: '2026-09-17', close: 3800, return_1d_pct: .1, return_5d_pct: .5, return_20d_pct: .9, ma20: 3780, distance_to_ma20_pct: .53, ma20_slope_5d_pct: .3, trend_state: 'above_rising_ma20', instrument_relative_5d_pct: .4, instrument_relative_20d_pct: -3.2 },
          ],
        },
        engine_note: 'market context is evidence only',
      },
    })
  })

  await page.goto('/')
  await page.getByRole('button', { name: '运行谐波分析' }).click()

  const card = page.getByTestId('market-context')
  await expect(card).toBeVisible()
  await expect(card.getByText('四指数齐全')).toBeVisible()
  await expect(page.getByTestId('market-benchmark-star50').getByText('科创50')).toBeVisible()
  await expect(page.getByTestId('market-benchmark-chinext').getByText('创业板指')).toBeVisible()
  await expect(card.getByText(/不创建、修复或否定谐波身份/)).toBeVisible()
})
