import type { AppDestination } from './appTypes'
import type {
  EvidenceRuntimeStatusPayload, ProductRuntimeStatusPayload, ProductSupervisorStatusPayload,
} from './ProductRuntimeStatus'
import './HomeView.css'

export default function HomeView({
  product, market, harmonic, evidence, recentSymbols, onOpenSymbol, onNavigate,
}: {
  product: ProductSupervisorStatusPayload | null
  market: ProductRuntimeStatusPayload | null
  harmonic: ProductRuntimeStatusPayload | null
  evidence: EvidenceRuntimeStatusPayload | null
  recentSymbols: string[]
  onOpenSymbol: (symbol: string) => void
  onNavigate: (destination: AppDestination) => void
}) {
  const productOk = Boolean(product?.healthy || product?.status === 'healthy' || product?.status === 'ready')
  const marketOk = Boolean(market?.healthy || market?.status === 'idle_current')
  const harmonicOk = Boolean(harmonic?.healthy || harmonic?.status === 'idle_current')
  const ready = productOk && marketOk && harmonicOk

  return (
    <section className="home-view" aria-label="首页">
      <div className="home-topline">
        <span>HT-CN / 研究工作台</span>
        <span className={ready ? 'home-connection ready' : 'home-connection'}><i />{ready ? '研究环境已就绪' : '研究环境检查中'}</span>
      </div>
      <div className="home-layout">
        <section className="home-canvas">
          <div className="home-canvas__grid" aria-hidden="true" />
          <div className="home-canvas__message">
            <span className="home-canvas__eyebrow">CHART WORKSPACE</span>
            <h1>今天想研究什么？</h1>
            <p>在顶栏搜索本地股票代码，打开 K 线与谐波结构。图表、Source 时钟和当前判断会出现在同一个工作台。</p>
            <div className="home-canvas__actions">
              <button onClick={() => onNavigate('research')}>打开图表工作台 →</button>
              <button onClick={() => onNavigate('discover')}>查看机会发现</button>
            </div>
            <span className="home-canvas__hint">Ctrl + K 聚焦搜索 · 输入证券代码并回车</span>
          </div>
          <div className="home-canvas__foot">本地研究数据 · 不提供实时报价或自动交易</div>
        </section>
        <aside className="home-utility" aria-label="最近研究与运行概览">
          <div className="home-utility__heading"><strong>最近研究</strong><span>{recentSymbols.length} 个标的</span></div>
          {recentSymbols.length ? (
            <div className="home-recent">
              {recentSymbols.slice(0, 8).map((symbol) => (
                <button key={symbol} onClick={() => onOpenSymbol(symbol)}><strong>{symbol}</strong><span>打开图表 ↗</span></button>
              ))}
            </div>
          ) : (
            <p className="home-utility__empty">还没有最近研究的股票。第一次使用时，在顶栏输入本地证券代码即可。</p>
          )}
          <div className="home-utility__heading second"><strong>运行概览</strong><button onClick={() => onNavigate('system')}>详细状态 →</button></div>
          <div className="home-runtime">
            <div><span>本地行情</span><strong>{market?.last_success_trade_date ?? market?.target_trade_date ?? '等待连接'}</strong></div>
            <div><span>谐波分析</span><strong>{harmonic?.last_success_trade_date ?? harmonic?.target_trade_date ?? '等待连接'}</strong></div>
            <div><span>前瞻证据</span><strong>{evidence?.operational_fault ? '服务异常' : evidence?.evidence_insufficient ? '持续积累中' : '后台运行'}</strong></div>
          </div>
          <p className="home-utility__note">“证据积累中”只限制统计结论，不影响图表研究。</p>
        </aside>
      </div>
    </section>
  )
}
