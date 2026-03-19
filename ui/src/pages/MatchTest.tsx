import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { api } from '../lib/api'
import { Plane, Search, AlertCircle } from 'lucide-react'

interface MatchResult {
  rank: number
  pilot_id: number
  pilot_name: string
  score: number
  features: Record<string, number>
}

interface MatchResponse {
  origin: string
  destination: string
  num_passengers: number
  flight_type: string
  distance_nm: number | null
  month: number
  scoring_method: 'ml' | 'heuristic'
  top_pilots: MatchResult[]
}

const SCORE_COLOR = (score: number) => {
  if (score >= 0.8) return 'text-green-700 bg-green-50'
  if (score >= 0.5) return 'text-yellow-700 bg-yellow-50'
  return 'text-red-700 bg-red-50'
}

const FEATURE_LABELS: Record<string, string> = {
  route_flight_count: 'Route flights',
  origin_flight_count: 'Origin flights',
  dest_flight_count: 'Dest flights',
  inferred_home_dist_nm: 'Home dist (nm)',
  total_flights: 'Total flights',
  recency_days: 'Recency (days)',
  monthly_activity_score: 'Monthly activity',
  flight_type_match: 'Type match',
  passenger_count_delta: 'Pax delta',
}

export default function MatchTest() {
  const today = new Date().toISOString().split('T')[0]
  const [form, setForm] = useState({
    date: today,
    origin: '',
    destination: '',
    num_passengers: 1,
    flight_type: 'private' as 'private' | 'commercial',
  })

  const mutation = useMutation<MatchResponse, Error>({
    mutationFn: () => {
      const month = new Date(form.date).getMonth() + 1
      return api.get('/match', {
        params: {
          origin: form.origin.toUpperCase(),
          destination: form.destination.toUpperCase(),
          num_passengers: form.num_passengers,
          flight_type: form.flight_type,
          month,
        },
      }).then(r => r.data)
    },
  })

  const set = (k: string, v: any) => setForm(f => ({ ...f, [k]: v }))

  return (
    <div className="p-8 max-w-5xl">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-9 h-9 bg-blue-600 rounded-lg flex items-center justify-center">
          <Plane size={18} className="text-white" />
        </div>
        <div>
          <h1 className="text-2xl font-bold">Pilot Match</h1>
          <p className="text-sm text-gray-500">Find the best pilots for a flight</p>
        </div>
      </div>

      {/* Form */}
      <div className="bg-white rounded-xl border shadow-sm p-6 mb-6">
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          {/* Date */}
          <div className="col-span-2 md:col-span-1">
            <label className="block text-xs font-medium text-gray-600 mb-1.5">Date</label>
            <input
              type="date"
              value={form.date}
              onChange={e => set('date', e.target.value)}
              className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* Origin */}
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1.5">Origin</label>
            <input
              type="text"
              placeholder="e.g. BGR"
              maxLength={4}
              value={form.origin}
              onChange={e => set('origin', e.target.value.toUpperCase())}
              className="w-full border rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500 uppercase"
            />
          </div>

          {/* Destination */}
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1.5">Destination</label>
            <input
              type="text"
              placeholder="e.g. BED"
              maxLength={4}
              value={form.destination}
              onChange={e => set('destination', e.target.value.toUpperCase())}
              className="w-full border rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500 uppercase"
            />
          </div>

          {/* Passengers */}
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1.5">Passengers</label>
            <input
              type="number"
              min={1}
              max={20}
              value={form.num_passengers}
              onChange={e => set('num_passengers', parseInt(e.target.value) || 1)}
              className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* Flight type */}
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1.5">Flight type</label>
            <select
              value={form.flight_type}
              onChange={e => set('flight_type', e.target.value)}
              className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
            >
              <option value="private">Private</option>
              <option value="commercial">Commercial</option>
            </select>
          </div>

          {/* Submit */}
          <div className="flex items-end">
            <button
              onClick={() => mutation.mutate()}
              disabled={!form.origin || !form.destination || mutation.isPending}
              className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-sm font-medium transition-colors"
            >
              <Search size={15} />
              {mutation.isPending ? 'Searching…' : 'Find Pilots'}
            </button>
          </div>
        </div>
      </div>

      {/* Error */}
      {mutation.isError && (
        <div className="flex items-center gap-2 text-red-700 bg-red-50 border border-red-200 rounded-lg px-4 py-3 mb-6 text-sm">
          <AlertCircle size={16} />
          {mutation.error.message}
        </div>
      )}

      {/* Results */}
      {mutation.data && (
        <div className="bg-white rounded-xl border shadow-sm overflow-hidden">
          {/* Summary bar */}
          <div className="flex items-center justify-between px-5 py-3 bg-gray-50 border-b text-sm">
            <span className="font-medium text-gray-700">
              {mutation.data.origin} → {mutation.data.destination}
              {mutation.data.distance_nm && (
                <span className="ml-2 text-gray-400">({Math.round(mutation.data.distance_nm)} nm)</span>
              )}
            </span>
            <div className="flex items-center gap-4 text-gray-500">
              <span>{mutation.data.num_passengers} pax · {mutation.data.flight_type}</span>
              <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                mutation.data.scoring_method === 'ml'
                  ? 'bg-blue-100 text-blue-700'
                  : 'bg-gray-200 text-gray-600'
              }`}>
                {mutation.data.scoring_method === 'ml' ? 'ML model' : 'Heuristic'}
              </span>
            </div>
          </div>

          {/* Table */}
          {mutation.data.top_pilots.length === 0 ? (
            <p className="text-center py-12 text-gray-400">No pilots found</p>
          ) : (
            <table className="w-full text-sm">
              <thead className="border-b">
                <tr>
                  <th className="text-left px-5 py-3 font-medium text-gray-600 w-10">#</th>
                  <th className="text-left px-5 py-3 font-medium text-gray-600">Pilot</th>
                  <th className="text-left px-5 py-3 font-medium text-gray-600">Score</th>
                  <th className="text-left px-5 py-3 font-medium text-gray-600">Route flights</th>
                  <th className="text-left px-5 py-3 font-medium text-gray-600">Origin flights</th>
                  <th className="text-left px-5 py-3 font-medium text-gray-600">Home dist</th>
                  <th className="text-left px-5 py-3 font-medium text-gray-600">Recency</th>
                  <th className="text-left px-5 py-3 font-medium text-gray-600">Total flights</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {mutation.data.top_pilots.map(p => (
                  <tr key={p.pilot_id} className="hover:bg-gray-50">
                    <td className="px-5 py-3 text-gray-400 font-medium">{p.rank}</td>
                    <td className="px-5 py-3 font-medium">{p.pilot_name}</td>
                    <td className="px-5 py-3">
                      <span className={`px-2 py-0.5 rounded text-xs font-mono font-semibold ${SCORE_COLOR(p.score)}`}>
                        {p.score.toFixed(3)}
                      </span>
                    </td>
                    <td className="px-5 py-3 text-gray-600">{p.features.route_flight_count ?? '—'}</td>
                    <td className="px-5 py-3 text-gray-600">{p.features.origin_flight_count ?? '—'}</td>
                    <td className="px-5 py-3 text-gray-600">
                      {p.features.inferred_home_dist_nm != null
                        ? `${Math.round(p.features.inferred_home_dist_nm)} nm`
                        : '—'}
                    </td>
                    <td className="px-5 py-3 text-gray-600">
                      {p.features.recency_days != null
                        ? `${Math.round(p.features.recency_days)}d`
                        : '—'}
                    </td>
                    <td className="px-5 py-3 text-gray-600">{p.features.total_flights ?? '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  )
}
