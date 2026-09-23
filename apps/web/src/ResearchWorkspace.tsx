import AShareExecutionContext from './AShareExecutionContext'
import ConceptContext from './ConceptContext'
import ContextIntegrity from './ContextIntegrity'
import DecisionNarrative from './DecisionNarrative'
import HarmonicChart, { type CrosshairSnapshot, type Pattern } from './HarmonicChart'
import MarketContext from './MarketContext'
import PatternAuditPanel from './PatternAuditPanel'
import SectorContext from './SectorContext'
import TypeIT5Evidence from './TypeIT5Evidence'
import WorkbenchContextPanel from './WorkbenchContextPanel'
import type { Analysis, ResearchTab } from './appTypes'
import './ResearchWorkspace.css'

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

const TABS: Array<{ id: ResearchTab; label: string; hint: string }> = [
  { id: 'overview', label: '概要', hint: '当前状态与关键价' },
  { id: 'pattern', label: '形态与价位', hint: '比例、PRZ、目标' },
  { id: 'context', label: '市场环境', hint: '大盘、行业、题材、执行' },
  { id: 'audit', label: '审计', hint: '证据与引擎边界' },
]

function patternName(id: string) {
  return PATTERN_NAMES[id] ?? id
}

function patternKey(pattern: Pattern) {
  return `${pattern.state}:${pattern.pattern_id}:${pattern.scale}:${pattern.points.map((point) => point.index).join('-')}`
}

export default function ResearchWorkspace({
  analysis,
  loading,
  error,
  bars,
  onBarsChange,
  onRefresh,
  patterns,
  rawPatternCount,
  selectedPattern,
  onSelectPattern,
  showAllIdentities,
  onShowAllIdentities,
  focusPattern,
  onFocusPattern,
  crosshair,
  onCrosshair,
  tab,
  onTab,
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
}) {
  if (!analysis) {
    return (
      <section className="research-view" aria-label="个股研究">
        <div className="page-title-row">
          <div>
            <span className="page-eyebrow">RESEARCH</span>
            <h1>个股研究</h1>
            <p>从顶部搜索框输入证券代码并回车。这里一次只研究一只股票，不混入全市场队列。</p>
          </div>
        </div>

        {error && <div className="research-error">读取失败：{error}</div>}

        <div className="research-empty">
          <div className="research-empty__chart" aria-hidden="true">
            <i /><i /><i /><i /><i /><i /><i />
          </div>
          <div>
            <span>等待选择标的</span>
            <h2>{loading ? '正在读取与分析…' : '搜索股票后直接进入主图'}</h2>
            <p>打开后默认只看主图、当前阶段和下一关键条件。比例、市场环境和审计都在独立页签里。</p>
          </div>
        </div>
      </section>
    )
  }

  return (
    <section className="research-view" aria-label="个股研究">
      <div className="research-header">
        <div>
          <span className="page-eyebrow">RESEARCH · {analysis.price_mode.toUpperCase()}</span>
          <h1>{analysis.instrument_id}</h1>
          <p>{analysis.first_trade_date} → {analysis.last_trade_date} · {analysis.bars_returned} 根K线</p>
        </div>

        <section className="research-controls" aria-label="analysis-controls">
          <label>
            <span>观察范围</span>
            <select value={bars} onChange={(event) => onBarsChange(Number(event.target.value))}>
              <option value={240}>240 根</option>
              <option value={420}>420 根 · 推荐</option>
              <option value={720}>720 根</option>
              <option value={1200}>1200 根</option>
            </select>
          </label>
          <button
            aria-label="打开研究工作台 · 运行谐波分析"
            onClick={onRefresh}
            disabled={loading}
          >
            {loading ? '更新中…' : '重新分析'}
          </button>
        </section>
      </div>

      {error && <div className="research-error">读取失败：{error}</div>}
      {analysis.warning && <div className="research-warning">{analysis.warning}</div>}

      <section className="research-workbench" data-testid="product-workbench">
        <div className="research-stage">
          <section className="research-chart-card">
            <div className="research-chart-heading">
              <div>
                <span>当前结构</span>
                <h2>
                  {selectedPattern
                    ? `${patternName(selectedPattern.pattern_id)} · ${selectedPattern.state === 'completed' ? '已完成' : '形成中'}`
                    : '当前窗口没有有效谐波结构'}
                </h2>
              </div>
              <label>
                <input
                  type="checkbox"
                  checked={focusPattern}
                  onChange={(event) => onFocusPattern(event.target.checked)}
                />
                聚焦当前形态
              </label>
            </div>

            <HarmonicChart
              bars={analysis.bars}
              pattern={selectedPattern}
              focusPattern={focusPattern}
              onCrosshairChange={onCrosshair}
            />
          </section>

          <aside className="research-decision-rail">
            <DecisionNarrative narrative={selectedPattern?.decision_narrative} />

            <section className="candidate-switcher" aria-label="形态候选">
              <div className="candidate-switcher__heading">
                <div>
                  <span>识别结果</span>
                  <strong>{patterns.length} 个主显示结构</strong>
                </div>
                <label>
                  <input
                    type="checkbox"
                    checked={showAllIdentities}
                    onChange={(event) => onShowAllIdentities(event.target.checked)}
                  />
                  全部身份
                </label>
              </div>

              <div className="candidate-switcher__list">
                {patterns.length === 0 && <p>当前窗口没有通过规则的候选。</p>}
                {patterns.map((pattern) => {
                  const key = patternKey(pattern)
                  const active = selectedPattern ? patternKey(selectedPattern) === key : false
                  return (
                    <button key={key} className={active ? 'pattern-item active' : 'pattern-item'} onClick={() => onSelectPattern(key)}>
                      <span>
                        <strong>{patternName(pattern.pattern_id)}</strong>
                        <small>{pattern.state === 'completed' ? '已完成' : '形成中'} · S{pattern.scale} · {pattern.direction === 'bullish' ? '看涨' : '看跌'}</small>
                      </span>
                      <b>{pattern.geometry_score.toFixed(0)}</b>
                    </button>
                  )
                })}
              </div>
              <small className="candidate-switcher__meta">显示 {patterns.length} / 全部身份 {rawPatternCount}</small>
            </section>
          </aside>
        </div>

        <nav className="research-tabs" aria-label="研究页签">
          {TABS.map((item) => (
            <button
              key={item.id}
              className={tab === item.id ? 'active' : ''}
              onClick={() => onTab(item.id)}
              aria-selected={tab === item.id}
            >
              <strong>{item.label}</strong>
              <small>{item.hint}</small>
            </button>
          ))}
        </nav>

        <section className="research-tabpanel" data-research-tab={tab}>
          {tab === 'overview' && (
            <div className="overview-layout">
              <WorkbenchContextPanel
                instrumentId={analysis.instrument_id}
                pattern={selectedPattern}
                crosshair={crosshair}
                latestBar={analysis.bars.at(-1)}
              />
              <section className="reading-guide">
                <span>阅读顺序</span>
                <h3>先看右侧当前阶段，再看图上的关键区域</h3>
                <ol>
                  <li>确认当前是形成中、Terminal 后观察，还是 Type-I / Type-II 阶段。</li>
                  <li>看下一关键价是否来自已冻结的 Source lifecycle。</li>
                  <li>只有需要验证结构时，再进入“形态与价位”。</li>
                  <li>市场环境只作为上下文，不反向修改谐波身份。</li>
                </ol>
              </section>
            </div>
          )}

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
                <span>引擎边界</span>
                <h3>展示层不会重算谐波身份</h3>
                <p>{analysis.engine_note}</p>
                <dl>
                  <div><dt>完成结构</dt><dd>{analysis.completed.length}</dd></div>
                  <div><dt>形成中结构</dt><dd>{analysis.forming.length}</dd></div>
                  <div><dt>Pivot 尺度</dt><dd>{analysis.scales.join(' / ')}</dd></div>
                </dl>
              </section>
            </div>
          )}
        </section>
      </section>
    </section>
  )
}
