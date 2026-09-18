import { expect, test } from '@playwright/test'

function lifecycle(state: string, next: number, role: string) {
  return {
    state,
    state_reason: state,
    clock_source: 'source_terminal_price_bar',
    current_bar: 4,
    signal_bar: 1,
    source_prz_entry_bar: 2,
    source_terminal_bar: state === 'waiting_terminal' ? null : 2,
    execution_start_bar: state === 'waiting_terminal' ? null : 3,
    bars_since_terminal: state === 'waiting_terminal' ? null : 2,
    type_i_t1_bar: state === 'type_i_confirmed' ? 3 : null,
    type_i_t2_bar: null,
    first_source_prz_exit_bar: null,
    type_ii_retest_entry_bar: null,
    type_ii_terminal_bar: null,
    reversal_exit_after_type_ii_bar: null,
    source_prz_low: 100,
    source_prz_high: 102,
    pez_low: null,
    pez_high: null,
    target_382: 108,
    target_618: 112,
    next_key_price: next,
    next_key_price_role: role,
    strict_type_ii_full_retest: true,
    retrospective_geometry_clock_used: false,
  }
}

function narrative(
  lifecycleState: string,
  actionState: string,
  next: number,
  role: string,
  current: string,
) {
  return {
    lifecycle_state: lifecycleState,
    action_state: actionState,
    current_position: current,
    first_watch: '先看第一观察点',
    next_watch: '再看下一阶段',
    upgrade_blocker: '未满足 source gate 前不能升级',
    next_key_price: next,
    next_key_price_role: role,
    execution_context_gate: 'current',
    context_cautions: [],
    is_trade_instruction: false,
    uses_score: false,
    mutates_harmonic_identity: false,
    mutates_source_raw_prz: false,
    owns_lifecycle: false,
  }
}

function pattern(
  id: string,
  scale: number,
  state: string,
  actionState: string,
  next: number,
  role: string,
  current: string,
) {
  return {
    pattern_id: id,
    schema: 'XABCD',
    direction: 'bullish',
    state: 'completed',
    scale,
    geometry_score: 90 + scale,
    points: [
      { label: 'X', index: 0, price: 120, trade_date: '2026-09-14' },
      { label: 'A', index: 1, price: 100, trade_date: '2026-09-15' },
      { label: 'B', index: 2, price: 112, trade_date: '2026-09-16' },
      { label: 'C', index: 3, price: 104, trade_date: '2026-09-17' },
      { label: 'D', index: 4, price: 101, trade_date: '2026-09-18' },
    ],
    prz: {
      price_low: 100,
      price_high: 102,
      width: 2,
      components: [
        { name: 'XA', price_low: 100, price_high: 102, ratio_low: .786, ratio_high: .886 },
      ],
    },
    metrics: { b_xa: .618, c_ab: .618, bc_projection: 1.618, d_xa: .786, cd_ab: 1 },
    source_lifecycle: lifecycle(state, next, role),
    decision_narrative: narrative(state, actionState, next, role, current),
  }
}

test('selected candidate switches narrative with its own source lifecycle', async ({ page }) => {
  const first = pattern(
    'gartley',
    5,
    'waiting_terminal',
    'waiting',
    100,
    'source_prz_terminal_side',
    'Gartley 正在等待 Source T-Bar。',
  )
  const second = pattern(
    'bat',
    8,
    'type_i_confirmed',
    'execution_evaluation',
    112,
    'type_i_61_8_target',
    'Bat 已确认 Type-I 38.2%。',
  )

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
      bars_returned: 5,
      first_trade_date: '2026-09-14',
      last_trade_date: '2026-09-18',
      scales: [3,5,8,13],
      bars: [
        { index: 0, trade_date: '2026-09-14', open: 119, high: 121, low: 118, close: 120, volume: 1000 },
        { index: 1, trade_date: '2026-09-15', open: 101, high: 102, low: 99, close: 100, volume: 1000 },
        { index: 2, trade_date: '2026-09-16', open: 111, high: 113, low: 110, close: 112, volume: 1000 },
        { index: 3, trade_date: '2026-09-17', open: 105, high: 106, low: 103, close: 104, volume: 1000 },
        { index: 4, trade_date: '2026-09-18', open: 101, high: 102, low: 100, close: 101, volume: 1000 },
      ],
      completed: [first, second],
      forming: [],
      pivot_counts: {},
      engine_note: 'selection regression',
    } })
  })

  await page.goto('/')
  await page.getByRole('button', { name: '运行谐波分析' }).click()

  const card = page.getByTestId('decision-narrative')
  await expect(card).toHaveAttribute('data-action-state', 'waiting')
  await expect(card.getByText('Gartley 正在等待 Source T-Bar。')).toBeVisible()
  await expect(card.getByText(/100\.00/)).toBeVisible()

  const candidates = page.locator('.pattern-item')
  await expect(candidates).toHaveCount(2)
  await candidates.nth(1).click()

  await expect(card).toHaveAttribute('data-action-state', 'execution_evaluation')
  await expect(card.getByText('Bat 已确认 Type-I 38.2%。')).toBeVisible()
  await expect(card.getByText(/112\.00/)).toBeVisible()
  await expect(card.getByText('Gartley 正在等待 Source T-Bar。')).toHaveCount(0)
})
