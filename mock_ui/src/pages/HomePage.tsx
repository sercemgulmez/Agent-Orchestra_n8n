import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import client from '../api/client'
import Header from '../components/Header'
import { AddressSuggestion, Market, Restaurant } from '../types'

type Surface = 'restaurants' | 'pickup' | 'markets'

export default function HomePage() {
  const navigate = useNavigate()
  const [restaurants, setRestaurants] = useState<Restaurant[]>([])
  const [markets, setMarkets] = useState<Market[]>([])
  const [surface, setSurface] = useState<Surface>('restaurants')
  const [search, setSearch] = useState('')
  const [cuisine, setCuisine] = useState('')
  const [addressQuery, setAddressQuery] = useState('Kadıköy')
  const [selectedDistrict, setSelectedDistrict] = useState('Kadıköy')
  const [suggestions, setSuggestions] = useState<AddressSuggestion[]>([])
  const [sortByRating, setSortByRating] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchSurface()
  }, [surface, selectedDistrict])

  async function fetchSurface(q = search, c = cuisine) {
    setLoading(true)
    try {
      if (surface === 'markets') {
        const params: Record<string, string> = {}
        if (q) params.query = q
        if (selectedDistrict) params.district = selectedDistrict
        const res = await client.get('/v2/markets/search', { params })
        setMarkets(res.data.markets)
      } else {
        const params: Record<string, string> = {
          serviceType: surface === 'pickup' ? 'pickup' : 'delivery',
        }
        if (q) params.query = q
        if (c) params.cuisine = c
        if (selectedDistrict) params.district = selectedDistrict
        const res = await client.get('/v2/restaurants/search', { params })
        setRestaurants(res.data.restaurants)
      }
    } catch {
      // ignore
    } finally {
      setLoading(false)
    }
  }

  function handleSearch() {
    fetchSurface(search, cuisine)
  }

  async function handleAddressLookup() {
    const res = await client.get('/v2/addresses/suggestions', { params: { query: addressQuery } })
    setSuggestions(res.data.suggestions)
    if (res.data.suggestions?.[0]) {
      setSelectedDistrict(res.data.suggestions[0].district)
    }
  }

  const displayed = sortByRating
    ? [...restaurants].sort((a, b) => b.rating - a.rating)
    : restaurants

  const displayedMarkets = sortByRating
    ? [...markets].sort((a, b) => b.rating - a.rating)
    : markets

  return (
    <div data-testid="home-page">
      <Header />
      <div style={{ padding: '1.5rem', maxWidth: '1100px', margin: '0 auto' }}>
        <div data-testid="safe-testing-banner" style={{ background: '#fff7ed', border: '1px solid #fed7aa', color: '#9a3412', borderRadius: '8px', padding: '0.75rem 1rem', marginBottom: '1rem' }}>
          Mirror ortam: canlı Yemeksepeti üzerinde login, ödeme veya sipariş testi çalıştırılmaz.
        </div>

        <div data-testid="service-tabs" style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem', flexWrap: 'wrap' }}>
          {[
            { id: 'restaurants', label: 'Restoran' },
            { id: 'pickup', label: 'Gel Al' },
            { id: 'markets', label: 'Marketler' },
          ].map(tab => (
            <button
              key={tab.id}
              data-testid={`service-tab-${tab.id}`}
              onClick={() => setSurface(tab.id as Surface)}
              style={{ padding: '0.55rem 1rem', borderRadius: '999px', border: '1px solid #e63946', background: surface === tab.id ? '#e63946' : '#fff', color: surface === tab.id ? '#fff' : '#e63946', fontWeight: 700, cursor: 'pointer' }}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <div data-testid="location-panel" style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem', flexWrap: 'wrap' }}>
          <input
            data-testid="location-input"
            value={addressQuery}
            onChange={e => setAddressQuery(e.target.value)}
            placeholder="Adres veya ilçe gir"
            style={{ flex: 1, minWidth: '220px', padding: '0.6rem 1rem', border: '1px solid #cbd5e1', borderRadius: '8px' }}
          />
          <button data-testid="location-search-button" onClick={handleAddressLookup} style={{ padding: '0.6rem 1rem', background: '#334155', color: '#fff', border: 'none', borderRadius: '8px', cursor: 'pointer' }}>
            Konum Seç
          </button>
          <span data-testid="selected-district" style={{ alignSelf: 'center', color: '#475569', fontWeight: 600 }}>{selectedDistrict}</span>
        </div>
        {suggestions.length > 0 && (
          <div data-testid="address-suggestions" style={{ color: '#64748b', fontSize: '0.875rem', marginBottom: '1rem' }}>
            {suggestions.map(s => s.label).join(' · ')}
          </div>
        )}

        <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '1.5rem', flexWrap: 'wrap' }}>
          <input
            data-testid="search-input"
            type="text"
            placeholder={surface === 'markets' ? 'Market ürünü ara...' : 'Restoran ara...'}
            value={search}
            onChange={e => setSearch(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSearch()}
            style={{ flex: 1, minWidth: '200px', padding: '0.6rem 1rem', border: '1px solid #cbd5e1', borderRadius: '8px', fontSize: '1rem' }}
          />
          <select
            data-testid="filter-cuisine"
            value={cuisine}
            onChange={e => { setCuisine(e.target.value); fetchSurface(search, e.target.value) }}
            disabled={surface === 'markets'}
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
        ) : surface === 'markets' ? (
          <div data-testid="market-list" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '1rem' }}>
            {displayedMarkets.map(m => (
              <div
                key={m.id}
                data-testid="market-card"
                data-market-id={m.id}
                style={{ background: '#fff', borderRadius: '12px', padding: '1rem', boxShadow: '0 2px 8px #0001', border: '1px solid #f1f5f9' }}
              >
                <h3 data-testid="market-name" style={{ margin: '0 0 0.25rem', fontSize: '1.1rem' }}>{m.name}</h3>
                <p style={{ color: '#64748b', fontSize: '0.875rem', margin: 0 }}>⭐ {m.rating} · {m.deliveryTime} dk · Min. ₺{m.minimumOrder}</p>
                <p style={{ color: '#475569', fontSize: '0.8rem' }}>Marketler mirror yüzeyi</p>
              </div>
            ))}
            {displayedMarkets.length === 0 && (
              <p style={{ color: '#64748b', gridColumn: '1/-1', textAlign: 'center' }}>Market bulunamadı.</p>
            )}
          </div>
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
                  <p data-testid="service-type-label" style={{ color: '#475569', fontSize: '0.8rem', margin: '0.4rem 0 0' }}>
                    {surface === 'pickup' ? 'Gel Al uygun' : 'Restoran teslimat'}
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
