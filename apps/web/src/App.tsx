import { useEffect, useMemo, useRef, useState } from 'react'
import ApplicationShell from './ApplicationShell'
import DiscoverView from './DiscoverView'
import HomeView from './HomeView'
import ResearchWorkspace from './ResearchWorkspace'
import SystemStatusView from './SystemStatusView'
import type { CrosshairSnapshot, Pattern } from './HarmonicChart'
import type {
  EvidenceRuntimeStatusPayload,
  ProductRuntimeStatusPayload,
  ProductSupervisorStatusPayload,
} from './ProductRuntimeStatus'
import type {
  Analysis,
  AppDestination,
  Health,
  InstrumentRow,
  ResearchTab,
  ResearchTimeframe,
} from './appTypes'

const API = 'http://127.0.0.1:8765'
const RECENT_SYMBOLS_KEY = 'htcn.recent-symbols.v1'

function destinationFromHash(): AppDestination {
  const raw = window.location.hash.replace(/^#\/?/, '')
  if (raw === 'research' || raw === 'discover' || raw === 'system') return raw
  return 'home'
}

function patternKey(pattern: Pattern) {
  return `${pattern.channel ?? 'authoritative'}:${pattern.state}:${pattern.pattern_id}:${pattern.scale}:${pattern.points.map((point) => point.index).join('-')}`
}

function discoveryDistance(pattern: Pattern) {
  const metricDistance = pattern.metrics?.distance_to_prz_atr
  if (typeof metricDistance === 'number' && Number.isFinite(metricDistance)) return metricDistance
  const projectedDistance = pattern.discovery?.distance_to_source_prz_xa
  if (typeof projectedDistance === 'number' && Number.isFinite(projectedDistance)) return projectedDistance
  return Number.POSITIVE_INFINITY
}

function sortDiscoveryForMonitoring(items: Pattern[]) {
  return [...items].sort((left, right) => {
    const leftPine = left.discovery?.source === 'pine_r34'
    const rightPine = right.discovery?.source === 'pine_r34'

    // The backend already reproduces R3.4 candidate-table ranking. Do not
    // silently re-rank two Pine candidates in the UI.
    if (leftPine && rightPine) {
      const leftRank = left.discovery?.monitoring_rank
      const rightRank = right.discovery?.monitoring_rank
      if (
        typeof leftRank === 'number'
        && Number.isFinite(leftRank)
        && typeof rightRank === 'number'
        && Number.isFinite(rightRank)
        && Math.abs(leftRank - rightRank) > 1e-9
      ) return rightRank - leftRank
    }

    // Behavioral R3.4 candidates are the primary discovery baseline; the
    // extended graph remains a supplementary recall channel.
    if (leftPine !== rightPine) return leftPine ? -1 : 1

    const leftResearch = left.discovery?.research_only ? 1 : 0
    const rightResearch = right.discovery?.research_only ? 1 : 0
    if (leftResearch !== rightResearch) return leftResearch - rightResearch

    const leftQualified = left.discovery?.qualified === false ? 1 : 0
    const rightQualified = right.discovery?.qualified === false ? 1 : 0
    if (leftQualified !== rightQualified) return leftQualified - rightQualified

    const distanceGap = discoveryDistance(left) - discoveryDistance(right)
    if (Number.isFinite(distanceGap) && Math.abs(distanceGap) > 1e-9) return distanceGap

    const leftKnown = left.discovery?.known_from_bar ?? -1
    const rightKnown = right.discovery?.known_from_bar ?? -1
    if (leftKnown !== rightKnown) return rightKnown - leftKnown

    return right.scale - left.scale
  })
}

function readRecentSymbols() {
  try {
    const value = JSON.parse(window.localStorage.getItem(RECENT_SYMBOLS_KEY) ?? '[]')
    if (!Array.isArray(value)) return []
    return value.filter((item): item is string => typeof item === 'string').slice(0, 8)
  } catch {
    return []
  }
}

export default function App() {
  const analysisRequest = useRef(0)
  const firstLocation = useRef(window.location.hash)
  const startupRestored = useRef(false)
  const [destination, setDestination] = useState<AppDestination>(() => destinationFromHash())
  const [health, setHealth] = useState<Health | null>(null)
  const [instruments, setInstruments] = useState<InstrumentRow[]>([])
  const [symbol, setSymbol] = useState('')
  const [recentSymbols, setRecentSymbols] = useState<string[]>(readRecentSymbols)
  const [bars, setBars] = useState(420)
  const [timeframe, setTimeframe] = useState<ResearchTimeframe>('1d')

  const [analysis, setAnalysis] = useState<Analysis | null>(null)
  const [analysisError, setAnalysisError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const [selectedKey, setSelectedKey] = useState<string | null>(null)
  const [showAllIdentities, setShowAllIdentities] = useState(false)
  const [focusPattern, setFocusPattern] = useState(true)
  const [crosshair, setCrosshair] = useState<CrosshairSnapshot | null>(null)
  const [researchTab, setResearchTab] = useState<ResearchTab>('overview')

  const [productSupervisorStatus, setProductSupervisorStatus] = useState<ProductSupervisorStatusPayload | null>(null)
  const [marketDataStatus, setMarketDataStatus] = useState<ProductRuntimeStatusPayload | null>(null)
  const [harmonicRuntimeStatus, setHarmonicRuntimeStatus] = useState<ProductRuntimeStatusPayload | null>(null)
  const [evidenceRuntimeStatus, setEvidenceRuntimeStatus] = useState<EvidenceRuntimeStatusPayload | null>(null)

  useEffect(() => {
    if (!window.location.hash) {
      window.history.replaceState(null, '', '#/home')
    }
    const onHashChange = () => setDestination(destinationFromHash())
    window.addEventListener('hashchange', onHashChange)
    return () => window.removeEventListener('hashchange', onHashChange)
  }, [])

  useEffect(() => {
    fetch(`${API}/api/health`)
      .then((response) => {
        if (!response.ok) throw new Error(`HTTP ${response.status}`)
        return response.json() as Promise<Health>
      })
      .then(setHealth)
      .catch(() => setHealth(null))

    fetch(`${API}/api/instruments?limit=10000`)
      .then((response) => response.json())
      .then((payload: { items?: InstrumentRow[] }) => {
        const items = payload.items ?? []
        setInstruments(items)
        const last = readRecentSymbols()[0]
        if (!firstLocation.current && !startupRestored.current && last && items.some((item) => item.instrument_id === last)) {
          startupRestored.current = true
          runAnalysis(last)
        }
        if (items.length === 1) {
          setSymbol((current) => current || items[0].instrument_id)
        }
      })
      .catch(() => undefined)

    fetch(`${API}/api/product/status`)
      .then((response) => response.json() as Promise<ProductSupervisorStatusPayload>)
      .then(setProductSupervisorStatus)
      .catch(() => undefined)

    fetch(`${API}/api/market-data/status`)
      .then((response) => response.json() as Promise<ProductRuntimeStatusPayload>)
      .then(setMarketDataStatus)
      .catch(() => undefined)

    fetch(`${API}/api/harmonic/runtime/status`)
      .then((response) => response.json() as Promise<ProductRuntimeStatusPayload>)
      .then(setHarmonicRuntimeStatus)
      .catch(() => undefined)

    fetch(`${API}/api/evidence/status`)
      .then((response) => response.json() as Promise<EvidenceRuntimeStatusPayload>)
      .then(setEvidenceRuntimeStatus)
      .catch(() => undefined)
  }, [])

  function navigate(next: AppDestination) {
    setDestination(next)
    if (window.location.hash !== `#/${next}`) {
      window.location.hash = `#/${next}`
    }
  }

  function rememberSymbol(value: string) {
    setRecentSymbols((previous) => {
      const next = [value, ...previous.filter((item) => item !== value)].slice(0, 8)
      window.localStorage.setItem(RECENT_SYMBOLS_KEY, JSON.stringify(next))
      return next
    })
  }

  function runAnalysis(nextSymbol?: string, nextTimeframe?: ResearchTimeframe) {
    const target = (nextSymbol ?? symbol).trim().toUpperCase()
    const targetTimeframe = nextTimeframe ?? timeframe
    if (!target) {
      navigate('research')
      return
    }

    const changingInstrument = analysis?.instrument_id !== target || (analysis?.timeframe ?? '1d') !== targetTimeframe
    const request = ++analysisRequest.current
    if (changingInstrument) setAnalysis(null)

    setSymbol(target)
    setTimeframe(targetTimeframe)
    setLoading(true)
    setAnalysisError(null)
    setSelectedKey(null)
    setCrosshair(null)
    setResearchTab('overview')
    navigate('research')

    fetch(`${API}/api/harmonic/${encodeURIComponent(target)}?bars=${bars}&scales=3,5,8,13&timeframe=${targetTimeframe}`)
      .then(async (response) => {
        if (!response.ok) {
          const body = (await response.json().catch(() => null)) as { detail?: string } | null
          throw new Error(body?.detail ?? `HTTP ${response.status}`)
        }
        return response.json() as Promise<Analysis>
      })
      .then((payload) => {
        if (request !== analysisRequest.current) return
        setAnalysis(payload)
        rememberSymbol(payload.instrument_id)
      })
      .catch((error: Error) => {
        if (request !== analysisRequest.current) return
        if (changingInstrument) setAnalysis(null)
        setAnalysisError(error.message)
      })
      .finally(() => { if (request === analysisRequest.current) setLoading(false) })
  }

  function openResearch(nextSymbol?: string) {
    const target = (nextSymbol ?? symbol).trim().toUpperCase()
    if (!target) {
      navigate('research')
      return
    }
    if (analysis?.instrument_id === target && (analysis.timeframe ?? '1d') === timeframe) {
      setSymbol(target)
      navigate('research')
      return
    }
    runAnalysis(target)
  }

  const rawPatterns = useMemo(() => {
    if (!analysis) return []
    const authoritative = [...analysis.completed, ...analysis.forming]
    const discovery = sortDiscoveryForMonitoring(analysis.discovery ?? [])
    return [...authoritative, ...discovery]
  }, [analysis])

  const patterns = useMemo(() => {
    if (showAllIdentities) return rawPatterns
    return rawPatterns.filter((pattern) => pattern.is_primary_identity !== false)
  }, [rawPatterns, showAllIdentities])

  const selectedPattern = useMemo(() => {
    if (!patterns.length) return null
    if (!selectedKey) return patterns[0]
    return patterns.find((pattern) => patternKey(pattern) === selectedKey) ?? patterns[0]
  }, [patterns, selectedKey])

  return (
    <ApplicationShell
      destination={destination}
      onNavigate={navigate}
      health={health}
      symbol={symbol}
      onSymbolChange={setSymbol}
      instruments={instruments}
      loading={loading}
      onOpenResearch={() => openResearch()}
    >
      {destination === 'home' && (
        <HomeView
          product={productSupervisorStatus}
          market={marketDataStatus}
          harmonic={harmonicRuntimeStatus}
          evidence={evidenceRuntimeStatus}
          recentSymbols={recentSymbols}
          onOpenSymbol={(value) => openResearch(value)}
          onNavigate={navigate}
        />
      )}

      {destination === 'research' && (
        <ResearchWorkspace
          analysis={analysis}
          loading={loading}
          error={analysisError}
          bars={bars}
          onBarsChange={setBars}
          timeframe={timeframe}
          onTimeframeChange={(value) => runAnalysis(undefined, value)}
          onRefresh={() => runAnalysis()}
          patterns={patterns}
          rawPatternCount={rawPatterns.length}
          selectedPattern={selectedPattern}
          onSelectPattern={setSelectedKey}
          showAllIdentities={showAllIdentities}
          onShowAllIdentities={setShowAllIdentities}
          focusPattern={focusPattern}
          onFocusPattern={setFocusPattern}
          crosshair={crosshair}
          onCrosshair={setCrosshair}
          tab={researchTab}
          onTab={setResearchTab}
          instruments={instruments}
          onOpenInstrument={openResearch}
        />
      )}

      {destination === 'discover' && (
        <DiscoverView
          apiBase={API}
          onOpenInstrument={(instrumentId) => openResearch(instrumentId)}
        />
      )}

      {destination === 'system' && (
        <SystemStatusView
          product={productSupervisorStatus}
          market={marketDataStatus}
          harmonic={harmonicRuntimeStatus}
          evidence={evidenceRuntimeStatus}
        />
      )}
    </ApplicationShell>
  )
}
