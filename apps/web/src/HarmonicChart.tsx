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
  source_note?: string
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
  prz: {
    price_low: number
    price_high: number
    width: number
    component_price_low?: number
    component_price_high?: number
    source_prz_low?: number | null
    source_prz_high?: number | null
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
  const audit = pattern?.reaction_audit
  if (!audit) return []

  return [
    {
      id: 't1',
      label: '后验T1 38.2%',
      price: audit.target_382,
      reached: audit.bars_to_382 != null,
    },
    {
      id: 't2',
      label: '后验T2 61.8%',
      price: audit.target_618,
      reached: audit.bars_to_618 != null,
    },
  ]
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

  const extra = pattern
    ? [pattern.prz.price_low, pattern.prz.price_high, ...targets.map((target) => target.price)]
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
  const lifecycleStart = pattern?.reaction_audit
    ? Math.max(minIndex, Math.min(pattern.reaction_audit.d_index, maxIndex))
    : maxIndex

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
              className={`prz-zone ${pattern.direction}`}
            />
          )}

          {targets.map((target) => (
            <g
              key={target.id}
              className={`lifecycle-target ${target.reached ? 'reached' : 'pending'}`}
              data-testid={`type-i-target-${target.id}`}
              data-state={target.reached ? 'reached' : 'pending'}
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
