import { useEffect, useMemo, useState } from 'react'
import HarmonicChart, { Bar, Pattern } from './HarmonicChart'
import TypeIT5Evidence, { TypeIT5Event } from './TypeIT5Evidence'
import AShareExecutionContext, { AShareExecutionContextPayload } from './AShareExecutionContext'
import MarketContext, { MarketContextPayload } from './MarketContext'
import SectorContext, { IndustryContextPayload } from './SectorContext'
import ConceptContext, { ConceptContextPayload } from './ConceptContext'
import ContextIntegrity, { ContextIntegrityPayload } from './ContextIntegrity'

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
            <div><span>完成结构</span><strong>{primaryCount(analysis.completed)}</strong></div>
            <div><span>形成中结构</span><strong>{primaryCount(analysis.forming)}</strong></div>
          </section>

          {analysis.warning && <div className="warning-card">{analysis.warning}</div>}

          <ContextIntegrity context={analysis.context_integrity} />
          <AShareExecutionContext context={analysis.a_share_execution_context} />
          <MarketContext context={analysis.market_context} />
          <SectorContext context={analysis.sector_context} />
          <ConceptContext context={analysis.concept_context} />
          <TypeIT5Evidence events={analysis.type_i_t5_events ?? []} />

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
              <HarmonicChart bars={analysis.bars} pattern={selectedPattern} focusPattern={focusPattern} />
              <p className="engine-note">{analysis.engine_note}</p>
            </div>

            <aside className="pattern-panel">
              <div className="panel-heading small">
                <div>
                  <span className="kicker">候选列表</span>
                  <h2>形态与价格区</h2>
                </div>
              </div>
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
        </>
      )}
    </main>
  )
}
