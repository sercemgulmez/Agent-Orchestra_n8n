import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import client from '../api/client'
import Header from '../components/Header'
import { MenuCategory } from '../types'

export default function RestaurantDetail() {
  const { id } = useParams<{ id: string }>()
  const [categories, setCategories] = useState<MenuCategory[]>([])
  const [restaurantName, setRestaurantName] = useState('')
  const [cartCount, setCartCount] = useState(0)
  const [loading, setLoading] = useState(true)
  const [addedItem, setAddedItem] = useState<number | null>(null)

  useEffect(() => {
    loadMenu()
    loadCartCount()
  }, [id])

  async function loadMenu() {
    try {
      const res = await client.get(`/v2/restaurants/${id}/menu`)
      setCategories(res.data.categories)
      setRestaurantName(res.data.restaurantName)
    } finally {
      setLoading(false)
    }
  }

  async function loadCartCount() {
    try {
      const res = await client.get('/v2/cart')
      setCartCount(res.data.itemCount)
    } catch {/* ignore */}
  }

  async function addToCart(itemId: number, quantity = 1) {
    await client.post('/v2/cart/add', { itemId, quantity, restaurantId: Number(id) })
    setAddedItem(itemId)
    setCartCount(c => c + 1)
    setTimeout(() => setAddedItem(null), 1500)
  }

  if (loading) return <div data-testid="restaurant-detail-page"><Header cartCount={cartCount} /><p style={{ padding: '2rem', color: '#64748b' }}>Yükleniyor...</p></div>

  return (
    <div data-testid="restaurant-detail-page">
      <Header cartCount={cartCount} />
      <div style={{ padding: '1.5rem', maxWidth: '900px', margin: '0 auto' }}>
        <h2 style={{ marginBottom: '1.5rem', color: '#1e293b' }}>{restaurantName}</h2>
        <div data-testid="menu-list">
          {categories.map(cat => (
            <div key={cat.categoryId} data-testid="menu-category" style={{ marginBottom: '2rem' }}>
              <h3 style={{ color: '#e63946', borderBottom: '2px solid #e63946', paddingBottom: '0.25rem', marginBottom: '1rem' }}>{cat.categoryName}</h3>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: '0.75rem' }}>
                {cat.items.map(item => (
                  <div
                    key={item.id}
                    data-testid="menu-item"
                    data-item-id={item.id}
                    style={{ background: '#fff', border: '1px solid #f1f5f9', borderRadius: '10px', padding: '1rem', boxShadow: '0 1px 4px #0001' }}
                  >
                    <div data-testid="item-name" style={{ fontWeight: 600, marginBottom: '0.25rem' }}>{item.name}</div>
                    <div style={{ color: '#64748b', fontSize: '0.8rem', marginBottom: '0.5rem' }}>{item.description}</div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span data-testid="item-price" style={{ fontWeight: 700, color: '#e63946' }}>₺{item.price.toFixed(2)}</span>
                      <button
                        data-testid="add-to-cart-button"
                        data-item-quantity="1"
                        onClick={() => addToCart(item.id)}
                        style={{
                          background: addedItem === item.id ? '#22c55e' : '#e63946',
                          color: '#fff', border: 'none', borderRadius: '8px',
                          padding: '0.35rem 0.9rem', cursor: 'pointer', fontWeight: 600,
                          transition: 'background 0.2s',
                        }}
                      >
                        {addedItem === item.id ? '✓ Eklendi' : '+ Ekle'}
                      </button>
                    </div>
                    <div data-testid="item-quantity" style={{ display: 'none' }}>1</div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
