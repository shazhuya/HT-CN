import fs from 'node:fs'
import { expect, test } from '@playwright/test'

type LivePattern = {
  pattern_id: string
  state: 'forming' | 'completed'
  scale: number
  is_primary_identity?: boolean
  frontier?: boolean
  points: Array<{ index: number }>
}

type LiveAnalysis = {
  instrument_id: string
  price_mode: string
  warning: string | null
  bars_requested: number
  bars_returned: number
  first_trade_date: string
  last_trade_date: string
  scales: number[]
  completed: LivePattern[]
  forming: LivePattern[]
}

const API = 'http://127.0.0.1:8765'
const PRIORITY = ['SSE.688256', 'SZSE.300820', 'SSE.600519']

async function findLiveCandidate(request: import('@playwright/test').APIRequestContext) {
  const instrumentsResponse = await request.get(`${API}/api/instruments?limit=1000`)
  expect(instrumentsResponse.ok()).toBeTruthy()
  const instruments = (await instrumentsResponse.json()) as {
    items?: Array<{ instrument_id: string; has_qfq_factor: boolean }>
  }

  const qfqIds = (instruments.items ?? [])
    .filter((item) => item.has_qfq_factor)
    .map((item) => item.instrument_id)
  const ordered = [
    ...PRIORITY.filter((id) => qfqIds.includes(id)),
    ...qfqIds.filter((id) => !PRIORITY.includes(id)),
  ]

  for (const instrumentId of ordered.slice(0, 24)) {
    const response = await request.get(
      `${API}/api/harmonic/${encodeURIComponent(instrumentId)}?bars=420&scales=3,5,8,13`,
    )
    if (!response.ok()) continue
    const analysis = (await response.json()) as LiveAnalysis
    if (analysis.price_mode.startsWith('qfq') && analysis.bars_returned >= 80) {
      return { instrumentId, analysis }
    }
  }
  throw new Error('No live local QFQ instrument with at least 80 bars was available for M3 visual acceptance')
}

test('HT-CN M3 live local QFQ workbench renders real repository data', async ({ page, request }) => {
  const { instrumentId, analysis } = await findLiveCandidate(request)

  // Forming is live/frontier semantics: each pivot scale contributes at most one XABC node set.
  const formingNodeSets = new Set(analysis.forming.map((pattern) => pattern.points.map((point) => point.index).join('-')))
  expect(formingNodeSets.size).toBeLessThanOrEqual(analysis.scales.length)
  expect(analysis.forming.every((pattern) => pattern.frontier !== false)).toBeTruthy()

  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'A 股谐波研究与辅助决策系统' })).toBeVisible()
  await expect(page.getByText(/API 0\.3\.0/)).toBeVisible()

  const symbolInput = page.locator('input[list="instrument-list"]')
  await symbolInput.fill(instrumentId)
  await page.locator('select').selectOption('420')

  const browserResponsePromise = page.waitForResponse(
    (response) =>
      response.url().includes(`/api/harmonic/${encodeURIComponent(instrumentId)}?`) && response.status() === 200,
  )
  await page.getByRole('button', { name: '运行谐波分析' }).click()
  const browserResponse = await browserResponsePromise
  const browserAnalysis = (await browserResponse.json()) as LiveAnalysis

  expect(browserAnalysis.instrument_id).toBe(instrumentId)
  expect(browserAnalysis.price_mode.startsWith('qfq')).toBeTruthy()
  expect(browserAnalysis.bars_returned).toBeGreaterThanOrEqual(80)
  expect(browserAnalysis.bars_returned).toBe(analysis.bars_returned)
  expect(browserAnalysis.first_trade_date).toBe(analysis.first_trade_date)
  expect(browserAnalysis.last_trade_date).toBe(analysis.last_trade_date)

  await expect(page.getByText(instrumentId, { exact: true })).toBeVisible()
  await expect(page.getByText(`${analysis.first_trade_date} → ${analysis.last_trade_date}`, { exact: true })).toBeVisible()
  await expect(page.getByText(`${analysis.bars_returned} / 420`, { exact: true })).toBeVisible()
  await expect(page.getByLabel('harmonic-chart')).toBeVisible()
  await expect(page.getByText(/当前显示 \d+ \/ \d+ 个身份/)).toBeVisible()

  const outDir = '../../artifacts/screenshots'
  fs.mkdirSync(outDir, { recursive: true })
  await page.screenshot({ path: `${outDir}/m2-harmonic-workbench-live.png`, fullPage: true })
})
