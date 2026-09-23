import { expect, test } from '@playwright/test'

test('industry context renders local aggregate and preserves harmonic boundaries', async ({ page }) => {
  await page.route('**/api/health', async (route) => {
    await route.fulfill({ json: { status: 'ok', service: 'ht-cn-api', version: '0.3.0' } })
  })
  await page.route('**/api/instruments?**', async (route) => {
    await route.fulfill({ json: { count: 1, items: [{ instrument_id: 'SSE.688256', has_qfq_factor: true }] } })
  })
  await page.route('**/api/harmonic/SSE.688256?**', async (route) => {
    await route.fulfill({ json: {
      instrument_id: 'SSE.688256',
      price_mode: 'qfq',
      warning: null,
      bars_requested: 420,
      bars_returned: 1,
      first_trade_date: '2026-09-18',
      last_trade_date: '2026-09-18',
      scales: [3, 5, 8, 13],
      bars: [{ index: 0, trade_date: '2026-09-18', open: 100, high: 102, low: 99, close: 101, volume: 1000 }],
      completed: [],
      forming: [],
      pivot_counts: {},
      sector_context: {
        status: 'resolved',
        sector_kind: 'industry',
        sector_code: 'BK1036',
        sector_name: '半导体',
        mapping_source: 'akshare_eastmoney_industry',
        mapping_observed_on: '2026-09-18',
        candidate_sectors: [{ sector_code: 'BK1036', sector_name: '半导体' }],
        snapshot_trade_date: '2026-09-18',
        total_member_count: 120,
        return_1d_count: 118,
        return_5d_count: 116,
        return_20d_count: 110,
        mean_return_1d_pct: .4,
        median_return_1d_pct: .2,
        mean_return_5d_pct: 1.5,
        median_return_5d_pct: 1.1,
        mean_return_20d_pct: -2.1,
        median_return_20d_pct: -2.5,
        pct_above_ma20: 42.5,
        up_ratio_1d: 55,
        down_ratio_1d: 38,
        avg_volume_ratio_20: 1.18,
        instrument_relative_5d_vs_sector_median_pct: 3.2,
        instrument_relative_20d_vs_sector_median_pct: 4.8,
        aggregate_method: 'local_constituent_equal_weight_mean_and_median',
        mutates_harmonic_identity: false,
        mutates_source_raw_prz: false,
        owns_lifecycle: false,
      },
      engine_note: 'sector evidence only',
    } })
  })

  await page.goto('/')
  await page.getByRole('button', { name: '运行谐波分析' }).click()
  await page.getByRole('button', { name: '市场环境' }).click()
  const card = page.getByTestId('sector-context')
  await expect(card).toBeVisible()
  await expect(card.getByText('半导体')).toBeVisible()
  await expect(card.getByText(/MA20上方 \+42\.50%/)).toBeVisible()
  await expect(card.getByText(/5日 \+3\.20%/)).toBeVisible()
  await expect(card.getByText(/本地 M1 成分股等权均值\/中位数重算/)).toBeVisible()
  await expect(card.getByText(/不拥有 lifecycle/)).toBeVisible()
})
