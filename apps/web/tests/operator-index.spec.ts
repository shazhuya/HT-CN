import { expect, test } from '@playwright/test'

const contract = {
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
}

function makeItem(index: number) {
  const code = String(index).padStart(6, '0')
  const execution = index > 55
  return {
    display_key: `SSE.${code}:bat:XABCD:bullish:S5:2026-09-01-2026-09-02-2026-09-03-2026-09-04`,
    instrument_id: `SSE.${code}`,
    last_trade_date: '2026-09-18',
    price_mode: 'qfq',
    warning: null,
    pattern_id: 'bat',
    schema: 'XABCD',
    direction: 'bullish',
    scale: 5,
    pattern_state: 'forming',
    action_state: execution ? 'execution_evaluation' : 'waiting',
    workflow_bucket_order: execution ? 0 : 2,
    lifecycle_state: execution ? 'type_i_confirmed' : 'approaching_source_prz',
    state_reason: 'source backed',
    current_position: execution ? 'Type-I confirmed' : 'Approaching PRZ',
    first_watch: 'first watch',
    next_watch: 'next watch',
    upgrade_blocker: 'blocker',
    next_key_price: 100 + index,
    next_key_price_role: execution
      ? 'type_i_61_8_target'
      : 'source_prz_entry_edge',
    execution_context_gate: 'tradable',
    context_cautions: [],
    source_prz_low: 95,
    source_prz_high: 100,
    bars_since_terminal: execution ? 3 : null,
    is_trade_instruction: false,
    predictive_score_used: false,
    alpha_inference_allowed: false,
  }
}

const items = Array.from({ length: 60 }, (_, offset) => makeItem(offset + 1))

const queuePayload = {
  schema_version: 2,
  as_of_trade_date: '2026-09-18',
  observed_trade_dates: ['2026-09-18'],
  observation_integrity: 'single_as_of',
  contract,
  instrument_count: 5000,
  analyzed_instrument_count: 5000,
  failed_instrument_count: 0,
  candidate_count: items.length,
  candidate_instrument_count: items.length,
  action_state_counts: {
    execution_evaluation: 5,
    waiting: 55,
  },
  lifecycle_state_counts: {
    type_i_confirmed: 5,
    approaching_source_prz: 55,
  },
  items,
  errors: [],
  operator_index: {
    schema_version: 1,
    universe_scope: 'all_initialized_local_instruments',
    universe_instrument_count: 5000,
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
    cache_path: 'data/product/m5/operator_queue/full.json',
    generated_at_utc: '2026-09-18T08:00:00+00:00',
    authoritative_evidence: false,
    writes_m4_evidence: false,
  },
}

test('M5 full-universe operator index paginates and filters presentation only', async ({ page }) => {
  await page.route('**/api/health', async (route) => {
    await route.fulfill({
      json: { status: 'ok', service: 'ht-cn-api', version: '0.4.0' },
    })
  })
  await page.route('**/api/instruments?**', async (route) => {
    const url = new URL(route.request().url())
    expect(url.searchParams.get('limit')).toBe('10000')
    await route.fulfill({
      json: {
        count: 5000,
        items: items.map((item) => ({
          instrument_id: item.instrument_id,
          has_qfq_factor: true,
        })),
      },
    })
  })
  await page.route('**/api/operator/queue?**', async (route) => {
    const url = new URL(route.request().url())
    expect(url.searchParams.has('limit')).toBe(false)
    await route.fulfill({ json: queuePayload })
  })

  await page.goto('/')
  await page.getByRole('button', { name: '机会发现' }).click()

  const queue = page.getByLabel('operator-queue')
  await expect(
    queue.getByText('扫描范围：完整本地初始化 universe'),
  ).toBeVisible()
  await expect(queue.getByText('5000 只标的')).toBeVisible()

  const controls = page.getByLabel('operator-index-controls')
  await expect(controls.getByText(/匹配/)).toContainText('60')
  await expect(controls.getByText(/页码/)).toContainText('1 / 2')

  await expect(
    queue.getByRole('button', { name: 'SSE.000050' }),
  ).toBeVisible()
  await expect(
    queue.getByRole('button', { name: 'SSE.000051' }),
  ).toHaveCount(0)

  await controls.getByRole('button', { name: '下一页' }).click()
  await expect(
    queue.getByRole('button', { name: 'SSE.000051' }),
  ).toBeVisible()
  await expect(controls.getByText(/页码/)).toContainText('2 / 2')

  await controls.getByPlaceholder('代码 / 形态 / 生命周期').fill('SSE.000060')
  await expect(controls.getByText(/匹配/)).toContainText('1')
  await expect(controls.getByText(/页码/)).toContainText('1 / 1')
  await expect(
    queue.getByRole('button', { name: 'SSE.000060' }),
  ).toBeVisible()

  await controls.getByPlaceholder('代码 / 形态 / 生命周期').fill('')
  await controls.getByLabel('工作状态').selectOption('execution_evaluation')
  await expect(controls.getByText(/匹配/)).toContainText('5')
  await expect(
    queue.getByRole('heading', { name: '执行评估' }),
  ).toBeVisible()
  await expect(
    queue.getByRole('heading', { name: '等待' }),
  ).toHaveCount(0)
})
