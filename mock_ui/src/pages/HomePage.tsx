import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import client from '../api/client'
import Header from '../components/Header'
import { Restaurant } from '../types'

export default function HomePage() {
  const navigate = useNavigate()
  const [restaurants, setRestaurants] = useState<Restaurant[]>([])
  const [search, setSearch] = useState('')
  const [cuisine, setCuisine] = useState('')
  const [sortByRating, setSortByRating] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchRestaurants()
  }, [])

  async function fetchRestaurants(q = '', c = '') {
    setLoading(true)
    try {
      const params: Record<string, string> = {}
      if (q) params.query = q
      if (c) params.cuisine = c
      const res = await client.get('/v2/restaurants/search', { params })
      setRestaurants(res.data.restaurants)
    } catch {
      // ignore
    } finally {
      setLoading(false)
    }
  }

  function handleSearch() {
    fetchRestaurants(search, cuisine)
  }

  const displayed = sortByRating
    ? [...restaurants].sort((a, b) => b.rating - a.rating)
    : restaurants

  return (
    <div data-testid="home-page">
      <Header />
      <div style={{ padding: '1.5rem', maxWidth: '1100px', margin: '0 auto' }}>
        <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '1.5rem', flexWrap: 'wrap' }}>
          <input
            data-testid="search-input"
            type="text"
            placeholder="Restoran ara..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSearch()}
            style={{ flex: 1, minWidth: '200px', padding: '0.6rem 1rem', border: '1px solid #cbd5e1', borderRadius: '8px', fontSize: '1rem' }}
          />
          <select
            data-testid="filter-cuisine"
            value={cuisine}
            onChange={e => { setCuisine(e.target.value); fetchRestaurants(search, e.target.value) }}
            style={{ padding: '0.6rem 1rem', border: '1px solid #cbd5e1', borderRadius: '8px', fontSize: '1rem' }}
          >
            <option value="">Tüm mutfaklar</option>
            <option value="burger">Burger</option>
            <option value="pizza">Pizza</option>
            <option value="sushi">Sushi</option>
            <option value="turkish">Türk</option>
            <option value="doner">Döner</option>
          </select>
          <button
            data-testid="search-button"
            onClick={handleSearch}
            style={{ padding: '0.6rem 1.25rem', background: '#e63946', color: '#fff', border: 'none', borderRadius: '8px', cursor: 'pointer', fontWeight: 600 }}
          >
            Ara
          </button>
          <button
            data-testid="sort-rating"
            onClick={() => setSortByRating(v => !v)}
            style={{ padding: '0.6rem 1.25rem', background: sortByRating ? '#e63946' : '#f1f5f9', color: sortByRating ? '#fff' : '#334155', border: '1px solid #cbd5e1', borderRadius: '8px', cursor: 'pointer' }}
          >
            Puana Göre {sortByRating ? '▼' : '▲'}
          </button>
        </div>

        {loading ? (
          <p style={{ color: '#64748b', textAlign: 'center' }}>Yükleniyor...</p>
        ) : (
          <div data-testid="restaurant-list" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '1rem' }}>
            {displayed.map(r => (
              <div
                key={r.id}
                data-testid="restaurant-card"
                data-restaurant-id={r.id}
                onClick={() => navigate(`/restaurant/${r.id}`)}
                style={{ background: '#fff', borderRadius: '12px', overflow: 'hidden', boxShadow: '0 2px 8px #0001', cursor: 'pointer', transition: 'transform 0.15s', border: '1px solid #f1f5f9' }}
              >
                <div style={{ height: '160px', background: '#f1f5f9', display: 'flex', alignItems: 'center', justifyContent: 'center', overflow: 'hidden' }}>
                  {r.imageUrl && <img src={r.imageUrl} alt={r.name} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />}
                </div>
                <div style={{ padding: '1rem' }}>
                  <h3 data-testid="restaurant-name" style={{ margin: '0 0 0.25rem', fontSize: '1.1rem' }}>{r.name}</h3>
                  <p style={{ color: '#64748b', fontSize: '0.875rem', margin: 0 }}>
                    ⭐ {r.rating} · {r.deliveryTime} dk · Min. ₺{r.minimumOrder}
                  </p>
                </div>
              </div>
            ))}
            {displayed.length === 0 && (
              <p style={{ color: '#64748b', gridColumn: '1/-1', textAlign: 'center' }}>Restoran bulunamadı.</p>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
