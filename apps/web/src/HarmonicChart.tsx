import { useEffect, useMemo, useRef, useState } from 'react'
import {
  CandlestickSeries,
  ColorType,
  CrosshairMode,
  createChart,
  type IChartApi,
  type ISeriesApi,
  type Time,
} from 'lightweight-charts'
import type { AShareExecutionContextPayload } from './AShareExecutionContext'
import type { DecisionNarrativePayload } from './DecisionNarrative'
import LifecycleCompass from './LifecycleCompass'
import './HarmonicChartLifecycle.css'
import './InteractiveHarmonicChart.css'

export type Bar = {
  index: number
  trade_date: string
  open: number
  high: number
  low: number
  close: number
  volume: number
}

export type HarmonicPoint = {
  label: string
  index: number
  price: number
  trade_date?: string
}

export type PivotSupport = {
  label: string
  index: number
  kind: 'high' | 'low' | null
  scales: number[]
  support_count: number
  max_scale: number
}

export type PrzComponent = {
  name: string
  price_low: number
  price_high: number
  ratio_low: number
  ratio_high: number
}

export type PriceZoneLayer = {
  price_low: number
  price_high: number
  width: number
  status?: string
}

export type SourcePrzLayer = {
  available: boolean
  price_low: number | null
  price_high: number | null
  width: number | null
  status: 'frozen' | 'unresolved_fail_closed' | string
}

export type ReactionAudit = {
  d_index: number
  bars_observed: number
  target_382: number
  target_618: number
  bars_to_382: number | null
  bars_to_618: number | null
  first_prz_exit_bar: number | null
  secondary_prz_retest_bar: number | null
  source_prz_available: boolean
  full_prz_retest_bar: number | null
  type_ii_terminal_bar?: number | null
  reversal_exit_after_retest_bar: number | null
  bars_to_reversal_exit_after_retest: number | null
  third_prz_test_bar: number | null
  no_prz_retest_first_3_bars: boolean | null
  no_prz_retest_first_5_bars: boolean | null
  max_favorable_price: number | null
  max_favorable_retracement: number | null
  type_ii_candidate: boolean
  rsi_period: number
  rsi_at_d: number | null
  rsi_extreme_bar: number | null
  rsi_extreme_value: number | null
  rsi_trigger_bar: number | null
  rsi_trigger_value: number | null
  rsi_confirmation: boolean
  indicator_evidence_kind?: string
  indicator_evidence_is_rsi_bamm?: boolean
  type_ii_evidence_state:
    | 'not_candidate'
    | 'source_prz_unresolved'
    | 'partial_retest_only'
    | 'full_retest_waiting_price'
    | 'price_confirmed_no_rsi'
    | 'price_and_rsi_confirmed'
    | 'retest_only'
}

export type ReactionTargets = {
  target_50: number
  target_618: number
  reciprocal_abcd: number
  bars_to_50: number | null
  bars_to_618: number | null
  bars_to_reciprocal_abcd: number | null
  initial_target?: number
  initial_target_basis?: string
  bars_to_initial_target?: number | null
  management_rule?: string
  source_note?: string
}

export type SourceLifecycle = {
  state: string
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

export type Pattern = {
  pattern_id: string
  schema?: 'XABCD' | 'ABCD' | '0XABC' | 'FIVE_ZERO'
  direction: 'bullish' | 'bearish'
  state: 'forming' | 'completed'
  scale: number
  geometry_score: number
  points: HarmonicPoint[]
  pivot_support?: PivotSupport[]
  identity_conflicts?: string[]
  is_primary_identity?: boolean
  reaction_audit?: ReactionAudit
  reaction_targets?: ReactionTargets
  completion_class?: string
  reciprocal_inside_execution_band?: boolean
  execution_clock?: Record<string, unknown>
  execution_clock_policy?: string
  source_lifecycle?: SourceLifecycle
  rsi_bamm_evidence?: Record<string, unknown>
  a_share_execution_context?: AShareExecutionContextPayload
  decision_narrative?: DecisionNarrativePayload
  prz: {
    price_low: number
    price_high: number
    width: number
    component_price_low?: number
    component_price_high?: number
    source_prz_low?: number | null
    source_prz_high?: number | null
    semantics_version?: number
    legacy_price_semantics?: string
    ideal_core?: PriceZoneLayer
    component_envelope?: PriceZoneLayer
    source_prz?: SourcePrzLayer
    components: PrzComponent[]
  }
  metrics: Record<string, number>
}

type Props = {
  bars: Bar[]
  pattern: Pattern | null
  focusPattern?: boolean
}

type LifecycleTarget = {
  id: 't1' | 't2'
  label: string
  price: number
  reached: boolean
  sourceClock: boolean
}

type SourceEvent = {
  id:
    | 'prz-entry'
    | 'tbar'
    | 'tplus1'
    | 'type-i-t1'
    | 'type-i-t2'
    | 'type-ii-entry'
    | 'type-ii-terminal'
    | 'reversal-exit'
  bar: number
  label: string
  emphasis: 'minor' | 'major' | 'confirm'
}

type OverlayPoint = HarmonicPoint & {
  x: number
  y: number
}

type OverlayLeg = {
  name: string
  x1: number
  y1: number
  x2: number
  y2: number
}

type OverlayZone = {
  id: 'ideal-core' | 'source-prz' | 'pez'
  x: number
  y: number
  width: number
  height: number
}

type OverlayTarget = LifecycleTarget & {
  x1: number
  x2: number
  y: number
}

type OverlayEvent = SourceEvent & {
  x: number
  y: number
}

type OverlayGeometry = {
  width: number
  height: number
  points: OverlayPoint[]
  legs: OverlayLeg[]
  zones: OverlayZone[]
  targets: OverlayTarget[]
  events: OverlayEvent[]
}

type CrosshairSnapshot = {
  date: string
  open: number
  high: number
  low: number
  close: number
  node: string | null
}

const CHART_HEIGHT = 520

function formatPrice(value: number) {
  return value >= 100 ? value.toFixed(2) : value.toFixed(3)
}

function timeKey(time: Time | undefined): string {
  if (time == null) return ''
  if (typeof time === 'string') return time
  if (typeof time === 'number') return new Date(time * 1000).toISOString().slice(0, 10)
  const month = String(time.month).padStart(2, '0')
  const day = String(time.day).padStart(2, '0')
  return `${time.year}-${month}-${day}`
}

function lifecycleTargets(pattern: Pattern | null): LifecycleTarget[] {
  const lifecycle = pattern?.source_lifecycle
  if (lifecycle?.target_382 != null && lifecycle.target_618 != null) {
    return [
      {
        id: 't1',
        label: 'Source T1 38.2%',
        price: lifecycle.target_382,
        reached: lifecycle.type_i_t1_bar != null,
        sourceClock: true,
      },
      {
        id: 't2',
        label: 'Source T2 61.8%',
        price: lifecycle.target_618,
        reached: lifecycle.type_i_t2_bar != null,
        sourceClock: true,
      },
    ]
  }

  const audit = pattern?.reaction_audit
  if (!audit) return []
  return [
    {
      id: 't1',
      label: '后验T1 38.2%',
      price: audit.target_382,
      reached: audit.bars_to_382 != null,
      sourceClock: false,
    },
    {
      id: 't2',
      label: '后验T2 61.8%',
      price: audit.target_618,
      reached: audit.bars_to_618 != null,
      sourceClock: false,
    },
  ]
}

function sourceEvents(lifecycle: SourceLifecycle | undefined): SourceEvent[] {
  if (!lifecycle) return []
  const candidates: Array<[SourceEvent['id'], number | null, string, SourceEvent['emphasis']]> = [
    ['prz-entry', lifecycle.source_prz_entry_bar, 'Source PRZ进入', 'minor'],
    ['tbar', lifecycle.source_terminal_bar, 'Source T-Bar', 'major'],
    ['tplus1', lifecycle.execution_start_bar, 'T+1', 'major'],
    ['type-i-t1', lifecycle.type_i_t1_bar, 'Type-I 38.2%', 'confirm'],
    ['type-i-t2', lifecycle.type_i_t2_bar, 'Type-I 61.8%', 'confirm'],
    ['type-ii-entry', lifecycle.type_ii_retest_entry_bar, 'Type-II重入', 'minor'],
    ['type-ii-terminal', lifecycle.type_ii_terminal_bar, 'Type-II T-Bar', 'major'],
    ['reversal-exit', lifecycle.reversal_exit_after_type_ii_bar, 'Type-II后离区', 'confirm'],
  ]
  return candidates
    .filter((item): item is [SourceEvent['id'], number, string, SourceEvent['emphasis']] => item[1] != null)
    .map(([id, bar, label, emphasis]) => ({ id, bar, label, emphasis }))
}

function eventPrice(
  event: SourceEvent,
  bars: Bar[],
  pattern: Pattern,
  lifecycle: SourceLifecycle,
): number | null {
  const bar = bars.find((item) => item.index === event.bar)
  if (!bar) return null
  if (event.id === 'tbar' || event.id === 'type-ii-terminal') {
    return pattern.direction === 'bullish' ? bar.low : bar.high
  }
  if (event.id === 'type-i-t1' && lifecycle.target_382 != null) return lifecycle.target_382
  if (event.id === 'type-i-t2' && lifecycle.target_618 != null) return lifecycle.target_618
  return bar.close
}

function emptyOverlay(width = 1): OverlayGeometry {
  return {
    width,
    height: CHART_HEIGHT,
    points: [],
    legs: [],
    zones: [],
    targets: [],
    events: [],
  }
}

export default function HarmonicChart({ bars, pattern, focusPattern = true }: Props) {
  const hostRef = useRef<HTMLDivElement | null>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const seriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null)
  const syncOverlayRef = useRef<() => void>(() => undefined)
  const [overlay, setOverlay] = useState<OverlayGeometry>(() => emptyOverlay())
  const [crosshair, setCrosshair] = useState<CrosshairSnapshot | null>(null)

  const targets = useMemo(() => lifecycleTargets(pattern), [pattern])
  const lifecycle = pattern?.source_lifecycle
  const events = useMemo(() => sourceEvents(lifecycle), [lifecycle])

  useEffect(() => {
    const host = hostRef.current
    if (!host || !bars.length) return

    const barByIndex = new Map(bars.map((bar) => [bar.index, bar]))
    const chart = createChart(host, {
      width: Math.max(host.clientWidth, 320),
      height: CHART_HEIGHT,
      layout: {
        background: { type: ColorType.Solid, color: '#0a1017' },
        textColor: '#748396',
      },
      grid: {
        vertLines: { color: '#17222e' },
        horzLines: { color: '#17222e' },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
      },
      rightPriceScale: {
        borderColor: '#263443',
        scaleMargins: { top: 0.08, bottom: 0.08 },
      },
      timeScale: {
        borderColor: '#263443',
        rightOffset: 2,
        barSpacing: 9,
        minBarSpacing: 2,
        fixLeftEdge: false,
        fixRightEdge: false,
      },
      handleScroll: {
        mouseWheel: true,
        pressedMouseMove: true,
        horzTouchDrag: true,
        vertTouchDrag: true,
      },
      handleScale: {
        axisPressedMouseMove: true,
        mouseWheel: true,
        pinch: true,
      },
    })

    const series = chart.addSeries(CandlestickSeries, {
      upColor: '#ef4444',
      downColor: '#22c55e',
      borderUpColor: '#ef4444',
      borderDownColor: '#22c55e',
      wickUpColor: '#ef4444',
      wickDownColor: '#22c55e',
      priceLineVisible: false,
      lastValueVisible: true,
    })
    series.setData(
      bars.map((bar) => ({
        time: bar.trade_date as Time,
        open: bar.open,
        high: bar.high,
        low: bar.low,
        close: bar.close,
      })),
    )

    chartRef.current = chart
    seriesRef.current = series

    const xForIndex = (index: number): number | null => {
      const date = barByIndex.get(index)?.trade_date
      if (!date) return null
      const value = chart.timeScale().timeToCoordinate(date as Time)
      return value == null ? null : Number(value)
    }

    const yForPrice = (price: number): number | null => {
      const value = series.priceToCoordinate(price)
      return value == null ? null : Number(value)
    }

    const recomputeOverlay = () => {
      const width = Math.max(host.clientWidth, 1)
      if (!pattern) {
        setOverlay(emptyOverlay(width))
        return
      }

      const points: OverlayPoint[] = pattern.points.flatMap((point) => {
        const date = point.trade_date ?? barByIndex.get(point.index)?.trade_date
        if (!date) return []
        const x = chart.timeScale().timeToCoordinate(date as Time)
        const y = series.priceToCoordinate(point.price)
        if (x == null || y == null) return []
        return [{ ...point, x: Number(x), y: Number(y) }]
      })

      const legs: OverlayLeg[] = points.slice(0, -1).map((point, index) => {
        const next = points[index + 1]
        return {
          name: `${point.label}${next.label}`,
          x1: point.x,
          y1: point.y,
          x2: next.x,
          y2: next.y,
        }
      })

      const lastIndex = bars.at(-1)?.index ?? 0
      const endX = xForIndex(lastIndex)
      const zones: OverlayZone[] = []

      const pushZone = (
        id: OverlayZone['id'],
        startIndex: number,
        low: number | null | undefined,
        high: number | null | undefined,
      ) => {
        if (low == null || high == null || endX == null) return
        const startX = xForIndex(startIndex)
        const yHigh = yForPrice(high)
        const yLow = yForPrice(low)
        if (startX == null || yHigh == null || yLow == null) return
        zones.push({
          id,
          x: Math.min(startX, endX),
          y: Math.min(yHigh, yLow),
          width: Math.max(2, Math.abs(endX - startX)),
          height: Math.max(2, Math.abs(yLow - yHigh)),
        })
      }

      const patternLastIndex = pattern.points.at(-1)?.index ?? lastIndex
      pushZone('ideal-core', patternLastIndex, pattern.prz.price_low, pattern.prz.price_high)
      if (lifecycle?.source_prz_low != null && lifecycle.source_prz_high != null) {
        pushZone(
          'source-prz',
          lifecycle.signal_bar ?? patternLastIndex,
          lifecycle.source_prz_low,
          lifecycle.source_prz_high,
        )
      }
      if (
        lifecycle?.source_terminal_bar != null
        && lifecycle.pez_low != null
        && lifecycle.pez_high != null
      ) {
        pushZone('pez', lifecycle.source_terminal_bar, lifecycle.pez_low, lifecycle.pez_high)
      }

      const lifecycleStart = lifecycle?.source_terminal_bar
        ?? pattern.reaction_audit?.d_index
        ?? patternLastIndex
      const targetRows: OverlayTarget[] = targets.flatMap((target) => {
        const x1 = xForIndex(lifecycleStart)
        const x2 = endX
        const y = yForPrice(target.price)
        if (x1 == null || x2 == null || y == null) return []
        return [{ ...target, x1, x2, y }]
      })

      const eventRows: OverlayEvent[] = []
      if (lifecycle) {
        for (const event of events) {
          const x = xForIndex(event.bar)
          const price = eventPrice(event, bars, pattern, lifecycle)
          const y = price == null ? null : yForPrice(price)
          if (x == null || y == null) continue
          eventRows.push({ ...event, x, y })
        }
      }

      setOverlay({
        width,
        height: CHART_HEIGHT,
        points,
        legs,
        zones,
        targets: targetRows,
        events: eventRows,
      })
    }

    let frame = 0
    const scheduleOverlay = () => {
      if (frame) cancelAnimationFrame(frame)
      frame = requestAnimationFrame(recomputeOverlay)
    }
    syncOverlayRef.current = scheduleOverlay

    const onVisibleRange = () => scheduleOverlay()
    chart.timeScale().subscribeVisibleLogicalRangeChange(onVisibleRange)

    const onInteraction = () => scheduleOverlay()
    host.addEventListener('wheel', onInteraction, { passive: true })
    host.addEventListener('pointermove', onInteraction)
    host.addEventListener('pointerup', onInteraction)

    chart.subscribeCrosshairMove((param) => {
      const datum = param.seriesData.get(series) as
        | { open: number; high: number; low: number; close: number }
        | undefined
      if (!datum || param.time == null) {
        setCrosshair(null)
        return
      }
      const date = timeKey(param.time)
      const node = pattern?.points.find((point) => {
        const pointDate = point.trade_date ?? barByIndex.get(point.index)?.trade_date
        return pointDate === date
      })?.label ?? null
      setCrosshair({
        date,
        open: datum.open,
        high: datum.high,
        low: datum.low,
        close: datum.close,
        node,
      })
    })

    const resizeObserver = new ResizeObserver((entries) => {
      const width = Math.max(Math.floor(entries[0]?.contentRect.width ?? host.clientWidth), 320)
      chart.resize(width, CHART_HEIGHT)
      scheduleOverlay()
    })
    resizeObserver.observe(host)

    if (focusPattern && pattern?.points.length) {
      const firstPatternIndex = pattern.points[0].index
      const startPosition = Math.max(
        0,
        bars.findIndex((bar) => bar.index >= firstPatternIndex) - Math.min(24, bars.length - 1),
      )
      chart.timeScale().setVisibleLogicalRange({
        from: startPosition - 0.5,
        to: bars.length - 0.5,
      })
    } else {
      chart.timeScale().fitContent()
    }
    scheduleOverlay()

    return () => {
      if (frame) cancelAnimationFrame(frame)
      resizeObserver.disconnect()
      chart.timeScale().unsubscribeVisibleLogicalRangeChange(onVisibleRange)
      host.removeEventListener('wheel', onInteraction)
      host.removeEventListener('pointermove', onInteraction)
      host.removeEventListener('pointerup', onInteraction)
      chart.remove()
      chartRef.current = null
      seriesRef.current = null
      syncOverlayRef.current = () => undefined
    }
  }, [bars, events, focusPattern, lifecycle, pattern, targets])

  if (!bars.length) return <div className="chart-empty">暂无 K 线数据</div>

  const resetViewport = () => {
    chartRef.current?.timeScale().fitContent()
    syncOverlayRef.current()
  }

  return (
    <>
      <LifecycleCompass pattern={pattern} bars={bars} />
      <div
        className="chart-wrap interactive-chart-wrap"
        aria-label="harmonic-chart"
        data-testid="interactive-harmonic-chart"
        data-render-engine="lightweight-charts-v5"
        data-coordinate-system="canonical-time-price"
      >
        <div className="interactive-chart-toolbar">
          <div>
            <strong>交互主图</strong>
            <span>拖动平移 · 滚轮缩放 · 十字光标</span>
          </div>
          <button type="button" onClick={resetViewport} data-testid="chart-reset-viewport">
            复位视图
          </button>
        </div>

        <div className="interactive-chart-stage">
          <div ref={hostRef} className="lightweight-chart-host" data-testid="lightweight-chart-host" />
          <svg
            className="chart-overlay"
            viewBox={`0 0 ${overlay.width} ${overlay.height}`}
            preserveAspectRatio="none"
            aria-label="HT-CN谐波与Source生命周期叠加层"
            data-testid="harmonic-coordinate-overlay"
          >
            {overlay.zones.map((zone) => (
              <g key={zone.id} data-layer-id={zone.id === 'source-prz' ? 'source_raw_prz' : zone.id}>
                <rect
                  x={zone.x}
                  y={zone.y}
                  width={zone.width}
                  height={zone.height}
                  className={
                    zone.id === 'source-prz'
                      ? 'source-prz-zone'
                      : zone.id === 'pez'
                        ? 'source-pez-zone'
                        : `prz-zone legacy-core ${pattern?.direction ?? 'bullish'}`
                  }
                  data-testid={
                    zone.id === 'source-prz'
                      ? 'source-prz-zone'
                      : zone.id === 'pez'
                        ? 'source-pez-zone'
                        : undefined
                  }
                />
              </g>
            ))}

            {overlay.targets.map((target) => (
              <g
                key={target.id}
                className={`lifecycle-target ${target.reached ? 'reached' : 'pending'} ${target.sourceClock ? 'source-clock-target' : 'retrospective-target'}`}
                data-testid={`type-i-target-${target.id}`}
                data-state={target.reached ? 'reached' : 'pending'}
                data-clock={target.sourceClock ? 'source' : 'retrospective'}
              >
                <line
                  x1={target.x1}
                  x2={target.x2}
                  y1={target.y}
                  y2={target.y}
                  className="lifecycle-target-line"
                />
                <text
                  x={Math.max(target.x1, target.x2) - 6}
                  y={target.y - 7}
                  textAnchor="end"
                  className="lifecycle-target-label"
                >
                  {target.label} · {formatPrice(target.price)} · {target.reached ? '已到达' : '待到达'}
                </text>
              </g>
            ))}

            {overlay.events.map((event, index) => (
              <g
                key={`${event.id}-${event.bar}`}
                className={`source-event ${event.emphasis}`}
                data-testid={`source-event-${event.id}`}
                data-anchor-index={event.bar}
              >
                <line
                  x1={event.x}
                  x2={event.x}
                  y1={0}
                  y2={overlay.height}
                  className="source-event-line"
                />
                <circle
                  cx={event.x}
                  cy={event.y}
                  r={event.emphasis === 'major' ? 5 : 4}
                  className="source-event-node"
                />
                <text
                  x={event.x + 5}
                  y={18 + (index % 3) * 15}
                  className="source-event-label"
                >
                  {event.label}
                </text>
              </g>
            ))}

            {overlay.legs.map((leg) => (
              <line
                key={leg.name}
                x1={leg.x1}
                y1={leg.y1}
                x2={leg.x2}
                y2={leg.y2}
                className={`pattern-line ${pattern?.state ?? 'forming'}`}
                data-leg-name={leg.name}
              />
            ))}

            {overlay.points.map((point) => (
              <g
                key={`${point.label}-${point.index}`}
                data-node-label={point.label}
                data-anchor-index={point.index}
                data-anchor-price={point.price}
              >
                <circle cx={point.x} cy={point.y} r="5" className="pattern-node" />
                <text x={point.x} y={point.y - 10} textAnchor="middle" className="point-label">
                  {point.label}
                </text>
              </g>
            ))}
          </svg>
        </div>

        <div className="chart-crosshair-readout" data-testid="chart-crosshair-readout">
          {crosshair ? (
            <>
              <strong>{crosshair.date}</strong>
              <span>O {formatPrice(crosshair.open)}</span>
              <span>H {formatPrice(crosshair.high)}</span>
              <span>L {formatPrice(crosshair.low)}</span>
              <span>C {formatPrice(crosshair.close)}</span>
              {crosshair.node && <b>节点 {crosshair.node}</b>}
            </>
          ) : (
            <span>移动十字光标读取 OHLC 与谐波节点</span>
          )}
        </div>
      </div>
    </>
  )
}
