import { expect, test } from '@playwright/test'

test('M9.5 product runtime exposes verified release and supervised zero-Vite operation', async ({ page }) => {
  await page.route('**/api/health', async (route) => {
    await route.fulfill({ json: { status: 'ok', service: 'ht-cn-api', version: '0.4.0' } })
  })
  await page.route('**/api/instruments?**', async (route) => {
    await route.fulfill({ json: { count: 0, items: [] } })
  })
  await page.route('**/api/product/status', async (route) => {
    await route.fulfill({
      json: {
        status: 'healthy',
        healthy: true,
        release_identity: {
          head: '1234567890abcdef1234567890abcdef12345678',
          worktree_clean: true,
          source: 'release_manifest',
        },
        children: {
          api: { status: 'running' },
          web: { status: 'running' },
          market_data: { status: 'running' },
          harmonic_runtime: { status: 'running' },
          background_evidence: { status: 'running' },
        },
        static_web: {
          mode: 'built_static',
          vite_required: false,
        },
        diagnostics_zh: ['HT-CN 产品运行层正常。'],
      },
    })
  })
  await page.route('**/api/market-data/status', async (route) => {
    await route.fulfill({ json: { status: 'idle_current', healthy: true, last_success_trade_date: '2026-09-22' } })
  })
  await page.route('**/api/harmonic/runtime/status', async (route) => {
    await route.fulfill({ json: { status: 'idle_current', healthy: true, last_success_trade_date: '2026-09-22' } })
  })
  await page.route('**/api/evidence/status', async (route) => {
    await route.fulfill({
      json: {
        status: 'healthy',
        healthy: true,
        operational_fault: false,
        evidence_insufficient: true,
        calibration_state: 'disabled_insufficient_evidence',
      },
    })
  })

  await page.goto('/')
  await page.getByRole('button', { name: '系统状态' }).click()

  const card = page.getByTestId('product-supervisor-card')
  await expect(card).toContainText('产品运行层')
  await expect(card).toContainText('运行正常')
  await expect(card).toContainText('release 1234567890 · verified package')
  await expect(card).toContainText('5/5 服务运行 · built Web / 无 Vite')
  await expect(card).toHaveAttribute('data-healthy', 'true')
  await expect(page.getByText('Supervisor 只管理进程和恢复')).toBeVisible()
})
