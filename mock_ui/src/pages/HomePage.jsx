import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import client from '../api/client'

export default function HomePage() {
  const [restaurants, setRestaurants] = useState([])
  const [markets, setMarkets] = useState([])
  const [query, setQuery] = useState('')
  const [surface, setSurface] = useState('restaurants')
  const [district, setDistrict] = useState('Kadıköy')
  const [suggestions, setSuggestions] = useState([])

  useEffect(() => {
    if (surface === 'markets') {
      client.get('/v2/markets/search', { params: { query, district } })
        .then(res => setMarkets(res.data.markets || []))
        .catch(() => setMarkets([]))
    } else {
      client.get('/v2/restaurants/search', { params: { query, district, serviceType: surface === 'pickup' ? 'pickup' : 'delivery' } })
        .then(res => setRestaurants(res.data.restaurants || []))
        .catch(() => setRestaurants([]))
    }
  }, [query, surface, district])

  async function handleLocationSearch() {
    const res = await client.get('/v2/addresses/suggestions', { params: { query: district } })
    setSuggestions(res.data.suggestions || [])
    if (res.data.suggestions?.[0]) setDistrict(res.data.suggestions[0].district)
  }

  return (
    <main data-testid="home-page" style={{ padding: 24 }}>
      <h1>YemekTest Hub</h1>
      <div data-testid="safe-testing-banner">Mirror ortam: canlı Yemeksepeti üzerinde sipariş testi çalıştırılmaz.</div>
      <div data-testid="service-tabs" style={{ display: 'flex', gap: 8, margin: '12px 0' }}>
        <button data-testid="service-tab-restaurants" onClick={() => setSurface('restaurants')}>Restoran</button>
        <button data-testid="service-tab-pickup" onClick={() => setSurface('pickup')}>Gel Al</button>
        <button data-testid="service-tab-markets" onClick={() => setSurface('markets')}>Marketler</button>
      </div>
      <div data-testid="location-panel">
        <input data-testid="location-input" value={district} onChange={e => setDistrict(e.target.value)} />
        <button data-testid="location-search-button" onClick={handleLocationSearch}>Konum Seç</button>
        <span data-testid="selected-district">{district}</span>
      </div>
      {suggestions.length > 0 && <div data-testid="address-suggestions">{suggestions.map(s => s.label).join(' · ')}</div>}
      <input data-testid="search-input" value={query} onChange={e => setQuery(e.target.value)} placeholder="Restoran ara" style={{ padding: 10, width: 320, maxWidth: '100%' }} />
      {surface === 'markets' ? (
        <div data-testid="market-list" style={{ display: 'grid', gap: 12, marginTop: 20 }}>
          {markets.map(item => <div data-testid="market-card" key={item.id}>{item.name}</div>)}
        </div>
      ) : (
        <div data-testid="restaurant-list" style={{ display: 'grid', gap: 12, marginTop: 20 }}>
          {restaurants.map(item => (
            <Link data-testid="restaurant-card" key={item.id} to={`/restaurant/${item.id}`} style={{ padding: 16, border: '1px solid #e5e7eb', borderRadius: 8, color: 'inherit', textDecoration: 'none' }}>
              <strong>{item.name}</strong>
              <div>{item.cuisine} - {item.rating}</div>
              <span data-testid="service-type-label">{surface === 'pickup' ? 'Gel Al uygun' : 'Restoran teslimat'}</span>
            </Link>
          ))}
        </div>
      )}
    </main>
  )
}
