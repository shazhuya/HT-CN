import './ContextIntegrity.css'

export type ContextLayerIntegrityPayload = {
  layer: string
  state: string
  evidence_date: string | null
  source: string | null
  coverage: string | null
  reason: string
}

export type ContextIntegrityPayload = {
  as_of_trade_date: string | null
  summary_state: string
  layers: ContextLayerIntegrityPayload[]
  is_score: boolean
  mutates_harmonic_identity: boolean
  mutates_source_raw_prz: boolean
  owns_lifecycle: boolean
}

const labels: Record<string, string> = {
  execution: 'A股执行制度',
  market: '核心指数',
  industry: '行业',
  concept: '概念题材',
}

const states: Record<string, string> = {
  current: '当前',
  partial: '部分覆盖',
  stale: '已过期',
  missing: '缺失',
  conflicted: '冲突',
  future_observation: '未来观测 · 禁止回填',
  unresolved: '未完整解析',
}

export default function ContextIntegrity({ context }: { context?: ContextIntegrityPayload }) {
  if (!context) return null
  return (
    <section className="context-integrity" data-testid="context-integrity" aria-label="上下文完整性">
      <div className="context-integrity-heading">
        <div>
          <p className="kicker">M3 · CONTEXT INTEGRITY</p>
          <h2>上下文完整性与证据日期</h2>
        </div>
        <span>
          {context.summary_state === 'all_current'
            ? '全部对齐分析交易日'
            : '存在上下文缺口 / 时钟不一致'}
        </span>
      </div>
      <div className="context-integrity-grid">
        {context.layers.map((item) => (
          <article key={item.layer} data-testid={`context-integrity-${item.layer}`} data-state={item.state}>
            <div className="context-integrity-row">
              <strong>{labels[item.layer] ?? item.layer}</strong>
              <b>{states[item.state] ?? item.state}</b>
            </div>
            <p>{item.reason}</p>
            <small>
              证据日 {item.evidence_date ?? '—'}
              {item.coverage ? ` · 覆盖 ${item.coverage}` : ''}
              {item.source ? ` · 来源 ${item.source}` : ''}
            </small>
          </article>
        ))}
      </div>
      <p className="context-integrity-note">
        这不是评分，也不会生成买卖信号；它只回答“哪些上下文当前可用、哪些过期/缺失/冲突，以及证据来自哪一天”。
      </p>
    </section>
  )
}
