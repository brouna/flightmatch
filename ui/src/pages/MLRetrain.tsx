import { useEffect, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../lib/api'

interface ModelMetadata {
  trained_at?: string
  train_rows?: number
  val_rows?: number
  auc?: number
  error?: string
}

interface RetrainResponse {
  async: boolean
  task_id?: string
  status: string
  result?: ModelMetadata
}

interface TaskStatus {
  status: 'pending' | 'running' | 'complete' | 'failed'
  result?: ModelMetadata
  error?: string
}

function ModelStats({ meta, label }: { meta: ModelMetadata; label: string }) {
  if (meta.error) {
    return <p className="text-yellow-700 text-sm">{meta.error}</p>
  }
  return (
    <div>
      <p className="text-xs text-gray-500 mb-2">{label}</p>
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-gray-50 rounded-lg p-3 text-center">
          <p className="text-2xl font-bold text-blue-600">{meta.auc?.toFixed(3) ?? '—'}</p>
          <p className="text-xs text-gray-500 mt-1">Validation AUC</p>
        </div>
        <div className="bg-gray-50 rounded-lg p-3 text-center">
          <p className="text-2xl font-bold text-gray-700">{meta.train_rows?.toLocaleString() ?? '—'}</p>
          <p className="text-xs text-gray-500 mt-1">Train rows</p>
        </div>
        <div className="bg-gray-50 rounded-lg p-3 text-center">
          <p className="text-2xl font-bold text-gray-700">{meta.val_rows?.toLocaleString() ?? '—'}</p>
          <p className="text-xs text-gray-500 mt-1">Val rows</p>
        </div>
      </div>
      {meta.trained_at && (
        <p className="text-xs text-gray-400 mt-2">
          Trained {new Date(meta.trained_at + 'Z').toLocaleString()}
        </p>
      )}
    </div>
  )
}

export default function MLRetrain() {
  const queryClient = useQueryClient()
  const [taskId, setTaskId] = useState<string | null>(null)
  const [taskStatus, setTaskStatus] = useState<TaskStatus | null>(null)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const { data: currentModel, isLoading: modelLoading } = useQuery<ModelMetadata>({
    queryKey: ['model-metadata'],
    queryFn: () => api.get('/admin/model-metadata').then(r => r.data),
    retry: false, // 404 = no model yet, that's fine
  })

  // Poll Celery task status when we have a task_id
  useEffect(() => {
    if (!taskId) return

    pollRef.current = setInterval(async () => {
      try {
        const { data } = await api.get<TaskStatus>(`/admin/retrain/${taskId}`)
        setTaskStatus(data)
        if (data.status === 'complete' || data.status === 'failed') {
          clearInterval(pollRef.current!)
          pollRef.current = null
          setTaskId(null)
          if (data.status === 'complete') {
            queryClient.invalidateQueries({ queryKey: ['model-metadata'] })
          }
        }
      } catch {
        clearInterval(pollRef.current!)
        pollRef.current = null
        setTaskId(null)
        setTaskStatus({ status: 'failed', error: 'Lost contact with server' })
      }
    }, 2000)

    return () => {
      if (pollRef.current) clearInterval(pollRef.current)
    }
  }, [taskId, queryClient])

  const retrainMutation = useMutation<RetrainResponse>({
    mutationFn: () => api.post('/admin/retrain').then(r => r.data),
    onSuccess: (data) => {
      if (data.async && data.task_id) {
        setTaskId(data.task_id)
        setTaskStatus({ status: 'pending' })
      } else {
        // Inline (no Celery): result is already here
        setTaskStatus({ status: 'complete', result: data.result })
        queryClient.invalidateQueries({ queryKey: ['model-metadata'] })
      }
    },
  })

  const isTraining = retrainMutation.isPending || taskId !== null ||
    (taskStatus?.status === 'pending' || taskStatus?.status === 'running')

  const statusLabel: Record<string, string> = {
    pending: 'Queued...',
    running: 'Training...',
    complete: 'Complete',
    failed: 'Failed',
  }

  return (
    <div className="p-8 max-w-2xl">
      <h1 className="text-2xl font-bold mb-2">ML Model Retraining</h1>
      <p className="text-gray-500 mb-6 text-sm">
        Train a LightGBM model on accumulated match response data. The model predicts which pilots are most likely to accept and complete a mission.
      </p>

      {/* Current model stats */}
      <div className="bg-white rounded-xl border shadow-sm p-6 mb-4">
        <h2 className="font-semibold mb-4">Current Model</h2>
        {modelLoading ? (
          <p className="text-sm text-gray-400">Loading...</p>
        ) : currentModel ? (
          <ModelStats meta={currentModel} label="Deployed model statistics" />
        ) : (
          <p className="text-sm text-gray-400">No model trained yet.</p>
        )}
      </div>

      {/* Retrain controls */}
      <div className="bg-white rounded-xl border shadow-sm p-6 mb-4">
        <h2 className="font-semibold mb-4">Trigger Retraining</h2>
        <p className="text-sm text-gray-600 mb-4">
          Retraining pulls data from match_logs where pilots have responded (accepted/declined).
          At least 50 labeled examples are needed; otherwise the heuristic scorer is used.
        </p>
        <button
          onClick={() => { setTaskStatus(null); retrainMutation.mutate() }}
          disabled={isTraining}
          className="px-5 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 text-sm"
        >
          {isTraining ? `⏳ ${statusLabel[taskStatus?.status ?? 'pending']}` : '🤖 Retrain Model'}
        </button>

        {/* Status / result */}
        {taskStatus?.status === 'complete' && taskStatus.result && (
          <div className="mt-4 p-4 bg-green-50 border border-green-200 rounded-lg">
            <p className="font-medium text-green-800 mb-3 text-sm">Training complete — new model deployed</p>
            <ModelStats meta={taskStatus.result} label="New model statistics" />
          </div>
        )}

        {taskStatus?.status === 'failed' && (
          <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-800">
            Training failed: {taskStatus.error ?? 'Unknown error'}
          </div>
        )}

        {retrainMutation.isError && (
          <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-800">
            {String((retrainMutation.error as any)?.response?.data?.detail ?? 'Request failed')}
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
