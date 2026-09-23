import ProductRuntimeStatus, {
  type EvidenceRuntimeStatusPayload,
  type ProductRuntimeStatusPayload,
  type ProductSupervisorStatusPayload,
} from './ProductRuntimeStatus'
import './SystemStatusView.css'

function diagnostics(rows: string[] | undefined) {
  return rows?.length ? rows : ['当前没有额外诊断信息。']
}

export default function SystemStatusView({
  product,
  market,
  harmonic,
  evidence,
}: {
  product: ProductSupervisorStatusPayload | null
  market: ProductRuntimeStatusPayload | null
  harmonic: ProductRuntimeStatusPayload | null
  evidence: EvidenceRuntimeStatusPayload | null
}) {
  const evidenceIsFault = Boolean(evidence?.operational_fault)
  const evidenceIsInsufficient = Boolean(evidence?.evidence_insufficient && !evidenceIsFault)

  return (
    <section className="destination-view system-view" aria-label="系统状态">
      <div className="page-title-row">
        <div>
          <span className="page-eyebrow">SYSTEM</span>
          <h1>系统状态</h1>
          <p>正常使用时不需要盯这里。只有行情、分析或后台服务异常时，再来查看具体原因。</p>
        </div>
      </div>

      <ProductRuntimeStatus product={product} market={market} harmonic={harmonic} evidence={evidence} />

      <div className="system-explain-grid">
        <section>
          <span>产品运行</span>
          <h2>{product?.status === 'blocked' ? '需要处理' : product?.healthy || product?.status === 'ready' ? '运行正常' : '状态读取中'}</h2>
          <p>Supervisor 只负责服务启动、恢复和运行健康，不改变谐波或证据语义。</p>
        </section>
        <section>
          <span>证据状态</span>
          <h2>{evidenceIsFault ? '证据服务故障' : evidenceIsInsufficient ? '证据正在积累' : '证据服务正常'}</h2>
          <p>{evidenceIsFault ? '这是运行问题，需要处理。' : '“证据不足”不是产品故障，也不会阻止日常研究功能。'}</p>
        </section>
      </div>

      <div className="system-diagnostics">
        <details>
          <summary>产品运行诊断</summary>
          <ul>{diagnostics(product?.diagnostics_zh).map((item) => <li key={item}>{item}</li>)}</ul>
        </details>
        <details>
          <summary>行情服务诊断</summary>
          <ul>{diagnostics(market?.diagnostics_zh).map((item) => <li key={item}>{item}</li>)}</ul>
        </details>
        <details>
          <summary>谐波运行时诊断</summary>
          <ul>{diagnostics(harmonic?.diagnostics_zh).map((item) => <li key={item}>{item}</li>)}</ul>
        </details>
        <details>
          <summary>前瞻证据诊断</summary>
          <ul>{diagnostics(evidence?.diagnostics_zh).map((item) => <li key={item}>{item}</li>)}</ul>
        </details>
      </div>
    </section>
  )
}
