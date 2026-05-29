import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { getHistory } from '../api'

function HistoryItem({ item }) {
  const [expanded, setExpanded] = useState(false)
  const date = item.created_at
    ? new Date(item.created_at).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' })
    : 'Unknown time'

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4 hover:shadow-sm transition-shadow">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-semibold text-gray-800">🏙️ {item.city}</span>
            <span className="text-xs text-gray-400">{date}</span>
            {item.degraded?.length > 0 && (
              <span className="text-xs bg-yellow-100 text-yellow-700 px-2 py-0.5 rounded">
                ⚠️ degraded
              </span>
            )}
          </div>
          {item.preference && (
            <p className="text-gray-600 text-sm mt-1 italic">"{item.preference}"</p>
          )}
          {item.locality && (
            <p className="text-gray-500 text-xs mt-0.5">📍 from {item.locality}</p>
          )}
        </div>
        <div className="text-right flex-shrink-0">
          <div className="text-sm font-medium text-indigo-600">{item.suggestion_count} places</div>
          {item.latency_ms > 0 && <div className="text-xs text-gray-400">{item.latency_ms}ms</div>}
          {item.suggestion_count > 0 && (
            <button
              onClick={() => setExpanded(!expanded)}
              className="text-xs text-indigo-500 hover:text-indigo-700 mt-1"
            >
              {expanded ? '▲ Hide' : '▼ Show'}
            </button>
          )}
        </div>
      </div>

      {expanded && item.top_suggestion && (
        <div className="mt-3 pt-3 border-t border-gray-100">
          <p className="text-xs text-gray-500">Top suggestion:</p>
          <p className="text-sm text-gray-700 font-medium">⭐ {item.top_suggestion}</p>
        </div>
      )}
    </div>
  )
}

export default function HistoryPage() {
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    getHistory(20)
      .then(data => setHistory(data.items || []))
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="max-w-3xl mx-auto px-4 py-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-bold text-gray-800">📋 Trip History</h1>
        <Link to="/dashboard"
          className="text-sm text-indigo-600 hover:text-indigo-800 transition-colors">
          ← Back to Dashboard
        </Link>
      </div>

      {loading && (
        <div className="text-center py-12 text-gray-400">Loading your history…</div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 rounded-xl px-4 py-3 text-sm">
          {error}
        </div>
      )}

      {!loading && !error && history.length === 0 && (
        <div className="text-center py-12">
          <div className="text-5xl mb-4">🗺️</div>
          <p className="text-gray-500">No trips yet. Head to the Dashboard and explore!</p>
          <Link to="/dashboard"
            className="mt-4 inline-block bg-indigo-600 text-white px-6 py-2 rounded-lg text-sm hover:bg-indigo-700 transition-colors">
            Explore Places
          </Link>
        </div>
      )}

      {history.length > 0 && (
        <div className="space-y-3">
          {history.map(item => (
            <HistoryItem key={item.id} item={item} />
          ))}
        </div>
      )}
    </div>
  )
}
