export type ProductRuntimeStatusPayload = {
  status: string
  healthy?: boolean
  target_trade_date?: string | null
  last_success_trade_date?: string | null
  diagnostics_zh?: string[]
}

function statusLabel(payload: ProductRuntimeStatusPayload | null, kind: 'market' | 'harmonic') {
  if (!payload) return '未读取'
  if (payload.healthy) return kind === 'market' ? '数据已就绪' : '分析已同步'
  if (payload.status === 'idle_current') return kind === 'market' ? '数据已就绪' : '分析已同步'
  if (payload.status === 'not_started') return '尚未启动'
  return payload.status
}

function dateLabel(payload: ProductRuntimeStatusPayload | null) {
  if (!payload) return '—'
  return payload.last_success_trade_date ?? payload.target_trade_date ?? '—'
}

export default function ProductRuntimeStatus({
  market,
  harmonic,
}: {
  market: ProductRuntimeStatusPayload | null
  harmonic: ProductRuntimeStatusPayload | null
}) {
  return (
    <section className="product-runtime-strip" aria-label="product-runtime-status">
      <article data-testid="market-data-runtime-card" data-healthy={Boolean(market?.healthy)}>
        <span>自动行情服务</span>
        <strong>{statusLabel(market, 'market')}</strong>
        <small>水位 {dateLabel(market)}</small>
      </article>
      <article data-testid="harmonic-runtime-card" data-healthy={Boolean(harmonic?.healthy || harmonic?.status === 'idle_current')}>
        <span>自动谐波运行时</span>
        <strong>{statusLabel(harmonic, 'harmonic')}</strong>
        <small>水位 {dateLabel(harmonic)}</small>
      </article>
      <div className="product-runtime-boundary">
        <strong>产品边界</strong>
        <span>数据变化触发分析；拖动、缩放、crosshair 只改变视图，不重算谐波身份。</span>
      </div>
    </section>
  )
}
