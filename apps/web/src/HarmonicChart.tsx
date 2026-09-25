import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  CandlestickSeries,
  ColorType,
  CrosshairMode,
  createChart,
  type CandlestickData,
  type IChartApi,
  type ISeriesApi,
  type Time,
} from 'lightweight-charts'
import type { AShareExecutionContextPayload } from './AShareExecutionContext'
import type { DecisionNarrativePayload } from './DecisionNarrative'
import LifecycleCompass from './LifecycleCompass'
import './HarmonicChartLifecycle.css'

export type Bar = {
  index: number
  trade_date: string
  time?: number
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

export type DiscoveryMetadata = {
  source?: 'pine_r34' | 'extended_graph'
  behavioral_baseline?: boolean
  authoritative_identity: boolean
  path_kind: 'consecutive' | 'minor_swing_skip' | 'pine_r34'
  skipped_pivots: number
  known_from_bar: number
  prz_status: 'projected' | 'tested'
  first_prz_test_bar: number | null
  c_family_target: number | null
  c_family_relative_error: number | null
  source_family_aligned: boolean
  distance_to_source_prz_xa: number
  research_only?: boolean
  qualified?: boolean
  precise?: boolean
  projected_label?: string
  structural_limit?: number
  pine_source_sha256?: string
  mutates_source_identity: boolean
  owns_lifecycle: boolean
  fabricates_d: boolean
}

export type Pattern = {
  pattern_id: string
  schema?: 'XABCD' | 'ABCD' | '0XABC' | '0XABCD' | 'FIVE_ZERO'
  direction: 'bullish' | 'bearish'
  state: 'forming' | 'completed'
  scale: number
  geometry_score: number
  points: HarmonicPoint[]
  pivot_support?: PivotSupport[]
  identity_conflicts?: string[]
  is_primary_identity?: boolean
  channel?: 'authoritative' | 'discovery'
  discovery_only?: boolean
  discovery?: DiscoveryMetadata
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
  lifecyclePlacement?: 'inline' | 'external'
  onCrosshairChange?: (snapshot: CrosshairSnapshot | null) => void
}

type LifecycleTarget = {
  id: 't1' | 't2'
  label: string
  price: number
  reached: boolean
  sourceClock: boolean
}

type SourceEvent = {
  id: 'prz-entry' | 'tbar' | 'tplus1' | 'type-i-t1' | 'type-i-t2' | 'type-ii-entry' | 'type-ii-terminal' | 'reversal-exit'
  bar: number
  label: string
  emphasis: 'minor' | 'major' | 'confirm'
}

export type CrosshairSnapshot = {
  tradeDate: string
  open: number
  high: number
  low: number
  close: number
  volume: number
  nodes: string[]
  lifecycle: string[]
}

type OverlayPoint = HarmonicPoint & {
  x: number
  y: number
  tradeDate: string
}

type OverlayLeg = {
  name: string
  x1: number
  y1: number
  x2: number
  y2: number
}

type OverlayZone = {
  id: string
  label: string
  x: number
  y: number
  width: number
  height: number
  className: string
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

function formatPrice(value: number) {
  return value >= 100 ? value.toFixed(2) : value.toFixed(3)
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

function eventPrice(event: SourceEvent, bars: Bar[], pattern: Pattern, lifecycle: SourceLifecycle): number | null {
  const bar = bars.find((item) => item.index === event.bar)
  if (!bar) return null
  if (event.id === 'tbar' || event.id === 'type-ii-terminal') {
    return pattern.direction === 'bullish' ? bar.low : bar.high
  }
  if (event.id === 'type-i-t1' && lifecycle.target_382 != null) return lifecycle.target_382
  if (event.id === 'type-i-t2' && lifecycle.target_618 != null) return lifecycle.target_618
  return bar.close
}

function pointTradeDate(point: HarmonicPoint, bars: Bar[]): string | null {
  if (point.trade_date) return point.trade_date
  return bars.find((bar) => bar.index === point.index)?.trade_date ?? null
}

function barChartTime(bar: Bar): Time {
  return (bar.time ?? bar.trade_date) as Time
}

function timeKey(time: Time | undefined): string | null {
  if (time == null) return null
  if (typeof time === 'string') return time
  if (typeof time === 'number') return new Date(time * 1000).toISOString().slice(0, 10)
  return String(time.year)
    + '-'
    + String(time.month).padStart(2, '0')
    + '-'
    + String(time.day).padStart(2, '0')
}

function applyViewport(chart: IChartApi, bars: Bar[], pattern: Pattern | null, focusPattern: boolean) {
  if (!bars.length) return
  if (!focusPattern || !pattern || !pattern.points.length) {
    chart.timeScale().fitContent()
    return
  }
  const firstPointIndex = pattern.points[0].index
  const firstOrdinal = Math.max(0, bars.findIndex((bar) => bar.index === firstPointIndex))
  const remaining = Math.max(1, bars.length - firstOrdinal)
  const padding = Math.max(4, Math.min(24, Math.round(remaining * 0.25)))
  chart.timeScale().setVisibleLogicalRange({
    from: Math.max(-2, firstOrdinal - padding),
    to: bars.length - 1 + 2,
  })
}

export default function HarmonicChart({
  bars,
  pattern,
  focusPattern = true,
  lifecyclePlacement = 'inline',
  onCrosshairChange,
}: Props) {
  const hostRef = useRef<HTMLDivElement | null>(null)
  const stageRef = useRef<HTMLDivElement | null>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const seriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null)
  const barsRef = useRef(bars)
  const patternRef = useRef(pattern)
  const animationFrameRef = useRef<number | null>(null)
  const [viewportVersion, setViewportVersion] = useState(0)
  const [crosshair, setCrosshair] = useState<CrosshairSnapshot | null>(null)

  barsRef.current = bars
  patternRef.current = pattern

  const scheduleViewportSync = useCallback(() => {
    if (animationFrameRef.current != null) {
      return
    }
    animationFrameRef.current = requestAnimationFrame(() => {
      animationFrameRef.current = null
      setViewportVersion((value) => value + 1)
    })
  }, [])

  useEffect(() => {
    const host = hostRef.current
    if (!host) return undefined

    const chart = createChart(host, {
      autoSize: true,
      height: 520,
      layout: {
        background: { type: ColorType.Solid, color: '#0a1017' },
        textColor: '#7f8ea1',
        attributionLogo: true,
      },
      grid: {
        vertLines: { color: '#16212c' },
        horzLines: { color: '#1b2632' },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
      },
      rightPriceScale: {
        borderColor: '#273341',
        scaleMargins: { top: 0.08, bottom: 0.08 },
      },
      timeScale: {
        borderColor: '#273341',
        rightOffset: 2,
        barSpacing: 8,
        minBarSpacing: 2,
      },
      handleScroll: {
        mouseWheel: true,
        pressedMouseMove: true,
        horzTouchDrag: true,
        vertTouchDrag: false,
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
    })
    chartRef.current = chart
    seriesRef.current = series

    const rangeHandler = () => scheduleViewportSync()
    chart.timeScale().subscribeVisibleLogicalRangeChange(rangeHandler)

    const publishCrosshair = (snapshot: CrosshairSnapshot | null) => {
      setCrosshair(snapshot)
      onCrosshairChange?.(snapshot)
    }

    chart.subscribeCrosshairMove((param) => {
      const key = timeKey(param.time)
      if (!key) {
        publishCrosshair(null)
        return
      }
      const raw = param.seriesData.get(series)
      if (!raw || !('open' in raw) || !('high' in raw) || !('low' in raw) || !('close' in raw)) {
        publishCrosshair(null)
        return
      }
      const bar = typeof param.time === 'number'
        ? barsRef.current.find((item) => item.time === param.time)
        : barsRef.current.find((item) => item.trade_date === key)
      if (!bar) {
        publishCrosshair(null)
        return
      }
      const activePattern = patternRef.current
      const activeTradeDate = bar.trade_date
      const nodes = activePattern
        ? activePattern.points
          .filter((point) => pointTradeDate(point, barsRef.current) === activeTradeDate)
          .map((point) => point.label)
        : []
      const lifecycle = activePattern?.source_lifecycle
      const lifecycleLabels = lifecycle
        ? sourceEvents(lifecycle)
          .filter((event) => barsRef.current.find((item) => item.index === event.bar)?.trade_date === activeTradeDate)
          .map((event) => event.label)
        : []

      publishCrosshair({
        tradeDate: bar.trade_date,
        open: Number(raw.open),
        high: Number(raw.high),
        low: Number(raw.low),
        close: Number(raw.close),
        volume: bar.volume,
        nodes,
        lifecycle: lifecycleLabels,
      })
    })

    const resizeObserver = new ResizeObserver(scheduleViewportSync)
    resizeObserver.observe(host)
    const stage = stageRef.current
    stage?.addEventListener('wheel', scheduleViewportSync, { passive: true, capture: true })
    stage?.addEventListener('pointermove', scheduleViewportSync, { capture: true })

    scheduleViewportSync()

    return () => {
      resizeObserver.disconnect()
      stage?.removeEventListener('wheel', scheduleViewportSync, { capture: true })
      stage?.removeEventListener('pointermove', scheduleViewportSync, { capture: true })
      chart.timeScale().unsubscribeVisibleLogicalRangeChange(rangeHandler)
      chart.remove()
      chartRef.current = null
      seriesRef.current = null
      if (animationFrameRef.current != null) {
        cancelAnimationFrame(animationFrameRef.current)
        animationFrameRef.current = null
      }
    }
  }, [onCrosshairChange, scheduleViewportSync])

  useEffect(() => {
    setCrosshair(null)
    onCrosshairChange?.(null)
  }, [bars, pattern, onCrosshairChange])

  useEffect(() => {
    const series = seriesRef.current
    if (!series) return
    const data: CandlestickData<Time>[] = bars.map((bar) => ({
      time: barChartTime(bar),
      open: bar.open,
      high: bar.high,
      low: bar.low,
      close: bar.close,
    }))
    series.setData(data)
    scheduleViewportSync()
  }, [bars, scheduleViewportSync])

  useEffect(() => {
    const chart = chartRef.current
    if (!chart || !bars.length) return
    applyViewport(chart, bars, pattern, focusPattern)
    scheduleViewportSync()
  }, [bars, pattern, focusPattern, scheduleViewportSync])

  const overlay = useMemo(() => {
    void viewportVersion
    const chart = chartRef.current
    const series = seriesRef.current
    const host = hostRef.current
    const lifecycle = pattern?.source_lifecycle
    if (!chart || !series || !host || !pattern || !bars.length) {
      return {
        points: [] as OverlayPoint[],
        legs: [] as OverlayLeg[],
        zones: [] as OverlayZone[],
        targets: [] as OverlayTarget[],
        events: [] as OverlayEvent[],
        height: host?.clientHeight ?? 0,
      }
    }

    const byIndex = new Map(bars.map((bar) => [bar.index, bar]))
    const xForIndex = (index: number) => {
      const bar = byIndex.get(index)
      if (!bar) return null
      return chart.timeScale().timeToCoordinate(barChartTime(bar))
    }
    const yForPrice = (price: number) => series.priceToCoordinate(price)
    const coordinate = (index: number, price: number) => {
      const x = xForIndex(index)
      const y = yForPrice(price)
      if (x == null || y == null) return null
      return { x: Number(x), y: Number(y) }
    }

    const points: OverlayPoint[] = []
    for (const point of pattern.points) {
      const value = coordinate(point.index, point.price)
      const tradeDate = pointTradeDate(point, bars)
      if (!value || !tradeDate) continue
      points.push({ ...point, x: value.x, y: value.y, tradeDate })
    }

    const legs: OverlayLeg[] = []
    for (let index = 1; index < pattern.points.length; index += 1) {
      const from = pattern.points[index - 1]
      const to = pattern.points[index]
      const p1 = coordinate(from.index, from.price)
      const p2 = coordinate(to.index, to.price)
      if (!p1 || !p2) continue
      legs.push({
        name: from.label + to.label,
        x1: p1.x,
        y1: p1.y,
        x2: p2.x,
        y2: p2.y,
      })
    }

    const lastBarIndex = bars[bars.length - 1].index
    const endX = xForIndex(lastBarIndex)
    const patternEndIndex = pattern.points[pattern.points.length - 1]?.index ?? lastBarIndex
    const zones: OverlayZone[] = []

    const addZone = (
      id: string,
      label: string,
      low: number | null | undefined,
      high: number | null | undefined,
      startIndex: number,
      className: string,
    ) => {
      if (low == null || high == null || endX == null) return
      const startX = xForIndex(startIndex)
      const highY = yForPrice(high)
      const lowY = yForPrice(low)
      if (startX == null || highY == null || lowY == null) return
      zones.push({
        id,
        label,
        x: Math.min(Number(startX), Number(endX)),
        y: Math.min(Number(highY), Number(lowY)),
        width: Math.max(2, Math.abs(Number(endX) - Number(startX))),
        height: Math.max(2, Math.abs(Number(lowY) - Number(highY))),
        className,
      })
    }

    const ideal = pattern.prz.ideal_core
    addZone(
      'ideal_core',
      'HT-CN Ideal Core',
      ideal?.price_low ?? pattern.prz.price_low,
      ideal?.price_high ?? pattern.prz.price_high,
      patternEndIndex,
      'overlay-zone ideal-core',
    )

    const envelope = pattern.prz.component_envelope
    if (envelope || (pattern.prz.component_price_low != null && pattern.prz.component_price_high != null)) {
      addZone(
        'component_envelope',
        'Component Envelope',
        envelope?.price_low ?? pattern.prz.component_price_low,
        envelope?.price_high ?? pattern.prz.component_price_high,
        patternEndIndex,
        'overlay-zone component-envelope',
      )
    }

    const sourceLayer = pattern.prz.source_prz
    const sourceLow = lifecycle?.source_prz_low
      ?? (sourceLayer?.available ? sourceLayer.price_low : pattern.prz.source_prz_low)
    const sourceHigh = lifecycle?.source_prz_high
      ?? (sourceLayer?.available ? sourceLayer.price_high : pattern.prz.source_prz_high)
    addZone(
      'source_raw_prz',
      'Source Raw PRZ',
      sourceLow,
      sourceHigh,
      lifecycle?.signal_bar ?? patternEndIndex,
      'overlay-zone source-raw-prz',
    )

    addZone(
      'pez',
      'PEZ',
      lifecycle?.pez_low,
      lifecycle?.pez_high,
      lifecycle?.source_terminal_bar ?? patternEndIndex,
      'overlay-zone source-pez',
    )

    const targetStartIndex = lifecycle?.source_terminal_bar ?? pattern.reaction_audit?.d_index ?? patternEndIndex
    const startX = xForIndex(targetStartIndex)
    const targets: OverlayTarget[] = []
    if (startX != null && endX != null) {
      for (const target of lifecycleTargets(pattern)) {
        const y = yForPrice(target.price)
        if (y == null) continue
        targets.push({
          ...target,
          x1: Number(startX),
          x2: Number(endX),
          y: Number(y),
        })
      }
    }

    const events: OverlayEvent[] = []
    if (lifecycle) {
      for (const event of sourceEvents(lifecycle)) {
        const markerPrice = eventPrice(event, bars, pattern, lifecycle)
        if (markerPrice == null) continue
        const value = coordinate(event.bar, markerPrice)
        if (!value) continue
        events.push({ ...event, x: value.x, y: value.y })
      }
    }

    return {
      points,
      legs,
      zones,
      targets,
      events,
      height: host.clientHeight,
    }
  }, [bars, pattern, viewportVersion])

  const resetViewport = useCallback(() => {
    const chart = chartRef.current
    if (!chart) return
    applyViewport(chart, bars, pattern, focusPattern)
    scheduleViewportSync()
  }, [bars, pattern, focusPattern, scheduleViewportSync])

  if (!bars.length) return <div className="chart-empty">暂无 K 线数据</div>

  return (
    <>
      {lifecyclePlacement === 'inline' && <LifecycleCompass pattern={pattern} bars={bars} />}
      <div className="chart-wrap interactive-chart-wrap" aria-label="harmonic-chart">
        <div className="interactive-chart-toolbar">
          <span>拖动平移 · 滚轮/坐标轴缩放 · 十字光标</span>
          <button type="button" onClick={resetViewport} data-testid="chart-reset-view">
            重置视图
          </button>
        </div>
        <div ref={stageRef} className="chart-stage" data-testid="interactive-chart-stage">
          <div ref={hostRef} className="chart-host" data-engine="lightweight-charts" />
          <svg
            className="harmonic-overlay"
            data-testid="harmonic-overlay"
            data-viewport-version={viewportVersion}
            aria-hidden="true"
          >
            {overlay.zones.map((zone) => (
              <g
                key={zone.id}
                data-layer-id={zone.id}
                data-testid={
                  zone.id === 'source_raw_prz'
                    ? 'source-prz-zone'
                    : zone.id === 'pez'
                      ? 'source-pez-zone'
                      : undefined
                }
              >
                <rect
                  x={zone.x}
                  y={zone.y}
                  width={zone.width}
                  height={zone.height}
                  className={zone.className}
                />
                <text x={zone.x + 6} y={zone.y + 13} className="overlay-zone-label">
                  {zone.label}
                </text>
              </g>
            ))}

            {overlay.targets.map((target) => (
              <g
                key={target.id}
                className={'overlay-target ' + (target.reached ? 'reached' : 'pending')}
                data-testid={'type-i-target-' + target.id}
                data-state={target.reached ? 'reached' : 'pending'}
                data-clock={target.sourceClock ? 'source' : 'retrospective'}
              >
                <line x1={target.x1} x2={target.x2} y1={target.y} y2={target.y} />
                <text x={Math.max(target.x1, target.x2) - 5} y={target.y - 7} textAnchor="end">
                  {target.label + ' · ' + formatPrice(target.price) + ' · ' + (target.reached ? '已到达' : '待到达')}
                </text>
              </g>
            ))}

            {overlay.events.map((event, index) => (
              <g
                key={event.id + '-' + event.bar}
                className={'overlay-source-event ' + event.emphasis}
                data-testid={'source-event-' + event.id}
              >
                <line x1={event.x} x2={event.x} y1={0} y2={Math.max(0, overlay.height - 28)} />
                <circle cx={event.x} cy={event.y} r={event.emphasis === 'major' ? 5 : 4} />
                <text x={event.x + 5} y={16 + (index % 4) * 13}>
                  {event.label}
                </text>
              </g>
            ))}

            {overlay.legs.map((leg) => (
              <g key={leg.name + '-' + leg.x1 + '-' + leg.x2}>
                <line
                  x1={leg.x1}
                  y1={leg.y1}
                  x2={leg.x2}
                  y2={leg.y2}
                  className={'overlay-pattern-line ' + (pattern?.state ?? '')}
                  data-leg-name={leg.name}
                />
                <text
                  x={(leg.x1 + leg.x2) / 2}
                  y={(leg.y1 + leg.y2) / 2 - 6}
                  textAnchor="middle"
                  className="overlay-leg-label"
                >
                  {leg.name}
                </text>
              </g>
            ))}

            {overlay.points.map((point) => (
              <g key={point.label + '-' + point.index}>
                <circle
                  cx={point.x}
                  cy={point.y}
                  r={5}
                  className="overlay-pattern-node"
                  data-node-label={point.label}
                  data-anchor-index={point.index}
                  data-anchor-date={point.tradeDate}
                />
                <text
                  x={point.x}
                  y={point.y - 10}
                  textAnchor="middle"
                  className="overlay-point-label"
                >
                  {point.label + ' ' + formatPrice(point.price)}
                </text>
              </g>
            ))}
          </svg>

          <div
            className={'chart-crosshair-readout ' + (crosshair ? 'visible' : '')}
            data-testid="chart-crosshair-readout"
            data-trade-date={crosshair?.tradeDate ?? ''}
          >
            {crosshair ? (
              <>
                <strong>{crosshair.tradeDate}</strong>
                <span>
                  O {formatPrice(crosshair.open)} · H {formatPrice(crosshair.high)} · L {formatPrice(crosshair.low)} · C {formatPrice(crosshair.close)}
                </span>
                {crosshair.nodes.length > 0 && <span>节点 {crosshair.nodes.join(' / ')}</span>}
                {crosshair.lifecycle.length > 0 && <span>{crosshair.lifecycle.join(' / ')}</span>}
              </>
            ) : (
              <span>移动十字光标查看 K 线 / 节点 / 生命周期 identity</span>
            )}
          </div>
        </div>
      </div>
    </>
  )
}
