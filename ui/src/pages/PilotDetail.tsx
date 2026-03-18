import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api, Pilot } from '../lib/api'
import { format } from 'date-fns'

export default function PilotDetail() {
  const { id } = useParams()
  const pilotId = Number(id)

  const { data: pilot, isLoading } = useQuery<Pilot>({
    queryKey: ['pilot', pilotId],
    queryFn: () => api.get(`/pilots/${pilotId}`).then(r => r.data),
  })

  const { data: aircraft = [] } = useQuery({
    queryKey: ['pilot-aircraft', pilotId],
    queryFn: () => api.get(`/pilots/${pilotId}/aircraft`).then(r => r.data),
    enabled: !!pilot,
  })

  const { data: availability = [] } = useQuery({
    queryKey: ['pilot-availability', pilotId],
    queryFn: () => api.get(`/pilots/${pilotId}/availability`).then(r => r.data),
    enabled: !!pilot,
  })

  const { data: rankedMissions = [] } = useQuery({
    queryKey: ['pilot-missions', pilotId],
    queryFn: () => api.get(`/pilots/${pilotId}/missions`).then(r => r.data),
    enabled: !!pilot,
  })

  if (isLoading) return <div className="p-8 text-gray-400">Loading...</div>
  if (!pilot) return <div className="p-8 text-red-500">Pilot not found</div>

  return (
    <div className="p-8 max-w-4xl">
      <h1 className="text-2xl font-bold mb-1">{pilot.name}</h1>
      <p className="text-gray-500 mb-6">{pilot.email}</p>

      <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-8">
        <Info label="Home Airport" value={pilot.home_airport} />
        <Info label="Phone" value={pilot.phone || '—'} />
        <Info label="Status" value={pilot.active ? 'Active' : 'Inactive'} />
        {pilot.certifications.length > 0 && (
          <Info label="Certifications" value={pilot.certifications.join(', ')} />
        )}
        {pilot.preferred_regions.length > 0 && (
          <Info label="Preferred Regions" value={pilot.preferred_regions.join(', ')} />
        )}
        {pilot.max_range_nm && (
          <Info label="Max Range" value={`${pilot.max_range_nm} nm`} />
        )}
      </div>

      {/* Aircraft */}
      <section className="mb-8">
        <h2 className="font-semibold mb-3">Aircraft</h2>
        {aircraft.length === 0 ? (
          <p className="text-gray-400 text-sm">No aircraft linked</p>
        ) : (
          <div className="grid gap-3">
            {aircraft.map((link: any) => (
              <div key={link.id} className="bg-white border rounded-lg p-4 text-sm">
                <div className="flex items-center justify-between">
                  <span className="font-medium">{link.aircraft.tail_number}</span>
                  {link.is_primary && <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded">Primary</span>}
                </div>
                <p className="text-gray-500">{link.aircraft.make_model} · {link.aircraft.aircraft_type}</p>
                <div className="flex gap-4 mt-2 text-gray-600">
                  <span>Range: {link.aircraft.range_nm} nm</span>
                  <span>Payload: {link.aircraft.payload_lbs} lbs</span>
                  <span>Seats: {link.aircraft.num_seats}</span>
                  {link.aircraft.has_oxygen && <span className="text-green-600">O₂</span>}
                  {link.aircraft.fiki && <span className="text-blue-600">FIKI</span>}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Upcoming missions */}
      {rankedMissions.length > 0 && (
        <section className="mb-8">
          <h2 className="font-semibold mb-3">Ranked Open Missions</h2>
          <div className="bg-white border rounded-lg overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b">
                <tr>
                  <th className="text-left px-4 py-2 font-medium text-gray-600">Rank</th>
                  <th className="text-left px-4 py-2 font-medium text-gray-600">Mission</th>
                  <th className="text-left px-4 py-2 font-medium text-gray-600">Route</th>
                  <th className="text-left px-4 py-2 font-medium text-gray-600">Score</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {rankedMissions.map((m: any) => (
                  <tr key={m.mission_id}>
                    <td className="px-4 py-2 font-bold text-blue-700">#{m.rank}</td>
                    <td className="px-4 py-2">{m.title}</td>
                    <td className="px-4 py-2 text-gray-500">{m.origin_airport} → {m.destination_airport}</td>
                    <td className="px-4 py-2 font-mono text-xs">{m.score.toFixed(3)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* Availability */}
      <section>
        <h2 className="font-semibold mb-3">Upcoming Busy Blocks</h2>
        {availability.filter((a: any) => a.is_busy).length === 0 ? (
          <p className="text-gray-400 text-sm">No busy blocks</p>
        ) : (
          <div className="space-y-2">
            {availability
              .filter((a: any) => a.is_busy)
              .slice(0, 10)
              .map((a: any) => (
                <div key={a.id} className="bg-white border rounded p-3 text-sm flex justify-between">
                  <span>{format(new Date(a.start_time), 'MMM d HH:mm')} – {format(new Date(a.end_time), 'HH:mm')}</span>
                  <span className="text-gray-400 capitalize">{a.source}</span>
                </div>
              ))}
          </div>
        )}
      </section>
    </div>
  )
}

function Info({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-white rounded-lg border p-4">
      <p className="text-xs text-gray-500">{label}</p>
      <p className="font-medium mt-0.5 text-sm">{value}</p>
    </div>
  )
}
