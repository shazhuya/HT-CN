import './OperatorDelta.css'

export type OperatorDeltaSnapshot = {
  display_key: string
  instrument_id: string
  pattern_id: string
  schema: string
  direction: string
  scale: number
  pattern_state: string
  action_state: string
  lifecycle_state: string
  next_key_price: number | null
  next_key_price_role: string | null
  execution_context_gate: string | null
  context_cautions: string[]
  current_position: string | null
  first_watch: string | null
  upgrade_blocker: string | null
}

export type OperatorDeltaChange = {
  display_key: string
  instrument_id: string
  change_types: string[]
  previous: OperatorDeltaSnapshot | null
  current: OperatorDeltaSnapshot | null
}

export type OperatorDeltaPayload = {
  schema_version: number
  contract: {
    version: number
    semantics: string
    authoritative_transition: boolean
    writes_m4_evidence: boolean
    predictive_score_used: boolean
    historical_outcome_used: boolean
    alpha_inference_allowed: boolean
    is_trade_instruction: boolean
    mutates_harmonic_identity: boolean
    mutates_source_raw_prz: boolean
    owns_lifecycle: boolean
  }
  previous_as_of_trade_date: string
  current_as_of_trade_date: string
  status: string
  change_count: number
  change_type_counts: Record<string, number>
  changes: OperatorDeltaChange[]
  comparison_incomplete_instruments: string[]
  warnings: string[]
}

type Props = {
  delta: OperatorDeltaPayload | null
  loading: boolean
  error: string | null
  baselineMessage: string | null
  onSelectInstrument: (instrumentId: string) => void
  onResetBaseline: () => void
}

const CHANGE_LABELS: Record<string, string> = {
  new_candidate: '新出现',
  disappeared_candidate: '已消失',
  action_state_changed: '工作状态变化',
  lifecycle_state_changed: '生命周期变化',
  pattern_state_changed: '形态状态变化',
  next_key_changed: '下一关键价变化',
  execution_gate_changed: '执行上下文变化',
  context_cautions_changed: '上下文提示变化',
}

function changeLabel(value: string) {
  return CHANGE_LABELS[value] ?? value
}

function price(value: number | null | undefined) {
  return value == null ? '—' : value.toFixed(2)
}

function stateLine(snapshot: OperatorDeltaSnapshot | null) {
  if (!snapshot) return '—'
  return `${snapshot.action_state} / ${snapshot.lifecycle_state}`
}

export default function OperatorDeltaPanel({
  delta,
  loading,
  error,
  baselineMessage,
  onSelectInstrument,
  onResetBaseline,
}: Props) {
  return (
    <section className="operator-delta" aria-label="operator-delta">
      <div className="operator-delta__heading">
        <div>
          <p className="eyebrow">M5 · OPERATOR DELTA</p>
          <h3>今日变化</h3>
          <p>比较最近两个交易日的产品观察快照，不是 M4 authoritative transition，也不用于收益预测。</p>
        </div>
        <button onClick={onResetBaseline}>重置变化基线</button>
      </div>

      {loading && <div className="operator-delta__status">正在比较最近两次产品快照…</div>}
      {error && <div className="operator-delta__error">变化比较失败：{error}</div>}
      {!loading && !error && !delta && baselineMessage && (
        <div className="operator-delta__status">{baselineMessage}</div>
      )}

      {delta && delta.status === 'same_as_of_no_delta' && (
        <div className="operator-delta__status">
          当前仍是 {delta.current_as_of_trade_date}，同交易日刷新不会生成“今日变化”。
        </div>
      )}

      {delta && delta.status === 'ready' && (
        <>
          <div className="operator-delta__range">
            <strong>{delta.previous_as_of_trade_date}</strong>
            <span>→</span>
            <strong>{delta.current_as_of_trade_date}</strong>
            <b>{delta.change_count} 个候选发生变化</b>
          </div>

          {delta.change_count === 0 ? (
            <div className="operator-delta__status">相较上一交易日，没有检测到需要展示的产品状态变化。</div>
          ) : (
            <div className="operator-delta__list">
              {delta.changes.map((change) => {
                const snapshot = change.current ?? change.previous
                return (
                  <article className="operator-delta__item" key={change.display_key}>
                    <div className="operator-delta__instrument">
                      <button onClick={() => onSelectInstrument(change.instrument_id)}>
                        {change.instrument_id}
                      </button>
                      <span>
                        {snapshot?.pattern_id ?? '—'} · S{snapshot?.scale ?? '—'}
                      </span>
                    </div>
                    <div className="operator-delta__badges">
                      {change.change_types.map((value) => (
                        <span key={value}>{changeLabel(value)}</span>
                      ))}
                    </div>
                    <div className="operator-delta__compare">
                      <div>
                        <small>上一观察</small>
                        <strong>{stateLine(change.previous)}</strong>
                        <span>下一关键价：{price(change.previous?.next_key_price)}</span>
                      </div>
                      <div>
                        <small>当前观察</small>
                        <strong>{stateLine(change.current)}</strong>
                        <span>下一关键价：{price(change.current?.next_key_price)}</span>
                      </div>
                    </div>
                  </article>
                )
              })}
            </div>
          )}

          {delta.comparison_incomplete_instruments.length > 0 && (
            <div className="operator-delta__warning">
              以下标的当前分析失败，系统已抑制其“候选消失”判断：
              {delta.comparison_incomplete_instruments.join('、')}
            </div>
          )}
        </>
      )}
    </section>
  )
}
