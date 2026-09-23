import { expect, test } from '@playwright/test'

const queuePayload = {
  schema_version: 2,
  as_of_trade_date: '2026-09-18',
  observed_trade_dates: ['2026-09-18'],
  observation_integrity: 'single_as_of',
  contract: {
    version: 1,
    source_of_truth: 'existing_source_lifecycle_and_decision_narrative',
    ranking_mode: 'workflow_bucket_only',
    predictive_score_used: false,
    historical_outcome_used: false,
    alpha_inference_allowed: false,
    is_trade_instruction: false,
    mutates_harmonic_identity: false,
    mutates_source_raw_prz: false,
    owns_lifecycle: false,
  },
  instrument_count: 2,
  analyzed_instrument_count: 2,
  failed_instrument_count: 0,
  candidate_count: 2,
  candidate_instrument_count: 2,
  action_state_counts: {
    execution_evaluation: 1,
    waiting: 1,
  },
  lifecycle_state_counts: {
    type_i_confirmed: 1,
    approaching_source_prz: 1,
  },
  items: [
    {
      display_key: 'SSE.600000:bat:XABCD:S5:1-2-3-4-5',
      instrument_id: 'SSE.600000',
      last_trade_date: '2026-09-18',
      price_mode: 'qfq',
      warning: null,
      pattern_id: 'bat',
      schema: 'XABCD',
      direction: 'bullish',
      scale: 5,
      pattern_state: 'completed',
      action_state: 'execution_evaluation',
      workflow_bucket_order: 0,
      lifecycle_state: 'type_i_confirmed',
      state_reason: 'source backed',
      current_position: 'Type-I 38.2% 早期反应已确认。',
      first_watch: '先看 61.8% 与首次离开 Source PRZ。',
      next_watch: '回到 Source PRZ 再看 Type-II。',
      upgrade_blocker: 'Type-I 不等于长期 reversal。',
      next_key_price: 12.34,
      next_key_price_role: 'type_i_61_8_target',
      execution_context_gate: 'tradable',
      context_cautions: [],
      source_prz_low: 9.8,
      source_prz_high: 10.1,
      bars_since_terminal: 3,
    },
    {
      display_key: 'SZSE.000002:crab:XABCD:S8:1-2-3-4',
      instrument_id: 'SZSE.000002',
      last_trade_date: '2026-09-18',
      price_mode: 'qfq',
      warning: null,
      pattern_id: 'crab',
      schema: 'XABCD',
      direction: 'bearish',
      scale: 8,
      pattern_state: 'forming',
      action_state: 'waiting',
      workflow_bucket_order: 2,
      lifecycle_state: 'approaching_source_prz',
      state_reason: 'source backed',
      current_position: '价格尚未进入 Source Raw PRZ。',
      first_watch: '先看 Source PRZ 入场边界。',
      next_watch: '进入后再看 terminal side。',
      upgrade_blocker: '未进入 PRZ 前不能视为完成。',
      next_key_price: 25.67,
      next_key_price_role: 'source_prz_entry_edge',
      execution_context_gate: 'tradable',
      context_cautions: ['market:stale — stale benchmark'],
      source_prz_low: 25.6,
      source_prz_high: 26.1,
      bars_since_terminal: null,
    },
  ],
  errors: [],
  operator_index: {
    schema_version: 1,
    universe_scope: 'all_initialized_local_instruments',
    universe_instrument_count: 2,
    presentation_does_not_define_universe: true,
    legacy_limit_ignored: null,
    authoritative_evidence: false,
    writes_m4_evidence: false,
  },
  product_cache: {
    schema_version: 1,
    contract_version: 1,
    status: 'hit',
    expected_local_trade_date: '2026-09-18',
    queue_as_of_trade_date: '2026-09-18',
    freshness: 'current',
    cache_path: 'data/product/m5/operator_queue/test.json',
    generated_at_utc: '2026-09-18T08:00:00+00:00',
    authoritative_evidence: false,
    writes_m4_evidence: false,
  },
}

test('M5 operator queue renders workflow buckets and selects an instrument', async ({ page }) => {
  await page.route('**/api/health', async (route) => {
    await route.fulfill({ json: { status: 'ok', service: 'ht-cn-api', version: '0.4.0' } })
  })
  await page.route('**/api/instruments?**', async (route) => {
    await route.fulfill({
      json: {
        count: 2,
        items: [
          { instrument_id: 'SSE.600000', has_qfq_factor: true },
          { instrument_id: 'SZSE.000002', has_qfq_factor: true },
        ],
      },
    })
  })
  let forceRefreshSeen = false
  await page.route('**/api/operator/queue?**', async (route) => {
    const url = new URL(route.request().url())
    const forceRefresh = url.searchParams.get('refresh') === 'true'
    if (forceRefresh) forceRefreshSeen = true
    await route.fulfill({
      json: {
        ...queuePayload,
        product_cache: {
          ...queuePayload.product_cache,
          status: forceRefresh ? 'rebuilt_force' : 'hit',
        },
      },
    })
  })

  await page.goto('/')
  await page.getByLabel('应用导航').getByRole('button', { name: '机会发现', exact: true }).click()

  await expect(page.getByRole('heading', { name: '机会发现' })).toBeVisible()
  await expect(page.getByRole('heading', { name: '今日观察队列' })).toBeVisible()
  await expect(page.getByText(/这是观察工作流顺序，不是收益率排名/)).toBeVisible()

  const queue = page.getByLabel('operator-queue')
  await expect(queue.getByRole('heading', { name: '执行评估' })).toBeVisible()
  await expect(queue.getByRole('heading', { name: '等待' })).toBeVisible()
  const queueBody = queue.locator('tbody')
  await expect(queueBody.getByText('Type-I 已确认', { exact: true })).toBeVisible()
  await expect(queueBody.getByText('接近 Source PRZ', { exact: true })).toBeVisible()
  await expect(queue.getByText('12.34')).toBeVisible()
  await expect(queue.getByText('25.67')).toBeVisible()
  await expect(queue.getByText('扫描范围：完整本地初始化 universe')).toBeVisible()
  await expect(queue.getByText(/Queue cache：/)).toBeVisible()
  await expect(queue.getByText('hit', { exact: true })).toBeVisible()

  await page.getByRole('button', { name: '刷新队列' }).click()
  await expect.poll(() => forceRefreshSeen).toBe(true)
  await expect(queue.getByText('rebuilt_force', { exact: true })).toBeVisible()

  await queue.getByRole('button', { name: 'SSE.600000' }).click()
  await expect(page.getByRole('textbox', { name: '搜索股票' })).toHaveValue('SSE.600000')
})


test('M5 operator index paginates locally without shrinking full queue', async ({ page }) => {
  const items = Array.from({ length: 60 }, (_, index) => {
    const suffix = String(index + 1).padStart(6, '0')
    return {
      display_key: `SSE.${suffix}:bat:XABCD:bullish:S5:2026-09-01-2026-09-02-2026-09-03-2026-09-04`,
      instrument_id: `SSE.${suffix}`,
      last_trade_date: '2026-09-18',
      price_mode: 'qfq',
      warning: null,
      pattern_id: 'bat',
      schema: 'XABCD',
      direction: 'bullish',
      scale: 5,
      pattern_state: 'forming',
      action_state: 'waiting',
      workflow_bucket_order: 2,
      lifecycle_state: 'approaching_source_prz',
      state_reason: 'source backed',
      current_position: '接近 Source PRZ',
      first_watch: '看 Source PRZ 入场边界',
      next_watch: '进入后再看 Terminal',
      upgrade_blocker: '未进入 Source PRZ',
      next_key_price: 100 + index,
      next_key_price_role: 'source_prz_entry_edge',
      execution_context_gate: 'tradable',
      context_cautions: [],
      source_prz_low: 95,
      source_prz_high: 100,
      bars_since_terminal: null,
    }
  })

  const payload = {
    ...queuePayload,
    instrument_count: 60,
    analyzed_instrument_count: 60,
    candidate_count: 60,
    candidate_instrument_count: 60,
    action_state_counts: { waiting: 60 },
    lifecycle_state_counts: { approaching_source_prz: 60 },
    items,
    operator_index: {
      ...queuePayload.operator_index,
      universe_instrument_count: 60,
    },
  }

  await page.route('**/api/health', async (route) => {
    await route.fulfill({
      json: { status: 'ok', service: 'ht-cn-api', version: '0.4.0' },
    })
  })
  await page.route('**/api/instruments?**', async (route) => {
    await route.fulfill({
      json: {
        count: 60,
        items: items.map((item) => ({
          instrument_id: item.instrument_id,
          has_qfq_factor: true,
        })),
      },
    })
  })

  let queueRequests = 0
  await page.route('**/api/operator/queue?**', async (route) => {
    queueRequests += 1
    const url = new URL(route.request().url())
    expect(url.searchParams.has('limit')).toBe(false)
    await route.fulfill({ json: payload })
  })

  await page.goto('/')
  await page.getByLabel('应用导航').getByRole('button', { name: '机会发现', exact: true }).click()

  const queue = page.getByLabel('operator-queue')
  const controls = page.getByLabel('operator-index-controls')
  await expect(queue.getByText('60 只标的')).toBeVisible()
  await expect(controls.getByText(/匹配/)).toContainText('60')
  await expect(controls.getByText(/页码/)).toContainText('1 / 2')
  await expect(queue.locator('tbody tr')).toHaveCount(50)
  const initialQueueRequests = queueRequests
  expect(initialQueueRequests).toBeGreaterThan(0)

  await controls.getByRole('button', { name: '下一页' }).click()
  await expect(controls.getByText(/页码/)).toContainText('2 / 2')
  await expect(queue.locator('tbody tr')).toHaveCount(10)
  await expect(queue.getByRole('button', { name: 'SSE.000060' })).toBeVisible()
  expect(queueRequests).toBe(initialQueueRequests)

  await controls.getByPlaceholder('代码 / 形态 / 生命周期').fill('SSE.000060')
  await expect(controls.getByText(/匹配/)).toContainText('1')
  await expect(controls.getByText(/页码/)).toContainText('1 / 1')
  await expect(queue.locator('tbody tr')).toHaveCount(1)
  await expect(queue.getByRole('button', { name: 'SSE.000060' })).toBeVisible()
  expect(queueRequests).toBe(initialQueueRequests)
})
