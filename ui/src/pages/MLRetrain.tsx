import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'

interface ModelMetadata {
  trained_at?: string
  train_rows?: number
  val_rows?: number
  auc?: number
  error?: string
}

export default function MLRetrain() {
  const retrainMutation = useMutation<{ message: string; result?: ModelMetadata }>({
    mutationFn: () => api.post('/admin/retrain').then(r => r.data),
  })

  return (
    <div className="p-8 max-w-2xl">
      <h1 className="text-2xl font-bold mb-2">ML Model Retraining</h1>
      <p className="text-gray-500 mb-6 text-sm">
        Train a LightGBM model on accumulated match response data. The model predicts which pilots are most likely to accept and complete a mission.
      </p>

      <div className="bg-white rounded-xl border shadow-sm p-6 mb-6">
        <h2 className="font-semibold mb-4">Trigger Retraining</h2>
        <p className="text-sm text-gray-600 mb-4">
          Retraining pulls data from match_logs where pilots have responded (accepted/declined).
          At least 50 labeled examples are needed for model training; otherwise the heuristic scorer is used.
        </p>
        <button
          onClick={() => retrainMutation.mutate()}
          disabled={retrainMutation.isPending}
          className="px-5 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 text-sm"
        >
          {retrainMutation.isPending ? '⏳ Training...' : '🤖 Retrain Model'}
        </button>

        {retrainMutation.isSuccess && (
          <div className="mt-4 p-4 bg-green-50 border border-green-200 rounded-lg text-sm">
            <p className="font-medium text-green-800 mb-2">Training Complete</p>
            {retrainMutation.data.result?.auc && (
              <div className="grid grid-cols-2 gap-2 text-green-700">
                <span>Validation AUC: <strong>{retrainMutation.data.result.auc}</strong></span>
                <span>Train rows: <strong>{retrainMutation.data.result.train_rows}</strong></span>
                <span>Val rows: <strong>{retrainMutation.data.result.val_rows}</strong></span>
              </div>
            )}
            {retrainMutation.data.result?.error && (
              <p className="text-yellow-700">{retrainMutation.data.result.error}</p>
            )}
          </div>
        )}

        {retrainMutation.isError && (
          <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-800">
            Training failed: {String((retrainMutation.error as any)?.response?.data?.detail || 'Unknown error')}
          </div>
        )}
      </div>

      <div className="bg-blue-50 rounded-lg border border-blue-200 p-4">
        <h3 className="font-medium text-blue-900 mb-2">How Matching Works</h3>
        <ol className="text-sm text-blue-800 space-y-1 list-decimal list-inside">
          <li>Hard rules filter pilots by aircraft capability, availability, and distance</li>
          <li>Remaining pilots are scored using LightGBM (or heuristic if no model exists)</li>
          <li>Pilots are ranked by score and match results are persisted</li>
          <li>Email notifications sent to matched pilots with response links</li>
          <li>Pilot responses feed back as training labels for future models</li>
        </ol>
      </div>
    </div>
  )
}
