import { useParams } from 'react-router-dom'
import { useQuery, useMutation } from '@tanstack/react-query'
import { api, Mission, RankedPilot } from '../lib/api'
import { format } from 'date-fns'

export default function MissionDetail() {
  const { id } = useParams()
  const missionId = Number(id)

  const { data: mission, isLoading } = useQuery<Mission>({
    queryKey: ['mission', missionId],
    queryFn: () => api.get(`/missions/${missionId}`).then(r => r.data),
  })

  const { data: ranked, mutate: runMatch, isPending } = useMutation<RankedPilot[]>({
    mutationFn: () => api.post(`/missions/${missionId}/match`).then(r => r.data),
  })

  if (isLoading) return <div className="p-8 text-gray-400">Loading...</div>
  if (!mission) return <div className="p-8 text-red-500">Mission not found</div>

  return (
    <div className="p-8 max-w-4xl">
      <h1 className="text-2xl font-bold mb-1">{mission.title}</h1>
      <p className="text-gray-500 mb-6">Mission #{mission.id}</p>

      <div className="grid grid-cols-2 gap-4 mb-8">
        <InfoCard label="Route" value={`${mission.origin_airport} → ${mission.destination_airport}`} />
        <InfoCard label="Status" value={mission.status} />
        <InfoCard label="Earliest Departure" value={format(new Date(mission.earliest_departure), 'MMM d, yyyy HH:mm')} />
        <InfoCard label="Duration" value={`${mission.estimated_duration_h}h`} />
        <InfoCard label="Passengers" value={String((mission as any).passenger_count ?? '—')} />
        <InfoCard label="Total Payload" value={`${(mission as any).total_payload_lbs ?? '—'} lbs`} />
        {(mission as any).requires_oxygen && <InfoCard label="Oxygen Required" value="Yes" />}
      </div>

      {mission.coordinator_notes && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-6">
          <p className="text-sm font-medium text-yellow-800">Coordinator Notes</p>
          <p className="text-sm text-yellow-700 mt-1">{mission.coordinator_notes}</p>
        </div>
      )}

      <div className="flex items-center gap-4 mb-6">
        <button
          onClick={() => runMatch()}
          disabled={isPending}
          className="px-5 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 text-sm"
        >
          {isPending ? 'Running Match...' : '⚡ Run Match'}
        </button>
        <p className="text-xs text-gray-400">This will notify matched pilots via email</p>
      </div>

      {ranked && (
        <div className="bg-white rounded-lg border shadow-sm overflow-hidden">
          <div className="px-4 py-3 border-b bg-gray-50">
            <h2 className="font-semibold">Matched Pilots ({ranked.length})</h2>
          </div>
          <table className="w-full text-sm">
            <thead className="border-b">
              <tr>
                <th className="text-left px-4 py-3 text-gray-600 font-medium">Rank</th>
                <th className="text-left px-4 py-3 text-gray-600 font-medium">Pilot</th>
                <th className="text-left px-4 py-3 text-gray-600 font-medium">Home</th>
                <th className="text-left px-4 py-3 text-gray-600 font-medium">Score</th>
                <th className="text-left px-4 py-3 text-gray-600 font-medium">Ferry Dist</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {ranked.map(p => (
                <tr key={p.pilot_id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-bold text-blue-700">#{p.rank}</td>
                  <td className="px-4 py-3">
                    <p className="font-medium">{p.pilot_name}</p>
                    <p className="text-gray-400 text-xs">{p.pilot_email}</p>
                  </td>
                  <td className="px-4 py-3 text-gray-600">{p.home_airport}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <div className="w-24 bg-gray-200 rounded-full h-2">
                        <div
                          className="bg-blue-500 h-2 rounded-full"
                          style={{ width: `${p.score * 100}%` }}
                        />
                      </div>
                      <span className="font-mono text-xs">{p.score.toFixed(3)}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-gray-600">
                    {p.features.ferry_distance_to_origin_nm?.toFixed(0)} nm
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {ranked.length === 0 && (
            <p className="text-center py-8 text-gray-400">No pilots passed hard filters</p>
          )}
        </div>
      )}
    </div>
  )
}

function InfoCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-white rounded-lg border p-4">
      <p className="text-xs text-gray-500">{label}</p>
      <p className="font-medium mt-0.5">{value}</p>
    </div>
  )
}
