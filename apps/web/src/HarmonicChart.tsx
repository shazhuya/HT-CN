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

export type PrzComponent = {
  name: string
  price_low: number
  price_high: number
  ratio_low: number
  ratio_high: number
}

export type Pattern = {
  pattern_id: string
  direction: 'bullish' | 'bearish'
  state: 'forming' | 'completed'
  scale: number
  geometry_score: number
  points: HarmonicPoint[]
  prz: {
    price_low: number
    price_high: number
    width: number
    components: PrzComponent[]
  }
  metrics: Record<string, number>
}

type Props = {
  bars: Bar[]
  pattern: Pattern | null
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

export default function HarmonicChart({ bars, pattern }: Props) {
  if (!bars.length) return <div className="chart-empty">暂无 K 线数据</div>

  const extra = pattern ? [pattern.prz.price_low, pattern.prz.price_high] : []
  const low = Math.min(...bars.map((bar) => bar.low), ...extra)
  const high = Math.max(...bars.map((bar) => bar.high), ...extra)
  const span = Math.max(high - low, Math.abs(high) * 0.01, 0.01)
  const paddedLow = low - span * 0.04
  const paddedHigh = high + span * 0.04
  const priceSpan = paddedHigh - paddedLow
  const plotWidth = WIDTH - LEFT - RIGHT
  const plotHeight = HEIGHT - TOP - BOTTOM
  const step = plotWidth / Math.max(bars.length - 1, 1)
  const candleWidth = Math.max(1, Math.min(7, step * 0.64))

  const x = (index: number) => LEFT + (index / Math.max(bars.length - 1, 1)) * plotWidth
  const y = (price: number) => TOP + ((paddedHigh - price) / priceSpan) * plotHeight

  const grid = Array.from({ length: 6 }, (_, index) => paddedLow + (priceSpan * index) / 5)
  const patternPoints = pattern?.points.map((point) => `${x(point.index)},${y(point.price)}`).join(' ') ?? ''
  const lastIndex = bars.length - 1
  const przStart = pattern ? Math.min(pattern.points.at(-1)?.index ?? lastIndex, lastIndex) : lastIndex

  return (
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
            width={Math.max(3, x(lastIndex) - x(przStart))}
            height={Math.max(2, y(pattern.prz.price_low) - y(pattern.prz.price_high))}
            className={`prz-zone ${pattern.direction}`}
          />
        )}

        {bars.map((bar) => {
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
          {bars[0]?.trade_date}
        </text>
        <text x={WIDTH - RIGHT} y={HEIGHT - 12} textAnchor="end" className="axis-label">
          {bars.at(-1)?.trade_date}
        </text>
      </svg>
    </div>
  )
}
