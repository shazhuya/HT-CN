import { useCallback, useEffect, useState } from 'react'
import './DailyReviewDigest.css'

type ReviewSnapshot = {
  action_state?: string
  lifecycle_state?: string
  next_key_price?: number | null
  next_key_price_role?: string | null
} | null

type ReviewItem = {
  display_key: string
  instrument_id: string
  review_bucket: string
  change_types: string[]
  previous: ReviewSnapshot
  current: ReviewSnapshot
}

type ReviewSection = {
  workflow_bucket: string
  change_count: number
  items: ReviewItem[]
}

type ReviewDigestPayload = {
  schema_version: number
  status: string
  review_ready: boolean
  trade_date: string | null
  source_observation_id: string | null
  source_revision_ordinal: number | null
  previous_recorded_trade_date: string | null
  delta_status: string | null
  change_count: number
  change_type_counts: Record<string, number>
  workflow_bucket_counts: Record<string, number>
  workflow_sections: ReviewSection[]
  filtered_change_count: number
  filtered_workflow_sections: ReviewSection[]
  analysis_incomplete_count: number
  analysis_incomplete_instruments: string[]
  source_change_count_unchanged: number
  authoritative_evidence: boolean
  writes_m4_evidence: boolean
  historical_outcome_used_for_ranking: boolean
  predictive_score_used: boolean
  alpha_inference_allowed: boolean
  is_trade_instruction: boolean
}

type Props = {
  apiBase: string
  onSelectInstrument: (instrumentId: string) => void
}

const WORKFLOW_LABELS: Record<string, string> = {
  execution_evaluation: '执行评估变化',
  reaction_observation: '反应观察变化',
  waiting: '等待阶段变化',
  evidence_insufficient: '证据不足变化',
  disappeared_candidate: '候选消失',
}

const CHANGE_LABELS: Record<string, string> = {
  new_candidate: '新出现候选',
  disappeared_candidate: '候选消失',
  action_state_changed: '工作状态变化',
  lifecycle_state_changed: '生命周期变化',
  pattern_state_changed: '形态状态变化',
  next_key_changed: '下一关键价变化',
  execution_gate_changed: '执行约束变化',
  context_cautions_changed: '上下文注意项变化',
}

const CHANGE_OPTIONS = Object.keys(CHANGE_LABELS)
const WORKFLOW_OPTIONS = Object.keys(WORKFLOW_LABELS)

function price(value: number | null | undefined) {
  return value == null ? '—' : value.toFixed(2)
}

function transition(
  before: string | undefined,
  after: string | undefined,
) {
  return `${before ?? '—'} → ${after ?? '—'}`
}

export default function DailyReviewDigest({
  apiBase,
  onSelectInstrument,
}: Props) {
  const [payload, setPayload] = useState<ReviewDigestPayload | null>(null)
  const [workflow, setWorkflow] = useState('all')
  const [changeType, setChangeType] = useState('all')
  const [instrument, setInstrument] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback((
    nextWorkflow = 'all',
    nextChangeType = 'all',
    nextInstrument = '',
  ) => {
    setLoading(true)
    setError(null)
    const query = new URLSearchParams()
    if (nextWorkflow !== 'all') {
      query.set('workflow_bucket', nextWorkflow)
    }
    if (nextChangeType !== 'all') {
      query.set('change_type', nextChangeType)
    }
    if (nextInstrument.trim()) {
      query.set('instrument_id', nextInstrument.trim().toUpperCase())
    }

    const suffix = query.toString()
    fetch(`${apiBase}/api/operator/review-digest${suffix ? `?${suffix}` : ''}`)
      .then(async (response) => {
        if (!response.ok) {
          const body = (await response.json().catch(() => null)) as { detail?: string } | null
          throw new Error(body?.detail ?? `HTTP ${response.status}`)
        }
        return response.json() as Promise<ReviewDigestPayload>
      })
      .then(setPayload)
      .catch((err: Error) => {
        setPayload(null)
        setError(err.message)
      })
      .finally(() => setLoading(false))
  }, [apiBase])

  useEffect(() => {
    load()
  }, [load])

  return (
    <section className="daily-review-digest" aria-label="daily-review-digest">
      <div className="daily-review-digest__heading">
        <div>
          <p className="eyebrow">M5 · DAILY REVIEW DIGEST</p>
          <h3>每日变化复盘</h3>
          <p>
            基于最终 append-only 产品历史，把当天变化按既有工作流归类。
            顺序只表示“先看哪类变化”，不是收益率、胜率或买卖排名。
          </p>
        </div>
        <button
          onClick={() => load(workflow, changeType, instrument)}
          disabled={loading}
        >
          {loading ? '刷新中…' : '刷新复盘'}
        </button>
      </div>

      {error && (
        <div className="daily-review-digest__error">
          每日变化复盘不可用：{error}
        </div>
      )}

      {payload && (
        <>
          <div className="daily-review-digest__meta">
            <span>日期：<strong>{payload.trade_date ?? '—'}</strong></span>
            <span>
              对比：<strong>{payload.previous_recorded_trade_date ?? '首个观察日'}</strong>
            </span>
            <span>
              revision：<strong>{payload.source_revision_ordinal ?? '—'}</strong>
            </span>
            <span>产品复盘，不是 M4 evidence</span>
          </div>

          <div className="daily-review-digest__summary">
            <div>
              <span>源变化总数</span>
              <strong>{payload.change_count}</strong>
            </div>
            <div>
              <span>当前筛选命中</span>
              <strong>{payload.filtered_change_count}</strong>
            </div>
            <div>
              <span>分析不完整标的</span>
              <strong>{payload.analysis_incomplete_count}</strong>
            </div>
            <div>
              <span>状态</span>
              <strong>{payload.status}</strong>
            </div>
          </div>

          <div className="daily-review-digest__types">
            {Object.entries(payload.change_type_counts).map(([key, count]) => (
              <span key={key}>
                {CHANGE_LABELS[key] ?? key} <strong>{count}</strong>
              </span>
            ))}
            {Object.keys(payload.change_type_counts).length === 0 && (
              <span>当前没有跨日变化</span>
            )}
          </div>

          <div className="daily-review-digest__filters">
            <label>
              <span>工作流</span>
              <select
                value={workflow}
                onChange={(event) => setWorkflow(event.target.value)}
              >
                <option value="all">全部</option>
                {WORKFLOW_OPTIONS.map((value) => (
                  <option value={value} key={value}>
                    {WORKFLOW_LABELS[value]}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span>变化类型</span>
              <select
                value={changeType}
                onChange={(event) => setChangeType(event.target.value)}
              >
                <option value="all">全部</option>
                {CHANGE_OPTIONS.map((value) => (
                  <option value={value} key={value}>
                    {CHANGE_LABELS[value]}
                  </option>
                ))}
              </select>
            </label>
            <label className="daily-review-digest__instrument">
              <span>证券代码</span>
              <input
                value={instrument}
                onChange={(event) => setInstrument(event.target.value)}
                placeholder="例如 SSE.688256"
              />
            </label>
            <button
              onClick={() => load(workflow, changeType, instrument)}
              disabled={loading}
            >
              应用筛选
            </button>
            <button
              onClick={() => {
                setWorkflow('all')
                setChangeType('all')
                setInstrument('')
                load('all', 'all', '')
              }}
              disabled={loading}
            >
              清除
            </button>
          </div>

          <div className="daily-review-digest__sections">
            {payload.filtered_workflow_sections.map((section) => (
              <section
                className="daily-review-digest__section"
                key={section.workflow_bucket}
              >
                <div className="daily-review-digest__section-head">
                  <strong>
                    {WORKFLOW_LABELS[section.workflow_bucket] ?? section.workflow_bucket}
                  </strong>
                  <span>{section.change_count} 个结构</span>
                </div>
                <div className="daily-review-digest__items">
                  {section.items.map((item) => (
                    <div
                      className="daily-review-digest__item"
                      key={item.display_key}
                    >
                      <button
                        className="daily-review-digest__symbol"
                        onClick={() => onSelectInstrument(item.instrument_id)}
                      >
                        {item.instrument_id}
                      </button>
                      <div>
                        <strong>
                          {item.change_types
                            .map((value) => CHANGE_LABELS[value] ?? value)
                            .join(' · ')}
                        </strong>
                        <span>
                          lifecycle：
                          {transition(
                            item.previous?.lifecycle_state,
                            item.current?.lifecycle_state,
                          )}
                        </span>
                      </div>
                      <div>
                        <span>
                          action：
                          {transition(
                            item.previous?.action_state,
                            item.current?.action_state,
                          )}
                        </span>
                        <span>
                          key：
                          {price(item.previous?.next_key_price)}
                          {' → '}
                          {price(item.current?.next_key_price)}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </section>
            ))}
          </div>

          {payload.filtered_change_count === 0 && (
            <p className="daily-review-digest__empty">
              当前筛选没有命中变化。源变化总数仍为 {payload.change_count}。
            </p>
          )}

          {payload.analysis_incomplete_count > 0 && (
            <details className="daily-review-digest__gaps">
              <summary>
                {payload.analysis_incomplete_count} 个标的本日分析不完整
              </summary>
              <p>
                这些标的的候选缺失不会被误记为“候选消失”。
              </p>
              <div>
                {payload.analysis_incomplete_instruments.join('、')}
              </div>
            </details>
          )}
        </>
      )}
    </section>
  )
}
