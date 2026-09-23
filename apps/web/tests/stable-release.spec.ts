import { expect, test } from '@playwright/test'

test('Stable v1.0.0 exposes one version and keeps statistical claims unavailable', async ({ page }) => {
  await page.route('**/api/health', async (route) => {
    await route.fulfill({ json: { status: 'ok', service: 'ht-cn-api', version: '1.0.0' } })
  })
  await page.route('**/api/instruments?**', async (route) => {
    await route.fulfill({ json: { count: 0, items: [] } })
  })
  await page.route('**/api/product/status', async (route) => {
    await route.fulfill({ json: {
      status: 'healthy', healthy: true,
      release_identity: { head: '1234567890abcdef1234567890abcdef12345678', worktree_clean: true, source: 'release_manifest' },
      children: {
        api: { status: 'running' }, web: { status: 'running' }, market_data: { status: 'running' },
        harmonic_runtime: { status: 'running' }, background_evidence: { status: 'running' },
      },
    } })
  })
  await page.route('**/api/market-data/status', async (route) => {
    await route.fulfill({ json: { status: 'idle_current', healthy: true } })
  })
  await page.route('**/api/harmonic/runtime/status', async (route) => {
    await route.fulfill({ json: { status: 'idle_current', healthy: true } })
  })
  await page.route('**/api/evidence/status', async (route) => {
    await route.fulfill({ json: {
      status: 'healthy', healthy: true, evidence_insufficient: true,
      evidence_state: 'insufficient_evidence', calibration_state: 'disabled_insufficient_evidence',
      prospective_candidate_count: 14, outcome_snapshot_count: 14,
    } })
  })

  await page.goto('/')
  await page.getByLabel('应用导航').getByRole('button', { name: '系统状态', exact: true }).click()
  await expect(page.getByRole('heading', { name: '系统状态' })).toBeVisible()
  await expect(page.getByText('API 1.0.0')).toBeVisible()
  const evidence = page.getByTestId('evidence-runtime-card')
  await expect(evidence).toContainText('证据积累中')
  await expect(evidence).toContainText('M8 未启用 · 统计证据不足')
  await expect(evidence).not.toContainText('%')
})
