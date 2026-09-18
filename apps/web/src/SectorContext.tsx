import './SectorContext.css'

export type SectorCandidatePayload = {
  sector_code: string
  sector_name: string
}

export type IndustryContextPayload = {
  status: string
  sector_kind: string
  sector_code: string | null
  sector_name: string | null
  mapping_source: string | null
  mapping_observed_on: string | null
  candidate_sectors: SectorCandidatePayload[]
  snapshot_trade_date: string | null
  total_member_count: number | null
  return_1d_count: number | null
  return_5d_count: number | null
  return_20d_count: number | null
  mean_return_1d_pct: number | null
  median_return_1d_pct: number | null
  mean_return_5d_pct: number | null
  median_return_5d_pct: number | null
  mean_return_20d_pct: number | null
  median_return_20d_pct: number | null
  pct_above_ma20: number | null
  up_ratio_1d: number | null
  down_ratio_1d: number | null
  avg_volume_ratio_20: number | null
  instrument_relative_5d_vs_sector_median_pct: number | null
  instrument_relative_20d_vs_sector_median_pct: number | null
  aggregate_method: string
  mutates_harmonic_identity: boolean
  mutates_source_raw_prz: boolean
  owns_lifecycle: boolean
}

function pct(value: number | null) {
  if (value == null) return '—'
  return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`
}

export default function SectorContext({ context }: { context?: IndustryContextPayload }) {
  if (!context) return null
  const resolved = context.status === 'resolved'
  return (
    <section className="sector-context" data-testid="sector-context" aria-label="行业与板块环境">
      <div className="sector-context-heading">
        <div>
          <p className="kicker">M3 · INDUSTRY CONTEXT</p>
          <h2>行业环境与分层相对强弱</h2>
        </div>
        <span>
          {resolved
            ? '已解析'
            : context.status === 'membership_ambiguous'
              ? '行业映射冲突 · Fail Safe'
              : '行业数据不可用'}
        </span>
      </div>

      {context.status === 'membership_ambiguous' ? (
        <div className="sector-context-warning">
          同一来源返回多个行业：{context.candidate_sectors.map((item) => `${item.sector_name}(${item.sector_code})`).join('、')}。系统不擅自选择行业，因此不计算板块相对强弱。
        </div>
      ) : !resolved ? (
        <div className="sector-context-warning">
          {context.sector_name
            ? `${context.sector_name} 已映射，但本地行业快照尚未生成。`
            : '尚未建立可审计的证券→行业映射。'}
        </div>
      ) : (
        <>
          <div className="sector-context-grid">
            <article>
              <span>行业</span>
              <strong>{context.sector_name}</strong>
              <small>{context.sector_code} · 成分 {context.total_member_count ?? '—'} 家</small>
            </article>
            <article>
              <span>行业中位收益</span>
              <strong>1日 {pct(context.median_return_1d_pct)}</strong>
              <small>5日 {pct(context.median_return_5d_pct)} · 20日 {pct(context.median_return_20d_pct)}</small>
            </article>
            <article>
              <span>内部广度</span>
              <strong>MA20上方 {pct(context.pct_above_ma20)}</strong>
              <small>上涨 {pct(context.up_ratio_1d)} · 下跌 {pct(context.down_ratio_1d)}</small>
            </article>
            <article>
              <span>个股相对行业</span>
              <strong>5日 {pct(context.instrument_relative_5d_vs_sector_median_pct)}</strong>
              <small>20日 {pct(context.instrument_relative_20d_vs_sector_median_pct)} · 行业量比 {context.avg_volume_ratio_20?.toFixed(2) ?? '—'}</small>
            </article>
          </div>
          <p className="sector-context-meta">
            行业映射：{context.mapping_source} · 观察于 {context.mapping_observed_on ?? '—'}；行业强弱由本地 M1 成分股等权均值/中位数重算，不使用黑箱行业评分。
          </p>
        </>
      )}

      <p className="sector-context-note">
        行业层只作为 environment / relative-strength evidence，不拥有 lifecycle，不修改 harmonic identity 或 Source Raw PRZ。
      </p>
    </section>
  )
}
