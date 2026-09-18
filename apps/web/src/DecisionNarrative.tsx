import './DecisionNarrative.css'

export type DecisionNarrativePayload = {
  lifecycle_state: string
  action_state: string
  current_position: string
  first_watch: string
  next_watch: string
  upgrade_blocker: string
  next_key_price: number | null
  next_key_price_role: string | null
  execution_context_gate: string
  context_cautions: string[]
  is_trade_instruction: boolean
  uses_score: boolean
  mutates_harmonic_identity: boolean
  mutates_source_raw_prz: boolean
  owns_lifecycle: boolean
}

const actionLabels: Record<string, string> = {
  waiting: '等待',
  reaction_observation: '反应观察',
  execution_evaluation: '执行评估',
  evidence_insufficient: '证据不足',
}

const roleLabels: Record<string, string> = {
  source_prz_entry_edge: 'Source PRZ 入场边界',
  source_prz_terminal_side: 'Source PRZ terminal side',
  type_i_38_2_target: 'Type-I 38.2% 目标',
  type_i_61_8_target: 'Type-I 61.8% 目标',
  type_ii_reversal_exit_edge: 'Type-II 后反转方向离区边界',
}

function price(value: number | null) {
  if (value == null) return '—'
  return value >= 100 ? value.toFixed(2) : value.toFixed(3)
}

export default function DecisionNarrative({ narrative }: { narrative?: DecisionNarrativePayload }) {
  if (!narrative) return null
  return (
    <section className="decision-narrative" data-testid="decision-narrative" data-action-state={narrative.action_state}>
      <div className="decision-narrative-heading">
        <div>
          <p className="kicker">M3 · ACTION-STATE NARRATIVE</p>
          <h2>当前阶段：{actionLabels[narrative.action_state] ?? narrative.action_state}</h2>
        </div>
        <span>Lifecycle: {narrative.lifecycle_state}</span>
      </div>

      <div className="decision-narrative-grid">
        <article>
          <span>现在在哪</span>
          <p>{narrative.current_position}</p>
        </article>
        <article>
          <span>先看什么</span>
          <p>{narrative.first_watch}</p>
        </article>
        <article>
          <span>到了再看什么</span>
          <p>{narrative.next_watch}</p>
        </article>
        <article>
          <span>不能升级的条件</span>
          <p>{narrative.upgrade_blocker}</p>
        </article>
      </div>

      <div className="decision-narrative-key">
        <strong>下一关键价</strong>
        <span>{price(narrative.next_key_price)} · {narrative.next_key_price_role ? (roleLabels[narrative.next_key_price_role] ?? narrative.next_key_price_role) : '当前无冻结关键价'}</span>
      </div>

      {narrative.context_cautions.length > 0 && (
        <div className="decision-narrative-cautions">
          <strong>上下文注意项</strong>
          <ul>{narrative.context_cautions.map((item) => <li key={item}>{item}</li>)}</ul>
        </div>
      )}

      <p className="decision-narrative-note">
        该卡片组织观察顺序，不是买卖指令，也不使用综合评分。市场/行业/题材只能形成注意项，不能反向修改 source lifecycle、harmonic identity 或 Source Raw PRZ。
      </p>
    </section>
  )
}
