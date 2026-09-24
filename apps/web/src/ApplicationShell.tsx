import { useEffect, useRef, type ReactNode } from 'react'
import type { AppDestination, Health, InstrumentRow } from './appTypes'
import './ApplicationShell.css'

const NAV_ITEMS: Array<{ id: AppDestination; label: string; path: ReactNode }> = [
  { id: 'home', label: '首页', path: <path d="m3 10 9-7 9 7v11h-7v-7h-4v7H3z" /> },
  { id: 'research', label: '个股研究', path: <><path d="M3 3v18h18" /><path d="m5 16 5-5 4 3 6-8" /></> },
  { id: 'discover', label: '机会发现', path: <><circle cx="11" cy="11" r="7" /><path d="m16 16 5 5M8 11h6m-3-3v6" /></> },
  { id: 'system', label: '系统状态', path: <><circle cx="12" cy="12" r="8" /><path d="M12 8v4l3 2" /></> },
]

export default function ApplicationShell({
  destination, onNavigate, health, symbol, onSymbolChange, instruments, loading, onOpenResearch, children,
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
  const searchRef = useRef<HTMLInputElement>(null)
  useEffect(() => {
    function onShortcut(event: KeyboardEvent) {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault()
        searchRef.current?.focus()
        searchRef.current?.select()
      }
    }
    window.addEventListener('keydown', onShortcut)
    return () => window.removeEventListener('keydown', onShortcut)
  }, [])

  return (
    <div className={`app-frame app-frame--${destination}`}>
      <header className="app-commandbar">
        <button className="app-brand" onClick={() => onNavigate('home')} aria-label="返回首页" title="HT-CN 首页">
          <span className="app-brand__mark">H</span><strong>HT-CN</strong>
        </button>
        <div className="app-commandbar__search">
          <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="7" /><path d="m16 16 5 5" /></svg>
          <label className="visually-hidden" htmlFor="global-symbol-search">搜索股票</label>
          <input
            ref={searchRef} id="global-symbol-search" list="global-instrument-list" value={symbol}
            onChange={(event) => onSymbolChange(event.target.value.toUpperCase())}
            onKeyDown={(event) => { if (event.key === 'Enter') onOpenResearch() }}
            placeholder="输入代码，如 SSE.688256" autoComplete="off"
          />
          <datalist id="global-instrument-list">
            {instruments.map((item) => <option key={item.instrument_id} value={item.instrument_id} />)}
          </datalist>
          <kbd>Ctrl K</kbd>
          <button aria-label="打开研究工作台 · 运行谐波分析" onClick={onOpenResearch} disabled={loading || !symbol.trim()}>
            {loading ? '分析中…' : '打开图表'}
          </button>
        </div>
        <div className="app-commandbar__meta">
          <span className={health ? 'command-health ok' : 'command-health'} title={health ? `API ${health.version}` : '本机 API 尚未连接'}>
            <i />{health ? '本机已连接' : '服务未连接'}
          </span>
          <button type="button" onClick={() => onNavigate('system')} aria-label="查看系统状态" title="系统状态">⋯</button>
        </div>
      </header>
      <aside className="app-sidebar" aria-label="应用导航">
        <nav className="app-nav">
          {NAV_ITEMS.map((item) => (
            <button
              key={item.id} className={destination === item.id ? 'app-nav__item active' : 'app-nav__item'}
              onClick={() => onNavigate(item.id)} aria-current={destination === item.id ? 'page' : undefined}
              aria-label={item.label} title={item.label}
            >
              <svg viewBox="0 0 24 24" aria-hidden="true">{item.path}</svg><span>{item.label}</span>
            </button>
          ))}
        </nav>
        <div className="app-sidebar__footer" title="HT-CN · 仅辅助人工决策">H</div>
      </aside>
      <main className="app-content">{children}</main>
    </div>
  )
}
