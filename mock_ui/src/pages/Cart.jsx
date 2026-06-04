import { useEffect, useState } from 'react'
import client from '../api/client'

export default function Cart() {
  const [cart, setCart] = useState({ items: [], total: 0 })

  function loadCart() {
    client.get('/v2/cart').then(res => setCart(res.data)).catch(() => setCart({ items: [], total: 0 }))
  }

  useEffect(() => {
    loadCart()
  }, [])

  async function updateQuantity(item, quantity) {
    await client.put('/v2/cart/update', { itemId: item.itemId, quantity })
    loadCart()
  }

  return (
    <main data-testid="cart-page" style={{ padding: 24 }}>
      <h1>Sepet</h1>
      {(cart.items || []).map(item => (
        <div data-testid="cart-item" key={item.itemId || item.id} style={{ padding: 12, borderBottom: '1px solid #e5e7eb' }}>
          {item.name} x <span data-testid="item-quantity">{item.quantity}</span>
          <button data-testid="quantity-increase" onClick={() => updateQuantity(item, item.quantity + 1)} style={{ marginLeft: 12 }}>+</button>
        </div>
      ))}
      <strong data-testid="cart-total">Toplam: {cart.total || 0} TL</strong>
      <button data-testid="checkout-button" style={{ display: 'block', marginTop: 16 }}>Odeme Yap</button>
    </main>
  )
}
