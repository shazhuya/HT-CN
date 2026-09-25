import type { AShareExecutionContextPayload } from './AShareExecutionContext'
import type { ConceptContextPayload } from './ConceptContext'
import type { ContextIntegrityPayload } from './ContextIntegrity'
import type { Bar, Pattern } from './HarmonicChart'
import type { MarketContextPayload } from './MarketContext'
import type { IndustryContextPayload } from './SectorContext'
import type { TypeIT5Event } from './TypeIT5Evidence'

export type Health = {
  status: string
  service: string
  version: string
}

export type InstrumentRow = {
  instrument_id: string
  has_qfq_factor: boolean
}

export type ResearchTimeframe = '1d' | '60m' | '15m'

export type Analysis = {
  instrument_id: string
  timeframe?: ResearchTimeframe
  price_mode: string
  data_provenance?: Record<string, unknown>
  warning: string | null
  bars_requested: number
  bars_returned: number
  first_trade_date: string
  last_trade_date: string
  scales: number[]
  bars: Bar[]
  completed: Pattern[]
  forming: Pattern[]
  discovery?: Pattern[]
  pivot_counts: Record<string, number>
  discovery_scales?: number[]
  discovery_pivot_counts?: Record<string, number>
  recognition_diagnostics?: Record<string, number | string | object>
  pine_r34_diagnostics?: Record<string, unknown>
  type_i_t5_events?: TypeIT5Event[]
  a_share_execution_context?: AShareExecutionContextPayload
  market_context?: MarketContextPayload
  sector_context?: IndustryContextPayload
  concept_context?: ConceptContextPayload
  context_integrity?: ContextIntegrityPayload
  engine_note: string
}

export type AppDestination = 'home' | 'research' | 'discover' | 'system'
export type ResearchTab = 'overview' | 'pattern' | 'context' | 'audit'
