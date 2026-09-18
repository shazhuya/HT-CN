import './ConceptContext.css'

export type ConceptEvidencePayload = {
  sector_code: string
  sector_name: string
  snapshot_trade_date: string | null
  total_member_count: number | null
  median_return_5d_pct: number | null
  median_return_20d_pct: number | null
  pct_above_ma20: number | null
  up_ratio_1d: number | null
  avg_volume_ratio_20: number | null
  instrument_relative_5d_pct: number | null
  instrument_relative_20d_pct: number | null
}

export type ConceptContextPayload = {
  status: string
  mapping_source: string | null
  mapping_observed_on: string | null
  membership_count: number
  resolved_count: number
  concepts: ConceptEvidencePayload[]
  aggregate_method: string
  ordering: string
  mutates_harmonic_identity: boolean
  mutates_source_raw_prz: boolean
  owns_lifecycle: boolean
}

function pct(value: number | null) {
  if (value == null) return '—'
  return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`
}

export default function ConceptContext({ context }: { context?: ConceptContextPayload }) {
  if (!context) return null
  const visible = context.concepts.slice(0, 8)
  const hidden = Math.max(context.concepts.length - visible.length, 0)

  return (
    <section className="concept-context" data-testid="concept-context" aria-label="概念题材环境">
      <div className="concept-context-heading">
        <div>
          <p className="kicker">M3 · CONCEPT / THEME CONTEXT</p>
          <h2>概念题材与相对强弱</h2>
        </div>
        <span>
          {context.status === 'resolved'
            ? `已解析 ${context.resolved_count}/${context.membership_count}`
            : context.status === 'partial'
              ? `部分解析 ${context.resolved_count}/${context.membership_count}`
              : '概念数据不可用'}
        </span>
      </div>

      {visible.length === 0 ? (
        <div className="concept-context-warning">
          当前证券尚未建立可审计概念映射，或本地概念快照尚未生成。
        </div>
      ) : (
        <>
          <div className="concept-context-grid">
            {visible.map((item) => (
              <article key={item.sector_code} data-testid={`concept-${item.sector_code}`}>
                <div className="concept-context-row">
                  <strong>{item.sector_name}</strong>
                  <span>{item.sector_code}</span>
                </div>
                <p>题材中位：5日 {pct(item.median_return_5d_pct)} · 20日 {pct(item.median_return_20d_pct)}</p>
                <p>广度：MA20上方 {pct(item.pct_above_ma20)} · 当日上涨 {pct(item.up_ratio_1d)}</p>
                <p>个股相对题材：5日 {pct(item.instrument_relative_5d_pct)} · 20日 {pct(item.instrument_relative_20d_pct)}</p>
                <small>成分 {item.total_member_count ?? '—'} · 平均量比 {item.avg_volume_ratio_20?.toFixed(2) ?? '—'}</small>
              </article>
            ))}
          </div>
          {hidden > 0 && (
            <p className="concept-context-more">另有 {hidden} 个已映射概念未展开。</p>
          )}
        </>
      )}

      <p className="concept-context-note">
        概念天然多对多；展示顺序仅按概念 5 日中位收益降序，属于透明原始指标，不是“题材评分”。该层不拥有 lifecycle，不修改 harmonic identity 或 Source Raw PRZ。
      </p>
    </section>
  )
}
