import axios from 'axios'

const API_KEY = import.meta.env.VITE_API_KEY || 'change-me-in-production'

export const api = axios.create({
  baseURL: '/api/v1',
  headers: { 'X-API-Key': API_KEY },
})

// Types
export interface Pilot {
  id: number
  email: string
  name: string
  home_airport: string
  phone: string | null
  certifications: string[]
  preferred_regions: string[]
  max_range_nm: number | null
  active: boolean
  created_at: string
}

export interface Aircraft {
  id: number
  tail_number: string
  make_model: string
  aircraft_type: string
  range_nm: number
  payload_lbs: number
  num_seats: number
  has_oxygen: boolean
  ifr_equipped: boolean
  fiki: boolean
  is_accessible: boolean
  home_airport: string
  active: boolean
}

export interface Mission {
  id: number
  title: string
  origin_airport: string
  destination_airport: string
  earliest_departure: string
  latest_departure: string
  estimated_duration_h: number
  status: 'open' | 'matched' | 'completed' | 'cancelled'
  coordinator_notes: string | null
  total_payload_lbs: number
  passenger_count: number
  requires_oxygen: boolean
  has_mobility_equipment: boolean
  created_at: string
}

export interface RankedPilot {
  pilot_id: number
  pilot_name: string
  pilot_email: string
  home_airport: string
  score: number
  rank: number
  hard_filter_pass: boolean
  features: Record<string, number>
  match_log_id: number
}

export interface MatchLog {
  id: number
  mission_id: number
  pilot_id: number
  matched_at: string
  score: number | null
  rank: number | null
  pilot_response: 'accepted' | 'declined' | 'no_response'
  notification_sent: boolean
}

export interface MatchingRule {
  id: number
  name: string
  description: string | null
  rule_key: string
  enabled: boolean
  parameters: Record<string, unknown>
}

export interface Stats {
  pilots: { total: number; active: number }
  missions: { total: number; open: number }
  matches: { total: number }
  historical_flights: number
  recent_match_logs: MatchLog[]
}
