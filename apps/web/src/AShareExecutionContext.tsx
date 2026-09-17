import './AShareExecutionContext.css'

export type AShareExecutionContextPayload = {
  instrument_id: string
  symbol: string
  board: string
  as_of_trade_date: string | null
  metadata_available: boolean
  metadata_source: string | null
  list_date: string | null
  is_st: boolean | null
  t_plus_one: boolean
  same_day_sell_after_buy: boolean
  earliest_sell_offset_sessions_after_buy: number
  nominal_price_limit_pct: number | null
  rule_based_price_limit_pct: number | null
  price_limit_status: string
  ipo_first_five_sessions: boolean | null
  special_event_exceptions_unresolved: boolean
  atr_period: number
  atr: number | null
  atr_pct: number | null
  latest_range_pct: number | null
  avg_volume_20: number | null
  volume_ratio_20: number | null
  bse_deferred: boolean
  mutates_harmonic_identity: boolean
  mutates_source_raw_prz: boolean
}

type Props = {
  context?: AShareExecutionContextPayload
}

function pct(value: number | null) {
  return value == null ? '未解析' : `${value.toFixed(2)}%`
}

function num(value: number | null, digits = 2) {
  return value == null ? '—' : value.toFixed(digits)
}

function boardLabel(value: string) {
  if (value === 'STAR') return '科创板'
  if (value === 'CHINEXT') return '创业板'
  if (value === 'MAIN') return '沪深主板'
  if (value === 'BSE') return '北交所（暂缓）'
  return value
}

function limitStatus(context: AShareExecutionContextPayload) {
  if (context.bse_deferred) return '北交所规则暂不进入默认执行层'
  if (context.price_limit_status === 'ipo_first_five_sessions_no_price_limit') return '上市前5个交易日：不套用日常涨跌幅限制'
  if (context.price_limit_status === 'historical_main_risk_warning_5pct_before_2026_07_06') return '历史风险警示主板规则：5%（2026-07-06前）'
  if (context.price_limit_status === 'nominal_only_security_metadata_unavailable') return '只有板块名义规则；证券元数据不足，禁止推断精确适用规则'
  if (context.price_limit_status === 'board_rule_profile_resolved_special_events_unresolved') return '板块/风险警示/上市年龄规则已解析；特殊事件例外仍需元数据'
  return context.price_limit_status
}

export default function AShareExecutionContext({ context }: Props) {
  if (!context) return null

  return (
    <section className="execution-context" data-testid="a-share-execution-context" aria-label="A股执行约束">
      <div className="execution-context-heading">
        <div>
          <p className="kicker">M3 · A-SHARE EXECUTION CONTEXT</p>
          <h2>A 股执行约束与波动背景</h2>
        </div>
        <span>{boardLabel(context.board)} · {context.as_of_trade_date ?? '日期未知'}</span>
      </div>

      <div className="execution-context-grid">
        <article>
          <span>T+1</span>
          <strong>{context.t_plus_one ? '买入后最早下一交易日卖出' : '未启用'}</strong>
          <p>同日买入后卖出：{context.same_day_sell_after_buy ? '允许' : '不允许'}</p>
        </article>
        <article>
          <span>涨跌幅制度</span>
          <strong>{context.rule_based_price_limit_pct == null ? '当前不设规则值' : `规则值 ±${context.rule_based_price_limit_pct.toFixed(0)}%`}</strong>
          <p>{limitStatus(context)}</p>
        </article>
        <article>
          <span>ATR({context.atr_period})</span>
          <strong>{num(context.atr)} · {pct(context.atr_pct)}</strong>
          <p>用来理解该标的正常波动尺度，不作为谐波形态通过条件。</p>
        </article>
        <article>
          <span>最新日内振幅</span>
          <strong>{pct(context.latest_range_pct)}</strong>
          <p>按上一收盘价归一化的当日高低区间。</p>
        </article>
        <article>
          <span>20日量能</span>
          <strong>量比 {num(context.volume_ratio_20)}</strong>
          <p>前20日均量 {context.avg_volume_20 == null ? '—' : Math.round(context.avg_volume_20).toLocaleString()}</p>
        </article>
        <article>
          <span>证券元数据</span>
          <strong>{context.metadata_available ? '已接入' : '不足 · Fail Safe'}</strong>
          <p>{context.list_date ? `上市 ${context.list_date}` : '上市日未知'} · ST状态 {context.is_st == null ? '未知' : context.is_st ? '是' : '否'}</p>
        </article>
      </div>

      <p className="execution-context-note">
        此层只解释“当前 source lifecycle 事件能否以及如何被 A 股制度/波动环境约束”。
        {context.special_event_exceptions_unresolved ? ' 停复牌等特殊事件例外尚未完整接入，因此不把规则值冒充当天精确涨跌停价。' : ''}
        {' '}它不会创建、修复或否定谐波身份，也不会修改 Source Raw PRZ。
      </p>
    </section>
  )
}
