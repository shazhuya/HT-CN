import { useEffect, useMemo, useState } from 'react'
import HarmonicChart, { Bar, CrosshairSnapshot, Pattern } from './HarmonicChart'
import TypeIT5Evidence, { TypeIT5Event } from './TypeIT5Evidence'
import AShareExecutionContext, { AShareExecutionContextPayload } from './AShareExecutionContext'
import MarketContext, { MarketContextPayload } from './MarketContext'
import SectorContext, { IndustryContextPayload } from './SectorContext'
import ConceptContext, { ConceptContextPayload } from './ConceptContext'
import ContextIntegrity, { ContextIntegrityPayload } from './ContextIntegrity'
import DecisionNarrative from './DecisionNarrative'
import OperatorQueue from './OperatorQueue'
import ProductRuntimeStatus, {
  EvidenceRuntimeStatusPayload,
  ProductRuntimeStatusPayload,
  ProductSupervisorStatusPayload,
} from './ProductRuntimeStatus'
import WorkbenchContextPanel from './WorkbenchContextPanel'

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
  type_i_t5_events?: TypeIT5Event[]
  a_share_execution_context?: AShareExecutionContextPayload
  market_context?: MarketContextPayload
  sector_context?: IndustryContextPayload
  concept_context?: ConceptContextPayload
  context_integrity?: ContextIntegrityPayload
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
  abcd: 'AB=CD',
  shark: 'Shark',
  five_zero: '5-0',
}

function patternName(id: string) {
  return PATTERN_NAMES[id] ?? id
}

function fmt(value: number | undefined) {
  return value == null ? '—' : value.toFixed(3)
}

function priceRange(low: number | null | undefined, high: number | null | undefined) {
  if (low == null || high == null) return '未冻结 · fail closed'
  return `${low.toFixed(2)} – ${high.toFixed(2)}`
}

function idealCoreLabel(pattern: Pattern) {
  const layer = pattern.prz.ideal_core
  return priceRange(layer?.price_low ?? pattern.prz.price_low, layer?.price_high ?? pattern.prz.price_high)
}

function componentEnvelopeLabel(pattern: Pattern) {
  const layer = pattern.prz.component_envelope
  return priceRange(
    layer?.price_low ?? pattern.prz.component_price_low ?? pattern.prz.price_low,
    layer?.price_high ?? pattern.prz.component_price_high ?? pattern.prz.price_high,
  )
}

function sourcePrzLabel(pattern: Pattern) {
  const source = pattern.prz.source_prz
  if (source) {
    if (!source.available) return '未冻结 · fail closed'
    return priceRange(source.price_low, source.price_high)
  }
  return priceRange(pattern.prz.source_prz_low, pattern.prz.source_prz_high)
}

function sharkTargetBasisLabel(value: string | undefined) {
  if (value === '50_percent') return '50% BC 回撤先到'
  if (value === 'reciprocal_abcd') return 'Reciprocal AB=CD 先到'
  if (value === '50_percent_and_reciprocal_abcd_tie') return '50% 与 Reciprocal AB=CD 同位'
  return '—'
}

function primaryCount(patterns: Pattern[]) {
  return patterns.filter((pattern) => pattern.is_primary_identity !== false).length
}

function hitLabel(value: number | null | undefined) {
  return value == null ? '未触及' : `${value} 根K线`
}

function evidenceLabel(state: string) {
  if (state === 'price_and_rsi_confirmed') return '后验价格 + Wilder RSI 辅助证据'
  if (state === 'price_confirmed_no_rsi') return '后验仅价格证据'
  if (state === 'full_retest_waiting_price') return 'Source PRZ 完整回测 · 等价格确认'
  if (state === 'partial_retest_only') return '仅部分 Source PRZ 回测'
  if (state === 'source_prz_unresolved') return 'Source PRZ 未冻结 · 禁止升级'
  if (state === 'retest_only') return '仅二次回测'
  return '非 Type-II 候选'
}

function isStandaloneAbcd(pattern: Pattern) {
  return pattern.schema === 'ABCD'
}

function isShark(pattern: Pattern) {
  return pattern.schema === '0XABC' || pattern.pattern_id === 'shark'
}

function isFiveZero(pattern: Pattern) {
  return pattern.schema === 'FIVE_ZERO' || pattern.pattern_id === 'five_zero'
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
  const [showAllIdentities, setShowAllIdentities] = useState(false)
  const [focusPattern, setFocusPattern] = useState(true)
  const [crosshair, setCrosshair] = useState<CrosshairSnapshot | null>(null)
  const [productSupervisorStatus, setProductSupervisorStatus] = useState<ProductSupervisorStatusPayload | null>(null)
  const [marketDataStatus, setMarketDataStatus] = useState<ProductRuntimeStatusPayload | null>(null)
  const [harmonicRuntimeStatus, setHarmonicRuntimeStatus] = useState<ProductRuntimeStatusPayload | null>(null)
  const [evidenceRuntimeStatus, setEvidenceRuntimeStatus] = useState<EvidenceRuntimeStatusPayload | null>(null)

  useEffect(() => {
    fetch(`${API}/api/health`)
      .then((response) => {
        if (!response.ok) throw new Error(`HTTP ${response.status}`)
        return response.json() as Promise<Health>
      })
      .then(setHealth)
      .catch((err: Error) => setError(err.message))

    fetch(`${API}/api/instruments?limit=10000`)
      .then((response) => response.json())
      .then((payload: { items?: InstrumentRow[] }) => setInstruments(payload.items ?? []))
      .catch(() => undefined)

    fetch(`${API}/api/product/status`)
      .then((response) => response.json() as Promise<ProductSupervisorStatusPayload>)
      .then(setProductSupervisorStatus)
      .catch(() => undefined)

    fetch(`${API}/api/market-data/status`)
      .then((response) => response.json() as Promise<ProductRuntimeStatusPayload>)
      .then(setMarketDataStatus)
      .catch(() => undefined)

    fetch(`${API}/api/harmonic/runtime/status`)
      .then((response) => response.json() as Promise<ProductRuntimeStatusPayload>)
      .then(setHarmonicRuntimeStatus)
      .catch(() => undefined)

    fetch(`${API}/api/evidence/status`)
      .then((response) => response.json() as Promise<EvidenceRuntimeStatusPayload>)
      .then(setEvidenceRuntimeStatus)
      .catch(() => undefined)
  }, [])

  const rawPatterns = useMemo(() => {
    if (!analysis) return []
    return [...analysis.completed, ...analysis.forming]
  }, [analysis])

  const allPatterns = useMemo(() => {
    if (showAllIdentities) return rawPatterns
    return rawPatterns.filter((pattern) => pattern.is_primary_identity !== false)
  }, [rawPatterns, showAllIdentities])

  const selectedPattern = useMemo(() => {
    if (!allPatterns.length) return null
    const key = (pattern: Pattern) => `${pattern.state}:${pattern.pattern_id}:${pattern.scale}:${pattern.points.map((p) => p.index).join('-')}`
    return allPatterns.find((pattern) => key(pattern) === selectedKey) ?? allPatterns[0]
  }, [allPatterns, selectedKey])

  const patternKey = (pattern: Pattern) => `${pattern.state}:${pattern.pattern_id}:${pattern.scale}:${pattern.points.map((p) => p.index).join('-')}`

  function runAnalysis(nextSymbol?: string) {
    const targetSymbol = (nextSymbol ?? symbol).trim().toUpperCase()
    if (!targetSymbol) return
    if (targetSymbol !== symbol) setSymbol(targetSymbol)
    setLoading(true)
    setError(null)
    setSelectedKey(null)
    setCrosshair(null)
    fetch(`${API}/api/harmonic/${encodeURIComponent(targetSymbol)}?bars=${bars}&scales=3,5,8,13`)
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
      <header className="app-topbar">
        <div className="brand-lockup">
          <div className="brand-mark" aria-hidden="true">H</div>
          <div>
            <p className="eyebrow">HT-CN STABLE v1.0.0 · LOCAL PRODUCT RUNTIME</p>
            <h1>A 股谐波研究与辅助决策系统</h1>
            <p className="subtitle">把复杂研究压缩成：看图 · 看阶段 · 看下一关键条件</p>
          </div>
        </div>
        <nav className="top-nav" aria-label="主导航">
          <a href="#workspace">研究工作台</a>
          <a href="#watchlist">今日观察</a>
          <a href="#research-context">研究信息</a>
        </nav>
        <div className="health-pill" data-ok={Boolean(health)}>
          <span className="health-dot" />
          {health ? `API ${health.version}` : 'API 未连接'}
        </div>
      </header>

      <div className="runtime-shell">
        <ProductRuntimeStatus
          product={productSupervisorStatus}
          market={marketDataStatus}
          harmonic={harmonicRuntimeStatus}
          evidence={evidenceRuntimeStatus}
        />
      </div>

      <section className="command-deck" id="workspace">
        <div className="command-deck__intro">
          <div>
            <p className="kicker">研究入口</p>
            <h2>先选股票，再看结构</h2>
            <p>输入证券代码后直接回车。系统会读取本地最新数据并打开对应的谐波工作台。</p>
          </div>
          <div className="command-deck__hint">
            <span>推荐窗口</span>
            <strong>420 根 K 线</strong>
            <small>适合日常波段结构观察</small>
          </div>
        </div>

        <section className="controls command-controls" aria-label="analysis-controls">
          <label className="symbol-control">
            <span>股票代码</span>
            <input
              list="instrument-list"
              value={symbol}
              onChange={(event) => setSymbol(event.target.value.toUpperCase())}
              onKeyDown={(event) => {
                if (event.key === 'Enter') runAnalysis()
              }}
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
            <span>观察范围</span>
            <select value={bars} onChange={(event) => setBars(Number(event.target.value))}>
              <option value={240}>240 根 · 短窗口</option>
              <option value={420}>420 根 · 推荐</option>
              <option value={720}>720 根 · 中长</option>
              <option value={1200}>1200 根 · 长周期</option>
            </select>
          </label>
          <button className="primary-analysis-button" onClick={() => runAnalysis()} disabled={loading || !symbol.trim()}>
            {loading ? '正在读取与分析…' : '打开研究工作台'}
          </button>
        </section>
      </section>

      {error && <p className="error">{error}</p>}

      {!analysis && !error && (
        <section className="placeholder start-placeholder">
          <div className="start-placeholder__visual" aria-hidden="true">
            <span className="start-placeholder__axis" />
            <i /><i /><i /><i /><i /><i />
          </div>
          <div className="start-placeholder__copy">
            <p className="kicker">准备就绪</p>
            <h2>从一只你正在研究的股票开始</h2>
            <p>在上方输入代码并回车。打开后先看主图，再看右侧“现在在哪 / 先看什么 / 下一步看什么”。</p>
            <div className="start-steps">
              <span><b>1</b> 输入代码</span>
              <span><b>2</b> 看主图结构</span>
              <span><b>3</b> 看下一关键条件</span>
            </div>
          </div>
        </section>
      )}

      {analysis && (
        <>
          <section className="summary-grid">
            <div><span>价格视图</span><strong>{analysis.price_mode.toUpperCase()}</strong></div>
            <div><span>区间</span><strong>{analysis.first_trade_date} → {analysis.last_trade_date}</strong></div>
            <div><span>实际K线</span><strong>{analysis.bars_returned} / {analysis.bars_requested}</strong></div>
            <div><span>完成结构</span><strong>{primaryCount(analysis.completed)}</strong></div>
            <div><span>形成中结构</span><strong>{primaryCount(analysis.forming)}</strong></div>
          </section>

          {analysis.warning && <div className="warning-card">{analysis.warning}</div>}

          <section className="product-workbench" data-testid="product-workbench">
            <div className="product-workbench-heading">
              <div>
                <p className="kicker">实时单标的研究</p>
                <h2>端到端研究工作台</h2>
              </div>
              <span>标的 → K线 → 形态 → Source lifecycle → 下一观察点</span>
            </div>
            <section className="workspace">
            <div className="chart-panel">
              <div className="panel-heading">
                <div>
                  <span className="kicker">{analysis.instrument_id}</span>
                  <h2>{selectedPattern ? `${patternName(selectedPattern.pattern_id)} · ${selectedPattern.state === 'completed' ? '已完成' : '形成中'}` : '暂无有效形态'}</h2>
                </div>
                <div className="chart-heading-actions">
                  <label className="toggle-line">
                    <input type="checkbox" checked={focusPattern} onChange={(event) => setFocusPattern(event.target.checked)} />
                    聚焦当前形态
                  </label>
                  {selectedPattern && (
                    <div className="score-box">
                      <span>几何评分</span>
                      <strong>{selectedPattern.geometry_score.toFixed(1)}</strong>
                    </div>
                  )}
                </div>
              </div>
              <HarmonicChart
                bars={analysis.bars}
                pattern={selectedPattern}
                focusPattern={focusPattern}
                onCrosshairChange={setCrosshair}
              />
              <p className="engine-note">{analysis.engine_note}</p>
            </div>

            <aside className="pattern-panel">
              <div className="panel-heading small">
                <div>
                  <span className="kicker">候选列表</span>
                  <h2>形态与价格区</h2>
                </div>
              </div>
              <DecisionNarrative narrative={selectedPattern?.decision_narrative} />
              <WorkbenchContextPanel
                instrumentId={analysis.instrument_id}
                pattern={selectedPattern}
                crosshair={crosshair}
                latestBar={analysis.bars.at(-1)}
              />
              <label className="toggle-line identity-toggle">
                <input type="checkbox" checked={showAllIdentities} onChange={(event) => setShowAllIdentities(event.target.checked)} />
                显示同节点备选身份
              </label>
              <p className="candidate-summary">
                当前显示 {allPatterns.length} / {rawPatterns.length} 个身份；默认只显示每组节点的主身份。
              </p>
              <div className="pattern-list">
                {allPatterns.length === 0 && <p className="muted">当前窗口没有通过规则的谐波候选。</p>}
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
                  <h3>节点区间</h3>
                  <p className="node-range">
                    {selectedPattern.points[0]?.trade_date ?? '—'} → {selectedPattern.points.at(-1)?.trade_date ?? '—'} · S{selectedPattern.scale} · {selectedPattern.schema ?? 'XABCD'}
                  </p>

                  {(selectedPattern.identity_conflicts?.length ?? 0) > 1 && (
                    <>
                      <h3>同节点身份冲突</h3>
                      <p className="identity-note">
                        主身份为 {patternName(selectedPattern.pattern_id)}；同一节点还满足 {selectedPattern.identity_conflicts?.filter((value) => !value.startsWith(`${selectedPattern.pattern_id}@`)).join('、')}。这些身份保留供审计，不代表多个独立机会。
                      </p>
                    </>
                  )}

                  {selectedPattern.pivot_support && selectedPattern.pivot_support.length > 0 && (
                    <>
                      <h3>Pivot 跨尺度支持</h3>
                      <ul>
                        {selectedPattern.pivot_support.map((support) => (
                          <li key={`${support.label}-${support.index}`}>
                            <span>{support.label} · {support.kind ?? 'pivot'}</span>
                            <b>{support.support_count}尺度 · S{support.scales.join('/')}</b>
                          </li>
                        ))}
                      </ul>
                      <p className="identity-note">跨尺度支持只表示同一极值被多个独立 Pivot 尺度重复识别，用于选点稳健性审计，不参与 Carney 身份判定。</p>
                    </>
                  )}

                  <h3>比例审计</h3>
                  {isShark(selectedPattern) ? (
                    <dl>
                      <div><dt>A/0X</dt><dd>{fmt(selectedPattern.metrics.a_0x)}</dd></div>
                      <div><dt>B/XA</dt><dd>{fmt(selectedPattern.metrics.b_xa)}</dd></div>
                      <div><dt>C/AB</dt><dd>{fmt(selectedPattern.metrics.c_ab)}</dd></div>
                      <div><dt>C/0B</dt><dd>{fmt(selectedPattern.metrics.c_0b)}</dd></div>
                    </dl>
                  ) : isFiveZero(selectedPattern) ? (
                    <dl>
                      <div><dt>B/XA</dt><dd>{fmt(selectedPattern.metrics.b_xa)}</dd></div>
                      <div><dt>C/AB</dt><dd>{fmt(selectedPattern.metrics.c_ab)}</dd></div>
                      <div><dt>D/BC</dt><dd>{fmt(selectedPattern.metrics.d_bc)}</dd></div>
                      <div><dt>CD/AB</dt><dd>{fmt(selectedPattern.metrics.cd_ab)}</dd></div>
                      <div><dt>Reciprocal AB=CD</dt><dd>{fmt(selectedPattern.metrics.reciprocal_abcd_price)}</dd></div>
                    </dl>
                  ) : isStandaloneAbcd(selectedPattern) ? (
                    <dl>
                      <div><dt>C/AB</dt><dd>{fmt(selectedPattern.metrics.c_ab)}</dd></div>
                      <div><dt>CD/BC</dt><dd>{fmt(selectedPattern.metrics.bc_projection)}</dd></div>
                      <div><dt>CD/AB</dt><dd>{fmt(selectedPattern.metrics.cd_ab)}</dd></div>
                      <div><dt>目标C比率</dt><dd>{fmt(selectedPattern.metrics.reciprocal_c_target)}</dd></div>
                      <div><dt>目标BC投影</dt><dd>{fmt(selectedPattern.metrics.reciprocal_bc_target)}</dd></div>
                    </dl>
                  ) : (
                    <dl>
                      <div><dt>B/XA</dt><dd>{fmt(selectedPattern.metrics.b_xa)}</dd></div>
                      <div><dt>C/AB</dt><dd>{fmt(selectedPattern.metrics.c_ab)}</dd></div>
                      <div><dt>BC投影</dt><dd>{fmt(selectedPattern.metrics.bc_projection)}</dd></div>
                      <div><dt>D/XA</dt><dd>{fmt(selectedPattern.metrics.d_xa)}</dd></div>
                      <div><dt>CD/AB</dt><dd>{fmt(selectedPattern.metrics.cd_ab)}</dd></div>
                    </dl>
                  )}

                  {isFiveZero(selectedPattern) && (
                    <p className="identity-note">
                      5-0 当前是 Source Conflict 研究态，默认生产扫描不会发布。Volume Two 的结构完成语义与 Volume Three 的执行细化尚未完成图例级 reconciliation；这里保留比例只用于审计，禁止压成一个“已解决”的生产区间。
                    </p>
                  )}

                  <h3>价格区语义</h3>
                  <dl>
                    <div><dt>HT-CN收敛核心</dt><dd>{idealCoreLabel(selectedPattern)}</dd></div>
                    <div><dt>组件审计包络</dt><dd>{componentEnvelopeLabel(selectedPattern)}</dd></div>
                    <div><dt>Source PRZ</dt><dd>{sourcePrzLabel(selectedPattern)}</dd></div>
                  </dl>
                  <p className="identity-note">
                    图中着色区与旧 price_low/high 均表示 HT-CN 收敛核心，不等于 Carney Source PRZ。Source PRZ 未经 Book Golden Set 冻结时，Terminal / PEZ / Type-II 一律 fail closed。
                  </p>

                  <h3>组件测量审计</h3>
                  <ul>
                    {selectedPattern.prz.components.map((component) => (
                      <li key={`${component.name}-${component.ratio_low}-${component.ratio_high}`}>
                        <span>{component.name}</span>
                        <b>{component.price_low.toFixed(2)}{component.price_high !== component.price_low ? `–${component.price_high.toFixed(2)}` : ''}</b>
                      </li>
                    ))}
                  </ul>

                  {selectedPattern.state === 'completed' && selectedPattern.reaction_targets && (
                    <>
                      <h3>Shark 反应目标审计</h3>
                      <dl>
                        {selectedPattern.reaction_targets.initial_target != null && (
                          <>
                            <div><dt>原书第一目标</dt><dd>{selectedPattern.reaction_targets.initial_target.toFixed(2)}</dd></div>
                            <div><dt>第一目标依据</dt><dd>{sharkTargetBasisLabel(selectedPattern.reaction_targets.initial_target_basis)}</dd></div>
                            <div><dt>到达第一目标</dt><dd>{hitLabel(selectedPattern.reaction_targets.bars_to_initial_target)}</dd></div>
                          </>
                        )}
                        <div><dt>50% BC回撤</dt><dd>{selectedPattern.reaction_targets.target_50.toFixed(2)}</dd></div>
                        <div><dt>到达50%</dt><dd>{hitLabel(selectedPattern.reaction_targets.bars_to_50)}</dd></div>
                        <div><dt>61.8% BC回撤</dt><dd>{selectedPattern.reaction_targets.target_618.toFixed(2)}</dd></div>
                        <div><dt>到达61.8%</dt><dd>{hitLabel(selectedPattern.reaction_targets.bars_to_618)}</dd></div>
                        <div><dt>Reciprocal AB=CD</dt><dd>{selectedPattern.reaction_targets.reciprocal_abcd.toFixed(2)}</dd></div>
                        <div><dt>到达Reciprocal</dt><dd>{hitLabel(selectedPattern.reaction_targets.bars_to_reciprocal_abcd)}</dd></div>
                      </dl>
                      <p className="identity-note">{selectedPattern.reaction_targets.source_note}</p>
                    </>
                  )}

                  {selectedPattern.state === 'completed' && selectedPattern.reaction_audit && (
                    <>
                      <h3>后验 Reaction vs. Reversal 审计</h3>
                      <dl>
                        <div><dt>后验38.2%目标</dt><dd>{selectedPattern.reaction_audit.target_382.toFixed(2)}</dd></div>
                        <div><dt>后验61.8%目标</dt><dd>{selectedPattern.reaction_audit.target_618.toFixed(2)}</dd></div>
                        <div><dt>后验到达T1</dt><dd>{hitLabel(selectedPattern.reaction_audit.bars_to_382)}</dd></div>
                        <div><dt>后验到达T2</dt><dd>{hitLabel(selectedPattern.reaction_audit.bars_to_618)}</dd></div>
                        <div>
                          <dt>{selectedPattern.reaction_audit.source_prz_available ? 'Source PRZ二次回测' : '观察区二次重入'}</dt>
                          <dd>{selectedPattern.reaction_audit.secondary_prz_retest_bar == null ? '未观察到' : `D后第 ${selectedPattern.reaction_audit.secondary_prz_retest_bar} 根`}</dd>
                        </div>
                        <div>
                          <dt>Source PRZ完整回测</dt>
                          <dd>
                            {!selectedPattern.reaction_audit.source_prz_available
                              ? '不可判定 · Source PRZ未冻结'
                              : selectedPattern.reaction_audit.full_prz_retest_bar == null
                                ? '未观察到'
                                : `D后第 ${selectedPattern.reaction_audit.full_prz_retest_bar} 根`}
                          </dd>
                        </div>
                        <div><dt>回测后二次离开</dt><dd>{selectedPattern.reaction_audit.bars_to_reversal_exit_after_retest == null ? '未观察到' : `${selectedPattern.reaction_audit.bars_to_reversal_exit_after_retest} 根K线`}</dd></div>
                        <div><dt>第三次测试</dt><dd>{selectedPattern.reaction_audit.third_prz_test_bar == null ? '未观察到' : `D后第 ${selectedPattern.reaction_audit.third_prz_test_bar} 根`}</dd></div>
                        <div><dt>Wilder RSI({selectedPattern.reaction_audit.rsi_period})辅助确认</dt><dd>{selectedPattern.reaction_audit.rsi_confirmation ? '有' : '无'}</dd></div>
                        <div><dt>Type-II证据</dt><dd>{evidenceLabel(selectedPattern.reaction_audit.type_ii_evidence_state)}</dd></div>
                      </dl>
                      <p className="identity-note">Type-II 证据层与形态身份严格分离。当前 RSI 仅是 Wilder 30/70 极值区辅助证据，明确不是 RSI BAMM；后验 T1/T2、价格或 RSI 证据都不会自动转化为实时执行结论或交易建议。</p>
                    </>
                  )}
                </div>
              )}
            </aside>
            </section>
          </section>

          <section className="research-context" id="research-context">
            <div className="research-context__heading">
              <div>
                <p className="kicker">需要时再深入</p>
                <h2>市场、执行与证据上下文</h2>
              </div>
              <p>这些信息帮助解释环境与约束，但不会反向改写谐波身份和 Source lifecycle。</p>
            </div>
            <div className="research-context__stack">
              <ContextIntegrity context={analysis.context_integrity} />
              <AShareExecutionContext context={analysis.a_share_execution_context} />
              <MarketContext context={analysis.market_context} />
              <SectorContext context={analysis.sector_context} />
              <ConceptContext context={analysis.concept_context} />
              <TypeIT5Evidence events={analysis.type_i_t5_events ?? []} />
            </div>
          </section>
        </>
      )}

      <section className="discovery-section" id="watchlist">
        <div className="section-heading">
          <div>
            <p className="kicker">全市场观察</p>
            <h2>今天还有哪些结构值得看</h2>
          </div>
          <p>这里是候选发现与跨日复盘区。它负责“找标的”，不会覆盖上面的单标的判断。</p>
        </div>
        <OperatorQueue
          apiBase={API}
          onSelectInstrument={(instrumentId) => {
            setSymbol(instrumentId)
            setAnalysis(null)
            setSelectedKey(null)
            setCrosshair(null)
            runAnalysis(instrumentId)
            window.location.hash = 'workspace'
          }}
        />
      </section>
    </main>
  )
}
