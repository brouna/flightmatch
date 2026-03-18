import { useQuery } from '@tanstack/react-query'
import { api, Stats } from '../lib/api'
import { format } from 'date-fns'

function StatCard({ label, value, sub }: { label: string; value: number; sub?: string }) {
  return (
    <div className="bg-white rounded-lg border p-5 shadow-sm">
      <p className="text-sm text-gray-500">{label}</p>
      <p className="text-3xl font-bold mt-1">{value}</p>
      {sub && <p className="text-xs text-gray-400 mt-1">{sub}</p>}
    </div>
  )
}

export default function Dashboard() {
  const { data, isLoading } = useQuery<Stats>({
    queryKey: ['stats'],
    queryFn: () => api.get('/admin/stats').then(r => r.data),
    refetchInterval: 30_000,
  })

  if (isLoading) return <div className="p-8 text-gray-500">Loading...</div>
  if (!data) return null

  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold mb-6">Dashboard</h1>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <StatCard label="Total Pilots" value={data.pilots.total} sub={`${data.pilots.active} active`} />
        <StatCard label="Open Missions" value={data.missions.open} sub={`${data.missions.total} total`} />
        <StatCard label="Total Matches" value={data.matches.total} />
        <StatCard label="Historical Flights" value={data.historical_flights} />
      </div>

      <div className="bg-white rounded-lg border shadow-sm">
        <div className="px-5 py-4 border-b">
          <h2 className="font-semibold">Recent Match Activity</h2>
        </div>
        <div className="divide-y">
          {data.recent_match_logs.length === 0 && (
            <p className="p-5 text-gray-400 text-sm">No match activity yet</p>
          )}
          {data.recent_match_logs.map((log: any) => (
            <div key={log.id} className="px-5 py-3 flex items-center justify-between text-sm">
              <span>
                Mission #{log.mission_id} → Pilot #{log.pilot_id}
              </span>
              <span className="text-gray-500">
                Score: {log.score?.toFixed(3) ?? '—'} · Rank: {log.rank ?? '—'}
              </span>
              <span className={
                log.pilot_response === 'accepted' ? 'text-green-600 font-medium' :
                log.pilot_response === 'declined' ? 'text-red-600 font-medium' :
                'text-gray-400'
              }>
                {log.pilot_response}
              </span>
              <span className="text-gray-400">
                {format(new Date(log.matched_at), 'MMM d, HH:mm')}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
