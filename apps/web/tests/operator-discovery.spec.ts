import { expect, test } from '@playwright/test'

const discoveryItem = {
  display_key: 'SSE.688256:gartley:XABCD:bullish:S10:2026-09-01-2026-09-08-2026-09-15-2026-09-22',
  instrument_id: 'SSE.688256',
  last_trade_date: '2026-09-24',
  price_mode: 'qfq',
  timeframe: '1d',
  warning: null,
  pattern_id: 'gartley',
  schema: 'XABCD',
  direction: 'bullish',
  scale: 10,
  pattern_state: 'discovery',
  discovery_only: true,
  action_state: 'evidence_insufficient',
  workflow_bucket_order: 3,
  lifecycle_state: 'discovery_candidate',
  state_reason: 'XABC discovery candidate; Source lifecycle has not started.',
  current_position: '发现候选已投影 Source PRZ，尚未在可观察时钟内测试。',
  first_watch: '先观察投影 Source PRZ；不得虚构 D 或 Source Terminal。',
  next_watch: '只有权威 identity / Source Clock 成立后才进入正式生命周期。',
  upgrade_blocker: 'Discovery 不是 canonical identity，不能用排名或评分升级。',
  next_key_price: 104.6,
  next_key_price_role: 'Source PRZ首触边界',
  execution_context_gate: 'discovery_only',
  context_cautions: ['minor_swing_skip'],
  source_prz_low: 104.0,
  source_prz_high: 104.6,
  bars_since_terminal: null,
}

const queuePayload = {
  schema_version: 2,
  as_of_trade_date: '2026-09-24',
  observed_trade_dates: ['2026-09-24'],
  observation_integrity: 'single_as_of',
  contract: {
    version: 2,
    source_of_truth: 'source_lifecycle_plus_non_authoritative_discovery',
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
  action_state_counts: { evidence_insufficient: 1 },
  lifecycle_state_counts: { discovery_candidate: 1 },
  items: [discoveryItem],
  errors: [],
  operator_index: {
    schema_version: 1,
    universe_scope: 'all_initialized_local_instruments',
    universe_instrument_count: 1,
    presentation_does_not_define_universe: true,
    legacy_limit_ignored: null,
    authoritative_evidence: false,
    writes_m4_evidence: false,
  },
}

test('opportunity discovery visibly separates discovery-only candidates from Source lifecycle', async ({ page }) => {
  await page.route('**/api/health', async (route) => {
    await route.fulfill({ json: { status: 'ok', service: 'ht-cn-api', version: '1.0.0' } })
  })
  await page.route('**/api/instruments?**', async (route) => {
    await route.fulfill({ json: { count: 1, items: [{ instrument_id: 'SSE.688256', has_qfq_factor: true }] } })
  })
  await page.route('**/api/operator/queue?**', async (route) => {
    await route.fulfill({ json: queuePayload })
  })

  await page.goto('/')
  await page.getByLabel('应用导航').getByRole('button', { name: '机会发现', exact: true }).click()

  const queue = page.getByLabel('operator-queue')
  await expect(queue.getByRole('heading', { name: '证据不足' })).toBeVisible()
  await expect(queue.getByText('Gartley · S10 · 日线 · 发现候选 · 看涨')).toBeVisible()
  await expect(queue.getByText('发现候选', { exact: true })).toBeVisible()
  await expect(queue.getByText(/尚未进入权威 Source 生命周期/)).toBeVisible()
  await expect(queue.getByText(/不是低质量或收益率排名/)).toBeVisible()
  await expect(queue.getByText('104.60', { exact: true })).toBeVisible()
  await expect(queue.getByText('Source PRZ首触边界', { exact: true })).toBeVisible()
})
