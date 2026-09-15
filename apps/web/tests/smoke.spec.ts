import fs from 'node:fs'
import { expect, test } from '@playwright/test'

const analysis = {
  instrument_id: 'SSE.688256',
  price_mode: 'qfq',
  warning: null,
  bars_requested: 420,
  bars_returned: 6,
  first_trade_date: '2026-09-08',
  last_trade_date: '2026-09-15',
  scales: [3, 5, 8, 13],
  bars: [
    { index: 0, trade_date: '2026-09-08', open: 100, high: 102, low: 99, close: 101, volume: 1000 },
    { index: 1, trade_date: '2026-09-09', open: 118, high: 121, low: 117, close: 120, volume: 1100 },
    { index: 2, trade_date: '2026-09-10', open: 109, high: 110, low: 107.5, close: 108, volume: 950 },
    { index: 3, trade_date: '2026-09-11', open: 115, high: 117, low: 114, close: 116.5, volume: 1050 },
    { index: 4, trade_date: '2026-09-14', open: 105, high: 106, low: 103.8, close: 104.3, volume: 1250 },
    { index: 5, trade_date: '2026-09-15', open: 106, high: 108, low: 105, close: 107, volume: 900 },
  ],
  completed: [
    {
      pattern_id: 'gartley',
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
        components: [
          { name: 'XA completion', price_low: 104.28, price_high: 104.28, ratio_low: 0.786, ratio_high: 0.786 },
          { name: 'BC projection', price_low: 102.1, price_high: 106.4, ratio_low: 1.13, ratio_high: 1.618 },
          { name: 'AB=CD x1', price_low: 104.28, price_high: 104.28, ratio_low: 1, ratio_high: 1 },
        ],
      },
      metrics: { b_xa: 0.618, c_ab: 0.728, bc_projection: 1.373, d_xa: 0.786, cd_ab: 1 },
    },
  ],
  forming: [],
  pivot_counts: { '3': 8, '5': 5, '8': 3, '13': 2 },
  engine_note: 'geometry_score 仅衡量几何贴合度，不代表胜率、预期收益或交易建议。',
}

test('HT-CN M2 harmonic workbench renders analysis and chart', async ({ page }) => {
  await page.route('**/api/health', async (route) => {
    await route.fulfill({ json: { status: 'ok', service: 'ht-cn-api', version: '0.2.0' } })
  })
  await page.route('**/api/instruments?**', async (route) => {
    await route.fulfill({ json: { count: 1, items: [{ instrument_id: 'SSE.688256', has_qfq_factor: true }] } })
  })
  await page.route('**/api/harmonic/SSE.688256?**', async (route) => {
    await route.fulfill({ json: analysis })
  })

  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'A 股谐波研究与辅助决策系统' })).toBeVisible()
  await expect(page.getByText('Carney 几何识别 · QFQ 连续价格 · 多尺度 Pivot · PRZ 审计')).toBeVisible()

  await page.getByRole('button', { name: '运行谐波分析' }).click()
  await expect(page.getByRole('heading', { name: 'Gartley · 已完成' })).toBeVisible()
  await expect(page.getByLabel('harmonic-chart')).toBeVisible()
  await expect(page.getByText('98.7')).toBeVisible()
  await expect(page.getByText('0.618')).toBeVisible()
  await expect(page.getByText('XA completion')).toBeVisible()

  const outDir = '../../artifacts/screenshots'
  fs.mkdirSync(outDir, { recursive: true })
  await page.screenshot({ path: `${outDir}/m2-harmonic-workbench.png`, fullPage: true })
})
