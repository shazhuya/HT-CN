import type { ReactNode } from 'react'
import type { AppDestination, Health, InstrumentRow } from './appTypes'
import './ApplicationShell.css'

const NAV_ITEMS: Array<{ id: AppDestination; label: string; hint: string; icon: string }> = [
  { id: 'home', label: '首页', hint: '开始与继续研究', icon: '⌂' },
  { id: 'research', label: '个股研究', hint: '图表与当前结构', icon: '⌁' },
  { id: 'discover', label: '机会发现', hint: '全市场候选', icon: '◫' },
  { id: 'system', label: '系统状态', hint: '数据与运行健康', icon: '◌' },
]

export default function ApplicationShell({
  destination,
  onNavigate,
  health,
  symbol,
  onSymbolChange,
  instruments,
  loading,
  onOpenResearch,
  children,
}: {
  destination: AppDestination
  onNavigate: (destination: AppDestination) => void
  health: Health | null
  symbol: string
  onSymbolChange: (symbol: string) => void
  instruments: InstrumentRow[]
  loading: boolean
  onOpenResearch: () => void
  children: ReactNode
}) {
  return (
    <div className="app-frame">
      <aside className="app-sidebar" aria-label="应用导航">
        <button className="app-brand" onClick={() => onNavigate('home')} aria-label="返回首页">
          <span className="app-brand__mark">H</span>
          <span className="app-brand__copy">
            <strong>HT-CN</strong>
            <small>Stable Research</small>
          </span>
        </button>

        <nav className="app-nav">
          {NAV_ITEMS.map((item) => (
            <button
              key={item.id}
              className={destination === item.id ? 'app-nav__item active' : 'app-nav__item'}
              onClick={() => onNavigate(item.id)}
              aria-current={destination === item.id ? 'page' : undefined}
            >
              <span className="app-nav__icon" aria-hidden="true">{item.icon}</span>
              <span>
                <strong>{item.label}</strong>
                <small>{item.hint}</small>
              </span>
            </button>
          ))}
        </nav>

        <div className="app-sidebar__footer">
          <span className={health ? 'status-dot ok' : 'status-dot'} />
          <div>
            <strong>{health ? '本机服务已连接' : '本机服务未连接'}</strong>
            <small>{health ? `API ${health.version}` : '检查启动状态'}</small>
          </div>
        </div>
      </aside>

      <div className="app-main">
        <header className="app-commandbar">
          <div className="app-commandbar__search">
            <span className="search-glyph" aria-hidden="true">⌕</span>
            <label className="visually-hidden" htmlFor="global-symbol-search">搜索股票</label>
            <input
              id="global-symbol-search"
              list="global-instrument-list"
              value={symbol}
              onChange={(event) => onSymbolChange(event.target.value.toUpperCase())}
              onKeyDown={(event) => {
                if (event.key === 'Enter') onOpenResearch()
              }}
              placeholder="输入股票代码，例如 SSE.688256"
              autoComplete="off"
            />
            <datalist id="global-instrument-list">
              {instruments.map((item) => (
                <option key={item.instrument_id} value={item.instrument_id}>
                  {item.has_qfq_factor ? 'QFQ' : 'RAW'}
                </option>
              ))}
            </datalist>
            <button onClick={onOpenResearch} disabled={loading || !symbol.trim()}>
              {loading ? '分析中…' : '打开'}
            </button>
          </div>

          <div className="app-commandbar__meta">
            <span className={health ? 'command-health ok' : 'command-health'}>
              <i />
              {health ? '系统在线' : '服务未连接'}
            </span>
          </div>
        </header>

        <main className="app-content">{children}</main>
      </div>
    </div>
  )
}
