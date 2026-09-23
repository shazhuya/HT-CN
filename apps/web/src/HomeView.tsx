import type { AppDestination } from './appTypes'
import type {
  EvidenceRuntimeStatusPayload,
  ProductRuntimeStatusPayload,
  ProductSupervisorStatusPayload,
} from './ProductRuntimeStatus'
import './HomeView.css'

function readiness(
  product: ProductSupervisorStatusPayload | null,
  market: ProductRuntimeStatusPayload | null,
  harmonic: ProductRuntimeStatusPayload | null,
) {
  const productOk = Boolean(product?.healthy || product?.status === 'healthy' || product?.status === 'ready')
  const marketOk = Boolean(market?.healthy || market?.status === 'idle_current')
  const harmonicOk = Boolean(harmonic?.healthy || harmonic?.status === 'idle_current')
  if (productOk && marketOk && harmonicOk) return { label: '可以开始研究', tone: 'ok' }
  if (product?.status === 'blocked') return { label: '系统需要处理', tone: 'blocked' }
  return { label: '正在准备服务', tone: 'pending' }
}

export default function HomeView({
  product,
  market,
  harmonic,
  evidence,
  recentSymbols,
  onOpenSymbol,
  onNavigate,
}: {
  product: ProductSupervisorStatusPayload | null
  market: ProductRuntimeStatusPayload | null
  harmonic: ProductRuntimeStatusPayload | null
  evidence: EvidenceRuntimeStatusPayload | null
  recentSymbols: string[]
  onOpenSymbol: (symbol: string) => void
  onNavigate: (destination: AppDestination) => void
}) {
  const state = readiness(product, market, harmonic)
  const marketDate = market?.last_success_trade_date ?? market?.target_trade_date ?? '—'
  const harmonicDate = harmonic?.last_success_trade_date ?? harmonic?.target_trade_date ?? '—'
  const evidenceText = evidence?.operational_fault
    ? '证据服务异常'
    : evidence?.evidence_insufficient
      ? '证据仍在积累'
      : '证据服务正常'

  return (
    <section className="home-view" aria-label="首页">
      <div className="page-title-row">
        <div>
          <span className="page-eyebrow">HT-CN</span>
          <h1>今天想研究什么？</h1>
          <p>在上方输入股票代码即可开始。研究、机会发现和系统状态已经分开，不需要在一个长页面里找功能。</p>
        </div>
        <span className={'home-ready-badge ' + state.tone}>{state.label}</span>
      </div>

      <section className="home-hero">
        <div className="home-hero__copy">
          <span>最快开始方式</span>
          <h2>搜索一只股票，直接进入图表与当前结构</h2>
          <p>打开研究后，先看主图和右侧当前阶段；需要比例、环境或审计时再切换页签。</p>
          <div className="home-hero__actions">
            <button className="primary" onClick={() => onNavigate('research')}>进入个股研究</button>
            <button onClick={() => onNavigate('discover')}>浏览机会候选</button>
          </div>
        </div>
        <div className="home-hero__flow" aria-hidden="true">
          <div><b>1</b><span>搜索股票</span></div>
          <i />
          <div><b>2</b><span>看主图</span></div>
          <i />
          <div><b>3</b><span>看下一关键条件</span></div>
        </div>
      </section>

      <div className="home-grid">
        <section className="home-card recent-card">
          <div className="home-card__heading">
            <div>
              <span>最近研究</span>
              <h2>继续刚才的股票</h2>
            </div>
          </div>
          {recentSymbols.length > 0 ? (
            <div className="recent-list">
              {recentSymbols.slice(0, 6).map((symbol) => (
                <button key={symbol} onClick={() => onOpenSymbol(symbol)}>
                  <span>{symbol}</span>
                  <small>继续研究 →</small>
                </button>
              ))}
            </div>
          ) : (
            <div className="home-empty">
              <strong>还没有最近研究</strong>
              <span>从顶部搜索框输入第一只股票即可。</span>
            </div>
          )}
        </section>

        <section className="home-card health-card">
          <div className="home-card__heading">
            <div>
              <span>研究环境</span>
              <h2>今天的数据是否可用</h2>
            </div>
            <button className="text-button" onClick={() => onNavigate('system')}>查看详情</button>
          </div>
          <div className="health-list">
            <div>
              <i className={market?.healthy || market?.status === 'idle_current' ? 'ok' : ''} />
              <span>行情数据</span>
              <strong>{marketDate}</strong>
            </div>
            <div>
              <i className={harmonic?.healthy || harmonic?.status === 'idle_current' ? 'ok' : ''} />
              <span>谐波分析</span>
              <strong>{harmonicDate}</strong>
            </div>
            <div>
              <i className={evidence?.operational_fault ? 'bad' : 'ok'} />
              <span>前瞻证据</span>
              <strong>{evidenceText}</strong>
            </div>
          </div>
        </section>

        <button className="home-shortcut" onClick={() => onNavigate('discover')}>
          <span className="home-shortcut__icon">◫</span>
          <span>
            <strong>机会发现</strong>
            <small>从全市场候选中找值得打开的结构</small>
          </span>
          <b>→</b>
        </button>

        <button className="home-shortcut" onClick={() => onNavigate('system')}>
          <span className="home-shortcut__icon">◌</span>
          <span>
            <strong>系统状态</strong>
            <small>只有出现数据或运行问题时才需要来这里</small>
          </span>
          <b>→</b>
        </button>
      </div>
    </section>
  )
}
