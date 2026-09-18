import type { Bar, Pattern } from './HarmonicChart'
import './LifecycleCompass.css'

type Props = {
  pattern: Pattern | null
  bars: Bar[]
}

type CompassState = {
  now: string
  nowDetail: string
  first: string
  next: string
  boundary: string
  action?: string
}

type SourceLifecycleState =
  | 'source_clock_unavailable'
  | 'source_prz_unresolved'
  | 'approaching_source_prz'
  | 'entered_source_prz'
  | 'waiting_terminal'
  | 'source_terminal_complete'
  | 't_plus_1'
  | 'type_i_early_reaction'
  | 'type_i_confirmed'
  | 'type_i_failed'
  | 'reaction_only'
  | 'type_ii_retest_forming'
  | 'type_ii_terminal'
  | 'reversal_evidence'
  | 'invalidated'

type SourceLifecycle = {
  state: SourceLifecycleState
  state_reason: string
  clock_source: string
  current_bar: number
  signal_bar: number | null
  source_prz_entry_bar: number | null
  source_terminal_bar: number | null
  execution_start_bar: number | null
  bars_since_terminal: number | null
  type_i_t1_bar: number | null
  type_i_t2_bar: number | null
  first_source_prz_exit_bar: number | null
  type_ii_retest_entry_bar: number | null
  type_ii_terminal_bar: number | null
  reversal_exit_after_type_ii_bar: number | null
  source_prz_low: number | null
  source_prz_high: number | null
  pez_low: number | null
  pez_high: number | null
  target_382: number | null
  target_618: number | null
  next_key_price: number | null
  next_key_price_role: string | null
  strict_type_ii_full_retest: boolean
  retrospective_geometry_clock_used: boolean
}

type SourceAwarePattern = Pattern & {
  source_lifecycle?: SourceLifecycle
  rsi_bamm_evidence?: Record<string, unknown>
}

function fmtPrice(value: number) {
  return value >= 100 ? value.toFixed(2) : value.toFixed(3)
}

function directionLabel(pattern: Pattern) {
  return pattern.direction === 'bullish' ? '看涨结构' : '看跌结构'
}

function coreLabel(pattern: Pattern) {
  return `${fmtPrice(pattern.prz.price_low)}–${fmtPrice(pattern.prz.price_high)}`
}

function sourceBoundary(pattern: Pattern, lifecycle: SourceLifecycle) {
  const source = lifecycle.source_prz_low != null && lifecycle.source_prz_high != null
    ? `Source PRZ ${fmtPrice(lifecycle.source_prz_low)}–${fmtPrice(lifecycle.source_prz_high)}`
    : 'Source PRZ 未可用'
  const pez = lifecycle.pez_low != null && lifecycle.pez_high != null
    ? ` · PEZ ${fmtPrice(lifecycle.pez_low)}–${fmtPrice(lifecycle.pez_high)}`
    : ''
  return `${source}${pez} · ${directionLabel(pattern)} · S${pattern.scale}`
}

function nextPriceText(lifecycle: SourceLifecycle) {
  if (lifecycle.next_key_price == null) return '当前没有可合法提前指定的下一关键价位。'
  const role: Record<string, string> = {
    source_prz_entry_edge: 'Source PRZ 进入边界',
    source_prz_terminal_side: 'Source PRZ 终端侧',
    type_i_38_2_target: 'Type-I 38.2% 反应目标',
    type_i_61_8_target: 'Type-I 61.8% 反应目标',
    type_ii_reversal_exit_edge: 'Type-II 后反转方向离区边界',
  }
  return `下一关键价位：${fmtPrice(lifecycle.next_key_price)}（${role[lifecycle.next_key_price_role ?? ''] ?? lifecycle.next_key_price_role ?? 'source clock'}）。`
}

function buildSourceLifecycleCompass(pattern: Pattern, lifecycle: SourceLifecycle, latestBar?: Bar): CompassState {
  const price = latestBar ? `最新收盘 ${fmtPrice(latestBar.close)}；` : ''
  const boundary = sourceBoundary(pattern, lifecycle)
  const key = nextPriceText(lifecycle)

  switch (lifecycle.state) {
    case 'source_clock_unavailable':
      return {
        now: 'Source 执行时钟不可重建',
        nowDetail: `${price}${lifecycle.state_reason} 历史 D/C 仍可做几何审计，但不能替代实时执行状态。`,
        first: '先确认该历史形态在终点之前是否存在可观察的 forming projection 与冻结 Source Raw PRZ。',
        next: '只有 source clock 可重建后，才允许进入 PRZ → T-Bar → T+1 → Type-I/II 状态链。',
        action: '当前动作：只做结构审计，不把后验 D/C 当成可执行信号。',
        boundary,
      }
    case 'source_prz_unresolved':
      return {
        now: 'Source PRZ 未冻结 · Fail Closed',
        nowDetail: `${price}${lifecycle.state_reason}`,
        first: '先解决该形态 Source Raw PRZ；Ideal Core、component envelope 和统计容差都不能代替。',
        next: 'Source PRZ 冻结后才能重新建立 entry / Terminal / PEZ 执行时钟。',
        action: '当前动作：等待 source 定义，不升级执行状态。',
        boundary,
      }
    case 'approaching_source_prz':
      return {
        now: '接近 Source PRZ · 尚未进入',
        nowDetail: `${price}forming projection 已经可观察，但价格还没有进入冻结 Source Raw PRZ。${key}`,
        first: '先看价格是否真实触及 Source PRZ 进入边界；未进入前不讨论 Terminal Price Bar。',
        next: '进入后再观察是否继续测试终端侧，而不是把普通 overlap 直接叫完成。',
        action: '当前动作：等待进入，不提前把预测完成点当反转。',
        boundary,
      }
    case 'entered_source_prz':
      return {
        now: '已进入 Source PRZ · 尚未 Terminal',
        nowDetail: `${price}价格刚进入 Source Raw PRZ，但尚未完成终端侧测试。${key}`,
        first: '先看本次进入是否继续触及终端 harmonic side。',
        next: '只有 Terminal Price Bar 成立后才生成 PEZ，并从下一根 T-Bar+1 开始执行观察。',
        action: '当前动作：观察 PRZ 内价格行为，不抢跑 Type-I。',
        boundary,
      }
    case 'waiting_terminal':
      return {
        now: 'PRZ 内/曾进入 · 等待 Source T-Bar',
        nowDetail: `${price}Source PRZ 已被进入，但终端侧测试尚未发生。${key}`,
        first: '先盯 Source PRZ 终端侧；普通区间重叠不等于谐波执行完成。',
        next: 'T-Bar 出现后再切换到 PEZ 与 T-Bar+1 的 Type-I 早期反应观察。',
        action: '当前动作：等待 Terminal，不使用历史 D/C 代替。',
        boundary,
      }
    case 'source_terminal_complete':
      return {
        now: 'Source Terminal Price Bar 已完成',
        nowDetail: `${price}终端侧测试已经真实发生，PEZ 现在才合法成立。${key}`,
        first: '先固定本根 T-Bar 与 PEZ，不在同一根 bar 上偷看后续反应。',
        next: '下一根进入 T-Bar+1；随后观察前 3–5 根的反应力度与 38.2% 目标。',
        action: '当前动作：T-Bar 完成，等待下一根开始执行观察。',
        boundary,
      }
    case 't_plus_1':
      return {
        now: 'T-Bar+1 · 执行观察开始',
        nowDetail: `${price}这是 Source T-Bar 后第一根可执行观察 bar。${key}`,
        first: '先看价格是否迅速脱离 PEZ/Source PRZ，并向 38.2% Type-I 目标推进。',
        next: '前五根内到达 38.2% 才升级为 HT-CN Type-I 早期确认；否则降级为反应不足/晚反应。',
        action: '当前动作：观察早期反应，不把 BAMM 或普通 RSI 单独当成状态升级器。',
        boundary,
      }
    case 'type_i_early_reaction':
      return {
        now: 'Type-I · 早期反应窗口',
        nowDetail: `${price}仍处于 T-Bar 后前五根窗口，38.2% 尚未到达。${key}`,
        first: '先看 38.2% 是否在五根窗口内到达，并观察是否形成对 Source PRZ 的有效分离。',
        next: '五根内到达则升级早期确认；窗口结束仍未到达则记为 Type-I 早期反应不足。',
        action: '当前动作：继续观察，不因一两根反抽提前宣布反转。',
        boundary,
      }
    case 'type_i_confirmed':
      return {
        now: 'Type-I · 早期 38.2% 反应确认',
        nowDetail: `${price}38.2% 在 Source T-Bar 后五根内到达；这是反应确认，不是长期反转证明。${key}`,
        first: '先看 61.8% 延伸目标与价格是否保持离开 Source PRZ。',
        next: '随后重点监控二次回测；一旦重新进入 Source PRZ，转入 Type-II retest 状态链。',
        action: '当前动作：按已发生的 Type-I 反应管理，禁止把它外推成稳定 alpha。',
        boundary,
      }
    case 'type_i_failed':
      return {
        now: 'Type-I · 早期反应不足',
        nowDetail: `${price}T-Bar 后前五根已经结束，38.2% 仍未到达。这不是 harmonic identity 失效，只代表早期 Type-I 反应不够强。${key}`,
        first: '先区分后续是迟到反应、继续滞留，还是重新测试 Source PRZ。',
        next: '迟到到达 38.2% 只能记为 reaction-only；二次进入则按 Type-II retest 处理。',
        action: '当前动作：降低对早期反转的信任，但不要把执行失败偷换成形态身份失败。',
        boundary,
      }
    case 'reaction_only':
      return {
        now: '反应存在 · 已超出早期 Type-I 窗口',
        nowDetail: `${price}38.2% 最终到达，但发生在 T-Bar 后五根之外，因此不追认早期 Type-I confirmation。${key}`,
        first: '先看后续能否继续扩展到 61.8%，以及是否重新进入 Source PRZ。',
        next: '二次进入后只按 strict Type-II retest 状态机升级，禁止回写早期状态。',
        action: '当前动作：把它当晚反应管理，不回填成早期确认。',
        boundary,
      }
    case 'type_ii_retest_forming':
      return {
        now: 'Type-II · 二次回测形成中',
        nowDetail: `${price}第一次反应离开 Source PRZ 后，价格已经重新进入，但尚未完整测试终端侧。${key}`,
        first: '先看是否达到冻结 Source Raw PRZ 的终端侧；partial overlap 不能叫 Type-II Terminal。',
        next: '完整终端侧回测后，再观察回测后的价格离区与独立指标证据。',
        action: '当前动作：等待 strict full-retest，不用 nominal overlap 偷偷升级。',
        boundary,
      }
    case 'type_ii_terminal':
      return {
        now: 'Type-II Terminal 已形成',
        nowDetail: `${price}二次回测已经完整触及冻结 Source PRZ 终端侧。${key}`,
        first: '先看回测后能否重新向反转方向离开 Source PRZ。',
        next: '价格离区后才升级 reversal evidence；RSI/BAMM 仍作为独立辅助证据，不拥有状态。',
        action: '当前动作：等待 Type-II 后价格确认，不在 T-Bar 本身宣布更大级别反转。',
        boundary,
      }
    case 'reversal_evidence':
      return {
        now: 'Type-II 后 · 价格反转证据已出现',
        nowDetail: `${price}strict Type-II Terminal 后，价格已重新向反转方向离开 Source PRZ。该状态仍不等于长期趋势反转已经得到证明。`,
        first: '先看离区后的延续性、第三次测试以及更高层级市场环境。',
        next: '若再次失去结构，应进入独立 invalidation 研究；Phase 1 不发明新的 Carney 失效规则。',
        action: '当前动作：把价格确认与 BAMM/市场环境并列评估，不把单一证据绝对化。',
        boundary,
      }
    case 'invalidated':
      return {
        now: 'Source lifecycle · 已失效',
        nowDetail: `${price}${lifecycle.state_reason}`,
        first: '先确认失效来源是 source-backed 规则，而不是短期价格噪声。',
        next: '失效后回到新的 forming projection；旧生命周期不得复活。',
        action: '当前动作：停止沿用旧 lifecycle。',
        boundary,
      }
  }
}

function buildRetrospectiveCompass(pattern: Pattern, latestBar?: Bar): CompassState {
  const audit = pattern.reaction_audit
  const price = latestBar ? `最新收盘 ${fmtPrice(latestBar.close)}；` : ''
  const boundary = `当前显示核心区 ${coreLabel(pattern)} · ${directionLabel(pattern)} · S${pattern.scale}`

  if (pattern.state === 'forming') {
    return {
      now: '形成中 · 尚未完成',
      nowDetail: `${price}当前只是 ${pattern.schema ?? 'XABCD'} 候选；几何终点仍在形成，不能把预测 D 或核心区当成已经发生的反转。`,
      first: '先看价格是否在仍有效的 forming 投影下测试 source PRZ 的最终/极端测量，并形成 Terminal Price Bar。',
      next: '只有 T-Bar 出现后，执行时钟才从 T-Bar+1 开始；随后再看 3–5 根价格棒与 Type-I 反应。',
      boundary,
    }
  }

  if (!audit) {
    return {
      now: '几何已完成 · 执行时钟未接入',
      nowDetail: `${price}后验几何结构已经成立，但当前 payload 还没有 source-aligned Terminal Price Bar 事件，不能把 D Pivot 直接等同于执行完成。`,
      first: '先补齐 no-lookahead T-Bar 执行时钟；在此之前只把该形态当作结构审计结果。',
      next: 'T-Bar 接入后再判断 source PRZ、PEZ、T-Bar+1、Type-I 以及后续 Type-II。',
      boundary,
    }
  }

  const hasRetest = audit.secondary_prz_retest_bar != null || audit.full_prz_retest_bar != null
  const hasExitAfterRetest = audit.reversal_exit_after_retest_bar != null

  if (hasRetest) {
    if (audit.type_ii_evidence_state === 'source_prz_unresolved') {
      return {
        now: '二次重入已见 · Source PRZ 未冻结',
        nowDetail: `${price}后验价格已经再次进入当前观察区，但该形态的 source Raw PRZ 边界尚未通过 Book Golden Set 冻结，因此系统禁止把这次重入升级为 Type-II。`,
        first: '先完成该形态 source PRZ 的教材图例回归；不能拿 ideal core 或 component envelope 代替。',
        next: 'source PRZ 冻结后，才能重新判断是否完整测试所有关键测量并形成 Type-II Terminal Price Bar。',
        boundary,
      }
    }

    if (audit.type_ii_evidence_state === 'price_and_rsi_confirmed') {
      return {
        now: '后验 Type-II · 价格 + RSI 辅助证据',
        nowDetail: `${price}后验 D 时钟中已经记录 source PRZ 完整回测、回测后价格离开，以及 Wilder RSI 极值反转证据。该 RSI 证据明确不是 RSI BAMM。`,
        first: hasExitAfterRetest
          ? '先看回测后二次离开的延续性；这仍是后验生命周期证据，不是新的谐波身份。'
          : '先看回测后能否重新离开 source PRZ；未离开前不把二次测试解释成反转完成。',
        next: '随后再看第三次测试、结构失效；真正执行结论仍需 source-aligned T-Bar/PEZ 时钟。',
        boundary,
      }
    }

    if (audit.type_ii_evidence_state === 'price_confirmed_no_rsi') {
      return {
        now: '后验 Type-II · 仅价格证据',
        nowDetail: `${price}后验 D 时钟中已经完成 source PRZ 终端侧回测并出现价格确认，但 Wilder RSI 辅助证据没有同步。`,
        first: '先看价格确认能否延续，并保持与 source PRZ 的有效分离。',
        next: '再观察指标辅助证据、第三次测试与失效；不要把普通 RSI 证据称为 BAMM。',
        boundary,
      }
    }

    if (audit.type_ii_evidence_state === 'full_retest_waiting_price') {
      return {
        now: '后验 Type-II T-Bar · 等价格确认',
        nowDetail: `${price}二次测试已经触及冻结 source PRZ 的终端侧，但回测后尚未重新离开，不能升级为 Type-II 价格确认。`,
        first: '先看回测后是否重新离开 source PRZ，形成明确价格确认。',
        next: '价格确认后再看指标辅助证据；实时执行仍由独立 source-aligned T-Bar/PEZ 时钟负责。',
        boundary,
      }
    }

    if (audit.type_ii_evidence_state === 'partial_retest_only') {
      return {
        now: '二次进入 · 尚未完整回测',
        nowDetail: `${price}价格再次进入已冻结的 source PRZ，但尚未测试终端侧；这只是 secondary retest，不是 Type-II Terminal Price Bar。`,
        first: '先看是否完成 source PRZ 全部关键测量的二次测试。',
        next: '形成 Type-II T-Bar 后，才进入回测后价格确认与指标确认阶段。',
        boundary,
      }
    }

    return {
      now: '二次回测 · 后验候选',
      nowDetail: `${price}价格已经回到后验生命周期的第二次测试阶段，但当前证据不足以升级为 Type-II。`,
      first: '先看 source PRZ 是否已冻结、随后是否完整测试终端侧；单纯 overlap 不再视为 Type-II 完成。',
      next: '完整回测后再看价格离开和指标辅助证据。',
      boundary,
    }
  }

  if (audit.bars_to_618 != null) {
    return {
      now: '后验 Type-I · 已到 T2（61.8%）',
      nowDetail: `${price}按 D 点后验时钟，第一阶段反应已经到达 61.8%；这证明历史上发生过反应，但不等于 source-aligned 实时执行完成，更不等于长期反转。`,
      first: '先看后续是否发生二次回测；若 source PRZ 尚未冻结，则禁止升级 Type-II。',
      next: '同时等待正式 runtime 接入 Terminal Price Bar/PEZ 双时钟。',
      boundary,
    }
  }

  if (audit.bars_to_382 != null) {
    return {
      now: '后验 Type-I · 已到 T1，T2 未到',
      nowDetail: `${price}按 D 点后验时钟，第一阶段反应已经到达 38.2%，尚未到达 61.8%。`,
      first: '先看后验 T2 与二次重入哪一个先发生；Type-II 仍要求明确 source PRZ。',
      next: '该记录只用于结构/历史审计；source-aligned 执行路径必须由 T-Bar 时钟单独给出。',
      boundary,
    }
  }

  return {
    now: '几何已完成 · 后验反应早期',
    nowDetail: `${price}当前只有以历史 D 点为锚的反应审计；不能把这一状态写成“Terminal 已完成”。`,
    first: '先看后验价格是否离开当前核心区并推进至 38.2%；同时等待 source-aligned T-Bar runtime 接入。',
    next: '真正的执行顺序应是 source PRZ → Terminal Price Bar → PEZ → T-Bar+1 → Type-I，而不是 D Pivot → 自动执行。',
    boundary,
  }
}

export function buildLifecycleCompass(pattern: Pattern, latestBar?: Bar): CompassState {
  const source = (pattern as SourceAwarePattern).source_lifecycle
  if (source) return buildSourceLifecycleCompass(pattern, source, latestBar)
  return buildRetrospectiveCompass(pattern, latestBar)
}

function getBammEvidence(pattern: Pattern) {
  const sourceAware = pattern as SourceAwarePattern
  const clock = pattern.execution_clock as { rsi_bamm_evidence?: Record<string, unknown> } | undefined
  const evidence = sourceAware.rsi_bamm_evidence ?? clock?.rsi_bamm_evidence
  if (!evidence) return null
  const confirmed = evidence.source_confirmed === true || Number(evidence.source_confirmed_count ?? 0) > 0
  const profile = typeof evidence.profile === 'string' ? ` · ${evidence.profile}` : ''
  const status = typeof evidence.status === 'string' ? evidence.status : 'unknown'
  return {
    confirmed,
    label: confirmed ? `RSI BAMM · Source confirmed${profile}` : 'RSI BAMM · 独立证据未确认',
    detail: confirmed
      ? 'BAMM 与 Source T-Bar/谐波完成通过独立 source gate；它增强确认，但不改变 lifecycle、identity 或 Source PRZ。'
      : `当前状态：${status}。BAMM 不拥有 lifecycle，也不能救活无效形态。`,
  }
}

export default function LifecycleCompass({ pattern, bars }: Props) {
  if (!pattern) return null

  const latestBar = bars.at(-1)
  const sourceLifecycle = (pattern as SourceAwarePattern).source_lifecycle
  const state = buildLifecycleCompass(pattern, latestBar)
  const bamm = getBammEvidence(pattern)
  const sourceDriven = Boolean(sourceLifecycle)

  if (sourceDriven && sourceLifecycle) {
    const mark = (value: number | null) => value == null ? '—' : `#${value}`
    const hit = (value: number | null) => value == null ? '未到达' : `#${value}`
    return (
      <section className="lifecycle-compass source-evidence-compact" aria-label="Source Clock 证据" data-testid="lifecycle-compass">
        <div className="lifecycle-title-row">
          <div>
            <p className="kicker">M3 · Source-Clock Evidence</p>
            <h2>Source Clock 证据</h2>
          </div>
          <span className="lifecycle-boundary">{sourceBoundary(pattern, sourceLifecycle)}</span>
        </div>

        <div className="source-clock-grid">
          <article data-testid="source-clock-state">
            <span>Canonical State</span>
            <strong>{sourceLifecycle.state}</strong>
            <p>{sourceLifecycle.state_reason}</p>
          </article>
          <article>
            <span>Source 时间点</span>
            <strong>T-Bar {mark(sourceLifecycle.source_terminal_bar)} · T+1 {mark(sourceLifecycle.execution_start_bar)}</strong>
            <p>Signal {mark(sourceLifecycle.signal_bar)} · PRZ Entry {mark(sourceLifecycle.source_prz_entry_bar)}</p>
          </article>
          <article>
            <span>Type-I</span>
            <strong>T1 {hit(sourceLifecycle.type_i_t1_bar)} · T2 {hit(sourceLifecycle.type_i_t2_bar)}</strong>
            <p>距 T-Bar {sourceLifecycle.bars_since_terminal ?? '—'} 根 · 下一关键价 {sourceLifecycle.next_key_price == null ? '—' : fmtPrice(sourceLifecycle.next_key_price)}</p>
          </article>
          <article>
            <span>Type-II</span>
            <strong>重入 {mark(sourceLifecycle.type_ii_retest_entry_bar)} · T-Bar {mark(sourceLifecycle.type_ii_terminal_bar)}</strong>
            <p>再离区 {mark(sourceLifecycle.reversal_exit_after_type_ii_bar)} · strict full retest {sourceLifecycle.strict_type_ii_full_retest ? '开启' : '关闭'}</p>
          </article>
        </div>

        {bamm && (
          <div className={`lifecycle-evidence ${bamm.confirmed ? 'confirmed' : ''}`} data-testid="bamm-evidence-channel">
            <strong>{bamm.label}</strong>
            <span>{bamm.detail}</span>
          </div>
        )}

        <p className="lifecycle-note">
          本区只展示 Source Clock 原始证据；“现在在哪 / 先看什么 / 到了再看什么 / 不能升级条件”统一由上方 Decision Narrative 负责。历史 reaction_audit 不覆盖 canonical source lifecycle。
        </p>
      </section>
    )
  }

  return (
    <section className="lifecycle-compass" aria-label="谐波生命周期导航" data-testid="lifecycle-compass">
      <div className="lifecycle-title-row">
        <div>
          <p className="kicker">{sourceDriven ? 'M3 · Source-Clock Lifecycle' : '兼容层 · Retrospective Diagnostic'}</p>
          <h2>现在在哪 · 先看哪 · 到了再看哪</h2>
        </div>
        <span className="lifecycle-boundary">{state.boundary}</span>
      </div>

      <div className={`lifecycle-grid ${state.action ? 'with-action' : ''}`}>
        <article className="lifecycle-step current">
          <span>现在在哪</span>
          <strong>{state.now}</strong>
          <p>{state.nowDetail}</p>
        </article>
        <article className="lifecycle-step">
          <span>先看哪</span>
          <strong>当前第一观察点</strong>
          <p>{state.first}</p>
        </article>
        <article className="lifecycle-step">
          <span>到了再看哪</span>
          <strong>下一阶段</strong>
          <p>{state.next}</p>
        </article>
        {state.action && (
          <article className="lifecycle-step action" data-testid="lifecycle-action">
            <span>当前动作</span>
            <strong>执行层提示</strong>
            <p>{state.action}</p>
          </article>
        )}
      </div>

      {bamm && (
        <div className={`lifecycle-evidence ${bamm.confirmed ? 'confirmed' : ''}`} data-testid="bamm-evidence-channel">
          <strong>{bamm.label}</strong>
          <span>{bamm.detail}</span>
        </div>
      )}

      <p className="lifecycle-note">
        {sourceDriven
          ? '当前状态由当时可观察的 Source PRZ / Terminal Price Bar 时钟驱动。历史 reaction_audit 仅保留为诊断兼容；BAMM、普通 RSI 与 A 股环境均是独立证据层。'
          : '当前 payload 尚未提供 canonical source_lifecycle，因此这里保留旧后验诊断展示；不得把后验 D 时钟误认成实时执行时钟。'}
      </p>
    </section>
  )
}
