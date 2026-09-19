import { useCallback, useEffect, useState } from 'react'
import './DailyReviewDigest.css'

type ReviewSnapshot = {
  action_state?: string
  lifecycle_state?: string
  next_key_price?: number | null
  next_key_price_role?: string | null
} | null

type ReviewState = 'unseen' | 'reviewed' | 'follow_up'

type ReviewInfo = {
  review_state: ReviewState
  note: string
  current_event_id: string | null
  active_follow_up: boolean
  active_follow_up_event_id: string | null
  active_follow_up_origin_observation_id: string | null
  active_follow_up_origin_trade_date: string | null
}

type ReviewItem = {
  display_key: string
  instrument_id: string
  review_bucket: string
  change_types: string[]
  previous: ReviewSnapshot
  current: ReviewSnapshot
  review: ReviewInfo
}

type ReviewSection = {
  workflow_bucket: string
  change_count: number
  items: ReviewItem[]
}

type ActiveFollowUp = {
  display_key: string
  instrument_id: string
  source_observation_id: string
  source_trade_date: string
  source_revision_ordinal: number
  source_change_types: string[]
  event_id: string
  created_at_utc: string
  note: string
  review_state: 'follow_up'
  in_current_digest: boolean
}

type ReviewSessionPayload = {
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
  review_state_counts: Record<ReviewState, number>
  active_follow_ups: ActiveFollowUp[]
  active_follow_up_count: number
  active_follow_up_in_current_digest_count: number
  source_review_state_counts_unchanged: Record<ReviewState, number>
  source_active_follow_up_count_unchanged: number
  authoritative_evidence: boolean
  writes_m4_evidence: boolean
  historical_outcome_used_for_ranking: boolean
  predictive_score_used: boolean
  alpha_inference_allowed: boolean
  is_trade_instruction: boolean
}

type ReviewDraft = {
  state: ReviewState
  note: string
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

const REVIEW_LABELS: Record<ReviewState, string> = {
  unseen: '未看',
  reviewed: '已看',
  follow_up: '后续跟踪',
}

const CHANGE_OPTIONS = Object.keys(CHANGE_LABELS)
const WORKFLOW_OPTIONS = Object.keys(WORKFLOW_LABELS)
const REVIEW_OPTIONS: ReviewState[] = ['unseen', 'reviewed', 'follow_up']

function price(value: number | null | undefined) {
  return value == null ? '—' : value.toFixed(2)
}

function transition(
  before: string | undefined,
  after: string | undefined,
) {
  return `${before ?? '—'} → ${after ?? '—'}`
}

function newClientRequestId() {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return crypto.randomUUID()
  }
  return `review-${Date.now()}-${Math.random().toString(16).slice(2)}`
}

export default function DailyReviewDigest({
  apiBase,
  onSelectInstrument,
}: Props) {
  const [payload, setPayload] = useState<ReviewSessionPayload | null>(null)
  const [workflow, setWorkflow] = useState('all')
  const [changeType, setChangeType] = useState('all')
  const [instrument, setInstrument] = useState('')
  const [reviewState, setReviewState] = useState('all')
  const [followUpOnly, setFollowUpOnly] = useState(false)
  const [drafts, setDrafts] = useState<Record<string, ReviewDraft>>({})
  const [loading, setLoading] = useState(false)
  const [savingKey, setSavingKey] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [saveMessage, setSaveMessage] = useState<string | null>(null)

  const load = useCallback((
    nextWorkflow = 'all',
    nextChangeType = 'all',
    nextInstrument = '',
    nextReviewState = 'all',
    nextFollowUpOnly = false,
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
    if (nextReviewState !== 'all') {
      query.set('review_state', nextReviewState)
    }
    if (nextFollowUpOnly) {
      query.set('follow_up_only', 'true')
    }

    const suffix = query.toString()
    fetch(`${apiBase}/api/operator/review-session${suffix ? `?${suffix}` : ''}`)
      .then(async (response) => {
        if (!response.ok) {
          const body = (await response.json().catch(() => null)) as { detail?: string } | null
          throw new Error(body?.detail ?? `HTTP ${response.status}`)
        }
        return response.json() as Promise<ReviewSessionPayload>
      })
      .then((value) => {
        setPayload(value)
        setDrafts({})
      })
      .catch((err: Error) => {
        setPayload(null)
        setError(err.message)
      })
      .finally(() => setLoading(false))
  }, [apiBase])

  useEffect(() => {
    load()
  }, [load])

  const currentFilters = () => [
    workflow,
    changeType,
    instrument,
    reviewState,
    followUpOnly,
  ] as const

  const closeFollowUp = async (item: ActiveFollowUp) => {
    const key = `follow:${item.display_key}`
    setSavingKey(key)
    setSaveMessage(null)
    setError(null)
    try {
      const response = await fetch(
        `${apiBase}/api/operator/review-session/event`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            source_observation_id: item.source_observation_id,
            display_key: item.display_key,
            review_state: 'reviewed',
            note: '',
            client_request_id: newClientRequestId(),
          }),
        },
      )
      if (!response.ok) {
        const body = (await response.json().catch(() => null)) as { detail?: string } | null
        throw new Error(body?.detail ?? `HTTP ${response.status}`)
      }
      setSaveMessage(`${item.instrument_id} 已结束持续跟踪`)
      const [a, b, c, d, e] = currentFilters()
      load(a, b, c, d, e)
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err)
      setError(`结束跟踪失败：${message}`)
    } finally {
      setSavingKey(null)
    }
  }

  const saveReview = async (item: ReviewItem) => {
    if (!payload?.source_observation_id) return

    const draft = drafts[item.display_key] ?? {
      state: item.review.review_state,
      note: item.review.note,
    }
    setSavingKey(item.display_key)
    setSaveMessage(null)
    setError(null)

    try {
      const response = await fetch(
        `${apiBase}/api/operator/review-session/event`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            source_observation_id: payload.source_observation_id,
            display_key: item.display_key,
            review_state: draft.state,
            note: draft.note,
            client_request_id: newClientRequestId(),
          }),
        },
      )
      if (!response.ok) {
        const body = (await response.json().catch(() => null)) as { detail?: string } | null
        throw new Error(body?.detail ?? `HTTP ${response.status}`)
      }
      setSaveMessage(
        `${item.instrument_id} 已保存：${REVIEW_LABELS[draft.state]}`,
      )
      const [a, b, c, d, e] = currentFilters()
      load(a, b, c, d, e)
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err)
      setError(`复盘状态保存失败：${message}`)
    } finally {
      setSavingKey(null)
    }
  }

  const editFor = (item: ReviewItem): ReviewDraft => (
    drafts[item.display_key] ?? {
      state: item.review.review_state,
      note: item.review.note,
    }
  )

  return (
    <section className="daily-review-digest" aria-label="daily-review-digest">
      <div className="daily-review-digest__heading">
        <div>
          <p className="eyebrow">M5 · DAILY REVIEW SESSION</p>
          <h3>每日变化复盘</h3>
          <p>
            基于最终 append-only 产品历史，把当天变化按既有工作流归类。
            “未看 / 已看 / 后续跟踪”只记录你的复盘进度，不修改 lifecycle、
            action、M4 evidence，也不是收益率、胜率或买卖排名。
          </p>
        </div>
        <button
          onClick={() => {
            const [a, b, c, d, e] = currentFilters()
            load(a, b, c, d, e)
          }}
          disabled={loading}
        >
          {loading ? '刷新中…' : '刷新复盘'}
        </button>
      </div>

      {error && (
        <div className="daily-review-digest__error">
          {error}
        </div>
      )}
      {saveMessage && (
        <div className="daily-review-digest__saved">
          {saveMessage}
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
            <span>复盘 journal，不是 M4 evidence</span>
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
              <span>未看</span>
              <strong>{payload.review_state_counts.unseen ?? 0}</strong>
            </div>
            <div>
              <span>已看</span>
              <strong>{payload.review_state_counts.reviewed ?? 0}</strong>
            </div>
            <div>
              <span>当天后续跟踪</span>
              <strong>{payload.review_state_counts.follow_up ?? 0}</strong>
            </div>
            <div>
              <span>持续跟踪中</span>
              <strong>{payload.active_follow_up_count}</strong>
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

          {payload.active_follow_ups.length > 0 && (
            <section
              className="daily-review-digest__followups"
              aria-label="active-follow-ups"
            >
              <div className="daily-review-digest__followups-head">
                <div>
                  <strong>持续跟踪清单</strong>
                  <span>
                    {payload.active_follow_up_count} 个结构 · 不要求今天必须有新变化
                  </span>
                </div>
                <span>
                  今日有新变化 {payload.active_follow_up_in_current_digest_count}
                </span>
              </div>
              <div className="daily-review-digest__followups-list">
                {payload.active_follow_ups.map((item) => (
                  <div
                    className="daily-review-digest__followup-item"
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
                        {item.in_current_digest ? '今日有新变化' : '今日无新变化'}
                      </strong>
                      <span>
                        跟踪始于 {item.source_trade_date}
                      </span>
                    </div>
                    <div>
                      <span>{item.note || '无备注'}</span>
                    </div>
                    <button
                      onClick={() => closeFollowUp(item)}
                      disabled={savingKey === `follow:${item.display_key}`}
                    >
                      {savingKey === `follow:${item.display_key}`
                        ? '处理中…'
                        : '结束跟踪'}
                    </button>
                  </div>
                ))}
              </div>
            </section>
          )}

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
                aria-label="工作流"
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
                aria-label="变化类型"
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
            <label>
              <span>复盘状态</span>
              <select
                aria-label="复盘状态"
                value={reviewState}
                onChange={(event) => setReviewState(event.target.value)}
              >
                <option value="all">全部</option>
                {REVIEW_OPTIONS.map((value) => (
                  <option value={value} key={value}>
                    {REVIEW_LABELS[value]}
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
            <label className="daily-review-digest__follow-filter">
              <input
                type="checkbox"
                checked={followUpOnly}
                onChange={(event) => setFollowUpOnly(event.target.checked)}
              />
              <span>只看持续跟踪</span>
            </label>
            <button
              onClick={() => {
                const [a, b, c, d, e] = currentFilters()
                load(a, b, c, d, e)
              }}
              disabled={loading}
            >
              应用筛选
            </button>
            <button
              onClick={() => {
                setWorkflow('all')
                setChangeType('all')
                setInstrument('')
                setReviewState('all')
                setFollowUpOnly(false)
                load('all', 'all', '', 'all', false)
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
                  {section.items.map((item) => {
                    const draft = editFor(item)
                    return (
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
                          {item.review.active_follow_up && (
                            <span className="daily-review-digest__follow-badge">
                              {(
                                item.review.active_follow_up_origin_trade_date
                                && payload.trade_date
                                && item.review.active_follow_up_origin_trade_date < payload.trade_date
                              ) ? '跨日跟踪中' : '跟踪中'}
                              {item.review.active_follow_up_origin_trade_date
                                ? ` · 始于 ${item.review.active_follow_up_origin_trade_date}`
                                : ''}
                            </span>
                          )}
                        </div>
                        <div className="daily-review-digest__review-editor">
                          <label>
                            <span>复盘状态</span>
                            <select
                              aria-label={`复盘状态 ${item.instrument_id}`}
                              value={draft.state}
                              onChange={(event) => {
                                const state = event.target.value as ReviewState
                                setDrafts((current) => ({
                                  ...current,
                                  [item.display_key]: {
                                    ...draft,
                                    state,
                                  },
                                }))
                              }}
                            >
                              {REVIEW_OPTIONS.map((value) => (
                                <option value={value} key={value}>
                                  {REVIEW_LABELS[value]}
                                </option>
                              ))}
                            </select>
                          </label>
                          <input
                            aria-label={`复盘备注 ${item.instrument_id}`}
                            value={draft.note}
                            maxLength={1000}
                            onChange={(event) => {
                              const note = event.target.value
                              setDrafts((current) => ({
                                ...current,
                                [item.display_key]: {
                                  ...draft,
                                  note,
                                },
                              }))
                            }}
                            placeholder="复盘备注（最多1000字）"
                          />
                          <button
                            onClick={() => saveReview(item)}
                            disabled={savingKey === item.display_key}
                          >
                            {savingKey === item.display_key ? '保存中…' : '保存复盘'}
                          </button>
                        </div>
                      </div>
                    )
                  })}
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
