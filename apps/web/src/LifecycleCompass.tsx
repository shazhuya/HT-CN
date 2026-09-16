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

export function buildLifecycleCompass(pattern: Pattern, latestBar?: Bar): CompassState {
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
      next: 'T-Bar 接入后再判断 PEZ、T-Bar+1、Type-I 以及后续 Type-II。',
      boundary,
    }
  }

  const hasRetest = audit.secondary_prz_retest_bar != null || audit.full_prz_retest_bar != null
  const hasExitAfterRetest = audit.reversal_exit_after_retest_bar != null

  if (hasRetest) {
    if (audit.type_ii_evidence_state === 'price_and_rsi_confirmed') {
      return {
        now: '后验 Type-II · 价格 + RSI 辅助证据',
        nowDetail: `${price}后验 D 时钟中已经记录完整 PRZ 回测、回测后价格离开，以及 Wilder RSI 极值反转证据。该 RSI 证据明确不是 RSI BAMM。`,
        first: hasExitAfterRetest
          ? '先看回测后二次离开的延续性；这仍是后验生命周期证据，不是新的谐波身份。'
          : '先看回测后能否重新离开核心区；未离开前不把二次测试解释成反转完成。',
        next: '随后再看第三次测试、结构失效；真正执行结论仍需 source-aligned T-Bar/PEZ 时钟。',
        boundary,
      }
    }

    if (audit.type_ii_evidence_state === 'price_confirmed_no_rsi') {
      return {
        now: '后验 Type-II · 仅价格证据',
        nowDetail: `${price}后验 D 时钟中已经完成原 PRZ 终端侧回测并出现价格确认，但 Wilder RSI 辅助证据没有同步。`,
        first: '先看价格确认能否延续，并保持与核心区的有效分离。',
        next: '再观察指标辅助证据、第三次测试与失效；不要把普通 RSI 证据称为 BAMM。',
        boundary,
      }
    }

    if (audit.type_ii_evidence_state === 'full_retest_waiting_price') {
      return {
        now: '后验 Type-II T-Bar · 等价格确认',
        nowDetail: `${price}二次测试已经触及当前审计区的终端侧，但回测后尚未重新离开，不能升级为 Type-II 价格确认。`,
        first: '先看回测后是否重新离开该区域，形成明确价格确认。',
        next: '价格确认后再看指标辅助证据；完整 source PRZ/PEZ 接入前保持“后验”标签。',
        boundary,
      }
    }

    if (audit.type_ii_evidence_state === 'partial_retest_only') {
      return {
        now: '二次进入 · 尚未完整回测',
        nowDetail: `${price}价格再次进入当前审计区，但尚未测试终端侧；这只是 secondary retest，不是 Type-II Terminal Price Bar。`,
        first: '先看是否完成原 PRZ 全部关键测量的二次测试。',
        next: '形成 Type-II T-Bar 后，才进入回测后价格确认与指标确认阶段。',
        boundary,
      }
    }

    return {
      now: '二次回测 · 后验候选',
      nowDetail: `${price}价格已经回到后验生命周期的第二次测试阶段，但当前证据不足以升级为 Type-II。`,
      first: '先看是否完整测试终端侧；单纯 overlap 不再视为 Type-II 完成。',
      next: '完整回测后再看价格离开和指标辅助证据。',
      boundary,
    }
  }

  if (audit.bars_to_618 != null) {
    return {
      now: '后验 Type-I · 已到 T2（61.8%）',
      nowDetail: `${price}按 D 点后验时钟，第一阶段反应已经到达 61.8%；这证明历史上发生过反应，但不等于 source-aligned 实时执行完成，更不等于长期反转。`,
      first: '先看后续是否发生二次回测，以及是否完整测试终端侧。',
      next: '同时等待正式 runtime 接入 Terminal Price Bar/PEZ 双时钟。',
      boundary,
    }
  }

  if (audit.bars_to_382 != null) {
    return {
      now: '后验 Type-I · 已到 T1，T2 未到',
      nowDetail: `${price}按 D 点后验时钟，第一阶段反应已经到达 38.2%，尚未到达 61.8%。`,
      first: '先看后验 T2 与二次完整回测哪一个先发生。',
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

export default function LifecycleCompass({ pattern, bars }: Props) {
  if (!pattern) return null

  const latestBar = bars.at(-1)
  const state = buildLifecycleCompass(pattern, latestBar)

  return (
    <section className="lifecycle-compass" aria-label="谐波生命周期导航" data-testid="lifecycle-compass">
      <div className="lifecycle-title-row">
        <div>
          <p className="kicker">M2.26 · Source Fidelity Guard</p>
          <h2>现在在哪 · 先看哪 · 到了再看哪</h2>
        </div>
        <span className="lifecycle-boundary">{state.boundary}</span>
      </div>

      <div className="lifecycle-grid">
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
      </div>

      <p className="lifecycle-note">
        当前工作台明确区分“几何/后验 D 时钟”和“source-aligned Terminal Price Bar 执行时钟”。后者尚未正式接入 runtime 前，后验 T1/T2 只用于研究与审计，不作为实时买卖信号。
      </p>
    </section>
  )
}
