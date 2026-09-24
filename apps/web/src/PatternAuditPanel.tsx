import type { Pattern } from './HarmonicChart'
import './PatternAuditPanel.css'

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

function sourcePrzLabel(pattern: Pattern) {
  const source = pattern.prz.source_prz
  if (source) {
    if (!source.available) return '未冻结 · fail closed'
    return priceRange(source.price_low, source.price_high)
  }
  return priceRange(pattern.prz.source_prz_low, pattern.prz.source_prz_high)
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

function isDiscovery(pattern: Pattern) {
  return pattern.discovery_only === true
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

function sharkTargetBasisLabel(value: string | undefined) {
  if (value === '50_percent') return '50% BC 回撤先到'
  if (value === 'reciprocal_abcd') return 'Reciprocal AB=CD 先到'
  if (value === '50_percent_and_reciprocal_abcd_tie') return '50% 与 Reciprocal AB=CD 同位'
  return '—'
}

export default function PatternAuditPanel({ pattern }: { pattern: Pattern | null }) {
  if (!pattern) {
    return <div className="pattern-audit-empty">当前窗口没有可审计的主身份。</div>
  }

  return (
    <section className="pattern-audit-panel" data-testid="pattern-audit-panel">
      <div className="pattern-audit-section">
        <div className="pattern-audit-heading">
          <div>
            <span>当前结构</span>
            <h3>{patternName(pattern.pattern_id)} · {isDiscovery(pattern) ? '发现候选' : pattern.state === 'completed' ? '已完成' : '形成中'}</h3>
          </div>
          <b>S{pattern.scale} · {pattern.schema ?? 'XABCD'}</b>
        </div>
        <div className="audit-node-strip">
          {pattern.points.map((point) => (
            <div key={point.label + point.index}>
              <span>{point.label}</span>
              <strong>{point.price.toFixed(2)}</strong>
              <small>{point.trade_date ?? '—'}</small>
            </div>
          ))}
        </div>
      </div>

      {isDiscovery(pattern) && pattern.discovery && (
        <section className="pattern-audit-section discovery-audit" data-testid="discovery-audit">
          <h3>发现层状态 · 非权威身份</h3>
          <dl>
            <div><dt>路径</dt><dd>{pattern.discovery.path_kind === 'minor_swing_skip' ? `跨次级摆动 · 跳过 ${pattern.discovery.skipped_pivots} 个 pivot` : '连续摆动'}</dd></div>
            <div><dt>可知时点</dt><dd>第 {pattern.discovery.known_from_bar} 根后</dd></div>
            <div><dt>Source PRZ</dt><dd>{pattern.discovery.prz_status === 'tested' ? `已测试 · 第 ${pattern.discovery.first_prz_test_bar} 根` : '已投影 · 尚未测试'}</dd></div>
            <div><dt>C 离散族</dt><dd>{pattern.discovery.source_family_aligned ? '3% 内对齐' : '结构区间有效 · 未达3%离散门槛'}</dd></div>
            <div><dt>最近 C 目标</dt><dd>{fmt(pattern.discovery.c_family_target ?? undefined)}</dd></div>
            <div><dt>C 相对偏差</dt><dd>{pattern.discovery.c_family_relative_error == null ? '—' : `${(pattern.discovery.c_family_relative_error * 100).toFixed(2)}%`}</dd></div>
          </dl>
          <p>这里只说明“值得继续观察”。它不创建 D、不启动 Source 生命周期，也不能用评分把未通过的 canonical identity 变成正式形态。</p>
        </section>
      )}

      <div className="pattern-audit-grid">
        <section className="pattern-audit-section">
          <h3>核心比例</h3>
          <dl>
            {isDiscovery(pattern) ? (
              <>
                <div><dt>B/XA</dt><dd>{fmt(pattern.metrics.b_xa)}</dd></div>
                <div><dt>C/AB</dt><dd>{fmt(pattern.metrics.c_ab)}</dd></div>
                <div><dt>D/XA</dt><dd>未生成</dd></div>
              </>
            ) : isShark(pattern) ? (
              <>
                <div><dt>A/0X</dt><dd>{fmt(pattern.metrics.a_0x)}</dd></div>
                <div><dt>B/XA</dt><dd>{fmt(pattern.metrics.b_xa)}</dd></div>
                <div><dt>C/AB</dt><dd>{fmt(pattern.metrics.c_ab)}</dd></div>
                <div><dt>C/0B</dt><dd>{fmt(pattern.metrics.c_0b)}</dd></div>
              </>
            ) : isFiveZero(pattern) ? (
              <>
                <div><dt>B/XA</dt><dd>{fmt(pattern.metrics.b_xa)}</dd></div>
                <div><dt>C/AB</dt><dd>{fmt(pattern.metrics.c_ab)}</dd></div>
                <div><dt>D/BC</dt><dd>{fmt(pattern.metrics.d_bc)}</dd></div>
                <div><dt>CD/AB</dt><dd>{fmt(pattern.metrics.cd_ab)}</dd></div>
              </>
            ) : isStandaloneAbcd(pattern) ? (
              <>
                <div><dt>C/AB</dt><dd>{fmt(pattern.metrics.c_ab)}</dd></div>
                <div><dt>CD/BC</dt><dd>{fmt(pattern.metrics.bc_projection)}</dd></div>
                <div><dt>CD/AB</dt><dd>{fmt(pattern.metrics.cd_ab)}</dd></div>
              </>
            ) : (
              <>
                <div><dt>B/XA</dt><dd>{fmt(pattern.metrics.b_xa)}</dd></div>
                <div><dt>C/AB</dt><dd>{fmt(pattern.metrics.c_ab)}</dd></div>
                <div><dt>BC投影</dt><dd>{fmt(pattern.metrics.bc_projection)}</dd></div>
                <div><dt>D/XA</dt><dd>{fmt(pattern.metrics.d_xa)}</dd></div>
                <div><dt>CD/AB</dt><dd>{fmt(pattern.metrics.cd_ab)}</dd></div>
              </>
            )}
          </dl>
        </section>

        <section className="pattern-audit-section">
          <h3>价格区</h3>
          <dl>
            <div><dt>HT-CN 收敛核心</dt><dd>{idealCoreLabel(pattern)}</dd></div>
            <div><dt>组件审计包络</dt><dd>{componentEnvelopeLabel(pattern)}</dd></div>
            <div><dt>Source PRZ</dt><dd>{sourcePrzLabel(pattern)}</dd></div>
          </dl>
          <p>{isDiscovery(pattern) ? '发现层只复用既有 Source PRZ 投影；即使价格测试该区，也不会自动生成 Terminal / PEZ / Type-II。' : 'Source PRZ 与工程收敛区严格分层；未冻结时 Terminal / PEZ / Type-II 保持 fail closed。'}</p>
        </section>
      </div>

      {(pattern.identity_conflicts?.length ?? 0) > 1 && (
        <section className="pattern-audit-section">
          <h3>同节点身份</h3>
          <p>主身份为 {patternName(pattern.pattern_id)}；同节点还满足 {pattern.identity_conflicts?.filter((value) => !value.startsWith(pattern.pattern_id + '@')).join('、')}。这些是身份审计，不是多个独立机会。</p>
        </section>
      )}

      {pattern.pivot_support && pattern.pivot_support.length > 0 && (
        <section className="pattern-audit-section">
          <h3>Pivot 跨尺度支持</h3>
          <div className="audit-list">
            {pattern.pivot_support.map((support) => (
              <div key={support.label + '-' + support.index}>
                <span>{support.label} · {support.kind ?? 'pivot'}</span>
                <strong>{support.support_count}尺度 · S{support.scales.join('/')}</strong>
              </div>
            ))}
          </div>
        </section>
      )}

      <section className="pattern-audit-section">
        <h3>组件测量</h3>
        <div className="audit-list">
          {pattern.prz.components.map((component) => (
            <div key={component.name + '-' + component.ratio_low + '-' + component.ratio_high}>
              <span>{component.name}</span>
              <strong>{component.price_low.toFixed(2)}{component.price_high !== component.price_low ? '–' + component.price_high.toFixed(2) : ''}</strong>
            </div>
          ))}
        </div>
      </section>

      {pattern.state === 'completed' && pattern.reaction_targets && (
        <section className="pattern-audit-section">
          <h3>Reaction 目标</h3>
          <dl>
            {pattern.reaction_targets.initial_target != null && (
              <>
                <div><dt>第一目标</dt><dd>{pattern.reaction_targets.initial_target.toFixed(2)}</dd></div>
                <div><dt>第一目标依据</dt><dd>{sharkTargetBasisLabel(pattern.reaction_targets.initial_target_basis)}</dd></div>
                <div><dt>到达第一目标</dt><dd>{hitLabel(pattern.reaction_targets.bars_to_initial_target)}</dd></div>
              </>
            )}
            <div><dt>50% BC 回撤</dt><dd>{pattern.reaction_targets.target_50.toFixed(2)}</dd></div>
            <div><dt>61.8% BC 回撤</dt><dd>{pattern.reaction_targets.target_618.toFixed(2)}</dd></div>
            <div><dt>Reciprocal AB=CD</dt><dd>{pattern.reaction_targets.reciprocal_abcd.toFixed(2)}</dd></div>
          </dl>
          {pattern.reaction_targets.source_note && <p>{pattern.reaction_targets.source_note}</p>}
        </section>
      )}

      {pattern.state === 'completed' && pattern.reaction_audit && (
        <section className="pattern-audit-section">
          <h3>Reaction vs. Reversal 后验审计</h3>
          <dl>
            <div><dt>后验 T1 38.2%</dt><dd>{pattern.reaction_audit.target_382.toFixed(2)} · {hitLabel(pattern.reaction_audit.bars_to_382)}</dd></div>
            <div><dt>后验 T2 61.8%</dt><dd>{pattern.reaction_audit.target_618.toFixed(2)} · {hitLabel(pattern.reaction_audit.bars_to_618)}</dd></div>
            <div><dt>Source PRZ 完整回测</dt><dd>{!pattern.reaction_audit.source_prz_available ? '不可判定' : pattern.reaction_audit.full_prz_retest_bar == null ? '未观察到' : 'D后第 ' + pattern.reaction_audit.full_prz_retest_bar + ' 根'}</dd></div>
            <div><dt>Wilder RSI({pattern.reaction_audit.rsi_period})</dt><dd>{pattern.reaction_audit.rsi_confirmation ? '有辅助确认' : '无辅助确认'}</dd></div>
            <div><dt>Type-II 证据</dt><dd>{evidenceLabel(pattern.reaction_audit.type_ii_evidence_state)}</dd></div>
          </dl>
          <p>此处是后验审计，不自动转化为实时执行结论；普通 Wilder RSI 不等于 RSI BAMM。</p>
        </section>
      )}

      {isFiveZero(pattern) && (
        <div className="pattern-audit-warning">
          5-0 仍处于 Source Conflict 隔离态，只用于研究审计，不作为生产机会发布。
        </div>
      )}
    </section>
  )
}
