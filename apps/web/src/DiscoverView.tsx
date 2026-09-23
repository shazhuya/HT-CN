import OperatorQueue from './OperatorQueue'
import './DestinationView.css'

export default function DiscoverView({
  apiBase,
  onOpenInstrument,
}: {
  apiBase: string
  onOpenInstrument: (instrumentId: string) => void
}) {
  return (
    <section className="destination-view" aria-label="机会发现">
      <div className="page-title-row">
        <div>
          <span className="page-eyebrow">DISCOVERY</span>
          <h1>机会发现</h1>
          <p>这里专门负责“找标的”。选择一个候选后直接进入个股研究，不在这页堆单标的审计信息。</p>
        </div>
      </div>
      <OperatorQueue apiBase={apiBase} onSelectInstrument={onOpenInstrument} />
    </section>
  )
}
