import { useMemo, useState } from 'react'
import type { Analysis, InstrumentRow } from './appTypes'

const STORAGE_KEY = 'htcn.watchlist.v1'

function savedWatchlist(): string[] {
  try {
    const value: unknown = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '[]')
    return Array.isArray(value)
      ? value.filter((item): item is string => typeof item === 'string').slice(0, 40)
      : []
  } catch {
    return []
  }
}

export default function WatchlistPanel({
  instruments, analysis, onOpenInstrument,
}: {
  instruments: InstrumentRow[]
  analysis: Analysis
  onOpenInstrument: (symbol: string) => void
}) {
  const [saved, setSaved] = useState(savedWatchlist)
  const [filter, setFilter] = useState('')
  const [adding, setAdding] = useState(false)
  const available = useMemo(() => new Set(instruments.map((item) => item.instrument_id)), [instruments])
  const current = analysis.instrument_id
  const watchlist = saved.length ? saved : [current, ...instruments.slice(0, 8).map((item) => item.instrument_id)]
  const rows = [...new Set([current, ...watchlist])]
    .filter((item) => item.toLowerCase().includes(filter.trim().toLowerCase()))
    .slice(0, 40)

  function persist(next: string[]) {
    setSaved(next)
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
  }

  function add(value: string) {
    const normalized = value.trim().toUpperCase()
    if (!available.has(normalized) && normalized !== current) return
    persist([...new Set([...watchlist, normalized])].slice(0, 40))
    setFilter('')
    setAdding(false)
  }

  return (
    <section className="watchlist-panel" aria-label="自选股列表">
      <div className="watchlist-panel__heading">
        <strong>自选列表</strong>
        <button type="button" onClick={() => setAdding(!adding)} aria-label="添加自选股" title="添加自选股">＋</button>
      </div>
      <div className="watchlist-panel__search">
        <input
          aria-label={adding ? '输入代码添加自选股' : '筛选自选股'} value={filter}
          onChange={(event) => setFilter(event.target.value)}
          onKeyDown={(event) => { if (event.key === 'Enter' && adding) add(filter) }}
          placeholder={adding ? '输入本地证券代码后回车' : '筛选代码…'}
          list={adding ? 'watchlist-available' : undefined}
        />
        <datalist id="watchlist-available">
          {instruments.slice(0, 10000).map((item) => <option key={item.instrument_id} value={item.instrument_id} />)}
        </datalist>
        {adding && <button type="button" onClick={() => add(filter)} aria-label="确认添加自选股">添加</button>}
      </div>
      <div className="watchlist-panel__columns"><span>本地证券</span><span>最近收盘</span></div>
      <div className="watchlist-panel__rows">
        {rows.length === 0 && <p className="watchlist-panel__empty">未找到该代码。可点 ＋ 添加本地已初始化标的。</p>}
        {rows.map((item) => (
          <div key={item} className={item === current ? 'watchlist-panel__row selected' : 'watchlist-panel__row'}>
            <button type="button" onClick={() => onOpenInstrument(item)} aria-current={item === current ? 'true' : undefined} aria-label={`打开 ${item} 图表`}>
              <span>{item}<small>{item === current ? '当前图表' : '点击查看'}</small></span>
              <b>{item === current ? analysis.bars.at(-1)?.close.toFixed(2) ?? '—' : '—'}</b>
            </button>
            {saved.includes(item) && (
              <button type="button" className="watchlist-panel__remove" onClick={() => persist(saved.filter((savedItem) => savedItem !== item))} aria-label={`从自选股移除 ${item}`} title="从自选股移除">×</button>
            )}
          </div>
        ))}
      </div>
      <p className="watchlist-panel__foot">仅当前图表显示本地最近收盘价 · {analysis.last_trade_date}；其余证券暂不提供实时报价</p>
    </section>
  )
}
