import './MarketContext.css'

export type BenchmarkContextPayload = {
  key: string
  symbol: string
  name_zh: string
  available: boolean
  as_of_trade_date: string | null
  close: number | null
  return_1d_pct: number | null
  return_5d_pct: number | null
  return_20d_pct: number | null
  ma20: number | null
  distance_to_ma20_pct: number | null
  ma20_slope_5d_pct: number | null
  trend_state: string
  instrument_relative_5d_pct: number | null
  instrument_relative_20d_pct: number | null
}

export type MarketContextPayload = {
  status: string
  as_of_trade_date: string | null
  benchmarks: BenchmarkContextPayload[]
  mutates_harmonic_identity: boolean
  mutates_source_raw_prz: boolean
  owns_lifecycle: boolean
}

function pct(value: number | null) {
  if (value == null) return '—'
  return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`
}

function trend(value: string) {
  if (value === 'above_rising_ma20') return 'MA20 上方且均线抬升'
  if (value === 'below_falling_ma20') return 'MA20 下方且均线下行'
  if (value === 'mixed_ma20') return 'MA20 状态混合'
  if (value === 'insufficient_history') return '历史不足'
  return '未同步'
}

export default function MarketContext({ context }: { context?: MarketContextPayload }) {
  if (!context) return null
  return (
    <section className="market-context" data-testid="market-context" aria-label="核心市场环境">
      <div className="market-context-heading">
        <div>
          <p className="kicker">M3 · CORE MARKET CONTEXT</p>
          <h2>核心市场环境与相对强弱</h2>
        </div>
        <span>{context.status === 'complete' ? '四指数齐全' : context.status === 'partial' ? '部分可用' : '未同步 · Fail Safe'}</span>
      </div>
      <div className="market-context-grid">
        {context.benchmarks.map((item) => (
          <article key={item.key} data-testid={`market-benchmark-${item.key}`}>
            <div className="market-context-row">
              <strong>{item.name_zh}</strong>
              <span>{item.symbol}</span>
            </div>
            {!item.available ? (
              <p>本地 benchmark 未同步，不据此推断市场状态。</p>
            ) : (
              <>
                <p>1日 {pct(item.return_1d_pct)} · 5日 {pct(item.return_5d_pct)} · 20日 {pct(item.return_20d_pct)}</p>
                <p>{trend(item.trend_state)} · 离 MA20 {pct(item.distance_to_ma20_pct)}</p>
                <p>个股相对强弱：5日 {pct(item.instrument_relative_5d_pct)} · 20日 {pct(item.instrument_relative_20d_pct)}</p>
              </>
            )}
          </article>
        ))}
      </div>
      <p className="market-context-note">
        该层只描述指数趋势和个股相对强弱，不创建、修复或否定谐波身份，不修改 Source Raw PRZ，也不拥有 lifecycle。
      </p>
    </section>
  )
}
