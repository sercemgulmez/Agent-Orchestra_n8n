import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import client from '../api/client'

export default function RestaurantDetail() {
  const { id } = useParams()
  const [menu, setMenu] = useState(null)
  const [cartCount, setCartCount] = useState(0)

  useEffect(() => {
    client.get(`/v2/restaurants/${id}/menu`).then(res => setMenu(res.data)).catch(() => setMenu(null))
  }, [id])

  async function addItem(item) {
    const res = await client.post('/v2/cart/add', { restaurantId: Number(id), itemId: item.id, quantity: 1 })
    setCartCount((res.data.cart?.items || []).reduce((sum, cartItem) => sum + cartItem.quantity, 0))
  }

  return (
    <main data-testid="restaurant-detail-page" style={{ padding: 24 }}>
      <Link to="/">Geri</Link>
      <Link data-testid="cart-link" to="/cart" style={{ float: 'right' }}>
        Sepet <span data-testid="cart-badge">{cartCount}</span>
      </Link>
      <h1>Restoran Detay</h1>
      <div data-testid="menu-list">
        {(menu?.categories || []).map(category => (
          <section key={category.id || category.categoryId}>
            <h2>{category.name || category.categoryName}</h2>
            {(category.items || []).map(item => (
              <div data-testid="menu-item" key={item.id} style={{ display: 'flex', justifyContent: 'space-between', padding: 12, borderBottom: '1px solid #e5e7eb' }}>
                <span>{item.name} - {item.price} TL</span>
                <button data-testid="add-to-cart-button" onClick={() => addItem(item)}>Sepete Ekle</button>
              </div>
            ))}
          </section>
        ))}
      </div>
    </main>
  )
}
