import { expect, test } from '@playwright/test'

const key = 'SSE.688256:bat:XABCD:bullish:S5:2026-09-01'
const observationId = 'a'.repeat(64)

const queue = {
  schema_version: 2,
  as_of_trade_date: '2026-09-19',
  observed_trade_dates: ['2026-09-19'],
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
    display_key: key,
    instrument_id: 'SSE.688256',
    last_trade_date: '2026-09-19',
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

const history = {
  schema_version: 1,
  contract: { version: 1, semantics: 'product_observation_only' },
  filter: {},
  observation_count: 1,
  observations: [{
    trade_date: '2026-09-19',
    observation_id: observationId,
    revision_ordinal: 1,
    source_generated_at_utc: '2026-09-19T01:00:00+00:00',
    previous_recorded_trade_date: '2026-09-18',
    queue_candidate_count: 1,
    delta_total_change_count: 1,
    item_count: 1,
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

function session(saved: boolean) {
  const review = saved
    ? {
        review_state: 'follow_up',
        note: '继续观察下一关键价',
        current_event_id: 'b'.repeat(64),
        active_follow_up: true,
        active_follow_up_event_id: 'b'.repeat(64),
        active_follow_up_origin_observation_id: observationId,
        active_follow_up_origin_trade_date: '2026-09-19',
      }
    : {
        review_state: 'unseen',
        note: '',
        current_event_id: null,
        active_follow_up: false,
        active_follow_up_event_id: null,
        active_follow_up_origin_observation_id: null,
        active_follow_up_origin_trade_date: null,
      }

  const sections = [{
    workflow_bucket: 'reaction_observation',
    change_count: 1,
    items: [{
      display_key: key,
      instrument_id: 'SSE.688256',
      review_bucket: 'reaction_observation',
      change_types: ['lifecycle_state_changed', 'next_key_changed'],
      previous: {
        action_state: 'waiting',
        lifecycle_state: 'waiting_terminal',
        next_key_price: 100,
      },
      current: {
        action_state: 'reaction_observation',
        lifecycle_state: 't_plus_1',
        next_key_price: 112.5,
      },
      review,
    }],
  }]

  return {
    schema_version: 1,
    status: 'changes_ready',
    review_ready: true,
    trade_date: '2026-09-19',
    source_observation_id: observationId,
    source_revision_ordinal: 1,
    previous_recorded_trade_date: '2026-09-18',
    delta_status: 'ready',
    change_count: 1,
    change_type_counts: {
      lifecycle_state_changed: 1,
      next_key_changed: 1,
    },
    workflow_bucket_counts: { reaction_observation: 1 },
    workflow_sections: sections,
    filtered_change_count: 1,
    filtered_workflow_sections: sections,
    analysis_incomplete_count: 0,
    analysis_incomplete_instruments: [],
    source_change_count_unchanged: 1,
    review_state_counts: saved
      ? { unseen: 0, reviewed: 0, follow_up: 1 }
      : { unseen: 1, reviewed: 0, follow_up: 0 },
    active_follow_up_count: saved ? 1 : 0,
    source_review_state_counts_unchanged: saved
      ? { unseen: 0, reviewed: 0, follow_up: 1 }
      : { unseen: 1, reviewed: 0, follow_up: 0 },
    source_active_follow_up_count_unchanged: saved ? 1 : 0,
    authoritative_evidence: false,
    writes_m4_evidence: false,
    historical_outcome_used_for_ranking: false,
    predictive_score_used: false,
    alpha_inference_allowed: false,
    is_trade_instruction: false,
  }
}

test('M5 review session saves follow-up without changing source review totals', async ({ page }) => {
  let saved = false
  let posted: Record<string, unknown> | null = null

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
    await route.fulfill({ json: history })
  })
  await page.route('**/api/operator/review-session/event', async (route) => {
    posted = route.request().postDataJSON() as Record<string, unknown>
    saved = true
    await route.fulfill({
      json: {
        schema_version: 1,
        status: 'appended',
        event: {
          event_id: 'b'.repeat(64),
          review_state: 'follow_up',
        },
        waited_for_lock: false,
        wait_seconds: 0,
        authoritative_evidence: false,
        writes_m4_evidence: false,
        is_trade_instruction: false,
      },
    })
  })
  await page.route('**/api/operator/review-session**', async (route) => {
    await route.fulfill({ json: session(saved) })
  })

  await page.goto('/')

  const review = page.getByLabel('daily-review-digest')
  const summary = review.locator('.daily-review-digest__summary')

  await expect(summary.getByText('源变化总数').locator('..')).toContainText('1')
  await expect(summary.getByText('未看').locator('..')).toContainText('1')
  await expect(summary.getByText('持续跟踪中').locator('..')).toContainText('0')

  await review
    .getByLabel('复盘状态 SSE.688256')
    .selectOption('follow_up')
  await review
    .getByLabel('复盘备注 SSE.688256')
    .fill('继续观察下一关键价')
  await review.getByRole('button', { name: '保存复盘' }).click()

  await expect(review.getByText('SSE.688256 已保存：后续跟踪')).toBeVisible()
  await expect(summary.getByText('源变化总数').locator('..')).toContainText('1')
  await expect(summary.getByText('当天后续跟踪').locator('..')).toContainText('1')
  await expect(summary.getByText('持续跟踪中').locator('..')).toContainText('1')
  await expect(review.getByText('跟踪中 · 始于 2026-09-19')).toBeVisible()

  expect(posted).not.toBeNull()
  expect(posted?.source_observation_id).toBe(observationId)
  expect(posted?.display_key).toBe(key)
  expect(posted?.review_state).toBe('follow_up')
  expect(posted?.note).toBe('继续观察下一关键价')
  expect(String(posted?.client_request_id ?? '')).not.toBe('')
})
