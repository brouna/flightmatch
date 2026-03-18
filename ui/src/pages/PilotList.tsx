import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api, Pilot } from '../lib/api'

export default function PilotList() {
  const qc = useQueryClient()
  const [search, setSearch] = useState('')
  const [showCreate, setShowCreate] = useState(false)

  const { data: pilots = [], isLoading } = useQuery<Pilot[]>({
    queryKey: ['pilots'],
    queryFn: () => api.get('/pilots').then(r => r.data).catch(() => []),
  })

  const createMutation = useMutation({
    mutationFn: (payload: any) => api.post('/pilots', payload),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['pilots'] }); setShowCreate(false) },
  })

  const filtered = pilots.filter(p =>
    p.name.toLowerCase().includes(search.toLowerCase()) ||
    p.email.toLowerCase().includes(search.toLowerCase()) ||
    p.home_airport.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Pilots</h1>
        <button
          onClick={() => setShowCreate(true)}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium"
        >
          + Add Pilot
        </button>
      </div>

      <input
        className="w-full max-w-sm border rounded-lg px-3 py-2 text-sm mb-4"
        placeholder="Search pilots..."
        value={search}
        onChange={e => setSearch(e.target.value)}
      />

      {isLoading ? (
        <div className="text-gray-400">Loading...</div>
      ) : (
        <div className="bg-white rounded-lg border shadow-sm overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Name</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Email</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Home Airport</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Status</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {filtered.map(p => (
                <tr key={p.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium">{p.name}</td>
                  <td className="px-4 py-3 text-gray-600">{p.email}</td>
                  <td className="px-4 py-3 text-gray-600">{p.home_airport}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${p.active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-600'}`}>
                      {p.active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <Link to={`/pilots/${p.id}`} className="text-blue-600 hover:underline">View</Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {filtered.length === 0 && (
            <p className="text-center py-8 text-gray-400">No pilots found</p>
          )}
        </div>
      )}

      {showCreate && <CreatePilotModal onSubmit={createMutation.mutate} onClose={() => setShowCreate(false)} />}
    </div>
  )
}

function CreatePilotModal({ onSubmit, onClose }: { onSubmit: (d: any) => void; onClose: () => void }) {
  const [form, setForm] = useState({
    email: '', name: '', home_airport: '', phone: '',
  })

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-md">
        <h2 className="text-lg font-bold mb-4">Add Pilot</h2>
        <form onSubmit={e => { e.preventDefault(); onSubmit({ ...form, certifications: [], preferred_regions: [] }) }} className="space-y-3">
          {Object.entries(form).map(([key, val]) => (
            <div key={key}>
              <label className="block text-xs font-medium text-gray-600 mb-1 capitalize">
                {key.replace(/_/g, ' ')}
              </label>
              <input
                className="w-full border rounded px-3 py-2 text-sm"
                type={key === 'email' ? 'email' : 'text'}
                value={val}
                onChange={e => setForm(f => ({ ...f, [key]: e.target.value }))}
                required={key !== 'phone'}
              />
            </div>
          ))}
          <div className="flex gap-2 pt-2">
            <button type="submit" className="flex-1 bg-blue-600 text-white py-2 rounded font-medium hover:bg-blue-700 text-sm">Add</button>
            <button type="button" onClick={onClose} className="flex-1 border py-2 rounded text-sm hover:bg-gray-50">Cancel</button>
          </div>
        </form>
      </div>
    </div>
  )
}
