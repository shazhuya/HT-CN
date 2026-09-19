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
  action_state_counts: { waiting: 2 },
  lifecycle_state_counts: { approaching_source_prz: 2 },
  items: [
    {
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
      action_state: 'waiting',
      workflow_bucket_order: 2,
      lifecycle_state: 'approaching_source_prz',
      state_reason: 'source backed',
      current_position: 'approaching',
      first_watch: 'watch',
      next_watch: 'next',
      upgrade_blocker: 'blocker',
      next_key_price: 100,
      next_key_price_role: 'source_prz_entry_edge',
      execution_context_gate: 'tradable',
      context_cautions: [],
      source_prz_low: 95,
      source_prz_high: 100,
      bars_since_terminal: null,
    },
    {
      display_key: 'SSE.600000:bat:XABCD:bullish:S5:2026-09-02',
      instrument_id: 'SSE.600000',
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
      current_position: 'approaching',
      first_watch: 'watch',
      next_watch: 'next',
      upgrade_blocker: 'blocker',
      next_key_price: 80,
      next_key_price_role: 'source_prz_entry_edge',
      execution_context_gate: 'tradable',
      context_cautions: [],
      source_prz_low: 75,
      source_prz_high: 80,
      bars_since_terminal: null,
    },
  ],
  errors: [],
}

const historyPayload = {
  schema_version: 1,
  contract: { version: 1, semantics: 'product_observation_only' },
  filter: {},
  observation_count: 1,
  observations: [{
    trade_date: '2026-09-18',
    observation_id: 'a'.repeat(64),
    revision_ordinal: 1,
    source_generated_at_utc: '2026-09-18T09:00:00+00:00',
    previous_recorded_trade_date: '2026-09-17',
    queue_candidate_count: 2,
    delta_total_change_count: 3,
    item_count: 2,
    items: [],
    change_count: 0,
    changes: [],
    delta_status: 'ready',
    comparison_incomplete_instruments: [],
  }],
  authoritative_evidence: false,
  writes_m4_evidence: false,
  historical_outcome_used_for_ranking: false,
  alpha_inference_allowed: false,
  is_trade_instruction: false,
}

const allSections = [
  {
    workflow_bucket: 'execution_evaluation',
    change_count: 1,
    items: [{
      display_key: 'k1',
      instrument_id: 'SSE.688256',
      review_bucket: 'execution_evaluation',
      change_types: ['action_state_changed', 'lifecycle_state_changed'],
      previous: {
        action_state: 'reaction_observation',
        lifecycle_state: 't_plus_1',
        next_key_price: 100,
      },
      current: {
        action_state: 'execution_evaluation',
        lifecycle_state: 'type_i_confirmed',
        next_key_price: 118,
      },
    }],
  },
  {
    workflow_bucket: 'reaction_observation',
    change_count: 1,
    items: [{
      display_key: 'k2',
      instrument_id: 'SSE.600000',
      review_bucket: 'reaction_observation',
      change_types: ['next_key_changed'],
      previous: {
        action_state: 'reaction_observation',
        lifecycle_state: 't_plus_1',
        next_key_price: 80,
      },
      current: {
        action_state: 'reaction_observation',
        lifecycle_state: 't_plus_1',
        next_key_price: 86,
      },
    }],
  },
  {
    workflow_bucket: 'disappeared_candidate',
    change_count: 1,
    items: [{
      display_key: 'gone',
      instrument_id: 'SSE.600009',
      review_bucket: 'disappeared_candidate',
      change_types: ['disappeared_candidate'],
      previous: {
        action_state: 'waiting',
        lifecycle_state: 'waiting_terminal',
        next_key_price: 20,
      },
      current: null,
    }],
  },
]

function digest(filtered = false) {
  const addReview = (section: typeof allSections[number]) => ({
    ...section,
    items: section.items.map((item) => ({
      ...item,
      review: {
        review_state: 'unseen',
        note: '',
        current_event_id: null,
        active_follow_up: false,
        active_follow_up_event_id: null,
        active_follow_up_origin_observation_id: null,
        active_follow_up_origin_trade_date: null,
      },
    })),
  })
  const fullSections = allSections.map(addReview)
  const sections = filtered ? [addReview(allSections[1])] : fullSections
  return {
    schema_version: 1,
    status: 'changes_ready',
    review_ready: true,
    trade_date: '2026-09-18',
    source_observation_id: 'a'.repeat(64),
    source_revision_ordinal: 1,
    previous_recorded_trade_date: '2026-09-17',
    delta_status: 'ready',
    change_count: 3,
    change_type_counts: {
      disappeared_candidate: 1,
      action_state_changed: 1,
      lifecycle_state_changed: 1,
      next_key_changed: 1,
    },
    workflow_bucket_counts: {
      execution_evaluation: 1,
      reaction_observation: 1,
      disappeared_candidate: 1,
    },
    workflow_sections: fullSections,
    filtered_change_count: filtered ? 1 : 3,
    filtered_workflow_sections: sections,
    analysis_incomplete_count: 0,
    analysis_incomplete_instruments: [],
    source_change_count_unchanged: 3,
    review_state_counts: {
      unseen: 3,
      reviewed: 0,
      follow_up: 0,
    },
    active_follow_ups: [],
    active_follow_up_count: 0,
    active_follow_up_in_current_digest_count: 0,
    source_review_state_counts_unchanged: {
      unseen: 3,
      reviewed: 0,
      follow_up: 0,
    },
    source_active_follow_up_count_unchanged: 0,
    authoritative_evidence: false,
    writes_m4_evidence: false,
    historical_outcome_used_for_ranking: false,
    predictive_score_used: false,
    alpha_inference_allowed: false,
    is_trade_instruction: false,
  }
}

test('M5 daily review digest keeps source totals while presentation filters drill down', async ({ page }) => {
  await page.route('**/api/health', async (route) => {
    await route.fulfill({
      json: { status: 'ok', service: 'ht-cn-api', version: '0.4.0' },
    })
  })
  await page.route('**/api/instruments?**', async (route) => {
    await route.fulfill({
      json: {
        count: 2,
        items: [
          { instrument_id: 'SSE.688256', has_qfq_factor: true },
          { instrument_id: 'SSE.600000', has_qfq_factor: true },
        ],
      },
    })
  })
  await page.route('**/api/operator/queue?**', async (route) => {
    await route.fulfill({ json: queuePayload })
  })
  await page.route('**/api/operator/history?**', async (route) => {
    await route.fulfill({ json: historyPayload })
  })
  await page.route('**/api/operator/review-session**', async (route) => {
    const url = new URL(route.request().url())
    const workflow = url.searchParams.get('workflow_bucket')
    const changeType = url.searchParams.get('change_type')
    const instrument = url.searchParams.get('instrument_id')
    if (workflow || changeType || instrument) {
      expect(workflow).toBe('reaction_observation')
      expect(changeType).toBe('next_key_changed')
      expect(instrument).toBe('SSE.600000')
      await route.fulfill({ json: digest(true) })
    } else {
      await route.fulfill({ json: digest(false) })
    }
  })

  await page.goto('/')

  const review = page.getByLabel('daily-review-digest')
  await expect(
    review.getByRole('heading', { name: '每日变化复盘' }),
  ).toBeVisible()
  await expect(review.getByText('工作状态变化 1')).toBeVisible()
  await expect(review.getByText('下一关键价变化 1')).toBeVisible()

  const summary = review.locator('.daily-review-digest__summary')
  await expect(summary.getByText('源变化总数').locator('..')).toContainText('3')
  await expect(summary.getByText('当前筛选命中').locator('..')).toContainText('3')

  await review.getByLabel('工作流').selectOption('reaction_observation')
  await review.getByLabel('变化类型').selectOption('next_key_changed')
  await review.getByPlaceholder('例如 SSE.688256').fill('SSE.600000')
  await review.getByRole('button', { name: '应用筛选' }).click()

  await expect(summary.getByText('源变化总数').locator('..')).toContainText('3')
  await expect(summary.getByText('当前筛选命中').locator('..')).toContainText('1')
  await expect(
    review.getByRole('button', { name: 'SSE.600000' }),
  ).toBeVisible()
  await expect(
    review.getByRole('button', { name: 'SSE.688256' }),
  ).toHaveCount(0)

  await review.getByRole('button', { name: 'SSE.600000' }).click()
  await expect(
    page.getByLabel('analysis-controls').locator('input[list="instrument-list"]'),
  ).toHaveValue('SSE.600000')
})
