export type TypeIT5EvidenceState = {
  state: 'pending_t5_observation' | 't2_already_reached_by_t5' | 'full_prz_exit_by_t5' | 'no_full_prz_exit_by_t5' | 'not_applicable'
  display_label: string
  eligible_for_frozen_contrast: boolean
  historical_group: 'exposure' | 'comparator' | null
  bars_until_t5: number | null
  endpoint_state: 't2_hit_by_t5' | 't2_hit_t6_t20' | 'pending_t20' | 'no_t2_by_t20' | 'not_applicable'
}

export type TypeIT5ReplicationEvidence = {
  status: string
  preregistration_id: string
  dataset_id: string
  snapshot_cutoff: string
  requested_symbols: number
  successful_symbols: number
  eligible_pending_t2_at_t5: number
  exposure: {
    name: string
    records: number
    endpoint_hits: number
    endpoint_rate: number
  }
  comparator: {
    name: string
    records: number
    endpoint_hits: number
    endpoint_rate: number
  }
  absolute_rate_difference: number
  newcombe_95_ci: {
    lower: number
    upper: number
  }
  concentration: {
    eligible_symbols: number
    largest_symbol_share: number
  }
  interpretation: string
}

export type TypeIT5HistoricalEvidence = {
  status: string
  preregistration_id: string
  dataset_id: string
  snapshot_cutoff: string
  cohort: string
  endpoint: string
  exposure: {
    name: string
    records: number
    endpoint_hits: number
    endpoint_rate: number
  }
  comparator: {
    name: string
    records: number
    endpoint_hits: number
    endpoint_rate: number
  }
  absolute_rate_difference: number
  newcombe_95_ci: {
    lower: number
    upper: number
  }
  external_replication?: TypeIT5ReplicationEvidence
  interpretation: string
}

export type TypeIT5Event = {
  event_id: string
  instrument_id: string
  pattern_id: string
  schema: string
  direction: 'bullish' | 'bearish'
  source_scale: number
  signal_scales: number[]
  forming_signal_bar: number
  forming_signal_trade_date: string
  terminal_bar: number
  terminal_trade_date: string
  terminal_price: number
  prz: {
    price_low: number
    price_high: number
  }
  t1_name: string
  t1_price: number
  t2_name: string
  t2_price: number
  bars_from_terminal_to_t1: number | null
  bars_from_terminal_to_t2: number | null
  bars_from_terminal_to_full_prz_exit: number | null
  available_future_bars_after_terminal: number
  t5_evidence: TypeIT5EvidenceState
  historical_evidence: TypeIT5HistoricalEvidence
  identity_separation: string
}

type Props = {
  events: TypeIT5Event[]
}

const PATTERN_NAMES: Record<string, string> = {
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

function pct(value: number) {
  return `${(value * 100).toFixed(1)}%`
}

function points(value: number) {
  return `${(value * 100).toFixed(1)}pct`
}

function endpointLabel(state: TypeIT5EvidenceState['endpoint_state']) {
  if (state === 't2_hit_by_t5') return 'T2已在T+5前到达'
  if (state === 't2_hit_t6_t20') return 'T+6..T+20已到T2'
  if (state === 'pending_t20') return 'T+20观察尚未成熟'
  if (state === 'no_t2_by_t20') return 'T+20内未到T2'
  return '不适用'
}

function groupLabel(group: TypeIT5EvidenceState['historical_group']) {
  if (group === 'exposure') return '对应冻结“5根内完整脱离”组'
  if (group === 'comparator') return '对应冻结“5根内未完整脱离”组'
  return '不进入冻结主检验人群'
}

export default function TypeIT5Evidence({ events }: Props) {
  if (!events.length) return null

  const reference = events[0].historical_evidence
  const replication = reference.external_replication
  const latest = events[0]

  return (
    <section className="type-i-panel" aria-label="type-i-t5-evidence">
      <div className="type-i-heading">
        <div>
          <span className="kicker">SOURCE-ALIGNED TERMINAL BAR · M2.23 / M2.24</span>
          <h2>Type-I T+5 早期证据</h2>
        </div>
        <div className="type-i-latest">
          <span>最近事件</span>
          <strong>{latest.terminal_trade_date}</strong>
        </div>
      </div>

      <div className="type-i-freeze-note">
        <strong>
          冻结45股 Holdout：{reference.status === 'confirmed' ? '已确认' : reference.status}
          {replication ? ` · 独立60股复现：${replication.status === 'confirmed' ? '已确认' : replication.status}` : ''}
        </strong>
        <span>
          原45股中，T+5 内完整脱离 PRZ 组后续 T2 progression 为 {pct(reference.exposure.endpoint_rate)}
          （{reference.exposure.endpoint_hits}/{reference.exposure.records}），未完整脱离组为 {pct(reference.comparator.endpoint_rate)}
          （{reference.comparator.endpoint_hits}/{reference.comparator.records}）；差 {points(reference.absolute_rate_difference)}，
          95% CI {points(reference.newcombe_95_ci.lower)} ～ {points(reference.newcombe_95_ci.upper)}。
        </span>
        {replication && (
          <span className="type-i-replication-line">
            独立60股、与原45股零重叠的冻结复现中，同一两组分别为 {pct(replication.exposure.endpoint_rate)}
            （{replication.exposure.endpoint_hits}/{replication.exposure.records}）与 {pct(replication.comparator.endpoint_rate)}
            （{replication.comparator.endpoint_hits}/{replication.comparator.records}）；差 {points(replication.absolute_rate_difference)}，
            95% CI {points(replication.newcombe_95_ci.lower)} ～ {points(replication.newcombe_95_ci.upper)}，
            provider coverage {replication.successful_symbols}/{replication.requested_symbols}。
          </span>
        )}
        <small>
          只适用于 source-aligned Terminal Bar 且 T+5 时仍未到达 T2 的事件。两组冻结样本只提供历史证据，
          不等于当前个股收益概率、胜率或交易建议，也不修改 Carney 几何身份。
        </small>
      </div>

      <div className="type-i-event-grid">
        {events.slice(0, 6).map((event, index) => (
          <article className={`type-i-event ${index === 0 ? 'latest' : ''}`} key={event.event_id}>
            <div className="type-i-event-head">
              <div>
                <strong>{PATTERN_NAMES[event.pattern_id] ?? event.pattern_id}</strong>
                <span>{event.terminal_trade_date} · S{event.source_scale} · {event.direction === 'bullish' ? '看涨结构' : '看跌结构'}</span>
              </div>
              <b data-state={event.t5_evidence.state}>{event.t5_evidence.display_label}</b>
            </div>
            <dl>
              <div><dt>Terminal</dt><dd>{event.terminal_price.toFixed(2)}</dd></div>
              <div><dt>PRZ</dt><dd>{event.prz.price_low.toFixed(2)}–{event.prz.price_high.toFixed(2)}</dd></div>
              <div><dt>完整脱离</dt><dd>{event.bars_from_terminal_to_full_prz_exit == null ? 'T+5内未见' : `T+${event.bars_from_terminal_to_full_prz_exit}`}</dd></div>
              <div><dt>当前路径</dt><dd>{endpointLabel(event.t5_evidence.endpoint_state)}</dd></div>
            </dl>
            <p className="type-i-group">
              {event.t5_evidence.bars_until_t5 ? `还需 ${event.t5_evidence.bars_until_t5} 根K线完成T+5观察 · ` : ''}
              {groupLabel(event.t5_evidence.historical_group)}
            </p>
          </article>
        ))}
      </div>

      <p className="type-i-separation">证据流来自 no-lookahead forming → Terminal-Bar 回放，与静态 D Pivot 身份分离；不会创建、删除或改写 Carney 几何形态。</p>
    </section>
  )
}
