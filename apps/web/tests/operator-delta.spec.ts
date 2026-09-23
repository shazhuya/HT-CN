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

function item(
  lifecycle: string,
  action: string,
  nextKey: number,
) {
  return {
    display_key: 'SSE.600000:bat:XABCD:bullish:S5:2026-09-01-2026-09-02-2026-09-03-2026-09-04',
    instrument_id: 'SSE.600000',
    last_trade_date: '2026-09-18',
    price_mode: 'qfq',
    warning: null,
    pattern_id: 'bat',
    schema: 'XABCD',
    direction: 'bullish',
    scale: 5,
    pattern_state: 'forming',
    action_state: action,
    workflow_bucket_order: action === 'reaction_observation' ? 1 : 2,
    lifecycle_state: lifecycle,
    state_reason: 'source backed',
    current_position: '当前产品状态',
    first_watch: '先看下一关键条件',
    next_watch: '到了再继续观察',
    upgrade_blocker: '没有 Source-backed 条件不能升级',
    next_key_price: nextKey,
    next_key_price_role: lifecycle === 't_plus_1'
      ? 'type_i_38_2_target'
      : 'source_prz_entry_edge',
    execution_context_gate: 'tradable',
    context_cautions: [],
    source_prz_low: 95,
    source_prz_high: 100,
    bars_since_terminal: lifecycle === 't_plus_1' ? 1 : null,
    is_trade_instruction: false,
    predictive_score_used: false,
    alpha_inference_allowed: false,
  }
}

function queue(asOf: string, row: ReturnType<typeof item>) {
  return {
    schema_version: 2,
    as_of_trade_date: asOf,
    observed_trade_dates: [asOf],
    observation_integrity: 'single_as_of',
    contract,
    instrument_count: 1,
    analyzed_instrument_count: 1,
    failed_instrument_count: 0,
    candidate_count: 1,
    candidate_instrument_count: 1,
    action_state_counts: { [row.action_state]: 1 },
    lifecycle_state_counts: { [row.lifecycle_state]: 1 },
    items: [row],
    errors: [],
  }
}

test('M5 operator delta shows daily lifecycle and next-key changes', async ({ page }) => {
  const previous = queue(
    '2026-09-17',
    item('approaching_source_prz', 'waiting', 100),
  )
  const current = queue(
    '2026-09-18',
    item('t_plus_1', 'reaction_observation', 112.5),
  )

  await page.addInitScript((snapshot) => {
    localStorage.setItem(
      'htcn.operator.queue.current.v2',
      JSON.stringify(snapshot),
    )
  }, previous)

  await page.route('**/api/health', async (route) => {
    await route.fulfill({
      json: { status: 'ok', service: 'ht-cn-api', version: '0.4.0' },
    })
  })
  await page.route('**/api/instruments?**', async (route) => {
    await route.fulfill({
      json: {
        count: 1,
        items: [{ instrument_id: 'SSE.600000', has_qfq_factor: true }],
      },
    })
  })
  await page.route('**/api/operator/queue?**', async (route) => {
    await route.fulfill({ json: current })
  })
  await page.route('**/api/operator/delta', async (route) => {
    const post = route.request().postDataJSON() as {
      previous: typeof previous
      current: typeof current
    }
    expect(post.previous.as_of_trade_date).toBe('2026-09-17')
    expect(post.current.as_of_trade_date).toBe('2026-09-18')
    await route.fulfill({
      json: {
        schema_version: 1,
        contract: {
          version: 1,
          semantics: 'product_observation_only',
          authoritative_transition: false,
          writes_m4_evidence: false,
          predictive_score_used: false,
          historical_outcome_used: false,
          alpha_inference_allowed: false,
          is_trade_instruction: false,
          mutates_harmonic_identity: false,
          mutates_source_raw_prz: false,
          owns_lifecycle: false,
        },
        previous_as_of_trade_date: '2026-09-17',
        current_as_of_trade_date: '2026-09-18',
        status: 'ready',
        change_count: 1,
        change_type_counts: {
          action_state_changed: 1,
          lifecycle_state_changed: 1,
          next_key_changed: 1,
        },
        changes: [{
          display_key: current.items[0].display_key,
          instrument_id: 'SSE.600000',
          change_types: [
            'action_state_changed',
            'lifecycle_state_changed',
            'next_key_changed',
          ],
          previous: {
            ...previous.items[0],
          },
          current: {
            ...current.items[0],
          },
        }],
        comparison_incomplete_instruments: [],
        warnings: [],
      },
    })
  })

  await page.goto('/')
  await page.getByRole('button', { name: '机会发现' }).click()

  const delta = page.getByLabel('operator-delta')
  await expect(delta.getByRole('heading', { name: '今日变化' })).toBeVisible()
  await expect(delta.getByText('2026-09-17')).toBeVisible()
  await expect(delta.getByText('2026-09-18')).toBeVisible()
  await expect(delta.getByText('生命周期变化')).toBeVisible()
  await expect(delta.getByText('下一关键价变化')).toBeVisible()
  await expect(delta.getByText('112.50')).toBeVisible()

  await delta.getByRole('button', { name: 'SSE.600000' }).click()
  await expect(
    page.getByRole('textbox', { name: '搜索股票' }),
  ).toHaveValue('SSE.600000')
})
