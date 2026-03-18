import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { api } from '../lib/api'

export default function HistoricalImport() {
  const [filePath, setFilePath] = useState('')

  const importMutation = useMutation({
    mutationFn: () => api.post('/admin/import', null, { params: { file_path: filePath } }),
  })

  return (
    <div className="p-8 max-w-2xl">
      <h1 className="text-2xl font-bold mb-2">Historical Flight Import</h1>
      <p className="text-gray-500 mb-6 text-sm">
        Import historical flight data from a CSV file on the server. The CSV should have columns:
        pilot_email, aircraft_type, origin_airport, destination_airport, flight_date, distance_nm, duration_h, accepted, outcome.
      </p>

      <div className="bg-white rounded-xl border shadow-sm p-6">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          CSV File Path (server-side)
        </label>
        <input
          type="text"
          className="w-full border rounded-lg px-3 py-2 text-sm mb-4"
          placeholder="/path/to/flights.csv"
          value={filePath}
          onChange={e => setFilePath(e.target.value)}
        />

        <button
          onClick={() => importMutation.mutate()}
          disabled={!filePath || importMutation.isPending}
          className="px-5 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 text-sm"
        >
          {importMutation.isPending ? 'Importing...' : 'Import Flights'}
        </button>

        {importMutation.isSuccess && (
          <div className="mt-4 p-3 bg-green-50 border border-green-200 rounded-lg text-sm text-green-800">
            Successfully imported {(importMutation.data as any)?.data?.imported ?? '?'} historical flights.
          </div>
        )}

        {importMutation.isError && (
          <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-800">
            Import failed: {String((importMutation.error as any)?.response?.data?.detail || 'Unknown error')}
          </div>
        )}
      </div>

      <div className="mt-6 bg-gray-50 rounded-lg border p-4">
        <h3 className="font-medium text-sm mb-2">Sample CSV Format</h3>
        <pre className="text-xs text-gray-600 overflow-x-auto">
{`pilot_email,aircraft_type,origin_airport,destination_airport,flight_date,distance_nm,duration_h,accepted,outcome
alice@example.com,SEL,KATL,KCLT,2024-01-15,180,1.5,true,completed
bob@example.com,MEL,KORD,KDTW,2024-01-20,200,1.8,true,completed
alice@example.com,SEL,KATL,KBOS,2024-02-10,900,6.0,false,`}</pre>
      </div>
    </div>
  )
}
