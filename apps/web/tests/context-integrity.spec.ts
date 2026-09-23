import { expect, test } from '@playwright/test'

test('context integrity surfaces freshness and conflicts without turning them into a score', async ({ page }) => {
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
      context_integrity: {
        as_of_trade_date: '2026-09-18',
        summary_state: 'issues_present',
        is_score: false,
        mutates_harmonic_identity: false,
        mutates_source_raw_prz: false,
        owns_lifecycle: false,
        layers: [
          { layer: 'execution', state: 'unresolved', evidence_date: '2026-09-18', source: 'akshare_stock_tfp_em', coverage: 'partial', reason: '特殊事件例外没有完整来源证明。' },
          { layer: 'market', state: 'stale', evidence_date: '2026-09-17', source: 'local_core_benchmarks', coverage: '4/4', reason: '至少一个核心指数尚未更新到分析交易日。' },
          { layer: 'industry', state: 'conflicted', evidence_date: '2026-09-18', source: 'akshare_eastmoney_industry', coverage: null, reason: '同一来源返回多个行业，系统拒绝自动选择。' },
          { layer: 'concept', state: 'current', evidence_date: '2026-09-18', source: 'akshare_eastmoney_concept', coverage: '2/2', reason: '全部已映射概念快照均对齐分析交易日。' },
        ],
      },
      engine_note: 'context integrity is not a score',
    } })
  })

  await page.goto('/')
  await page.getByRole('button', { name: '运行谐波分析' }).click()
  await page.getByRole('button', { name: '市场环境' }).click()
  const card = page.getByTestId('context-integrity')
  await expect(card).toBeVisible()
  await expect(card.getByText('存在上下文缺口 / 时钟不一致')).toBeVisible()
  await expect(page.getByTestId('context-integrity-execution')).toHaveAttribute('data-state', 'unresolved')
  await expect(page.getByTestId('context-integrity-market')).toHaveAttribute('data-state', 'stale')
  await expect(page.getByTestId('context-integrity-industry')).toHaveAttribute('data-state', 'conflicted')
  await expect(page.getByTestId('context-integrity-concept')).toHaveAttribute('data-state', 'current')
  await expect(card.getByText(/这不是评分，也不会生成买卖信号/)).toBeVisible()
})
