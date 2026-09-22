import type { Bar, CrosshairSnapshot, Pattern } from './HarmonicChart'

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

const METRIC_LABELS: Record<string, string> = {
  b_xa: 'B/XA',
  c_ab: 'C/AB',
  bc_projection: 'BC投影',
  d_xa: 'D/XA',
  cd_ab: 'CD/AB',
  a_0x: 'A/0X',
  c_0b: 'C/0B',
  d_bc: 'D/BC',
}

function patternName(id: string) {
  return PATTERN_NAMES[id] ?? id
}

function price(value: number | null | undefined) {
  if (value == null || !Number.isFinite(value)) return '—'
  return value >= 100 ? value.toFixed(2) : value.toFixed(3)
}

function range(low: number | null | undefined, high: number | null | undefined) {
  if (low == null || high == null) return '未冻结 · fail closed'
  return `${price(low)} – ${price(high)}`
}

function sourcePrz(pattern: Pattern | null) {
  if (!pattern) return '—'
  const lifecycle = pattern.source_lifecycle
  if (lifecycle?.source_prz_low != null && lifecycle.source_prz_high != null) {
    return range(lifecycle.source_prz_low, lifecycle.source_prz_high)
  }
  const source = pattern.prz.source_prz
  if (source) {
    if (!source.available) return '未冻结 · fail closed'
    return range(source.price_low, source.price_high)
  }
  return range(pattern.prz.source_prz_low, pattern.prz.source_prz_high)
}

function targetRows(pattern: Pattern | null) {
  if (!pattern) return [] as Array<{ label: string; value: string; state: string }>
  const lifecycle = pattern.source_lifecycle
  if (lifecycle?.target_382 != null && lifecycle.target_618 != null) {
    return [
      {
        label: 'Source T1 38.2%',
        value: price(lifecycle.target_382),
        state: lifecycle.type_i_t1_bar == null ? '待到达' : '已到达',
      },
      {
        label: 'Source T2 61.8%',
        value: price(lifecycle.target_618),
        state: lifecycle.type_i_t2_bar == null ? '待到达' : '已到达',
      },
    ]
  }
  const audit = pattern.reaction_audit
  if (!audit) return []
  return [
    {
      label: '后验 T1 38.2%',
      value: price(audit.target_382),
      state: audit.bars_to_382 == null ? '未触及' : '已触及',
    },
    {
      label: '后验 T2 61.8%',
      value: price(audit.target_618),
      state: audit.bars_to_618 == null ? '未触及' : '已触及',
    },
  ]
}

function lifecycleLabel(pattern: Pattern | null) {
  if (!pattern) return '暂无有效形态'
  if (pattern.source_lifecycle) return pattern.source_lifecycle.state
  return pattern.state === 'forming' ? 'forming · 等待完成' : 'completed · source clock 未接入'
}

export default function WorkbenchContextPanel({
  instrumentId,
  pattern,
  crosshair,
  latestBar,
}: {
  instrumentId: string
  pattern: Pattern | null
  crosshair: CrosshairSnapshot | null
  latestBar: Bar | undefined
}) {
  const narrative = pattern?.decision_narrative
  const observed = crosshair ?? (
    latestBar
      ? {
          tradeDate: latestBar.trade_date,
          open: latestBar.open,
          high: latestBar.high,
          low: latestBar.low,
          close: latestBar.close,
          volume: latestBar.volume,
          nodes: [] as string[],
          lifecycle: [] as string[],
        }
      : null
  )
  const metrics = pattern
    ? Object.entries(pattern.metrics)
        .filter(([key, value]) => METRIC_LABELS[key] && Number.isFinite(value))
        .slice(0, 6)
    : []

  return (
    <section className="workbench-context-panel" data-testid="workbench-context-panel">
      <div className="workbench-context-heading">
        <div>
          <span>CANONICAL WORKBENCH CONTEXT</span>
          <h3>实时研究上下文</h3>
        </div>
        <b>{instrumentId}</b>
      </div>

      <article className="workbench-crosshair-card" data-testid="workbench-crosshair-context">
        <span>{crosshair ? '十字光标定位' : '最新 canonical bar'}</span>
        {observed ? (
          <>
            <strong>{observed.tradeDate} · C {price(observed.close)}</strong>
            <small>
              O {price(observed.open)} · H {price(observed.high)} · L {price(observed.low)}
            </small>
            {(observed.nodes.length > 0 || observed.lifecycle.length > 0) && (
              <small>
                {observed.nodes.length > 0 ? `节点 ${observed.nodes.join(' / ')}` : ''}
                {observed.nodes.length > 0 && observed.lifecycle.length > 0 ? ' · ' : ''}
                {observed.lifecycle.join(' / ')}
              </small>
            )}
          </>
        ) : (
          <strong>暂无 K 线定位</strong>
        )}
      </article>

      {pattern ? (
        <>
          <div className="workbench-context-grid">
            <article>
              <span>当前形态</span>
              <strong>{patternName(pattern.pattern_id)}</strong>
              <small>
                {pattern.schema ?? 'XABCD'} · S{pattern.scale} · {pattern.direction === 'bullish' ? '看涨结构' : '看跌结构'}
              </small>
            </article>
            <article>
              <span>生命周期</span>
              <strong>{lifecycleLabel(pattern)}</strong>
              <small>{pattern.state === 'forming' ? '形成中，不制造未来节点' : '已完成几何'}</small>
            </article>
            <article>
              <span>Source PRZ</span>
              <strong>{sourcePrz(pattern)}</strong>
              <small>Raw PRZ 与 HT-CN core 严格分层</small>
            </article>
            <article>
              <span>下一关键价</span>
              <strong>{price(narrative?.next_key_price ?? pattern.source_lifecycle?.next_key_price)}</strong>
              <small>{narrative?.next_key_price_role ?? pattern.source_lifecycle?.next_key_price_role ?? '当前无冻结角色'}</small>
            </article>
          </div>

          {targetRows(pattern).length > 0 && (
            <div className="workbench-targets">
              {targetRows(pattern).map((item) => (
                <div key={item.label}>
                  <span>{item.label}</span>
                  <strong>{item.value}</strong>
                  <b>{item.state}</b>
                </div>
              ))}
            </div>
          )}

          {metrics.length > 0 && (
            <div className="workbench-ratios">
              {metrics.map(([key, value]) => (
                <div key={key}>
                  <span>{METRIC_LABELS[key]}</span>
                  <strong>{Number(value).toFixed(3)}</strong>
                </div>
              ))}
            </div>
          )}

          <p className="workbench-context-boundary">
            当前面板只读取 canonical bar / harmonic / Source lifecycle identity；hover、crosshair 与候选切换不会创建新形态，也不会改变 Source PRZ。
          </p>
        </>
      ) : (
        <p className="workbench-context-empty">当前窗口没有通过规则的主身份；K线与运行时状态仍可继续观察。</p>
      )}
    </section>
  )
}
