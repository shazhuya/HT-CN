import { expect, test } from '@playwright/test'

const queue = {
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
  instrument_count: 1,
  analyzed_instrument_count: 1,
  failed_instrument_count: 0,
  candidate_count: 1,
  candidate_instrument_count: 1,
  action_state_counts: { reaction_observation: 1 },
  lifecycle_state_counts: { t_plus_1: 1 },
  items: [{
    display_key: 'SSE.688256:bat:XABCD:bullish:S5:2026-09-01',
    instrument_id: 'SSE.688256',
    last_trade_date: '2026-09-18',
    price_mode: 'qfq',
    warning: null,
    pattern_id: 'bat',
    schema: 'XABCD',
    direction: 'bullish',
    scale: 5,
    pattern_state: 'forming',
    action_state: 'reaction_observation',
    workflow_bucket_order: 1,
    lifecycle_state: 't_plus_1',
    state_reason: 'source backed',
    current_position: 'T+1',
    first_watch: '观察反应',
    next_watch: 'T1',
    upgrade_blocker: '无确认不升级',
    next_key_price: 112.5,
    next_key_price_role: 'type_i_38_2_target',
    execution_context_gate: 'tradable',
    context_cautions: [],
    source_prz_low: 95,
    source_prz_high: 100,
    bars_since_terminal: 1,
  }],
  errors: [],
}

function historyPayload(filtered: boolean) {
  return {
    schema_version: 1,
    contract: {
      version: 1,
      semantics: 'product_observation_only',
      append_only: true,
      authoritative_transition: false,
      writes_m4_evidence: false,
      predictive_score_used: false,
      historical_outcome_used_for_ranking: false,
      alpha_inference_allowed: false,
      is_trade_instruction: false,
      mutates_harmonic_identity: false,
      mutates_source_raw_prz: false,
      owns_lifecycle: false,
    },
    observation_count: 2,
    observations: [
      {
        trade_date: '2026-09-18',
        observation_id: 'b'.repeat(64),
        revision_ordinal: 2,
        source_generated_at_utc: '2026-09-18T09:00:00+00:00',
        previous_recorded_trade_date: '2026-09-17',
        queue_candidate_count: 123,
        delta_total_change_count: 9,
        item_count: filtered ? 1 : 123,
        items: filtered ? [{ instrument_id: 'SSE.688256', lifecycle_state: 't_plus_1', action_state: 'reaction_observation' }] : [],
        change_count: filtered ? 1 : 9,
        changes: filtered ? [{
          display_key: queue.items[0].display_key,
          instrument_id: 'SSE.688256',
          change_types: ['lifecycle_state_changed', 'next_key_changed'],
          previous: { lifecycle_state: 'waiting_terminal' },
          current: { lifecycle_state: 't_plus_1' },
        }] : [],
        delta_status: 'ready',
        comparison_incomplete_instruments: [],
      },
      {
        trade_date: '2026-09-17',
        observation_id: 'a'.repeat(64),
        revision_ordinal: 1,
        source_generated_at_utc: '2026-09-17T09:00:00+00:00',
        previous_recorded_trade_date: null,
        queue_candidate_count: 118,
        delta_total_change_count: 0,
        item_count: filtered ? 1 : 118,
        items: [],
        change_count: 0,
        changes: [],
        delta_status: 'baseline_no_previous_observation',
        comparison_incomplete_instruments: [],
      },
    ],
    authoritative_evidence: false,
    writes_m4_evidence: false,
    historical_outcome_used_for_ranking: false,
    alpha_inference_allowed: false,
    is_trade_instruction: false,
  }
}

test('M5 operator history shows append-only summaries and instrument changes', async ({ page }) => {
  await page.route('**/api/health', async (route) => {
    await route.fulfill({
      json: { status: 'ok', service: 'ht-cn-api', version: '0.4.0' },
    })
  })
  await page.route('**/api/instruments?**', async (route) => {
    await route.fulfill({
      json: {
        count: 1,
        items: [{ instrument_id: 'SSE.688256', has_qfq_factor: true }],
      },
    })
  })
  await page.route('**/api/operator/queue?**', async (route) => {
    await route.fulfill({ json: queue })
  })
  await page.route('**/api/operator/history?**', async (route) => {
    const url = new URL(route.request().url())
    const instrument = url.searchParams.get('instrument_id')
    if (instrument) {
      expect(instrument).toBe('SSE.688256')
      expect(url.searchParams.get('summary_only')).toBe('false')
      await route.fulfill({ json: historyPayload(true) })
    } else {
      expect(url.searchParams.get('summary_only')).toBe('true')
      await route.fulfill({ json: historyPayload(false) })
    }
  })

  await page.goto('/')

  const history = page.getByLabel('operator-history')
  await expect(
    history.getByRole('heading', { name: '跨日产品观察历史' }),
  ).toBeVisible()
  await expect(history.getByText('append-only 产品 journal')).toBeVisible()
  await expect(history.getByText('全部候选 123')).toBeVisible()
  await expect(history.getByText('当日总变化 9')).toBeVisible()

  await history
    .getByPlaceholder('输入证券代码，例如 SSE.688256')
    .fill('SSE.688256')
  await history.getByRole('button', { name: '查询历史' }).click()

  const latestDay = history.locator('.operator-history__day').first()
  await expect(latestDay.getByText('2026-09-18')).toBeVisible()
  await expect(latestDay.getByText('该标的候选 1')).toBeVisible()
  await expect(latestDay.getByText('生命周期变化 · 下一关键价变化')).toBeVisible()
  await expect(latestDay.getByText('waiting_terminal → t_plus_1')).toBeVisible()

  await latestDay.getByRole('button', { name: 'SSE.688256' }).click()
  await expect(
    page.getByLabel('analysis-controls').locator('input[list="instrument-list"]'),
  ).toHaveValue('SSE.688256')
})
