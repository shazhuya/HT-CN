export type ProductRuntimeStatusPayload = {
  status: string
  healthy?: boolean
  target_trade_date?: string | null
  last_success_trade_date?: string | null
  diagnostics_zh?: string[]
}

export type EvidenceRuntimeStatusPayload = ProductRuntimeStatusPayload & {
  operational_state?: string
  operational_fault?: boolean
  evidence_state?: string
  evidence_insufficient?: boolean
  calibration_state?: string
  latest_committed_capture_date?: string | null
  prospective_candidate_count?: number
  outcome_snapshot_count?: number
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

function evidenceLabel(payload: EvidenceRuntimeStatusPayload | null) {
  if (!payload) return '未读取'
  if (payload.operational_fault) return '运行故障'
  if (payload.status === 'not_started') return '尚未启动'
  if (payload.calibration_state === 'authorized') return '校准已授权'
  if (payload.evidence_insufficient || payload.evidence_state === 'insufficient_evidence') {
    return '证据积累中'
  }
  if (payload.healthy || payload.status === 'idle_current') return '证据服务正常'
  return payload.status
}

function evidenceDetail(payload: EvidenceRuntimeStatusPayload | null) {
  if (!payload) return 'capture — · cohort — · outcome —'
  const capture = payload.latest_committed_capture_date ?? '—'
  const cohort = payload.prospective_candidate_count ?? 0
  const outcome = payload.outcome_snapshot_count ?? 0
  return `capture ${capture} · cohort ${cohort} · outcome ${outcome}`
}

function calibrationLabel(payload: EvidenceRuntimeStatusPayload | null) {
  if (!payload) return 'M8 未读取'
  if (payload.calibration_state === 'authorized') return 'M8 已授权'
  if (payload.calibration_state === 'disabled_operational_fault') return 'M8 因运行故障禁用'
  return 'M8 未启用 · 统计证据不足'
}

export default function ProductRuntimeStatus({
  market,
  harmonic,
  evidence,
}: {
  market: ProductRuntimeStatusPayload | null
  harmonic: ProductRuntimeStatusPayload | null
  evidence: EvidenceRuntimeStatusPayload | null
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
      <article
        data-testid="evidence-runtime-card"
        data-healthy={Boolean(evidence?.healthy && !evidence?.operational_fault)}
        data-insufficient={Boolean(evidence?.evidence_insufficient)}
      >
        <span>后台前瞻证据</span>
        <strong>{evidenceLabel(evidence)}</strong>
        <small>{evidenceDetail(evidence)}</small>
        <small>{calibrationLabel(evidence)}</small>
      </article>
      <div className="product-runtime-boundary">
        <strong>产品边界</strong>
        <span>运行故障与证据不足分开显示；样本不足不会伪装成胜率、Alpha、盈利能力，也不会阻塞正常研究工作台。</span>
      </div>
    </section>
  )
}
