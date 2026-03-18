import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api, Mission } from '../lib/api'
import { format } from 'date-fns'

const STATUS_COLORS: Record<string, string> = {
  open: 'bg-green-100 text-green-800',
  matched: 'bg-blue-100 text-blue-800',
  completed: 'bg-gray-100 text-gray-600',
  cancelled: 'bg-red-100 text-red-800',
}

export default function MissionList() {
  const qc = useQueryClient()
  const [statusFilter, setStatusFilter] = useState('')
  const [showCreate, setShowCreate] = useState(false)

  const { data: missions = [], isLoading } = useQuery<Mission[]>({
    queryKey: ['missions', statusFilter],
    queryFn: () =>
      api.get('/missions', { params: statusFilter ? { status: statusFilter } : {} }).then(r => r.data),
  })

  const createMutation = useMutation({
    mutationFn: (payload: any) => api.post('/missions', payload),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['missions'] }); setShowCreate(false) },
  })

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Missions</h1>
        <button
          onClick={() => setShowCreate(true)}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium"
        >
          + New Mission
        </button>
      </div>

      <div className="flex gap-2 mb-4">
        {['', 'open', 'matched', 'completed', 'cancelled'].map(s => (
          <button
            key={s}
            onClick={() => setStatusFilter(s)}
            className={`px-3 py-1 rounded text-sm ${statusFilter === s ? 'bg-blue-600 text-white' : 'bg-white border text-gray-600 hover:bg-gray-50'}`}
          >
            {s || 'All'}
          </button>
        ))}
      </div>

      {isLoading ? (
        <div className="text-gray-400">Loading...</div>
      ) : (
        <div className="bg-white rounded-lg border shadow-sm overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Title</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Route</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Departure</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Status</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {missions.map(m => (
                <tr key={m.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium">{m.title}</td>
                  <td className="px-4 py-3 text-gray-600">{m.origin_airport} → {m.destination_airport}</td>
                  <td className="px-4 py-3 text-gray-600">{format(new Date(m.earliest_departure), 'MMM d, yyyy HH:mm')}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${STATUS_COLORS[m.status]}`}>
                      {m.status}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <Link to={`/missions/${m.id}`} className="text-blue-600 hover:underline">View</Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {missions.length === 0 && (
            <p className="text-center py-8 text-gray-400">No missions found</p>
          )}
        </div>
      )}

      {showCreate && <CreateMissionModal onSubmit={createMutation.mutate} onClose={() => setShowCreate(false)} />}
    </div>
  )
}

function CreateMissionModal({ onSubmit, onClose }: { onSubmit: (d: any) => void; onClose: () => void }) {
  const [form, setForm] = useState({
    title: '', origin_airport: '', destination_airport: '',
    earliest_departure: '', latest_departure: '', estimated_duration_h: '1.5',
    coordinator_notes: '',
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSubmit({ ...form, estimated_duration_h: Number(form.estimated_duration_h), passengers: [] })
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-lg">
        <h2 className="text-lg font-bold mb-4">Create Mission</h2>
        <form onSubmit={handleSubmit} className="space-y-3">
          {Object.entries(form).map(([key, val]) => (
            <div key={key}>
              <label className="block text-xs font-medium text-gray-600 mb-1 capitalize">
                {key.replace(/_/g, ' ')}
              </label>
              <input
                className="w-full border rounded px-3 py-2 text-sm"
                type={key.includes('departure') ? 'datetime-local' : 'text'}
                value={val}
                onChange={e => setForm(f => ({ ...f, [key]: e.target.value }))}
                required={!['coordinator_notes'].includes(key)}
              />
            </div>
          ))}
          <div className="flex gap-2 pt-2">
            <button type="submit" className="flex-1 bg-blue-600 text-white py-2 rounded font-medium hover:bg-blue-700 text-sm">
              Create
            </button>
            <button type="button" onClick={onClose} className="flex-1 border py-2 rounded text-sm hover:bg-gray-50">
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
