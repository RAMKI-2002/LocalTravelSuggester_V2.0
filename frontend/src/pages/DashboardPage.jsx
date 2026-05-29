import { useState } from 'react'
import { MapContainer, TileLayer, Marker, Popup, Polyline, useMap } from 'react-leaflet'
import L from 'leaflet'
import { suggestTrip } from '../api'

// Leaflet icon fix for Vite (default icon URLs break in bundled builds)
delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
})

const userIcon = new L.Icon({
  iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-red.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
  iconSize: [25, 41], iconAnchor: [12, 41],
})

function MapFitBounds({ bounds }) {
  const map = useMap()
  if (bounds && bounds.length > 0) {
    map.fitBounds(bounds, { padding: [40, 40] })
  }
  return null
}

function WeatherCard({ weather }) {
  if (!weather?.condition) return null
  const icons = { Clear: '☀️', Rain: '🌧️', Clouds: '⛅', Snow: '❄️', Thunderstorm: '⛈️', Drizzle: '🌦️', Mist: '🌫️', Haze: '🌫️' }
  const icon = icons[weather.condition] || '🌤️'
  return (
    <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 flex items-center gap-4">
      <span className="text-4xl">{icon}</span>
      <div>
        <div className="font-semibold text-blue-800">{weather.condition} · {weather.temp_c?.toFixed(1)}°C</div>
        <div className="text-blue-600 text-sm capitalize">{weather.description}</div>
        {weather.humidity && <div className="text-blue-500 text-xs">Humidity: {weather.humidity}% · Wind: {weather.wind_kph?.toFixed(0)} km/h</div>}
      </div>
    </div>
  )
}

function MetaBadges({ meta }) {
  if (!meta) return null
  return (
    <div className="flex flex-wrap gap-2 text-xs">
      <span className="bg-gray-100 text-gray-600 px-2 py-1 rounded">{meta.elapsed_ms}ms</span>
      {meta.llm_curate_used && <span className="bg-purple-100 text-purple-700 px-2 py-1 rounded">✨ AI curated</span>}
      {meta.cache_hits?.map(h => <span key={h} className="bg-green-100 text-green-700 px-2 py-1 rounded">⚡ {h} cached</span>)}
      {meta.degraded?.map(d => <span key={d} className="bg-yellow-100 text-yellow-700 px-2 py-1 rounded">⚠️ {d}</span>)}
      {meta.intent && <span className="bg-indigo-100 text-indigo-700 px-2 py-1 rounded">🎯 {meta.intent.category}</span>}
    </div>
  )
}

function SuggestionCard({ suggestion, index }) {
  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4 hover:shadow-md transition-shadow">
      <div className="flex items-start gap-3">
        <span className="bg-indigo-600 text-white text-sm font-bold w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0">
          {index + 1}
        </span>
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-gray-800 text-sm">{suggestion.name}</h3>
          {suggestion.categories?.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-1">
              {suggestion.categories.slice(0, 3).map(c => (
                <span key={c} className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded">{c}</span>
              ))}
            </div>
          )}
          {suggestion.reasoning && (
            <p className="text-gray-600 text-xs mt-2 leading-relaxed">{suggestion.reasoning}</p>
          )}
          <div className="flex gap-3 mt-2 text-xs text-gray-500">
            {suggestion.distance_km != null && <span>📍 {suggestion.distance_km.toFixed(1)} km</span>}
            {suggestion.estimated_budget?.total != null && (
              <span>💰 ₹{suggestion.estimated_budget.total}</span>
            )}
            {suggestion.score > 0 && <span>⭐ {(suggestion.score * 100).toFixed(0)}%</span>}
          </div>
          {suggestion.website && (
            <a href={suggestion.website} target="_blank" rel="noopener noreferrer"
               className="text-xs text-indigo-600 hover:underline mt-1 block">🔗 Website</a>
          )}
        </div>
      </div>
    </div>
  )
}

export default function DashboardPage() {
  const [form, setForm] = useState({ city: '', preference: '', locality: '', max_results: 5 })
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  function handleChange(e) {
    setForm({ ...form, [e.target.name]: e.target.value })
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      const data = await suggestTrip({
        city: form.city,
        preference: form.preference || undefined,
        locality: form.locality || undefined,
        max_results: parseInt(form.max_results) || 5,
      })
      setResult(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  // Build map data from results
  const mapCenter = result?.user_location
    ? [result.user_location.lat, result.user_location.lng]
    : result?.suggestions?.[0]?.coords
    ? [result.suggestions[0].coords.lat, result.suggestions[0].coords.lng]
    : [20.5937, 78.9629]  // India centre default

  const validSuggestions = (result?.suggestions || []).filter(s => s.coords?.lat && s.coords?.lng)

  const allPoints = [
    ...(result?.user_location ? [[result.user_location.lat, result.user_location.lng]] : []),
    ...validSuggestions.map(s => [s.coords.lat, s.coords.lng]),
  ]

  return (
    <div className="max-w-7xl mx-auto px-4 py-6">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: Form + Results */}
        <div className="space-y-4">
          {/* Trip Form */}
          <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
            <h2 className="text-lg font-bold text-gray-800 mb-4">🗺️ Find Places to Visit</h2>
            <form onSubmit={handleSubmit} className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">City *</label>
                <input type="text" name="city" value={form.city} onChange={handleChange}
                  placeholder="Hyderabad" required
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">What are you looking for?</label>
                <textarea name="preference" value={form.preference} onChange={handleChange}
                  placeholder="e.g. peaceful temples, street food, adventure trekking"
                  rows={2}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Your Locality</label>
                  <input type="text" name="locality" value={form.locality} onChange={handleChange}
                    placeholder="Gachibowli"
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Results</label>
                  <select name="max_results" value={form.max_results} onChange={handleChange}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500">
                    {[3, 5, 7, 10].map(n => <option key={n} value={n}>{n} places</option>)}
                  </select>
                </div>
              </div>
              <button type="submit" disabled={loading}
                className="w-full bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-300 text-white py-2.5 rounded-lg font-medium text-sm transition-colors">
                {loading ? '⏳ Finding places…' : '🔍 Suggest Places'}
              </button>
            </form>
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 rounded-xl px-4 py-3 text-sm">
              {error}
            </div>
          )}

          {result && (
            <>
              <WeatherCard weather={result.weather} />
              <MetaBadges meta={result.meta} />
              <div className="space-y-3">
                <h3 className="font-semibold text-gray-700 text-sm">
                  {result.suggestions.length} suggestion{result.suggestions.length !== 1 ? 's' : ''} for {result.city}
                </h3>
                {result.suggestions.map((s, i) => (
                  <SuggestionCard key={s.name + i} suggestion={s} index={i} />
                ))}
                {result.suggestions.length === 0 && (
                  <div className="text-center py-8 text-gray-400 text-sm">
                    No places found. Try a different city or preference.
                  </div>
                )}
              </div>
            </>
          )}
        </div>

        {/* Right: Map */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden" style={{ minHeight: '500px' }}>
          <MapContainer center={mapCenter} zoom={12} style={{ height: '100%', minHeight: '500px' }}>
            <TileLayer
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            />
            {allPoints.length > 0 && <MapFitBounds bounds={allPoints} />}

            {result?.user_location && (
              <Marker position={[result.user_location.lat, result.user_location.lng]} icon={userIcon}>
                <Popup>📍 Your location</Popup>
              </Marker>
            )}

            {validSuggestions.map((s, i) => (
              <Marker key={s.name + i} position={[s.coords.lat, s.coords.lng]}>
                <Popup>
                  <strong>{i + 1}. {s.name}</strong>
                  {s.distance_km != null && <div>📍 {s.distance_km.toFixed(1)} km away</div>}
                  {s.reasoning && <div className="mt-1 text-xs">{s.reasoning}</div>}
                </Popup>
              </Marker>
            ))}

            {result?.user_location && validSuggestions.map((s, i) => (
              <Polyline
                key={'line-' + i}
                positions={[
                  [result.user_location.lat, result.user_location.lng],
                  [s.coords.lat, s.coords.lng],
                ]}
                color="#6366f1"
                weight={1.5}
                opacity={0.4}
              />
            ))}
          </MapContainer>
        </div>
      </div>
    </div>
  )
}
