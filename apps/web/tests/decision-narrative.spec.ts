import { expect, test } from '@playwright/test'

test('action-state narrative follows source lifecycle and execution context renders once', async ({ page }) => {
  const executionContext = {
    instrument_id: 'SSE.688256',
    symbol: '688256',
    board: 'STAR',
    as_of_trade_date: '2026-09-18',
    metadata_available: true,
    metadata_source: 'test',
    list_date: '2020-07-20',
    is_st: false,
    daily_event_available: false,
    daily_trading_status: null,
    tradable_on_as_of_date: null,
    daily_no_price_limit: null,
    daily_price_limit_override_pct: null,
    daily_event_resolution_complete: false,
    daily_event_source: null,
    daily_event_reason: null,
    t_plus_one: true,
    same_day_sell_after_buy: false,
    earliest_sell_offset_sessions_after_buy: 1,
    nominal_price_limit_pct: 20,
    rule_based_price_limit_pct: 20,
    price_limit_status: 'board_rule_profile_resolved_special_events_unresolved',
    ipo_first_five_sessions: false,
    special_event_exceptions_unresolved: true,
    atr_period: 14,
    atr: 5.2,
    atr_pct: 4.7,
    latest_range_pct: 3.1,
    avg_volume_20: 1000,
    volume_ratio_20: 1.2,
    bse_deferred: false,
    mutates_harmonic_identity: false,
    mutates_source_raw_prz: false,
  }

  const pattern = {
    pattern_id: 'gartley',
    schema: 'XABCD',
    direction: 'bullish',
    state: 'completed',
    scale: 5,
    geometry_score: 98,
    points: [
      { label: 'X', index: 0, price: 100, trade_date: '2026-09-15' },
      { label: 'A', index: 1, price: 120, trade_date: '2026-09-16' },
      { label: 'B', index: 2, price: 108, trade_date: '2026-09-17' },
      { label: 'C', index: 3, price: 116, trade_date: '2026-09-18' },
      { label: 'D', index: 3, price: 104, trade_date: '2026-09-18' },
    ],
    prz: {
      price_low: 103.9,
      price_high: 104.5,
      width: .6,
      components: [{ name: 'XA', price_low: 104, price_high: 104, ratio_low: .786, ratio_high: .786 }],
    },
    metrics: { b_xa: .618, c_ab: .72, bc_projection: 1.3, d_xa: .786, cd_ab: 1 },
    source_lifecycle: {
      state: 'type_i_confirmed',
      state_reason: '38.2 reached inside five bars.',
      clock_source: 'source_terminal_price_bar',
      current_bar: 3,
      signal_bar: 1,
      source_prz_entry_bar: 2,
      source_terminal_bar: 2,
      execution_start_bar: 3,
      bars_since_terminal: 1,
      type_i_t1_bar: 3,
      type_i_t2_bar: null,
      first_source_prz_exit_bar: 3,
      type_ii_retest_entry_bar: null,
      type_ii_terminal_bar: null,
      reversal_exit_after_type_ii_bar: null,
      source_prz_low: 103.9,
      source_prz_high: 104.5,
      pez_low: 103.8,
      pez_high: 104.5,
      target_382: 108,
      target_618: 111,
      next_key_price: 111,
      next_key_price_role: 'type_i_61_8_target',
      strict_type_ii_full_retest: true,
      retrospective_geometry_clock_used: false,
    },
    a_share_execution_context: executionContext,
    decision_narrative: {
      lifecycle_state: 'type_i_confirmed',
      action_state: 'execution_evaluation',
      current_position: 'Type-I 38.2% 早期反应已确认。',
      first_watch: '先看 61.8% 目标及首次离区质量。',
      next_watch: '若后续重新进入 Source PRZ，再按 strict full retest 观察 Type-II。',
      upgrade_blocker: 'Type-I confirmation 不等于长期 reversal。',
      next_key_price: 111,
      next_key_price_role: 'type_i_61_8_target',
      execution_context_gate: 'execution_unresolved',
      context_cautions: ['execution:unresolved — 特殊事件不完整'],
      is_trade_instruction: false,
      uses_score: false,
      mutates_harmonic_identity: false,
      mutates_source_raw_prz: false,
      owns_lifecycle: false,
    },
  }

  await page.route('**/api/health', async (route) => {
    await route.fulfill({ json: { status: 'ok', service: 'ht-cn-api', version: '0.4.0' } })
  })
  await page.route('**/api/instruments?**', async (route) => {
    await route.fulfill({ json: { count: 1, items: [{ instrument_id: 'SSE.688256', has_qfq_factor: true }] } })
  })
  await page.route('**/api/harmonic/SSE.688256?**', async (route) => {
    await route.fulfill({ json: {
      instrument_id: 'SSE.688256',
      price_mode: 'qfq',
      warning: null,
      bars_requested: 420,
      bars_returned: 4,
      first_trade_date: '2026-09-15',
      last_trade_date: '2026-09-18',
      scales: [3,5,8,13],
      bars: [
        { index: 0, trade_date: '2026-09-15', open: 100, high: 102, low: 99, close: 101, volume: 1000 },
        { index: 1, trade_date: '2026-09-16', open: 118, high: 121, low: 117, close: 120, volume: 1100 },
        { index: 2, trade_date: '2026-09-17', open: 105, high: 107, low: 103.8, close: 106, volume: 1200 },
        { index: 3, trade_date: '2026-09-18', open: 107, high: 109, low: 106, close: 108, volume: 1300 },
      ],
      completed: [pattern],
      forming: [],
      pivot_counts: {},
      a_share_execution_context: executionContext,
      engine_note: 'source lifecycle owns action state',
    } })
  })

  await page.goto('/')
  await page.getByRole('button', { name: '运行谐波分析' }).click()

  const narrative = page.getByTestId('decision-narrative')
  await expect(narrative).toBeVisible()
  await expect(narrative).toHaveAttribute('data-action-state', 'execution_evaluation')
  await expect(narrative.getByText('当前阶段：执行评估')).toBeVisible()
  await expect(narrative.getByText(/111\.00/)).toBeVisible()
  await expect(narrative.getByText(/不是买卖指令，也不使用综合评分/)).toBeVisible()
  await expect(page.getByTestId('execution-context-gate')).toHaveAttribute('data-gate', 'execution_unresolved')
  await expect(page.getByTestId('execution-context-gate')).toContainText('特殊事件证据未完整')
  await expect(page.getByTestId('a-share-execution-context')).toHaveCount(1)
})
