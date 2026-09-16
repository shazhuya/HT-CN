import { Bar, Pattern } from './HarmonicChart'
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

function przLabel(pattern: Pattern) {
  return `${fmtPrice(pattern.prz.price_low)}–${fmtPrice(pattern.prz.price_high)}`
}

export function buildLifecycleCompass(pattern: Pattern, latestBar?: Bar): CompassState {
  const audit = pattern.reaction_audit
  const price = latestBar ? `最新收盘 ${fmtPrice(latestBar.close)}；` : ''
  const boundary = `PRZ ${przLabel(pattern)} · ${directionLabel(pattern)} · S${pattern.scale}`

  if (pattern.state === 'forming') {
    return {
      now: '形成中 · 尚未完成',
      nowDetail: `${price}当前只是 ${pattern.schema ?? 'XABCD'} 候选，终点仍在形成，不能当成已经反转。`,
      first: '先看价格是否真正测试 PRZ，并形成可审计的 Terminal Price Bar。',
      next: '完成以后，再看价格能否脱离 PRZ，进入 Type-I 反应，而不是提前把预测终点当成事实。',
      boundary,
    }
  }

  if (!audit) {
    return {
      now: '已完成 · 反应待确认',
      nowDetail: `${price}形态已经完成，PRZ 已建立；当前需要从“几何完成”切换到“反应是否发生”的观察。`,
      first: '先看能否离开 PRZ，并向 Type-I T1（38.2%）推进。',
      next: 'T1 之后再看 T2（61.8%）与二次 PRZ 回测；二者决定后续属于延续反应还是进入 Type-II 观察。',
      boundary,
    }
  }

  const hasRetest = audit.secondary_prz_retest_bar != null || audit.full_prz_retest_bar != null
  const hasExitAfterRetest = audit.reversal_exit_after_retest_bar != null

  if (hasRetest) {
    if (audit.type_ii_evidence_state === 'price_and_rsi_confirmed') {
      return {
        now: 'Type-II · 价格 + RSI 证据',
        nowDetail: `${price}已经出现二次 PRZ 回测，并同时满足当前 Type-II 的价格与 Wilder RSI 证据层。`,
        first: hasExitAfterRetest
          ? '先看回测后二次离开的延续性；这是生命周期证据，不是新的谐波身份。'
          : '先看回测后能否重新离开 PRZ；未离开前不把二次测试解释成反转完成。',
        next: '随后再看是否出现第三次 PRZ 测试、结构失效或新的独立谐波结构。',
        boundary,
      }
    }

    if (audit.type_ii_evidence_state === 'price_confirmed_no_rsi') {
      return {
        now: 'Type-II · 仅价格证据',
        nowDetail: `${price}已经发生二次 PRZ 回测并出现价格确认，但 RSI 证据尚未同步。`,
        first: '先看价格确认能否延续，并保持与 PRZ 的有效分离。',
        next: '再看 RSI 是否补充确认，以及是否出现第三次 PRZ 测试或结构失效。',
        boundary,
      }
    }

    return {
      now: '二次回测 PRZ · Type-II 候选',
      nowDetail: `${price}价格已经回到 PRZ 生命周期的第二次测试阶段，但当前证据还不足以把它升级为 Type-II 确认。`,
      first: '先看回测后是否重新离开 PRZ，并形成价格确认。',
      next: '价格确认以后再看 RSI 证据；若继续反复测试 PRZ，则优先审计第三次测试与失效风险。',
      boundary,
    }
  }

  if (audit.bars_to_618 != null) {
    return {
      now: 'Type-I · 已到 T2（61.8%）',
      nowDetail: `${price}形态完成后的第一阶段反应已经到达 T2；这证明发生过反应，但不自动等于长期反转。`,
      first: '先看后续是否出现二次 PRZ 回测。',
      next: '若发生回测，再看能否重新离开 PRZ，并进入独立的 Type-II 证据判断。',
      boundary,
    }
  }

  if (audit.bars_to_382 != null) {
    return {
      now: 'Type-I · 已到 T1，T2 未到',
      nowDetail: `${price}第一阶段反应已经到达 38.2% 目标，但尚未到达 61.8% 目标。`,
      first: '先看 T2（61.8%）与二次 PRZ 回测哪一个先出现。',
      next: '若先回测 PRZ，再切换到 Type-II 候选审计；若先到 T2，则先完成 Type-I 反应记录。',
      boundary,
    }
  }

  return {
    now: '已完成 · Type-I 反应早期',
    nowDetail: `${price}Terminal/完成阶段已经出现，但 T1（38.2%）与 T2（61.8%）尚未记录到达。`,
    first: '先看能否完整离开 PRZ，并向 T1（38.2%）推进。',
    next: '若 T1 到达，再看 T2；若价格先回到 PRZ，则转入二次测试/Type-II 候选审计。',
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
          <p className="kicker">M3 · 生命周期导航</p>
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
        这是生命周期观察顺序，不是买卖信号。Carney 几何身份与 PRZ 来自 M2 冻结核心；统计证据和后续 A 股执行环境必须保持独立分层。
      </p>
    </section>
  )
}
