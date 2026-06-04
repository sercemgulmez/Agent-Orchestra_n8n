import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import client from '../api/client'

export default function LoginPage() {
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    setLoading(true)
    try {
      const res = await client.post('/v2/user/login', { email, password })
      localStorage.setItem('token', res.data.token)
      localStorage.setItem('user', JSON.stringify({ id: res.data.userId, name: res.data.name }))
      navigate('/')
    } catch (err) {
      setError(err?.response?.data?.detail || 'Giris basarisiz. Bilgilerinizi kontrol edin.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div data-testid="login-page" style={{ minHeight: '100vh', display: 'grid', placeItems: 'center', background: '#f8fafc' }}>
      <form data-testid="login-form" onSubmit={handleSubmit} style={{ width: 360, maxWidth: '92vw', background: 'white', padding: 24, border: '1px solid #e5e7eb', borderRadius: 8 }}>
        <h1 style={{ color: '#e63946', textAlign: 'center' }}>YemekTest Hub</h1>
        <label>E-posta</label>
        <input data-testid="email-input" type="email" value={email} onChange={e => setEmail(e.target.value)} required style={{ width: '100%', padding: 10, margin: '6px 0 12px' }} />
        <label>Sifre</label>
        <input data-testid="password-input" type="password" value={password} onChange={e => setPassword(e.target.value)} required style={{ width: '100%', padding: 10, margin: '6px 0 12px' }} />
        {error && <div data-testid="error-message" style={{ color: '#b91c1c', marginBottom: 12 }}>{error}</div>}
        <button data-testid="login-button" type="submit" disabled={loading} style={{ width: '100%', padding: 12, background: '#e63946', color: 'white', border: 0, borderRadius: 6 }}>
          {loading ? 'Giris yapiliyor...' : 'Giris Yap'}
        </button>
        <a data-testid="forgot-password-link" href="#forgot-password" style={{ display: 'block', marginTop: 12, textAlign: 'center', color: '#64748b' }}>
          Sifremi unuttum
        </a>
      </form>
    </div>
  )
}
