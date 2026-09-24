import { useState } from 'react'
import AShareExecutionContext from './AShareExecutionContext'
import ConceptContext from './ConceptContext'
import ContextIntegrity from './ContextIntegrity'
import DecisionNarrative from './DecisionNarrative'
import HarmonicChart, { type CrosshairSnapshot, type Pattern } from './HarmonicChart'
import LifecycleCompass from './LifecycleCompass'
import MarketContext from './MarketContext'
import PatternAuditPanel from './PatternAuditPanel'
import SectorContext from './SectorContext'
import TypeIT5Evidence from './TypeIT5Evidence'
import WatchlistPanel from './WatchlistPanel'
import WorkbenchContextPanel from './WorkbenchContextPanel'
import type { Analysis, InstrumentRow, ResearchTab } from './appTypes'
import './ResearchWorkspace.css'

const PATTERN_NAMES: Record<string, string> = {
  gartley: 'Gartley', bat: 'Bat', alternate_bat: 'Alternate Bat', butterfly: 'Butterfly',
  crab: 'Crab', deep_crab: 'Deep Crab', abcd: 'AB=CD', shark: 'Shark', five_zero: '5-0',
}
const TABS: Array<{ id: ResearchTab; label: string }> = [
  { id: 'overview', label: '概要' },
  { id: 'pattern', label: '形态与价位' },
  { id: 'context', label: '市场环境' },
  { id: 'audit', label: '审计' },
]
function patternKey(pattern: Pattern) {
  return `${pattern.channel ?? 'authoritative'}:${pattern.state}:${pattern.pattern_id}:${pattern.scale}:${pattern.points.map((point) => point.index).join('-')}`
}

function patternStateLabel(pattern: Pattern) {
  if (pattern.discovery_only) return '发现候选'
  return pattern.state === 'completed' ? '已完成' : '形成中'
}

export default function ResearchWorkspace({
  analysis, loading, error, bars, onBarsChange, onRefresh, patterns, rawPatternCount,
  selectedPattern, onSelectPattern, showAllIdentities, onShowAllIdentities,
  focusPattern, onFocusPattern, crosshair, onCrosshair, tab, onTab, instruments, onOpenInstrument,
}: {
  analysis: Analysis | null
  loading: boolean
  error: string | null
  bars: number
  onBarsChange: (bars: number) => void
  onRefresh: () => void
  patterns: Pattern[]
  rawPatternCount: number
  selectedPattern: Pattern | null
  onSelectPattern: (key: string) => void
  showAllIdentities: boolean
  onShowAllIdentities: (value: boolean) => void
  focusPattern: boolean
  onFocusPattern: (value: boolean) => void
  crosshair: CrosshairSnapshot | null
  onCrosshair: (value: CrosshairSnapshot | null) => void
  tab: ResearchTab
  onTab: (tab: ResearchTab) => void
  instruments: InstrumentRow[]
  onOpenInstrument: (symbol: string) => void
}) {
  const [inspectorOpen, setInspectorOpen] = useState(true)
  const [watchlistOpen, setWatchlistOpen] = useState(true)
  const [detailsTab, setDetailsTab] = useState<'decision' | 'source'>('decision')

  if (!analysis) {
    return (
      <section className="research-view research-view--empty" aria-label="个股研究">
        <div className="research-empty">
          <div className="research-empty__chart" aria-hidden="true"><i /><i /><i /><i /><i /><i /><i /></div>
          <div>
            <span>HT-CN · 图表工作台</span>
            <h1>{loading ? '正在读取图表…' : '选择证券，开始研究'}</h1>
            <p>在顶栏输入本地证券代码，按回车打开 K 线、谐波结构和 Source 生命周期。</p>
            {error && <div className="research-error" role="alert">读取失败：{error}</div>}
          </div>
        </div>
      </section>
    )
  }

  const latest = analysis.bars.at(-1)
  const previous = analysis.bars.at(-2)
  const change = latest && previous && previous.close !== 0 ? (latest.close / previous.close - 1) * 100 : null

  return (
    <section className={inspectorOpen ? 'research-view' : 'research-view inspector-collapsed'} aria-label="个股研究">
      <div className="research-header">
        <div className="research-header__identity">
          <h1>{analysis.instrument_id}</h1>
          <span>{analysis.price_mode.toUpperCase()} · 日K</span>
          <span className="research-header__date">{analysis.last_trade_date} 最近交易日</span>
        </div>
        <div className="research-header__quote" title="本地数据最后一根 K 线，不是实时报价">
          <strong>{latest?.close.toFixed(2) ?? '—'}</strong>
          <span className={change == null ? '' : change >= 0 ? 'is-up' : 'is-down'}>{change == null ? '—' : `${change >= 0 ? '+' : ''}${change.toFixed(2)}%`}</span>
          <small>本地收盘</small>
        </div>
        <div className="research-controls" aria-label="analysis-controls">
          <label><span className="visually-hidden">观察范围</span>
            <select value={bars} onChange={(event) => onBarsChange(Number(event.target.value))} aria-label="观察范围">
              <option value={240}>240 根</option><option value={420}>420 根</option>
              <option value={720}>720 根</option><option value={1200}>1200 根</option>
            </select>
          </label>
          <button onClick={onRefresh} disabled={loading} aria-label="打开研究工作台 · 运行谐波分析">
            {loading ? '更新中…' : '↻ 重新分析'}
          </button>
          <button onClick={() => setInspectorOpen(!inspectorOpen)} aria-label={inspectorOpen ? '收起右侧详情栏' : '打开右侧详情栏'} aria-expanded={inspectorOpen}>
            {inspectorOpen ? '▣ 收起右栏' : '▣ 打开右栏'}
          </button>
        </div>
      </div>
      {error && <div className="research-error" role="alert">读取失败：{error}</div>}
      {analysis.warning && <div className="research-warning" role="status">{analysis.warning}</div>}
      <div className="research-workbench" data-testid="product-workbench">
        <div className="research-center">
          <div className="research-stage">
            <div className="research-toolrail" aria-label="图表工具">
              <label className="research-toolrail__toggle" title="聚焦当前形态">
                <input type="checkbox" aria-label="聚焦当前形态" checked={focusPattern} onChange={(event) => onFocusPattern(event.target.checked)} />
                <span aria-hidden="true">⌖</span>
              </label>
              <button type="button" title="切换全部形态身份" aria-label="切换全部形态身份" aria-pressed={showAllIdentities} onClick={() => onShowAllIdentities(!showAllIdentities)}>◇</button>
              <button type="button" title="形态与价位" aria-label="打开结构明细" onClick={() => onTab('pattern')}>⌁</button>
              <button type="button" title="市场环境" aria-label="打开环境明细" onClick={() => onTab('context')}>▦</button>
              <button type="button" title="审计记录" aria-label="打开记录明细" onClick={() => onTab('audit')}>≡</button>
            </div>
            <section className="research-chart-card" aria-label="谐波主图">
              <div className="research-chart-heading">
                <div>
                  <h2>{selectedPattern ? `${PATTERN_NAMES[selectedPattern.pattern_id] ?? selectedPattern.pattern_id} · ${patternStateLabel(selectedPattern)}` : 'K 线图'}</h2>
                  <span>{selectedPattern ? `${selectedPattern.discovery_only ? '发现层 · ' : ''}S${selectedPattern.scale} · ${selectedPattern.direction === 'bullish' ? '看涨' : '看跌'}` : '当前窗口暂无有效形态'}</span>
                </div>
                <span className="research-chart-heading__tip">拖动平移 · 滚轮缩放 · 悬停查看节点</span>
              </div>
              <HarmonicChart
                bars={analysis.bars} pattern={selectedPattern} focusPattern={focusPattern}
                lifecyclePlacement="external" onCrosshairChange={onCrosshair}
              />
            </section>
          </div>
          <div className="research-bottom">
            <nav className="research-tabs" aria-label="研究页签">
              {TABS.map((item) => (
                <button key={item.id} className={tab === item.id ? 'active' : ''} onClick={() => onTab(item.id)} aria-selected={tab === item.id}>
                  {item.label}
                </button>
              ))}
              <span>图形用于研究 · 不执行证券交易</span>
            </nav>
            {tab !== 'overview' && (
              <section className="research-tabpanel" data-research-tab={tab}>
                {tab === 'pattern' && <PatternAuditPanel pattern={selectedPattern} />}
                {tab === 'context' && (
                  <div className="research-context-grid">
                    <ContextIntegrity context={analysis.context_integrity} />
                    <AShareExecutionContext context={analysis.a_share_execution_context} />
                    <MarketContext context={analysis.market_context} />
                    <SectorContext context={analysis.sector_context} />
                    <ConceptContext context={analysis.concept_context} />
                  </div>
                )}
                {tab === 'audit' && (
                  <div className="research-audit-layout">
                    <TypeIT5Evidence events={analysis.type_i_t5_events ?? []} />
                    <section className="engine-boundary-card">
                      <h3>引擎边界</h3><p>{analysis.engine_note}</p>
                      <dl><div><dt>完成结构</dt><dd>{analysis.completed.length}</dd></div>
                        <div><dt>权威形成中</dt><dd>{analysis.forming.length}</dd></div>
                        <div><dt>发现候选</dt><dd>{analysis.discovery?.length ?? 0}</dd></div>
                        <div><dt>权威 Pivot</dt><dd>{analysis.scales.join(' / ')}</dd></div>
                        <div><dt>发现 Pivot</dt><dd>{analysis.discovery_scales?.join(' / ') ?? '5 / 10 / 20'}</dd></div></dl>
                    </section>
                  </div>
                )}
              </section>
            )}
          </div>
        </div>
        {inspectorOpen && (
          <aside className="research-inspector" aria-label="自选股与详情栏">
            <div className={watchlistOpen ? 'research-inspector__watchlist' : 'research-inspector__watchlist collapsed'}>
              <div className="research-inspector__section-title">
                <strong>股票栏</strong>
                <button onClick={() => setWatchlistOpen(!watchlistOpen)} aria-label={watchlistOpen ? '收起自选列表' : '展开自选列表'} aria-expanded={watchlistOpen}>{watchlistOpen ? '⌃' : '⌄'}</button>
              </div>
              {watchlistOpen && <WatchlistPanel instruments={instruments} analysis={analysis} onOpenInstrument={onOpenInstrument} />}
            </div>
            <div className="research-inspector__detail">
              <nav className="research-inspector__tabs" aria-label="股票详情页签">
                <button className={detailsTab === 'decision' ? 'active' : ''} onClick={() => setDetailsTab('decision')}>当前判断</button>
                <button className={detailsTab === 'source' ? 'active' : ''} onClick={() => setDetailsTab('source')}>Source 时钟</button>
              </nav>
              <div className="research-inspector__scroll">
                {detailsTab === 'decision' && (
                  <>
                    {selectedPattern?.discovery_only ? (
                      <section className="discovery-candidate-note" data-testid="discovery-candidate-note">
                        <strong>发现候选 · 尚非权威身份</strong>
                        <p>已确认 XABC 并投影冻结 Source PRZ；当前仅用于发现与观察，不虚构 D，也不生成 Type-I / Type-II 或买卖结论。</p>
                        <small>{selectedPattern.discovery?.prz_status === 'tested' ? '价格已在 C 确认后测试 Source PRZ' : '价格尚未在可观察时钟内测试 Source PRZ'} · {selectedPattern.discovery?.path_kind === 'minor_swing_skip' ? '允许跳过一组次级摆动' : '连续摆动路径'}</small>
                      </section>
                    ) : (
                      <>
                        <DecisionNarrative narrative={selectedPattern?.decision_narrative} />
                        {!selectedPattern?.decision_narrative && <p className="research-inspector__empty">目前没有通过规则的主形态；先看 K 线与数据日期。</p>}
                      </>
                    )}
                    <WorkbenchContextPanel instrumentId={analysis.instrument_id} pattern={selectedPattern} crosshair={crosshair} latestBar={latest} />
                    <section className="candidate-switcher" aria-label="形态候选">
                      <div className="candidate-switcher__heading">
                        <strong>形态候选</strong><small>{patterns.length} / {rawPatternCount}</small>
                      </div>
                      {patterns.length === 0 && <p>当前窗口没有通过规则的候选。</p>}
                      {patterns.map((pattern) => {
                        const key = patternKey(pattern)
                        return (
                          <button key={key} className={selectedPattern && patternKey(selectedPattern) === key ? 'pattern-item active' : 'pattern-item'} onClick={() => onSelectPattern(key)}>
                            <span><strong>{PATTERN_NAMES[pattern.pattern_id] ?? pattern.pattern_id}</strong><small>{patternStateLabel(pattern)} · S{pattern.scale}</small></span>
                            <b>{pattern.direction === 'bullish' ? '↗' : '↘'}</b>
                          </button>
                        )
                      })}
                    </section>
                    {!selectedPattern?.discovery_only && <LifecycleCompass pattern={selectedPattern} bars={analysis.bars} />}
                  </>
                )}
                {detailsTab === 'source' && (
                  <>
                    {selectedPattern?.discovery_only ? (
                      <section className="discovery-candidate-note">
                        <strong>Source 生命周期未启动</strong>
                        <p>发现层只负责 XABC 与投影 PRZ；必须进入权威 identity / Source Clock 后才会出现正式生命周期。</p>
                      </section>
                    ) : (
                      <LifecycleCompass pattern={selectedPattern} bars={analysis.bars} />
                    )}
                    <WorkbenchContextPanel instrumentId={analysis.instrument_id} pattern={selectedPattern} crosshair={crosshair} latestBar={latest} />
                  </>
                )}
              </div>
            </div>
          </aside>
        )}
      </div>
    </section>
  )
}
