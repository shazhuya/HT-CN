import { useCallback, useEffect, useMemo, useState } from 'react'
import OperatorDeltaPanel, { OperatorDeltaPayload } from './OperatorDelta'
import './OperatorQueue.css'

type OperatorQueueContract = {
  version: number
  source_of_truth: string
  ranking_mode: string
  predictive_score_used: boolean
  historical_outcome_used: boolean
  alpha_inference_allowed: boolean
  is_trade_instruction: boolean
  mutates_harmonic_identity: boolean
  mutates_source_raw_prz: boolean
  owns_lifecycle: boolean
}

type OperatorQueueItem = {
  display_key: string
  instrument_id: string
  last_trade_date: string | null
  price_mode: string | null
  warning: string | null
  pattern_id: string
  schema: string
  direction: string
  scale: number
  pattern_state: string
  action_state: string
  workflow_bucket_order: number
  lifecycle_state: string
  state_reason: string | null
  current_position: string | null
  first_watch: string | null
  next_watch: string | null
  upgrade_blocker: string | null
  next_key_price: number | null
  next_key_price_role: string | null
  execution_context_gate: string | null
  context_cautions: string[]
  source_prz_low: number | null
  source_prz_high: number | null
  bars_since_terminal: number | null
}

type OperatorQueuePayload = {
  schema_version: number
  as_of_trade_date: string | null
  observed_trade_dates: string[]
  observation_integrity: string
  contract: OperatorQueueContract
  instrument_count: number
  analyzed_instrument_count: number
  failed_instrument_count: number
  candidate_count: number
  candidate_instrument_count: number
  action_state_counts: Record<string, number>
  lifecycle_state_counts: Record<string, number>
  items: OperatorQueueItem[]
  errors: { instrument_id: string; error: string }[]
  product_cache?: {
    schema_version: number
    contract_version: number
    status: string
    expected_local_trade_date: string | null
    queue_as_of_trade_date: string | null
    freshness: string
    cache_path: string | null
    generated_at_utc: string | null
    authoritative_evidence: boolean
    writes_m4_evidence: boolean
  }
}

type Props = {
  apiBase: string
  onSelectInstrument: (instrumentId: string) => void
}

const ACTION_LABELS: Record<string, string> = {
  execution_evaluation: '执行评估',
  reaction_observation: '反应观察',
  waiting: '等待',
  evidence_insufficient: '证据不足',
}

const LIFECYCLE_LABELS: Record<string, string> = {
  source_clock_unavailable: 'Source 时钟不可用',
  source_prz_unresolved: 'Source PRZ 未冻结',
  approaching_source_prz: '接近 Source PRZ',
  entered_source_prz: '已进入 Source PRZ',
  waiting_terminal: '等待 Terminal',
  source_terminal_complete: 'Terminal 已完成',
  t_plus_1: 'T+1',
  type_i_early_reaction: 'Type-I 早期窗口',
  type_i_confirmed: 'Type-I 已确认',
  type_i_failed: 'Type-I 早期失败',
  reaction_only: '仅 Reaction',
  type_ii_retest_forming: 'Type-II 回测形成中',
  type_ii_terminal: 'Type-II Terminal',
  reversal_evidence: 'Reversal evidence',
  invalidated: '失效/不可升级',
}

const PATTERN_LABELS: Record<string, string> = {
  gartley: 'Gartley',
  bat: 'Bat',
  alternate_bat: 'Alternate Bat',
  butterfly: 'Butterfly',
  crab: 'Crab',
  deep_crab: 'Deep Crab',
  abcd: 'AB=CD',
  shark: 'Shark',
  five_zero: '5-0',
}

function actionLabel(value: string) {
  return ACTION_LABELS[value] ?? value
}

function lifecycleLabel(value: string) {
  return LIFECYCLE_LABELS[value] ?? value
}

function patternLabel(value: string) {
  return PATTERN_LABELS[value] ?? value
}

function priceLabel(value: number | null) {
  return value == null ? '—' : value.toFixed(2)
}

const CURRENT_SNAPSHOT_KEY = 'htcn.operator.queue.current.v2'
const PREVIOUS_SNAPSHOT_KEY = 'htcn.operator.queue.previous.v2'

function readStoredSnapshot(key: string): OperatorQueuePayload | null {
  try {
    const raw = window.localStorage.getItem(key)
    if (!raw) return null
    const parsed = JSON.parse(raw) as OperatorQueuePayload
    if (!parsed || typeof parsed !== 'object') return null
    return parsed
  } catch {
    return null
  }
}

export default function OperatorQueue({ apiBase, onSelectInstrument }: Props) {
  const [payload, setPayload] = useState<OperatorQueuePayload | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [includeInsufficient, setIncludeInsufficient] = useState(true)
  const [delta, setDelta] = useState<OperatorDeltaPayload | null>(null)
  const [deltaLoading, setDeltaLoading] = useState(false)
  const [deltaError, setDeltaError] = useState<string | null>(null)
  const [baselineMessage, setBaselineMessage] = useState<string | null>(null)

  const compareSnapshots = useCallback((
    previous: OperatorQueuePayload,
    current: OperatorQueuePayload,
  ) => {
    setDeltaLoading(true)
    setDeltaError(null)
    fetch(`${apiBase}/api/operator/delta`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ previous, current }),
    })
      .then(async (response) => {
        if (!response.ok) {
          const body = (await response.json().catch(() => null)) as { detail?: string } | null
          throw new Error(body?.detail ?? `HTTP ${response.status}`)
        }
        return response.json() as Promise<OperatorDeltaPayload>
      })
      .then((value) => {
        setDelta(value)
        setBaselineMessage(null)
      })
      .catch((err: Error) => {
        setDelta(null)
        setDeltaError(err.message)
      })
      .finally(() => setDeltaLoading(false))
  }, [apiBase])

  const observeSnapshot = useCallback((next: OperatorQueuePayload) => {
    if (
      next.observation_integrity !== 'single_as_of'
      || !next.as_of_trade_date
    ) {
      setDelta(null)
      setDeltaError(null)
      setBaselineMessage(
        '当前 Queue 不是单一交易日快照，今日变化暂不生成，避免混合日期误判。',
      )
      return
    }

    const storedCurrent = readStoredSnapshot(CURRENT_SNAPSHOT_KEY)
    if (!storedCurrent?.as_of_trade_date) {
      window.localStorage.setItem(
        CURRENT_SNAPSHOT_KEY,
        JSON.stringify(next),
      )
      setDelta(null)
      setDeltaError(null)
      setBaselineMessage(
        `已建立 ${next.as_of_trade_date} 产品观察基线；下一交易日将显示变化。`,
      )
      return
    }

    if (next.as_of_trade_date < storedCurrent.as_of_trade_date) {
      setDelta(null)
      setDeltaError(null)
      setBaselineMessage(
        `当前快照 ${next.as_of_trade_date} 早于本地基线 ${storedCurrent.as_of_trade_date}，不回写变化历史。`,
      )
      return
    }

    let previous: OperatorQueuePayload | null = null
    if (next.as_of_trade_date > storedCurrent.as_of_trade_date) {
      previous = storedCurrent
      window.localStorage.setItem(
        PREVIOUS_SNAPSHOT_KEY,
        JSON.stringify(storedCurrent),
      )
      window.localStorage.setItem(
        CURRENT_SNAPSHOT_KEY,
        JSON.stringify(next),
      )
    } else {
      window.localStorage.setItem(
        CURRENT_SNAPSHOT_KEY,
        JSON.stringify(next),
      )
      previous = readStoredSnapshot(PREVIOUS_SNAPSHOT_KEY)
    }

    if (
      previous?.as_of_trade_date
      && previous.as_of_trade_date < next.as_of_trade_date
    ) {
      compareSnapshots(previous, next)
    } else {
      setDelta(null)
      setDeltaError(null)
      setBaselineMessage(
        `当前仍为 ${next.as_of_trade_date}；需要上一交易日产品快照后才能生成“今日变化”。`,
      )
    }
  }, [compareSnapshots])

  const load = useCallback((forceRefresh = false) => {
    setLoading(true)
    setError(null)
    const query = new URLSearchParams({
      limit: '500',
      bars: '420',
      include_evidence_insufficient: 'true',
      refresh: forceRefresh ? 'true' : 'false',
    })
    fetch(`${apiBase}/api/operator/queue?${query.toString()}`)
      .then(async (response) => {
        if (!response.ok) throw new Error(`HTTP ${response.status}`)
        return response.json() as Promise<OperatorQueuePayload>
      })
      .then((value) => {
        setPayload(value)
        observeSnapshot(value)
      })
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false))
  }, [apiBase, observeSnapshot])

  useEffect(() => {
    load(false)
  }, [load])

  const visibleItems = useMemo(() => {
    const items = payload?.items ?? []
    if (includeInsufficient) return items
    return items.filter(
      (item) => item.action_state !== 'evidence_insufficient',
    )
  }, [payload, includeInsufficient])

  const groups = useMemo(() => {
    const result = new Map<string, OperatorQueueItem[]>()
    for (const item of visibleItems) {
      const current = result.get(item.action_state) ?? []
      current.push(item)
      result.set(item.action_state, current)
    }
    return result
  }, [visibleItems])

  const orderedStates = [
    'execution_evaluation',
    'reaction_observation',
    'waiting',
    'evidence_insufficient',
  ]

  return (
    <section className="operator-queue" aria-label="operator-queue">
      <div className="operator-queue__heading">
        <div>
          <p className="eyebrow">M5 · DAILY OPERATOR QUEUE</p>
          <h2>今日观察队列</h2>
          <p>
            只按 Source lifecycle 工作流分桶，不使用胜率、收益预测或买卖评分。
            先看“现在在哪”，再看“下一关键价”和“什么条件不能升级”。
          </p>
        </div>
        <div className="operator-queue__controls">
          <label>
            <input
              type="checkbox"
              checked={includeInsufficient}
              onChange={(event) => setIncludeInsufficient(event.target.checked)}
            />
            显示证据不足
          </label>
          <button onClick={() => load(true)} disabled={loading}>
            {loading ? '刷新中…' : '刷新队列'}
          </button>
        </div>
      </div>

      {error && <div className="operator-queue__error">队列加载失败：{error}</div>}

      {payload && (
        <>
          {payload.product_cache && (
            <div className="operator-queue__cache">
              <span>
                Queue cache：<strong>{payload.product_cache.status}</strong>
              </span>
              <span>
                数据日期：{payload.product_cache.queue_as_of_trade_date ?? '—'}
              </span>
              <span>
                freshness：{payload.product_cache.freshness}
              </span>
              <span>产品缓存，不是 M4 evidence</span>
            </div>
          )}

          <div className="operator-queue__summary">
            <div><span>本地标的</span><strong>{payload.instrument_count}</strong></div>
            <div><span>分析成功</span><strong>{payload.analyzed_instrument_count}</strong></div>
            <div><span>候选标的</span><strong>{payload.candidate_instrument_count}</strong></div>
            <div><span>候选结构</span><strong>{payload.candidate_count}</strong></div>
            <div><span>数据错误</span><strong>{payload.failed_instrument_count}</strong></div>
          </div>

          <OperatorDeltaPanel
            delta={delta}
            loading={deltaLoading}
            error={deltaError}
            baselineMessage={baselineMessage}
            onSelectInstrument={onSelectInstrument}
            onResetBaseline={() => {
              window.localStorage.removeItem(CURRENT_SNAPSHOT_KEY)
              window.localStorage.removeItem(PREVIOUS_SNAPSHOT_KEY)
              setDelta(null)
              setDeltaError(null)
              if (
                payload.observation_integrity === 'single_as_of'
                && payload.as_of_trade_date
              ) {
                window.localStorage.setItem(
                  CURRENT_SNAPSHOT_KEY,
                  JSON.stringify(payload),
                )
                setBaselineMessage(
                  `已用 ${payload.as_of_trade_date} 重新建立产品观察基线。`,
                )
              } else {
                setBaselineMessage('变化基线已清除。')
              }
            }}
          />

          <div className="operator-queue__notice">
            <strong>排序含义：</strong>
            execution evaluation → reaction observation → waiting → evidence insufficient。
            这是观察工作流顺序，不是收益率排名。
          </div>

          {orderedStates.map((state) => {
            const items = groups.get(state) ?? []
            if (!items.length) return null
            return (
              <div className="operator-queue__group" key={state}>
                <div className="operator-queue__group-title">
                  <h3>{actionLabel(state)}</h3>
                  <span>{items.length} 个结构</span>
                </div>
                <div className="operator-queue__table-wrap">
                  <table className="operator-queue__table">
                    <thead>
                      <tr>
                        <th>标的 / 形态</th>
                        <th>当前阶段</th>
                        <th>下一关键价</th>
                        <th>先看什么</th>
                        <th>升级阻断</th>
                        <th>执行上下文</th>
                      </tr>
                    </thead>
                    <tbody>
                      {items.map((item) => (
                        <tr key={item.display_key}>
                          <td>
                            <button
                              className="operator-queue__symbol"
                              onClick={() => onSelectInstrument(item.instrument_id)}
                            >
                              {item.instrument_id}
                            </button>
                            <div className="operator-queue__meta">
                              {patternLabel(item.pattern_id)} · S{item.scale} ·
                              {item.direction === 'bullish' ? ' 看涨' : ' 看跌'}
                            </div>
                          </td>
                          <td>
                            <strong>{lifecycleLabel(item.lifecycle_state)}</strong>
                            <div className="operator-queue__meta">{item.current_position ?? '—'}</div>
                          </td>
                          <td>
                            <strong>{priceLabel(item.next_key_price)}</strong>
                            <div className="operator-queue__meta">{item.next_key_price_role ?? '—'}</div>
                          </td>
                          <td>{item.first_watch ?? '—'}</td>
                          <td>{item.upgrade_blocker ?? '—'}</td>
                          <td>
                            <strong>{item.execution_context_gate ?? '—'}</strong>
                            {item.context_cautions.length > 0 && (
                              <div className="operator-queue__caution">
                                {item.context_cautions.slice(0, 2).join('；')}
                              </div>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )
          })}

          {payload.errors.length > 0 && (
            <details className="operator-queue__errors">
              <summary>查看 {payload.errors.length} 个数据/分析错误</summary>
              <ul>
                {payload.errors.map((item) => (
                  <li key={item.instrument_id}>
                    <strong>{item.instrument_id}</strong>：{item.error}
                  </li>
                ))}
              </ul>
            </details>
          )}
        </>
      )}
    </section>
  )
}
