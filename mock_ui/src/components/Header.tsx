import { useNavigate } from 'react-router-dom'

interface Props {
  cartCount?: number
}

export default function Header({ cartCount = 0 }: Props) {
  const navigate = useNavigate()

  function handleLogout() {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    navigate('/login')
  }

  return (
    <header style={{ background: '#e63946', color: '#fff', padding: '0.75rem 1.5rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
      <span style={{ fontWeight: 700, fontSize: '1.2rem', cursor: 'pointer' }} onClick={() => navigate('/')}>
        YemekTest Hub
      </span>
      <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
        <span
          data-testid="cart-badge"
          style={{ cursor: 'pointer', background: '#fff', color: '#e63946', borderRadius: '999px', padding: '0.2rem 0.7rem', fontWeight: 700 }}
          onClick={() => navigate('/cart')}
        >
          Sepet ({cartCount})
        </span>
        <button
          data-testid="logout-button"
          onClick={handleLogout}
          style={{ background: 'transparent', border: '1px solid #fff', color: '#fff', borderRadius: '6px', padding: '0.3rem 0.8rem', cursor: 'pointer' }}
        >
          Çıkış
        </button>
      </div>
    </header>
  )
}
