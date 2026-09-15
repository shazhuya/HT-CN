import { expect, test } from '@playwright/test'

test('HT-CN M0 shell renders', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'A 股谐波研究与辅助决策系统' })).toBeVisible()
  await expect(page.getByText('本地优先 · 零订阅 · Agent First')).toBeVisible()
})
