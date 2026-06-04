import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import client from '../api/client'

export default function HomePage() {
  const [restaurants, setRestaurants] = useState([])
  const [query, setQuery] = useState('')

  useEffect(() => {
    client.get('/v2/restaurants/search', { params: { query } })
      .then(res => setRestaurants(res.data.restaurants || []))
      .catch(() => setRestaurants([]))
  }, [query])

  return (
    <main data-testid="home-page" style={{ padding: 24 }}>
      <h1>YemekTest Hub</h1>
      <input data-testid="search-input" value={query} onChange={e => setQuery(e.target.value)} placeholder="Restoran ara" style={{ padding: 10, width: 320, maxWidth: '100%' }} />
      <div data-testid="restaurant-list" style={{ display: 'grid', gap: 12, marginTop: 20 }}>
        {restaurants.map(item => (
          <Link data-testid="restaurant-card" key={item.id} to={`/restaurant/${item.id}`} style={{ padding: 16, border: '1px solid #e5e7eb', borderRadius: 8, color: 'inherit', textDecoration: 'none' }}>
            <strong>{item.name}</strong>
            <div>{item.cuisine} - {item.rating}</div>
          </Link>
        ))}
      </div>
    </main>
  )
}
