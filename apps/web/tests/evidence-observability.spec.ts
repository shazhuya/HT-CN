import { expect, test } from '@playwright/test'

test('M9.4 exposes evidence insufficiency without treating it as a product fault', async ({ page }) => {
  await page.route('**/api/health', async (route) => {
    await route.fulfill({ json: { status: 'ok', service: 'ht-cn-api', version: '0.4.0' } })
  })
  await page.route('**/api/instruments?**', async (route) => {
    await route.fulfill({ json: { count: 0, items: [] } })
  })
  await page.route('**/api/market-data/status', async (route) => {
    await route.fulfill({
      json: {
        status: 'idle_current',
        healthy: true,
        last_success_trade_date: '2026-09-22',
      },
    })
  })
  await page.route('**/api/harmonic/runtime/status', async (route) => {
    await route.fulfill({
      json: {
        status: 'idle_current',
        healthy: true,
        last_success_trade_date: '2026-09-22',
      },
    })
  })
  await page.route('**/api/evidence/status', async (route) => {
    await route.fulfill({
      json: {
        status: 'healthy',
        healthy: true,
        operational_state: 'healthy',
        operational_fault: false,
        evidence_state: 'insufficient_evidence',
        evidence_insufficient: true,
        calibration_state: 'disabled_insufficient_evidence',
        latest_committed_capture_date: '2026-09-21',
        prospective_candidate_count: 14,
        outcome_snapshot_count: 1,
        diagnostics_zh: [
          '产品运行正常，但前瞻样本仍不足；M8、胜率、Alpha 与盈利能力统计保持禁用。',
        ],
      },
    })
  })

  await page.goto('/')
  await page.getByLabel('应用导航').getByRole('button', { name: '系统状态', exact: true }).click()

  const card = page.getByTestId('evidence-runtime-card')
  await expect(card).toContainText('后台前瞻证据')
  await expect(card).toContainText('证据积累中')
  await expect(card).toContainText('capture 2026-09-21 · cohort 14 · outcome 1')
  await expect(card).toContainText('M8 未启用 · 统计证据不足')
  await expect(card).toHaveAttribute('data-healthy', 'true')
  await expect(card).toHaveAttribute('data-insufficient', 'true')
  await expect(card).not.toContainText('%')
  await expect(page.getByText('运行故障与证据不足分开显示')).toBeVisible()
})
