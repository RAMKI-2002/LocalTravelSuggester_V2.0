import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { getFavorites, deleteFavorite } from '../api'

function FavoriteItem({ item, onRemove }) {
  const [removing, setRemoving] = useState(false)
  const date = item.created_at
    ? new Date(item.created_at).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' })
    : 'Unknown time'

  async function handleRemove() {
    setRemoving(true)
    try {
      await deleteFavorite(item.id)
      onRemove(item.id)
    } catch (err) {
      if (err.message.includes('404') || err.message.includes('not found')) {
        onRemove(item.id)
      } else {
        alert(err.message)
      }
    } finally {
      setRemoving(false)
    }
  }

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4 hover:shadow-sm transition-shadow">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-gray-800">{item.place_name}</h3>
          <p className="text-xs text-gray-500 mt-0.5">🏙️ {item.city} · saved {date}</p>
          {item.categories?.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-2">
              {item.categories.slice(0, 3).map(c => (
                <span key={c} className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded">{c}</span>
              ))}
            </div>
          )}
          {item.reasoning && (
            <p className="text-gray-600 text-xs mt-2 leading-relaxed">{item.reasoning}</p>
          )}
          {(item.lat != null && item.lng != null) && (
            <p className="text-xs text-gray-400 mt-1">📍 {item.lat.toFixed(4)}, {item.lng.toFixed(4)}</p>
          )}
        </div>
        <button
          onClick={handleRemove}
          disabled={removing}
          className="text-red-500 hover:text-red-700 text-sm flex-shrink-0 disabled:opacity-50"
          title="Remove from favorites"
        >
          {removing ? '…' : '♥'}
        </button>
      </div>
    </div>
  )
}

export default function FavoritesPage() {
  const [favorites, setFavorites] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    getFavorites(20)
      .then(data => setFavorites(data.items || []))
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  function handleRemove(id) {
    setFavorites(prev => prev.filter(f => f.id !== id))
  }

  return (
    <div className="max-w-3xl mx-auto px-4 py-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-bold text-gray-800">♥ Saved Places</h1>
        <Link to="/dashboard"
          className="text-sm text-indigo-600 hover:text-indigo-800 transition-colors">
          ← Back to Dashboard
        </Link>
      </div>

      {loading && (
        <div className="text-center py-12 text-gray-400">Loading your favorites…</div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 rounded-xl px-4 py-3 text-sm">
          {error}
        </div>
      )}

      {!loading && !error && favorites.length === 0 && (
        <div className="text-center py-12">
          <div className="text-5xl mb-4">♡</div>
          <p className="text-gray-500">No saved places yet — find suggestions on the Dashboard.</p>
          <Link to="/dashboard"
            className="mt-4 inline-block bg-indigo-600 text-white px-6 py-2 rounded-lg text-sm hover:bg-indigo-700 transition-colors">
            Explore Places
          </Link>
        </div>
      )}

      {favorites.length > 0 && (
        <div className="space-y-3">
          {favorites.map(item => (
            <FavoriteItem key={item.id} item={item} onRemove={handleRemove} />
          ))}
        </div>
      )}
    </div>
  )
}
