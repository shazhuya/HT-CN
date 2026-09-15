import { useEffect, useMemo, useState } from 'react'
import HarmonicChart, { Bar, Pattern } from './HarmonicChart'

type Health = {
  status: string
  service: string
  version: string
}

type InstrumentRow = {
  instrument_id: string
  has_qfq_factor: boolean
}

type Analysis = {
  instrument_id: string
  price_mode: string
  warning: string | null
  bars_requested: number
  bars_returned: number
  first_trade_date: string
  last_trade_date: string
  scales: number[]
  bars: Bar[]
  completed: Pattern[]
  forming: Pattern[]
  pivot_counts: Record<string, number>
  engine_note: string
}

const API = 'http://127.0.0.1:8765'
const PATTERN_NAMES: Record<string, string> = {
  gartley: 'Gartley',
  bat: 'Bat',
  alternate_bat: 'Alternate Bat',
  butterfly: 'Butterfly',
  crab: 'Crab',
  deep_crab: 'Deep Crab',
}

function patternName(id: string) {
  return PATTERN_NAMES[id] ?? id
}

function fmt(value: number | undefined) {
  return value == null ? '—' : value.toFixed(3)
}

export default function App() {
  const [health, setHealth] = useState<Health | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [instruments, setInstruments] = useState<InstrumentRow[]>([])
  const [symbol, setSymbol] = useState('SSE.688256')
  const [bars, setBars] = useState(420)
  const [analysis, setAnalysis] = useState<Analysis | null>(null)
  const [loading, setLoading] = useState(false)
  const [selectedKey, setSelectedKey] = useState<string | null>(null)

  useEffect(() => {
    fetch(`${API}/api/health`)
      .then((response) => {
        if (!response.ok) throw new Error(`HTTP ${response.status}`)
        return response.json() as Promise<Health>
      })
      .then(setHealth)
      .catch((err: Error) => setError(err.message))

    fetch(`${API}/api/instruments?limit=500`)
      .then((response) => response.json())
      .then((payload: { items?: InstrumentRow[] }) => setInstruments(payload.items ?? []))
      .catch(() => undefined)
  }, [])

  const allPatterns = useMemo(() => {
    if (!analysis) return []
    return [...analysis.completed, ...analysis.forming]
  }, [analysis])

  const selectedPattern = useMemo(() => {
    if (!allPatterns.length) return null
    const key = (pattern: Pattern) => `${pattern.state}:${pattern.pattern_id}:${pattern.scale}:${pattern.points.map((p) => p.index).join('-')}`
    return allPatterns.find((pattern) => key(pattern) === selectedKey) ?? allPatterns[0]
  }, [allPatterns, selectedKey])

  const patternKey = (pattern: Pattern) => `${pattern.state}:${pattern.pattern_id}:${pattern.scale}:${pattern.points.map((p) => p.index).join('-')}`

  function runAnalysis() {
    setLoading(true)
    setError(null)
    setSelectedKey(null)
    fetch(`${API}/api/harmonic/${encodeURIComponent(symbol.trim())}?bars=${bars}&scales=3,5,8,13`)
      .then(async (response) => {
        if (!response.ok) {
          const body = (await response.json().catch(() => null)) as { detail?: string } | null
          throw new Error(body?.detail ?? `HTTP ${response.status}`)
        }
        return response.json() as Promise<Analysis>
      })
      .then(setAnalysis)
      .catch((err: Error) => {
        setAnalysis(null)
        setError(err.message)
      })
      .finally(() => setLoading(false))
  }

  return (
    <main className="shell">
      <section className="hero compact">
        <div>
          <p className="eyebrow">HT-CN LOCAL · M2 HARMONIC CORE</p>
          <h1>A 股谐波研究与辅助决策系统</h1>
          <p className="subtitle">Carney 几何识别 · QFQ 连续价格 · 多尺度 Pivot · PRZ 审计</p>
        </div>
        <div className="health-pill" data-ok={Boolean(health)}>
          <span className="health-dot" />
          {health ? `API ${health.version}` : 'API 未连接'}
        </div>
      </section>

      <section className="controls" aria-label="analysis-controls">
        <label>
          <span>证券代码</span>
          <input
            list="instrument-list"
            value={symbol}
            onChange={(event) => setSymbol(event.target.value.toUpperCase())}
            placeholder="SSE.688256"
          />
          <datalist id="instrument-list">
            {instruments.map((item) => (
              <option key={item.instrument_id} value={item.instrument_id}>
                {item.has_qfq_factor ? 'QFQ' : 'RAW'}
              </option>
            ))}
          </datalist>
        </label>
        <label>
          <span>K 线数量</span>
          <select value={bars} onChange={(event) => setBars(Number(event.target.value))}>
            <option value={240}>240</option>
            <option value={420}>420</option>
            <option value={720}>720</option>
            <option value={1200}>1200</option>
          </select>
        </label>
        <button onClick={runAnalysis} disabled={loading || !symbol.trim()}>
          {loading ? '分析中…' : '运行谐波分析'}
        </button>
      </section>

      {error && <p className="error">{error}</p>}

      {!analysis && !error && (
        <section className="placeholder">
          <h2>M2 谐波工作台</h2>
          <p>输入已建库的沪深 A 股代码，运行本地多尺度谐波识别。识别核心与 A 股交易判断分离。</p>
        </section>
      )}

      {analysis && (
        <>
          <section className="summary-grid">
            <div><span>价格视图</span><strong>{analysis.price_mode.toUpperCase()}</strong></div>
            <div><span>区间</span><strong>{analysis.first_trade_date} → {analysis.last_trade_date}</strong></div>
            <div><span>实际K线</span><strong>{analysis.bars_returned} / {analysis.bars_requested}</strong></div>
            <div><span>完成形态</span><strong>{analysis.completed.length}</strong></div>
            <div><span>形成中</span><strong>{analysis.forming.length}</strong></div>
          </section>

          {analysis.warning && <div className="warning-card">{analysis.warning}</div>}

          <section className="workspace">
            <div className="chart-panel">
              <div className="panel-heading">
                <div>
                  <span className="kicker">{analysis.instrument_id}</span>
                  <h2>{selectedPattern ? `${patternName(selectedPattern.pattern_id)} · ${selectedPattern.state === 'completed' ? '已完成' : '形成中'}` : '暂无有效形态'}</h2>
                </div>
                {selectedPattern && (
                  <div className="score-box">
                    <span>几何评分</span>
                    <strong>{selectedPattern.geometry_score.toFixed(1)}</strong>
                  </div>
                )}
              </div>
              <HarmonicChart bars={analysis.bars} pattern={selectedPattern} />
              <p className="engine-note">{analysis.engine_note}</p>
            </div>

            <aside className="pattern-panel">
              <div className="panel-heading small">
                <div>
                  <span className="kicker">候选列表</span>
                  <h2>形态与 PRZ</h2>
                </div>
              </div>
              <div className="pattern-list">
                {allPatterns.length === 0 && <p className="muted">当前窗口没有通过规则的 XABCD 候选。</p>}
                {allPatterns.map((pattern) => {
                  const key = patternKey(pattern)
                  return (
                    <button
                      key={key}
                      className={`pattern-item ${selectedPattern && patternKey(selectedPattern) === key ? 'active' : ''}`}
                      onClick={() => setSelectedKey(key)}
                    >
                      <div>
                        <strong>{patternName(pattern.pattern_id)}</strong>
                        <span>{pattern.state === 'completed' ? '已完成' : '形成中'} · S{pattern.scale} · {pattern.direction === 'bullish' ? '看涨结构' : '看跌结构'}</span>
                      </div>
                      <b>{pattern.geometry_score.toFixed(0)}</b>
                    </button>
                  )
                })}
              </div>

              {selectedPattern && (
                <div className="audit-card">
                  <h3>比例审计</h3>
                  <dl>
                    <div><dt>B/XA</dt><dd>{fmt(selectedPattern.metrics.b_xa)}</dd></div>
                    <div><dt>C/AB</dt><dd>{fmt(selectedPattern.metrics.c_ab)}</dd></div>
                    <div><dt>BC投影</dt><dd>{fmt(selectedPattern.metrics.bc_projection)}</dd></div>
                    <div><dt>D/XA</dt><dd>{fmt(selectedPattern.metrics.d_xa)}</dd></div>
                    <div><dt>CD/AB</dt><dd>{fmt(selectedPattern.metrics.cd_ab)}</dd></div>
                  </dl>
                  <h3>PRZ</h3>
                  <p className="prz-price">{selectedPattern.prz.price_low.toFixed(2)} – {selectedPattern.prz.price_high.toFixed(2)}</p>
                  <ul>
                    {selectedPattern.prz.components.map((component) => (
                      <li key={`${component.name}-${component.ratio_low}-${component.ratio_high}`}>
                        <span>{component.name}</span>
                        <b>{component.price_low.toFixed(2)}{component.price_high !== component.price_low ? `–${component.price_high.toFixed(2)}` : ''}</b>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </aside>
          </section>
        </>
      )}
    </main>
  )
}
