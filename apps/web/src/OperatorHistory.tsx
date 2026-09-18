import { useCallback, useEffect, useState } from 'react'
import './OperatorHistory.css'

type HistoryChange = {
  display_key: string
  instrument_id: string
  change_types: string[]
  previous: { lifecycle_state?: string } | null
  current: { lifecycle_state?: string } | null
}

type HistoryObservation = {
  trade_date: string
  observation_id: string
  revision_ordinal: number
  source_generated_at_utc: string
  previous_recorded_trade_date: string | null
  queue_candidate_count: number
  delta_total_change_count: number
  item_count: number
  items: { instrument_id: string; lifecycle_state: string; action_state: string }[]
  change_count: number
  changes: HistoryChange[]
  delta_status: string
  comparison_incomplete_instruments: string[]
}

type HistoryPayload = {
  schema_version: number
  observation_count: number
  observations: HistoryObservation[]
  authoritative_evidence: boolean
  writes_m4_evidence: boolean
  historical_outcome_used_for_ranking: boolean
  alpha_inference_allowed: boolean
  is_trade_instruction: boolean
}

type Props = {
  apiBase: string
  onSelectInstrument: (instrumentId: string) => void
}

const CHANGE_LABELS: Record<string, string> = {
  new_candidate: '新出现候选',
  disappeared_candidate: '候选消失',
  action_state_changed: '工作状态变化',
  lifecycle_state_changed: '生命周期变化',
  pattern_state_changed: '形态状态变化',
  next_key_changed: '下一关键价变化',
  execution_gate_changed: '执行约束变化',
  context_cautions_changed: '上下文注意项变化',
}

function changeLabel(value: string) {
  return CHANGE_LABELS[value] ?? value
}

export default function OperatorHistory({ apiBase, onSelectInstrument }: Props) {
  const [instrument, setInstrument] = useState('')
  const [payload, setPayload] = useState<HistoryPayload | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback((instrumentId = '') => {
    setLoading(true)
    setError(null)
    const query = new URLSearchParams({
      limit: '20',
      summary_only: instrumentId.trim() ? 'false' : 'true',
    })
    if (instrumentId.trim()) {
      query.set('instrument_id', instrumentId.trim().toUpperCase())
    }
    fetch(`${apiBase}/api/operator/history?${query.toString()}`)
      .then(async (response) => {
        if (!response.ok) {
          const body = (await response.json().catch(() => null)) as { detail?: string } | null
          throw new Error(body?.detail ?? `HTTP ${response.status}`)
        }
        return response.json() as Promise<HistoryPayload>
      })
      .then(setPayload)
      .catch((err: Error) => {
        setPayload(null)
        setError(err.message)
      })
      .finally(() => setLoading(false))
  }, [apiBase])

  useEffect(() => {
    load('')
  }, [load])

  return (
    <section className="operator-history" aria-label="operator-history">
      <div className="operator-history__heading">
        <div>
          <p className="eyebrow">M5 · DAILY OPERATOR HISTORY</p>
          <h3>跨日产品观察历史</h3>
          <p>
            记录每天最终 Queue 的产品级变化。它不是 M4 权威证据，
            不用于胜率、alpha 或预测排名。
          </p>
        </div>
        <div className="operator-history__search">
          <input
            value={instrument}
            onChange={(event) => setInstrument(event.target.value)}
            placeholder="输入证券代码，例如 SSE.688256"
          />
          <button onClick={() => load(instrument)} disabled={loading}>
            {loading ? '查询中…' : '查询历史'}
          </button>
          {instrument && (
            <button
              onClick={() => {
                setInstrument('')
                load('')
              }}
              disabled={loading}
            >
              清除
            </button>
          )}
        </div>
      </div>

      {error && <div className="operator-history__error">历史查询失败：{error}</div>}

      {payload && (
        <>
          <div className="operator-history__boundary">
            <span>最近 {payload.observation_count} 个交易日观察</span>
            <span>append-only 产品 journal</span>
            <span>不写 M4 evidence</span>
          </div>

          {payload.observations.length === 0 && (
            <p className="operator-history__empty">
              尚无可用历史。每日收盘流水线成功记录后，这里会开始积累。
            </p>
          )}

          <div className="operator-history__list">
            {payload.observations.map((observation) => (
              <article className="operator-history__day" key={observation.observation_id}>
                <div className="operator-history__day-head">
                  <div>
                    <strong>{observation.trade_date}</strong>
                    <span>revision {observation.revision_ordinal}</span>
                  </div>
                  <div>
                    <span>全部候选 {observation.queue_candidate_count}</span>
                    <span>当日总变化 {observation.delta_total_change_count}</span>
                    {instrument.trim() && (
                      <>
                        <span>该标的候选 {observation.item_count}</span>
                        <span>该标的变化 {observation.change_count}</span>
                      </>
                    )}
                  </div>
                </div>

                <div className="operator-history__meta">
                  <span>对比基线：{observation.previous_recorded_trade_date ?? '首个观察日'}</span>
                  <span>Delta：{observation.delta_status}</span>
                </div>

                {observation.changes.length > 0 && (
                  <div className="operator-history__changes">
                    {observation.changes.map((change) => (
                      <div
                        className="operator-history__change"
                        key={`${observation.observation_id}-${change.display_key}`}
                      >
                        <button onClick={() => onSelectInstrument(change.instrument_id)}>
                          {change.instrument_id}
                        </button>
                        <span>{change.change_types.map(changeLabel).join(' · ')}</span>
                        <span>
                          {change.previous?.lifecycle_state ?? '—'}
                          {' → '}
                          {change.current?.lifecycle_state ?? '—'}
                        </span>
                      </div>
                    ))}
                  </div>
                )}

                {observation.comparison_incomplete_instruments.length > 0 && (
                  <p className="operator-history__warning">
                    本日有 {observation.comparison_incomplete_instruments.length} 个标的分析失败；
                    这些标的的“候选消失”不会被误记。
                  </p>
                )}
              </article>
            ))}
          </div>
        </>
      )}
    </section>
  )
}
