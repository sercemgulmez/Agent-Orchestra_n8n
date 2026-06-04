import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import client from '../api/client'
import Header from '../components/Header'
import { CartItem } from '../types'

export default function Cart() {
  const navigate = useNavigate()
  const [items, setItems] = useState<CartItem[]>([])
  const [total, setTotal] = useState(0)
  const [coupon, setCoupon] = useState('')
  const [couponApplied, setCouponApplied] = useState(false)
  const [orderSuccess, setOrderSuccess] = useState(false)
  const [orderId, setOrderId] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => { loadCart() }, [])

  async function loadCart() {
    try {
      const res = await client.get('/v2/cart')
      setItems(res.data.items)
      setTotal(res.data.total)
    } finally {
      setLoading(false)
    }
  }

  async function handleIncrease(itemId: number) {
    const item = items.find(i => i.itemId === itemId)
    if (!item) return
    const res = await client.put('/v2/cart/update', { itemId, quantity: item.quantity + 1 })
    setItems(res.data.cart.items)
    setTotal(res.data.cart.total)
  }

  async function handleDecrease(itemId: number) {
    const item = items.find(i => i.itemId === itemId)
    if (!item) return
    const newQty = item.quantity - 1
    const res = await client.put('/v2/cart/update', { itemId, quantity: newQty })
    setItems(res.data.cart.items)
    setTotal(res.data.cart.total)
  }

  async function handleRemove(itemId: number) {
    const item = items.find(i => i.itemId === itemId)
    if (!item) return
    const res = await client.delete('/v2/cart/remove', { data: { itemId } })
    setItems(res.data.cart.items)
    setTotal(res.data.cart.total)
  }

  function handleApplyCoupon() {
    if (coupon.trim()) {
      setCouponApplied(true)
    }
  }

  async function handleCheckout() {
    if (items.length === 0) return
    const restaurantId = items[0]?.restaurantId ?? 1
    const res = await client.post('/v2/orders/create', {
      restaurantId,
      items,
      deliveryAddress: 'Test Adres, İstanbul',
      paymentMethod: 'card',
    })
    setOrderId(res.data.orderId)
    setOrderSuccess(true)
    setItems([])
    setTotal(0)
  }

  return (
    <div data-testid="cart-page">
      <Header cartCount={items.length} />
      <div style={{ padding: '1.5rem', maxWidth: '700px', margin: '0 auto' }}>
        <h2 style={{ marginBottom: '1.5rem', color: '#1e293b' }}>Sepetim</h2>

        {orderSuccess && (
          <div data-testid="order-success-message" style={{ background: '#f0fdf4', border: '1px solid #bbf7d0', borderRadius: '10px', padding: '1rem', marginBottom: '1.5rem', color: '#166534' }}>
            Siparişiniz alındı! Sipariş No: <strong>{orderId}</strong>
            <button onClick={() => navigate('/')} style={{ marginLeft: '1rem', background: '#22c55e', color: '#fff', border: 'none', borderRadius: '6px', padding: '0.25rem 0.75rem', cursor: 'pointer' }}>
              Ana Sayfa
            </button>
          </div>
        )}

        {loading ? (
          <p style={{ color: '#64748b' }}>Yükleniyor...</p>
        ) : items.length === 0 && !orderSuccess ? (
          <div data-testid="empty-cart-message" style={{ textAlign: 'center', color: '#64748b', padding: '3rem 0' }}>
            <div style={{ fontSize: '3rem' }}>🛒</div>
            <p>Sepetiniz boş</p>
            <button onClick={() => navigate('/')} style={{ marginTop: '1rem', background: '#e63946', color: '#fff', border: 'none', borderRadius: '8px', padding: '0.5rem 1.25rem', cursor: 'pointer' }}>
              Alışverişe Başla
            </button>
          </div>
        ) : (
          <>
            {items.map(item => (
              <div
                key={item.itemId}
                data-testid="cart-item"
                data-item-id={item.itemId}
                style={{ background: '#fff', border: '1px solid #f1f5f9', borderRadius: '10px', padding: '1rem', marginBottom: '0.75rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
              >
                <div>
                  <div style={{ fontWeight: 600 }}>{item.name}</div>
                  <div style={{ color: '#64748b', fontSize: '0.875rem' }}>₺{item.price.toFixed(2)} / adet</div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <button data-testid="quantity-decrease" onClick={() => handleDecrease(item.itemId)}
                    style={{ width: '30px', height: '30px', borderRadius: '50%', border: '1px solid #cbd5e1', cursor: 'pointer', background: '#f8fafc', fontWeight: 700 }}>−</button>
                  <span data-testid="item-quantity" style={{ minWidth: '24px', textAlign: 'center', fontWeight: 700 }}>{item.quantity}</span>
                  <button data-testid="quantity-increase" onClick={() => handleIncrease(item.itemId)}
                    style={{ width: '30px', height: '30px', borderRadius: '50%', border: '1px solid #cbd5e1', cursor: 'pointer', background: '#f8fafc', fontWeight: 700 }}>+</button>
                  <button data-testid="remove-item" onClick={() => handleRemove(item.itemId)}
                    style={{ marginLeft: '0.5rem', background: '#fef2f2', border: 'none', color: '#dc2626', borderRadius: '6px', padding: '0.25rem 0.5rem', cursor: 'pointer' }}>✕</button>
                </div>
              </div>
            ))}

            <div style={{ background: '#fff', border: '1px solid #f1f5f9', borderRadius: '10px', padding: '1rem', marginTop: '1rem' }}>
              <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem' }}>
                <input
                  data-testid="coupon-input"
                  type="text"
                  placeholder="Kupon kodu"
                  value={coupon}
                  onChange={e => setCoupon(e.target.value)}
                  style={{ flex: 1, padding: '0.5rem 0.75rem', border: '1px solid #cbd5e1', borderRadius: '8px' }}
                />
                <button
                  data-testid="apply-coupon"
                  onClick={handleApplyCoupon}
                  style={{ padding: '0.5rem 1rem', background: '#334155', color: '#fff', border: 'none', borderRadius: '8px', cursor: 'pointer' }}
                >
                  Uygula
                </button>
              </div>
              {couponApplied && <p style={{ color: '#22c55e', fontSize: '0.875rem', marginBottom: '0.5rem' }}>Kupon uygulandı!</p>}
              <div style={{ display: 'flex', justifyContent: 'space-between', fontWeight: 700, fontSize: '1.1rem', marginBottom: '1rem' }}>
                <span>Toplam:</span>
                <span data-testid="cart-total">₺{total.toFixed(2)}</span>
              </div>
              <button
                data-testid="checkout-button"
                onClick={handleCheckout}
                disabled={items.length === 0}
                style={{ width: '100%', padding: '0.75rem', background: '#e63946', color: '#fff', border: 'none', borderRadius: '8px', fontWeight: 700, fontSize: '1rem', cursor: items.length === 0 ? 'not-allowed' : 'pointer', opacity: items.length === 0 ? 0.6 : 1 }}
              >
                Sipariş Ver
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
