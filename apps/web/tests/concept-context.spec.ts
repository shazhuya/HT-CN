import { expect, test } from '@playwright/test'

test('concept context keeps multi-membership and exposes raw relative-strength evidence', async ({ page }) => {
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
      concept_context: {
        status: 'resolved',
        mapping_source: 'akshare_eastmoney_concept',
        mapping_observed_on: '2026-09-18',
        membership_count: 2,
        resolved_count: 2,
        aggregate_method: 'local_constituent_equal_weight_mean_and_median',
        ordering: 'sector_median_return_5d_desc',
        mutates_harmonic_identity: false,
        mutates_source_raw_prz: false,
        owns_lifecycle: false,
        concepts: [
          {
            sector_code: 'BK2',
            sector_name: 'AI算力',
            snapshot_trade_date: '2026-09-18',
            total_member_count: 60,
            median_return_5d_pct: 2.2,
            median_return_20d_pct: 2.8,
            pct_above_ma20: 62,
            up_ratio_1d: 58,
            avg_volume_ratio_20: 1.3,
            instrument_relative_5d_pct: 3.1,
            instrument_relative_20d_pct: 4.2,
          },
          {
            sector_code: 'BK1',
            sector_name: '国产芯片',
            snapshot_trade_date: '2026-09-18',
            total_member_count: 80,
            median_return_5d_pct: .8,
            median_return_20d_pct: 1.5,
            pct_above_ma20: 55,
            up_ratio_1d: 52,
            avg_volume_ratio_20: 1.1,
            instrument_relative_5d_pct: 4.5,
            instrument_relative_20d_pct: 5.5,
          },
        ],
      },
      engine_note: 'concept evidence only',
    } })
  })

  await page.goto('/')
  await page.getByRole('button', { name: '运行谐波分析' }).click()
  const card = page.getByTestId('concept-context')
  await expect(card).toBeVisible()
  await expect(card.getByText('已解析 2/2')).toBeVisible()
  await expect(card.getByText('AI算力')).toBeVisible()
  await expect(card.getByText('国产芯片')).toBeVisible()
  await expect(card.getByText(/不是“题材评分”/)).toBeVisible()
  await expect(card.getByText(/不拥有 lifecycle/)).toBeVisible()
})
