import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { setAccessToken } from '../api/client'
import styles from './Login.module.css'

export default function Login({ onLogin }) {
  const [senha, setSenha] = useState('')
  const [erro, setErro] = useState('')
  const [carregando, setCarregando] = useState(false)
  const navigate = useNavigate()

  async function handleSubmit(e) {
    e.preventDefault()
    setErro('')
    setCarregando(true)
    try {
      const resp = await fetch('/auth/login', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ senha }),
      })
      const data = await resp.json()
      if (!resp.ok) throw new Error(data.erro || 'Erro ao fazer login.')
      setAccessToken(data.access_token)
      onLogin()
      navigate('/')
    } catch (err) {
      setErro(err.message)
    } finally {
      setCarregando(false)
    }
  }

  return (
    <div className={styles.page}>
      <form className={styles.card} onSubmit={handleSubmit}>
        <div className={styles.icon}>⚙️</div>
        <h1 className={styles.title}>Motor MIMIC-IV</h1>
        <p className={styles.subtitle}>Painel Administrativo</p>

        <div className={styles.field}>
          <label className={styles.label}>Senha de administrador</label>
          <input
            type="password"
            className={styles.input}
            value={senha}
            onChange={e => setSenha(e.target.value)}
            placeholder="Digite a senha"
            autoFocus
            required
          />
        </div>

        {erro && <div className={styles.erro}>{erro}</div>}

        <button className={styles.btn} type="submit" disabled={carregando}>
          {carregando ? 'Entrando...' : 'Entrar'}
        </button>
      </form>
    </div>
  )
}
