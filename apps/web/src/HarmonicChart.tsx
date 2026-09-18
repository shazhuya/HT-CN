import type { AShareExecutionContextPayload } from './AShareExecutionContext'
import type { DecisionNarrativePayload } from './DecisionNarrative'
import LifecycleCompass from './LifecycleCompass'
import './HarmonicChartLifecycle.css'

export type Bar = {
  index: number
  trade_date: string
  open: number
  high: number
  low: number
  close: number
  volume: number
}

export type HarmonicPoint = {
  label: string
  index: number
  price: number
  trade_date?: string
}

export type PivotSupport = {
  label: string
  index: number
  kind: 'high' | 'low' | null
  scales: number[]
  support_count: number
  max_scale: number
}

export type PrzComponent = {
  name: string
  price_low: number
  price_high: number
  ratio_low: number
  ratio_high: number
}

export type PriceZoneLayer = {
  price_low: number
  price_high: number
  width: number
  status?: string
}

export type SourcePrzLayer = {
  available: boolean
  price_low: number | null
  price_high: number | null
  width: number | null
  status: 'frozen' | 'unresolved_fail_closed' | string
}

export type ReactionAudit = {
  d_index: number
  bars_observed: number
  target_382: number
  target_618: number
  bars_to_382: number | null
  bars_to_618: number | null
  first_prz_exit_bar: number | null
  secondary_prz_retest_bar: number | null
  source_prz_available: boolean
  full_prz_retest_bar: number | null
  type_ii_terminal_bar?: number | null
  reversal_exit_after_retest_bar: number | null
  bars_to_reversal_exit_after_retest: number | null
  third_prz_test_bar: number | null
  no_prz_retest_first_3_bars: boolean | null
  no_prz_retest_first_5_bars: boolean | null
  max_favorable_price: number | null
  max_favorable_retracement: number | null
  type_ii_candidate: boolean
  rsi_period: number
  rsi_at_d: number | null
  rsi_extreme_bar: number | null
  rsi_extreme_value: number | null
  rsi_trigger_bar: number | null
  rsi_trigger_value: number | null
  rsi_confirmation: boolean
  indicator_evidence_kind?: string
  indicator_evidence_is_rsi_bamm?: boolean
  type_ii_evidence_state:
    | 'not_candidate'
    | 'source_prz_unresolved'
    | 'partial_retest_only'
    | 'full_retest_waiting_price'
    | 'price_confirmed_no_rsi'
    | 'price_and_rsi_confirmed'
    | 'retest_only'
}

export type ReactionTargets = {
  target_50: number
  target_618: number
  reciprocal_abcd: number
  bars_to_50: number | null
  bars_to_618: number | null
  bars_to_reciprocal_abcd: number | null
  initial_target?: number
  initial_target_basis?: string
  bars_to_initial_target?: number | null
  management_rule?: string
  source_note?: string
}

export type SourceLifecycle = {
  state: string
  state_reason: string
  clock_source: string
  current_bar: number
  signal_bar: number | null
  source_prz_entry_bar: number | null
  source_terminal_bar: number | null
  execution_start_bar: number | null
  bars_since_terminal: number | null
  type_i_t1_bar: number | null
  type_i_t2_bar: number | null
  first_source_prz_exit_bar: number | null
  type_ii_retest_entry_bar: number | null
  type_ii_terminal_bar: number | null
  reversal_exit_after_type_ii_bar: number | null
  source_prz_low: number | null
  source_prz_high: number | null
  pez_low: number | null
  pez_high: number | null
  target_382: number | null
  target_618: number | null
  next_key_price: number | null
  next_key_price_role: string | null
  strict_type_ii_full_retest: boolean
  retrospective_geometry_clock_used: boolean
}

export type Pattern = {
  pattern_id: string
  schema?: 'XABCD' | 'ABCD' | '0XABC' | 'FIVE_ZERO'
  direction: 'bullish' | 'bearish'
  state: 'forming' | 'completed'
  scale: number
  geometry_score: number
  points: HarmonicPoint[]
  pivot_support?: PivotSupport[]
  identity_conflicts?: string[]
  is_primary_identity?: boolean
  reaction_audit?: ReactionAudit
  reaction_targets?: ReactionTargets
  completion_class?: string
  reciprocal_inside_execution_band?: boolean
  execution_clock?: Record<string, unknown>
  execution_clock_policy?: string
  source_lifecycle?: SourceLifecycle
  rsi_bamm_evidence?: Record<string, unknown>
  a_share_execution_context?: AShareExecutionContextPayload
  decision_narrative?: DecisionNarrativePayload
  prz: {
    price_low: number
    price_high: number
    width: number
    component_price_low?: number
    component_price_high?: number
    source_prz_low?: number | null
    source_prz_high?: number | null
    semantics_version?: number
    legacy_price_semantics?: string
    ideal_core?: PriceZoneLayer
    component_envelope?: PriceZoneLayer
    source_prz?: SourcePrzLayer
    components: PrzComponent[]
  }
  metrics: Record<string, number>
}

type Props = {
  bars: Bar[]
  pattern: Pattern | null
  focusPattern?: boolean
}

type LifecycleTarget = {
  id: 't1' | 't2'
  label: string
  price: number
  reached: boolean
  sourceClock: boolean
}

type SourceEvent = {
  id: 'prz-entry' | 'tbar' | 'tplus1' | 'type-i-t1' | 'type-i-t2' | 'type-ii-entry' | 'type-ii-terminal' | 'reversal-exit'
  bar: number
  label: string
  emphasis: 'minor' | 'major' | 'confirm'
}

const WIDTH = 1100
const HEIGHT = 520
const LEFT = 62
const RIGHT = 18
const TOP = 20
const BOTTOM = 42

function formatPrice(value: number) {
  return value >= 100 ? value.toFixed(2) : value.toFixed(3)
}

function lifecycleTargets(pattern: Pattern | null): LifecycleTarget[] {
  const lifecycle = pattern?.source_lifecycle
  if (lifecycle?.target_382 != null && lifecycle.target_618 != null) {
    return [
      {
        id: 't1',
        label: 'Source T1 38.2%',
        price: lifecycle.target_382,
        reached: lifecycle.type_i_t1_bar != null,
        sourceClock: true,
      },
      {
        id: 't2',
        label: 'Source T2 61.8%',
        price: lifecycle.target_618,
        reached: lifecycle.type_i_t2_bar != null,
        sourceClock: true,
      },
    ]
  }

  const audit = pattern?.reaction_audit
  if (!audit) return []
  return [
    {
      id: 't1',
      label: '后验T1 38.2%',
      price: audit.target_382,
      reached: audit.bars_to_382 != null,
      sourceClock: false,
    },
    {
      id: 't2',
      label: '后验T2 61.8%',
      price: audit.target_618,
      reached: audit.bars_to_618 != null,
      sourceClock: false,
    },
  ]
}

function sourceEvents(lifecycle: SourceLifecycle | undefined): SourceEvent[] {
  if (!lifecycle) return []
  const candidates: Array<[SourceEvent['id'], number | null, string, SourceEvent['emphasis']]> = [
    ['prz-entry', lifecycle.source_prz_entry_bar, 'Source PRZ进入', 'minor'],
    ['tbar', lifecycle.source_terminal_bar, 'Source T-Bar', 'major'],
    ['tplus1', lifecycle.execution_start_bar, 'T+1', 'major'],
    ['type-i-t1', lifecycle.type_i_t1_bar, 'Type-I 38.2%', 'confirm'],
    ['type-i-t2', lifecycle.type_i_t2_bar, 'Type-I 61.8%', 'confirm'],
    ['type-ii-entry', lifecycle.type_ii_retest_entry_bar, 'Type-II重入', 'minor'],
    ['type-ii-terminal', lifecycle.type_ii_terminal_bar, 'Type-II T-Bar', 'major'],
    ['reversal-exit', lifecycle.reversal_exit_after_type_ii_bar, 'Type-II后离区', 'confirm'],
  ]
  return candidates
    .filter((item): item is [SourceEvent['id'], number, string, SourceEvent['emphasis']] => item[1] != null)
    .map(([id, bar, label, emphasis]) => ({ id, bar, label, emphasis }))
}

function eventPrice(event: SourceEvent, bars: Bar[], pattern: Pattern, lifecycle: SourceLifecycle): number | null {
  const bar = bars.find((item) => item.index === event.bar)
  if (!bar) return null
  if (event.id === 'tbar' || event.id === 'type-ii-terminal') {
    return pattern.direction === 'bullish' ? bar.low : bar.high
  }
  if (event.id === 'type-i-t1' && lifecycle.target_382 != null) return lifecycle.target_382
  if (event.id === 'type-i-t2' && lifecycle.target_618 != null) return lifecycle.target_618
  return bar.close
}

export default function HarmonicChart({ bars, pattern, focusPattern = true }: Props) {
  if (!bars.length) return <div className="chart-empty">暂无 K 线数据</div>

  const fullFirstIndex = bars[0].index
  const fullLastIndex = bars.at(-1)?.index ?? fullFirstIndex
  const patternFirstIndex = pattern?.points[0]?.index ?? fullFirstIndex
  const focusPadding = Math.max(12, Math.min(40, Math.round((fullLastIndex - patternFirstIndex + 1) * 0.35)))
  const viewportStart = focusPattern && pattern
    ? Math.max(fullFirstIndex, patternFirstIndex - focusPadding)
    : fullFirstIndex
  const visibleBars = bars.filter((bar) => bar.index >= viewportStart)
  const targets = lifecycleTargets(pattern)
  const lifecycle = pattern?.source_lifecycle
  const events = sourceEvents(lifecycle)

  const sourcePrices = lifecycle
    ? [
        lifecycle.source_prz_low,
        lifecycle.source_prz_high,
        lifecycle.pez_low,
        lifecycle.pez_high,
        lifecycle.target_382,
        lifecycle.target_618,
      ].filter((value): value is number => value != null)
    : []
  const extra = pattern
    ? [pattern.prz.price_low, pattern.prz.price_high, ...targets.map((target) => target.price), ...sourcePrices]
    : []
  const low = Math.min(...visibleBars.map((bar) => bar.low), ...extra)
  const high = Math.max(...visibleBars.map((bar) => bar.high), ...extra)
  const span = Math.max(high - low, Math.abs(high) * 0.01, 0.01)
  const paddedLow = low - span * 0.04
  const paddedHigh = high + span * 0.04
  const priceSpan = paddedHigh - paddedLow
  const plotWidth = WIDTH - LEFT - RIGHT
  const plotHeight = HEIGHT - TOP - BOTTOM
  const minIndex = visibleBars[0]?.index ?? fullFirstIndex
  const maxIndex = visibleBars.at(-1)?.index ?? fullLastIndex
  const indexSpan = Math.max(maxIndex - minIndex, 1)
  const step = plotWidth / Math.max(visibleBars.length - 1, 1)
  const candleWidth = Math.max(1, Math.min(7, step * 0.64))

  const x = (index: number) => LEFT + ((index - minIndex) / indexSpan) * plotWidth
  const y = (price: number) => TOP + ((paddedHigh - price) / priceSpan) * plotHeight

  const grid = Array.from({ length: 6 }, (_, index) => paddedLow + (priceSpan * index) / 5)
  const patternPoints = pattern?.points.map((point) => `${x(point.index)},${y(point.price)}`).join(' ') ?? ''
  const przStart = pattern ? Math.min(pattern.points.at(-1)?.index ?? maxIndex, maxIndex) : maxIndex
  const lifecycleStart = lifecycle?.source_terminal_bar != null
    ? Math.max(minIndex, Math.min(lifecycle.source_terminal_bar, maxIndex))
    : pattern?.reaction_audit
      ? Math.max(minIndex, Math.min(pattern.reaction_audit.d_index, maxIndex))
      : maxIndex
  const sourceZoneStart = lifecycle?.signal_bar != null
    ? Math.max(minIndex, Math.min(lifecycle.signal_bar, maxIndex))
    : przStart
  const pezStart = lifecycle?.source_terminal_bar != null
    ? Math.max(minIndex, Math.min(lifecycle.source_terminal_bar, maxIndex))
    : null

  return (
    <>
      <LifecycleCompass pattern={pattern} bars={bars} />
      <div className="chart-wrap" aria-label="harmonic-chart">
        <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img" aria-label="A股K线与谐波形态">
          <rect x="0" y="0" width={WIDTH} height={HEIGHT} className="chart-bg" />
          {grid.map((price) => (
            <g key={price}>
              <line x1={LEFT} x2={WIDTH - RIGHT} y1={y(price)} y2={y(price)} className="grid-line" />
              <text x={LEFT - 8} y={y(price) + 4} textAnchor="end" className="axis-label">
                {formatPrice(price)}
              </text>
            </g>
          ))}

          {pattern && (
            <rect
              x={x(przStart)}
              y={y(pattern.prz.price_high)}
              width={Math.max(3, x(maxIndex) - x(przStart))}
              height={Math.max(2, y(pattern.prz.price_low) - y(pattern.prz.price_high))}
              className={`prz-zone legacy-core ${pattern.direction}`}
              aria-label="HT-CN收敛核心-非SourcePRZ"
            />
          )}

          {lifecycle?.source_prz_low != null && lifecycle.source_prz_high != null && (
            <g data-testid="source-prz-zone">
              <rect
                x={x(sourceZoneStart)}
                y={y(lifecycle.source_prz_high)}
                width={Math.max(3, x(maxIndex) - x(sourceZoneStart))}
                height={Math.max(2, y(lifecycle.source_prz_low) - y(lifecycle.source_prz_high))}
                className="source-prz-zone"
              />
              <text x={x(sourceZoneStart) + 6} y={y(lifecycle.source_prz_high) + 13} className="source-zone-label">
                Source Raw PRZ
              </text>
            </g>
          )}

          {pezStart != null && lifecycle?.pez_low != null && lifecycle.pez_high != null && (
            <g data-testid="source-pez-zone">
              <rect
                x={x(pezStart)}
                y={y(lifecycle.pez_high)}
                width={Math.max(3, x(maxIndex) - x(pezStart))}
                height={Math.max(2, y(lifecycle.pez_low) - y(lifecycle.pez_high))}
                className="source-pez-zone"
              />
              <text x={x(pezStart) + 6} y={y(lifecycle.pez_low) - 6} className="source-zone-label pez-label">
                PEZ
              </text>
            </g>
          )}

          {targets.map((target) => (
            <g
              key={target.id}
              className={`lifecycle-target ${target.reached ? 'reached' : 'pending'} ${target.sourceClock ? 'source-clock-target' : 'retrospective-target'}`}
              data-testid={`type-i-target-${target.id}`}
              data-state={target.reached ? 'reached' : 'pending'}
              data-clock={target.sourceClock ? 'source' : 'retrospective'}
            >
              <line
                x1={x(lifecycleStart)}
                x2={x(maxIndex)}
                y1={y(target.price)}
                y2={y(target.price)}
                className="lifecycle-target-line"
              />
              <text
                x={x(maxIndex) - 5}
                y={y(target.price) - 7}
                textAnchor="end"
                className="lifecycle-target-label"
              >
                {target.label} · {formatPrice(target.price)} · {target.reached ? '已到达' : '待到达'}
              </text>
            </g>
          ))}

          {visibleBars.map((bar) => {
            const rising = bar.close >= bar.open
            const top = y(Math.max(bar.open, bar.close))
            const bottom = y(Math.min(bar.open, bar.close))
            return (
              <g key={`${bar.trade_date}-${bar.index}`} className={rising ? 'candle up' : 'candle down'}>
                <line x1={x(bar.index)} x2={x(bar.index)} y1={y(bar.high)} y2={y(bar.low)} />
                <rect
                  x={x(bar.index) - candleWidth / 2}
                  y={top}
                  width={candleWidth}
                  height={Math.max(1.2, bottom - top)}
                />
              </g>
            )
          })}

          {pattern && lifecycle && events.map((event, index) => {
            if (event.bar < minIndex || event.bar > maxIndex) return null
            const markerPrice = eventPrice(event, bars, pattern, lifecycle)
            if (markerPrice == null) return null
            const labelY = TOP + 16 + (index % 3) * 15
            return (
              <g
                key={`${event.id}-${event.bar}`}
                className={`source-event ${event.emphasis}`}
                data-testid={`source-event-${event.id}`}
              >
                <line x1={x(event.bar)} x2={x(event.bar)} y1={TOP} y2={HEIGHT - BOTTOM} className="source-event-line" />
                <circle cx={x(event.bar)} cy={y(markerPrice)} r={event.emphasis === 'major' ? 5 : 4} className="source-event-node" />
                <text x={x(event.bar) + 5} y={labelY} className="source-event-label">
                  {event.label}
                </text>
              </g>
            )
          })}

          {pattern && (
            <>
              <polyline points={patternPoints} className={`pattern-line ${pattern.state}`} />
              {pattern.points.map((point) => (
                <g key={`${point.label}-${point.index}`}>
                  <circle cx={x(point.index)} cy={y(point.price)} r="5" className="pattern-node" />
                  <text x={x(point.index)} y={y(point.price) - 10} textAnchor="middle" className="point-label">
                    {point.label}
                  </text>
                </g>
              ))}
            </>
          )}

          <text x={LEFT} y={HEIGHT - 12} className="axis-label">
            {visibleBars[0]?.trade_date}
          </text>
          <text x={WIDTH - RIGHT} y={HEIGHT - 12} textAnchor="end" className="axis-label">
            {visibleBars.at(-1)?.trade_date}
          </text>
        </svg>
      </div>
    </>
  )
}
